from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator, Optional
import asyncio

from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread, Message
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.collaboration.callback_parser import parse_callbacks


@dataclass
class CatResponse:
    """猫的响应"""
    cat_id: str
    cat_name: str
    content: str
    targetCats: Optional[List[str]] = None  # 新增：结构化路由


class A2AController:
    """A2A 协作控制器"""

    def __init__(self, agents: List[Dict[str, Any]]):
        """
        Args:
            agents: 来自 router.route_message() 的结果列表
        """
        self.agents = agents

    async def execute(
        self,
        intent: IntentResult,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """
        执行协作

        Args:
            intent: 解析后的 intent
            message: 用户消息（已清理标签）
            thread: 当前 thread

        Yields:
            CatResponse
        """
        if intent.intent == "ideate":
            async for response in self._parallel_ideate(message, thread):
                yield response
        else:  # execute
            async for response in self._serial_execute(message, thread):
                yield response

    async def _parallel_ideate(
        self,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """并行 ideate 模式 - 所有猫同时独立思考"""
        # 创建所有任务
        tasks = []
        for agent_info in self.agents:
            service = agent_info["service"]
            name = agent_info["name"]
            breed_id = agent_info["breed_id"]

            task = self._call_cat(service, name, breed_id, message, thread)
            tasks.append(task)

        # 并行执行，按完成顺序返回
        for coro in asyncio.as_completed(tasks):
            response = await coro
            yield response

    async def _serial_execute(
        self,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """串行 execute 模式 - 猫按顺序接力（支持 targetCats 路由）"""
        # 如果没有显式路由，使用 agents 顺序
        agent_queue = list(self.agents)  # 创建副本
        executed_cats = set()

        while agent_queue:
            agent_info = agent_queue.pop(0)
            service = agent_info["service"]
            name = agent_info["name"]
            breed_id = agent_info["breed_id"]

            # 跳过已执行的猫
            if breed_id in executed_cats:
                continue
            executed_cats.add(breed_id)

            # 构建提示
            context_msg = self._build_context(message, thread, len(executed_cats) - 1)

            response = await self._call_cat(
                service, name, breed_id, context_msg, thread
            )
            yield response

            # 添加到 thread
            thread.add_message("assistant", response.content, cat_id=breed_id)

            # 处理 targetCats 路由
            if response.targetCats:
                # 将指定的猫加入队列
                for target_cat in response.targetCats:
                    for agent in self.agents:
                        if agent["breed_id"] == target_cat and target_cat not in executed_cats:
                            agent_queue.append(agent)
                            break

    async def _call_cat(
        self,
        service,
        name: str,
        breed_id: str,
        message: str,
        thread: Thread
    ) -> CatResponse:
        """调用单只猫（支持 MCP 回调）"""
        # 1. 创建 MCPClient 并注册工具
        mcp_client = MCPClient(thread)
        for tool_name, config in TOOL_REGISTRY.items():
            mcp_client.register_tool(
                name=tool_name,
                description=config["description"],
                parameters=config["parameters"],
                handler=config["handler"]
            )

        # 2. 构建系统提示
        system_prompt = service.build_system_prompt()

        # 3. 添加协作上下文
        if len(self.agents) > 1:
            system_prompt += self._build_collaboration_context(breed_id)

        # 4. 添加 MCP 工具说明
        system_prompt += mcp_client.build_tools_prompt()

        # 5. 调用服务
        chunks = []
        async for chunk in service.chat_stream(message, system_prompt):
            chunks.append(chunk)

        raw_content = "".join(chunks)

        # 6. 解析回调
        parsed = parse_callbacks(raw_content)

        # 7. 执行工具调用
        for tool_call in parsed.tool_calls:
            # 跳过 targetCats（已解析）
            if tool_call.tool_name == "targetcats":
                continue
            await mcp_client.call(tool_call.tool_name, tool_call.params)

        # 8. 返回处理后的响应
        return CatResponse(
            cat_id=breed_id,
            cat_name=name,
            content=parsed.clean_content,
            targetCats=parsed.targetCats if parsed.targetCats else None
        )

    def _build_collaboration_context(self, current_cat_id: str) -> str:
        """构建协作上下文提示"""
        other_cats = [a["name"] for a in self.agents if a["breed_id"] != current_cat_id]

        if not other_cats:
            return ""

        return f"\n\n## 协作说明\n本次有多只猫参与：{', '.join(other_cats)}。请专注于你的角色，给出独立见解。"

    def _build_context(self, message: str, thread: Thread, current_index: int) -> str:
        """为串行模式构建上下文"""
        if current_index == 0:
            return message

        # 添加之前猫的回复作为上下文
        context_parts = [message, "\n\n## 前面的回复"]

        for msg in thread.messages[-current_index:]:
            if msg.role == "assistant" and msg.cat_id:
                context_parts.append(f"\n{msg.cat_id}: {msg.content[:200]}...")

        context_parts.append("\n\n请继续完成或补充：")
        return "".join(context_parts)
