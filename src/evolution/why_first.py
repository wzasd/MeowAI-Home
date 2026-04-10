"""Why-First Protocol — structured handoff notes between agents"""
from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class HandoffNote:
    """5 要素交接笔记"""
    what: str           # 具体变更
    why: str            # 约束、目标、风险
    tradeoff: str       # 拒绝的方案
    open_questions: str # 未决定项
    next_action: str    # 接收者应该做什么


# Regex patterns for extracting 5 elements
_SECTION_PATTERNS = {
    "what": r'(?:##?\s*(?:What|变更|做了什么)[：:\s]*)(.*?)(?=##?\s*(?:Why|为什么|原因)|##?\s*(?:Tradeoff|权衡|拒绝)|##?\s*(?:Open|问题|未决)|##?\s*(?:Next|下一步|后续)|$)',
    "why": r'(?:##?\s*(?:Why|为什么|原因|背景)[：:\s]*)(.*?)(?=##?\s*(?:Tradeoff|权衡|拒绝)|##?\s*(?:Open|问题|未决)|##?\s*(?:Next|下一步|后续)|$)',
    "tradeoff": r'(?:##?\s*(?:Tradeoff|权衡|拒绝|备选)[：:\s]*)(.*?)(?=##?\s*(?:Open|问题|未决)|##?\s*(?:Next|下一步|后续)|$)',
    "open_questions": r'(?:##?\s*(?:Open\s*Questions?|问题|未决)[：:\s]*)(.*?)(?=##?\s*(?:Next|下一步|后续)|$)',
    "next_action": r'(?:##?\s*(?:Next\s*Action|下一步|后续)[：:\s]*)(.*)',
}


def parse_handoff_note(text: str) -> Optional[HandoffNote]:
    """从文本中解析 5 要素交接笔记"""
    sections = {}
    for key, pattern in _SECTION_PATTERNS.items():
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            sections[key] = match.group(1).strip()

    # Must have at least What + Why
    if not sections.get("what") or not sections.get("why"):
        return None

    return HandoffNote(
        what=sections["what"],
        why=sections["why"],
        tradeoff=sections.get("tradeoff", "无"),
        open_questions=sections.get("open_questions", "无"),
        next_action=sections.get("next_action", "无"),
    )


def build_handoff_prompt() -> str:
    """生成 Why-First 协议提示词，注入到系统提示中"""
    return (
        "## Why-First 交接协议\n"
        "当你将任务交给下一只猫时，必须按以下格式输出交接笔记：\n\n"
        "### What\n（具体做了什么变更）\n\n"
        "### Why\n（为什么这样做：约束、目标、风险）\n\n"
        "### Tradeoff\n（考虑过但拒绝的方案）\n\n"
        "### Open Questions\n（尚未决定的问题）\n\n"
        "### Next Action\n（下一只猫应该做什么）\n"
    )


def format_handoff_note(note: HandoffNote) -> str:
    """格式化交接笔记为可读文本"""
    parts = ["## 交接笔记"]
    if note.what:
        parts.append(f"### What\n{note.what}")
    if note.why:
        parts.append(f"### Why\n{note.why}")
    if note.tradeoff:
        parts.append(f"### Tradeoff\n{note.tradeoff}")
    if note.open_questions:
        parts.append(f"### Open Questions\n{note.open_questions}")
    if note.next_action:
        parts.append(f"### Next Action\n{note.next_action}")
    return "\n\n".join(parts)
