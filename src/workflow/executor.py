import asyncio
from typing import AsyncIterator, Dict, List, Optional

from src.workflow.dag import DAGNode, NodeResult, WorkflowDAG
from src.thread.models import Thread
from src.models.types import AgentMessageType, InvocationOptions


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
                layer, node_map, input_text, completed_results, thread
            )
            for result in layer_results:
                completed_results[result.node_id] = result
                yield result

    async def _execute_layer(
        self,
        layer: List[str],
        node_map: Dict[str, DAGNode],
        input_text: str,
        completed_results: Dict[str, NodeResult],
        thread: Thread,
    ) -> List[NodeResult]:
        tasks = []
        for node_id in layer:
            node = node_map[node_id]
            tasks.append(self._execute_node(node, input_text, completed_results, thread))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                node = node_map[layer[i]]
                output.append(NodeResult(
                    node_id=node.id, cat_id=node.cat_id,
                    content="", status="failed", error=str(result),
                ))
            else:
                output.append(result)
        return output

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
