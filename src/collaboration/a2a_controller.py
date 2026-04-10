import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator, Optional
from pathlib import Path

from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread
from src.collaboration.mcp_executor import MCPExecutor
from src.collaboration.skill_injector import SkillInjector
from src.models.types import AgentMessageType, InvocationOptions
from src.memory.entity_extractor import extract_entities
from src.governance.iron_laws import get_iron_laws_prompt
from src.evolution.scope_guard import ScopeGuard


@dataclass
class CatResponse:
    cat_id: str
    cat_name: str
    content: str
    targetCats: Optional[List[str]] = None
    thinking: Optional[str] = None


class A2AController:
    """A2A 协作控制器"""

    def __init__(self, agents: List[Dict[str, Any]], session_chain=None, dag_executor=None, template_factory=None, memory_service=None):
        self.agents = agents
        self.session_chain = session_chain
        self.dag_executor = dag_executor
        self.template_factory = template_factory
        self.memory_service = memory_service
        self.mcp_executor = MCPExecutor()
        self.skill_injector = SkillInjector()
        self.scope_guard = ScopeGuard(memory_service.episodic) if memory_service else None

        self.skill_router = None
        self.skill_loader = None
        manifest_path = Path("skills/manifest.yaml")
        if manifest_path.exists():
            try:
                from src.skills.router import ManifestRouter
                from src.skills.loader import SkillLoader
                self.skill_router = ManifestRouter(manifest_path)
                self.skill_loader = SkillLoader()
            except Exception:
                pass

    async def execute(
        self, intent: IntentResult, message: str, thread: Thread,
    ) -> AsyncIterator[CatResponse]:
        # Workflow path
        if intent.workflow and self.dag_executor and self.template_factory:
            from src.workflow.dag import NodeResult
            dag = self.template_factory.create(intent.workflow, self.agents, message)
            async for result in self.dag_executor.execute(dag, message, thread):
                yield CatResponse(
                    cat_id=result.cat_id,
                    cat_name=self._get_cat_name(result.cat_id),
                    content=result.content,
                    thinking=result.thinking,
                )
            return

        # Skill check
        active_skills = []
        if self.skill_router:
            active_skills = self.skill_router.route(message)

        if active_skills:
            skill_data = self._load_skill(active_skills[0]["skill_id"])
            if skill_data:
                self.skill_injector.inject(self.agents, active_skills[0]["skill_id"], skill_data["content"])
                try:
                    async for r in self._dispatch(intent, message, thread):
                        yield r
                finally:
                    self.skill_injector.restore(self.agents)
                return

        async for r in self._dispatch(intent, message, thread):
            yield r

    def _dispatch(self, intent: IntentResult, message: str, thread: Thread) -> AsyncIterator[CatResponse]:
        if intent.intent == "ideate":
            return self._parallel_ideate(message, thread)
        else:
            return self._serial_execute(message, thread)

    async def _parallel_ideate(self, message: str, thread: Thread) -> AsyncIterator[CatResponse]:
        tasks = [
            self._call_cat(a["service"], a["name"], a["breed_id"], message, thread)
            for a in self.agents
        ]
        for coro in asyncio.as_completed(tasks):
            response = await coro
            yield response

    async def _serial_execute(self, message: str, thread: Thread) -> AsyncIterator[CatResponse]:
        agent_queue = list(self.agents)
        executed_cats = set()

        while agent_queue:
            agent_info = agent_queue.pop(0)
            breed_id = agent_info["breed_id"]
            if breed_id in executed_cats:
                continue
            executed_cats.add(breed_id)

            context_msg = self._build_context(message, thread, len(executed_cats) - 1)
            response = await self._call_cat(
                agent_info["service"], agent_info["name"], breed_id, context_msg, thread
            )
            yield response

            thread.add_message("assistant", response.content, cat_id=breed_id)

            if response.targetCats:
                for target_cat in response.targetCats:
                    for agent in self.agents:
                        if agent["breed_id"] == target_cat and target_cat not in executed_cats:
                            agent_queue.append(agent)
                            break

    async def _call_cat(self, service, name: str, breed_id: str, message: str, thread: Thread) -> CatResponse:
        client = self.mcp_executor.register_tools(thread)
        system_prompt = get_iron_laws_prompt() + "\n\n" + service.build_system_prompt()

        if len(self.agents) > 1:
            other_cats = [a["name"] for a in self.agents if a["breed_id"] != breed_id]
            if other_cats:
                system_prompt += f"\n\n## 协作说明\n本次有多只猫参与：{', '.join(other_cats)}。请专注于你的角色，给出独立见解。"
                # Why-First protocol for multi-agent handoffs
                from src.evolution.why_first import build_handoff_prompt
                system_prompt += f"\n\n{build_handoff_prompt()}"

        system_prompt += self.mcp_executor.build_tools_prompt(client)

        # Auto-retrieve relevant memory
        if self.memory_service:
            memory_context = self.memory_service.build_context(
                query=message, thread_id=thread.id, max_items=5
            )
            if memory_context:
                system_prompt += f"\n\n## 相关记忆\n{memory_context}"

        # Scope guard: detect conversation drift
        if self.scope_guard:
            drift = self.scope_guard.check_drift(message, thread.id)
            if drift.is_drift:
                system_prompt += f"\n\n{self.scope_guard.build_drift_warning(drift)}"

        # Session chain
        session_id = None
        if self.session_chain:
            active = self.session_chain.get_active(breed_id, thread.id)
            if active:
                if self.session_chain.should_auto_seal(breed_id, thread.id):
                    self.session_chain.seal(breed_id, thread.id)
                else:
                    session_id = active.session_id

        options = InvocationOptions(system_prompt=system_prompt, session_id=session_id)
        chunks = []
        thinking_parts = []
        new_session_id = None

        async for msg in service.invoke(message, options):
            if msg.type == AgentMessageType.TEXT:
                chunks.append(msg.content)
            elif msg.type == AgentMessageType.THINKING:
                thinking_parts.append(msg.content)
            elif msg.type == AgentMessageType.DONE and msg.session_id:
                new_session_id = msg.session_id

        raw_content = "".join(chunks)
        parsed = await self.mcp_executor.execute_callbacks(raw_content, client, thread)

        if self.session_chain and new_session_id:
            self.session_chain.create(breed_id, thread.id, new_session_id)

        response = CatResponse(
            cat_id=breed_id, cat_name=name,
            content=parsed.clean_content,
            targetCats=parsed.targetCats if parsed.targetCats else None,
            thinking="".join(thinking_parts) if thinking_parts else None,
        )

        # Auto-store to episodic memory
        if self.memory_service:
            self.memory_service.store_episode(
                thread_id=thread.id, role="user",
                content=message, importance=3,
            )
            self.memory_service.store_episode(
                thread_id=thread.id, role="assistant",
                content=response.content, cat_id=breed_id,
                importance=5,
            )
            if response.thinking:
                self.memory_service.store_episode(
                    thread_id=thread.id, role="thinking",
                    content=response.thinking, cat_id=breed_id,
                    importance=2,
                )

        # Auto-extract entities to semantic memory
        if self.memory_service:
            combined = f"{message} {response.content}"
            entities = extract_entities(combined)
            for name, entity_type, description in entities:
                self.memory_service.semantic.add_entity(name, entity_type, description)

            # Auto-infer relations between extracted entities
            if len(entities) >= 2:
                from src.evolution.knowledge_evolution import _infer_relation_type
                for i in range(len(entities)):
                    for j in range(i + 1, len(entities)):
                        name_i, type_i = entities[i][0], entities[i][1]
                        name_j, type_j = entities[j][0], entities[j][1]
                        existing = self.memory_service.semantic.get_related(name_i, max_depth=1)
                        related_names = {r["name"] for r in existing}
                        if name_j not in related_names:
                            rel = _infer_relation_type(type_i, type_j)
                            self.memory_service.semantic.add_relation(name_i, name_j, rel)

        return response

    def _build_context(self, message: str, thread: Thread, current_index: int) -> str:
        if current_index == 0:
            return message
        parts = [message, "\n\n## 前面的回复"]
        for msg in thread.messages[-current_index:]:
            if msg.role == "assistant" and msg.cat_id:
                parts.append(f"\n{msg.cat_id}: {msg.content[:300]}...")
                # Try to extract Why-First handoff notes
                from src.evolution.why_first import parse_handoff_note, format_handoff_note
                note = parse_handoff_note(msg.content)
                if note:
                    parts.append(f"\n[结构化交接]: {format_handoff_note(note)}")
        parts.append("\n\n请继续完成或补充：")
        return "".join(parts)

    def _load_skill(self, skill_id: str) -> Optional[Dict]:
        if not self.skill_loader:
            return None
        try:
            skill_path = Path.home() / ".meowai" / "skills" / skill_id
            if skill_path.exists():
                return self.skill_loader.load_skill(skill_path)
        except Exception:
            pass
        return None

    def _get_cat_name(self, cat_id: str) -> str:
        for a in self.agents:
            if a["breed_id"] == cat_id:
                return a["name"]
        return cat_id
