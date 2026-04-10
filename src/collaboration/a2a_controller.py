import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator, Optional
from pathlib import Path

from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread
from src.collaboration.mcp_executor import MCPExecutor
from src.collaboration.skill_injector import SkillInjector
from src.models.types import AgentMessageType, InvocationOptions


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
        system_prompt = service.build_system_prompt()

        if len(self.agents) > 1:
            other_cats = [a["name"] for a in self.agents if a["breed_id"] != breed_id]
            if other_cats:
                system_prompt += f"\n\n## 协作说明\n本次有多只猫参与：{', '.join(other_cats)}。请专注于你的角色，给出独立见解。"

        system_prompt += self.mcp_executor.build_tools_prompt(client)

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

        return CatResponse(
            cat_id=breed_id, cat_name=name,
            content=parsed.clean_content,
            targetCats=parsed.targetCats if parsed.targetCats else None,
            thinking="".join(thinking_parts) if thinking_parts else None,
        )

    def _build_context(self, message: str, thread: Thread, current_index: int) -> str:
        if current_index == 0:
            return message
        parts = [message, "\n\n## 前面的回复"]
        for msg in thread.messages[-current_index:]:
            if msg.role == "assistant" and msg.cat_id:
                parts.append(f"\n{msg.cat_id}: {msg.content[:200]}...")
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
