import asyncio
import logging
import re
from typing import AsyncIterator, Dict, List, Optional

from src.workflow.dag import DAGNode, NodeResult, QualityGate, WorkflowDAG
from src.thread.models import Thread
from src.models.types import AgentMessageType, InvocationOptions

logger = logging.getLogger(__name__)


class DAGExecutor:
    def __init__(self, agent_registry, session_chain=None, tracker=None):
        self.agent_registry = agent_registry
        self.session_chain = session_chain
        self.tracker = tracker

    async def execute(
        self,
        dag: WorkflowDAG,
        input_text: str,
        thread: Thread,
    ) -> AsyncIterator[NodeResult]:
        errors = dag.validate()
        if errors:
            raise ValueError(f"DAG validation failed: {'; '.join(errors)}")

        layers = dag.topological_layers()
        node_map = {n.id: n for n in dag.nodes}
        completed_results: Dict[str, NodeResult] = {}

        for layer in layers:
            layer_results = await self._execute_layer(
                layer, node_map, dag, input_text, completed_results, thread
            )
            for result in layer_results:
                completed_results[result.node_id] = result
                yield result

    async def _execute_layer(
        self,
        layer: List[str],
        node_map: Dict[str, DAGNode],
        dag: WorkflowDAG,
        input_text: str,
        completed_results: Dict[str, NodeResult],
        thread: Thread,
    ) -> List[NodeResult]:
        tasks = []
        skipped = []
        for node_id in layer:
            node = node_map[node_id]
            # Phase 8.2: Check quality gate
            if not self._check_gate(node, dag, completed_results):
                skipped.append(node_id)
                tasks.append(None)
                continue
            tasks.append(self._execute_node(node, input_text, completed_results, thread))

        results = await asyncio.gather(
            *[t for t in tasks if t is not None], return_exceptions=True
        )

        output = []
        task_idx = 0
        for i, node_id in enumerate(layer):
            if node_id in skipped:
                node = node_map[node_id]
                output.append(NodeResult(
                    node_id=node.id, cat_id=node.cat_id,
                    content="", status="skipped",
                    error="Quality gate blocked",
                ))
                continue
            result = results[task_idx]
            task_idx += 1
            if isinstance(result, Exception):
                node = node_map[node_id]
                output.append(NodeResult(
                    node_id=node.id, cat_id=node.cat_id,
                    content="", status="failed", error=str(result),
                ))
            else:
                output.append(result)
        return output

    def _check_gate(
        self,
        node: DAGNode,
        dag: WorkflowDAG,
        completed_results: Dict[str, NodeResult],
    ) -> bool:
        """Check quality gate for a node based on predecessor results."""
        if node.gate is None:
            return True

        gate = node.gate
        predecessors = dag.predecessors(node.id)

        # Collect predecessor content
        pred_contents = []
        for pred_id in predecessors:
            if pred_id in completed_results:
                result = completed_results[pred_id]
                if result.status == "completed":
                    pred_contents.append(result.content)

        if not pred_contents:
            # No predecessors completed — gate passes (root nodes)
            return True

        combined = " ".join(pred_contents).lower()

        if gate.gate_type == "always":
            return True
        elif gate.gate_type == "test_exists":
            return "test_" in combined or "assert" in combined
        elif gate.gate_type == "test_pass":
            has_passed = "passed" in combined
            fail_match = re.search(r'(\d+)\s+failed', combined)
            has_real_failures = fail_match and int(fail_match.group(1)) > 0
            return has_passed and not has_real_failures
        elif gate.gate_type == "no_blocking":
            return "blocking" not in combined and "阻断" not in combined

        return True

    async def _execute_node(
        self,
        node: DAGNode,
        input_text: str,
        completed_results: Dict[str, NodeResult],
        thread: Thread,
    ) -> NodeResult:
        prev_results = self._collect_predecessor_results(node.id, completed_results)
        prompt = node.prompt_template.replace("{input}", input_text)
        prompt = prompt.replace("{prev_results}", prev_results)

        try:
            service = self.agent_registry.get(node.cat_id)
        except (KeyError, Exception) as e:
            return NodeResult(
                node_id=node.id, cat_id=node.cat_id,
                content="", status="failed", error=f"Agent not found: {node.cat_id}: {e}",
            )

        system_prompt = service.build_system_prompt()
        if node.role:
            system_prompt += f"\n你的角色：{node.role}"

        options = InvocationOptions(system_prompt=system_prompt)
        chunks = []
        thinking_parts = []
        session_id = None

        try:
            async for msg in service.invoke(prompt, options):
                if msg.type == AgentMessageType.TEXT:
                    chunks.append(msg.content)
                elif msg.type == AgentMessageType.THINKING:
                    thinking_parts.append(msg.content)
                elif msg.type == AgentMessageType.DONE:
                    if msg.session_id:
                        session_id = msg.session_id
                elif msg.type == AgentMessageType.ERROR:
                    return NodeResult(
                        node_id=node.id, cat_id=node.cat_id,
                        content="", status="failed", error=msg.content,
                    )
        except Exception as e:
            return NodeResult(
                node_id=node.id, cat_id=node.cat_id,
                content="", status="failed", error=str(e),
            )

        content = "".join(chunks)
        return NodeResult(
            node_id=node.id, cat_id=node.cat_id,
            content=content, status="completed",
            thinking="".join(thinking_parts) if thinking_parts else None,
        )

    def _collect_predecessor_results(
        self, node_id: str, completed_results: Dict[str, NodeResult],
    ) -> str:
        parts = []
        for nid, result in completed_results.items():
            if result.status == "completed":
                parts.append(f"[{result.cat_id} ({nid})]\n{result.content}")
        return "\n\n---\n\n".join(parts)
