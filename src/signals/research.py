"""Research report generator for signal articles — multi-cat collaborative analysis."""

import asyncio
from typing import List, Optional, Dict, Any

from src.models.agent_registry import AgentRegistry
from src.models.cat_registry import CatRegistry
from src.models.types import InvocationOptions


async def _call_provider(provider, prompt: str) -> str:
    """Call a single provider and collect its full text response."""
    try:
        parts = []
        async for msg in provider.invoke(prompt, InvocationOptions()):
            if msg.content:
                parts.append(msg.content)
        return "".join(parts)
    except Exception as e:
        return f"Error: {e}"


class ResearchGenerator:
    """Generate collaborative research reports from signal articles."""

    def __init__(self, cat_registry: CatRegistry, agent_registry: AgentRegistry):
        self.cat_registry = cat_registry
        self.agent_registry = agent_registry

    def _build_prompt(self, title: str, content: str, cat_name: str, role: str) -> str:
        return (
            f"你是一只擅长分析的猫咪，名字叫{cat_name}，角色是{role}。\n"
            f"请阅读下面的文章，并从你的专业角度给出 3-5 条核心见解。\n"
            f"要求：简明扼要，用中文回答，每条见解单独成段。\n\n"
            f"文章标题：《{title}》\n\n"
            f"文章内容：\n{content[:4000]}\n"
        )

    async def generate(self, title: str, content: str, cat_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a research report by dispatching to multiple cats."""
        if cat_ids is None:
            cat_ids = list(self.cat_registry.get_all_ids())

        tasks = []
        cats_info = []
        for cat_id in cat_ids:
            if not self.agent_registry.has(cat_id):
                continue
            cat_config = self.cat_registry.get(cat_id)
            provider = self.agent_registry.get(cat_id)
            prompt = self._build_prompt(
                title=title,
                content=content,
                cat_name=cat_config.display_name or cat_config.name or cat_id,
                role=cat_config.role_description or "研究员",
            )
            tasks.append(_call_provider(provider, prompt))
            cats_info.append({
                "cat_id": cat_id,
                "cat_name": cat_config.display_name or cat_config.name or cat_id,
                "role": cat_config.role_description or "研究员",
            })

        if not tasks:
            return {"title": title, "sections": [], "summary": "没有可用的研究员猫咪。"}

        results = await asyncio.gather(*tasks, return_exceptions=True)

        sections = []
        for info, result in zip(cats_info, results):
            if isinstance(result, Exception):
                text = f"生成失败: {result}"
            else:
                text = result.strip()
            sections.append({
                "cat_id": info["cat_id"],
                "cat_name": info["cat_name"],
                "role": info["role"],
                "content": text,
            })

        # Simple summary: concatenate all sections into markdown
        lines = [f"# 研究报告：{title}\n"]
        for sec in sections:
            lines.append(f"## {sec['cat_name']} ({sec['role']})\n")
            lines.append(f"{sec['content']}\n")

        return {
            "title": title,
            "sections": sections,
            "summary": "\n".join(lines),
        }
