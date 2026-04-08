from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class MCPResult:
    """MCP 工具调用结果"""
    success: bool
    tool_name: str
    data: Any
    error: Optional[str] = None


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable


class MCPClient:
    """MCP 回调客户端（轻量级本地实现）"""

    def __init__(self, thread=None):
        self.thread = thread
        self._tools: Dict[str, MCPTool] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ) -> None:
        """注册工具"""
        self._tools[name] = MCPTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )

    async def call(self, tool_name: str, params: Dict[str, Any]) -> MCPResult:
        """调用工具"""
        if tool_name not in self._tools:
            return MCPResult(
                success=False,
                tool_name=tool_name,
                data=None,
                error=f"Tool not found: {tool_name}"
            )

        tool = self._tools[tool_name]
        try:
            # 注入 thread 到参数（如果需要）
            if self.thread and "thread" not in params:
                result = await tool.handler(thread=self.thread, **params)
            else:
                result = await tool.handler(**params)
            return MCPResult(
                success=True,
                tool_name=tool_name,
                data=result
            )
        except Exception as e:
            return MCPResult(
                success=False,
                tool_name=tool_name,
                data=None,
                error=str(e)
            )

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self._tools.keys())

    def build_tools_prompt(self) -> str:
        """构建工具说明（注入系统提示）"""
        lines = ["\n## 可用工具\n"]
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        lines.append("\n使用格式:")
        lines.append("<mcp:工具名>")
        lines.append('{"参数": "值"}')
        lines.append("</mcp:工具名>")
        return "\n".join(lines)

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取工具定义"""
        return self._tools.get(name)
