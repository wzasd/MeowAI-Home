from dataclasses import dataclass
from typing import List, Literal, Optional
import re

IntentType = Literal["ideate", "execute"]
PromptTagType = Literal["critique"]

VALID_INTENTS = {"ideate", "execute"}
VALID_PROMPT_TAGS = {"critique"}
WORKFLOW_TAGS = {"brainstorm": "brainstorm", "parallel": "parallel", "autoplan": "auto_plan"}
TAG_PATTERN = re.compile(r"#(\w+)", re.IGNORECASE)


@dataclass
class IntentResult:
    """Intent 解析结果"""
    intent: IntentType
    explicit: bool  # 是否显式指定
    prompt_tags: List[PromptTagType]
    clean_message: str  # 移除标签后的消息
    workflow: Optional[str] = None


class IntentParser:
    """解析用户输入的 intent"""

    def parse(self, message: str, cat_count: int) -> IntentResult:
        """
        解析消息中的 intent

        Args:
            message: 用户输入
            cat_count: 涉及的猫数量

        Returns:
            IntentResult
        """
        tags = self._extract_tags(message)
        workflow = self._find_workflow_tag(tags)

        if not workflow and "@planner" in message.lower():
            workflow = "auto_plan"

        explicit_intent = self._find_explicit_intent(tags)

        if not workflow and not explicit_intent and cat_count >= 3:
            workflow = "brainstorm"

        if explicit_intent:
            intent = explicit_intent
            explicit = True
        else:
            # 自动推断: >=2猫 -> ideate, 1猫 -> execute
            intent = "ideate" if cat_count >= 2 else "execute"
            explicit = False

        prompt_tags = self._find_prompt_tags(tags)
        clean_message = self._strip_tags(message)

        return IntentResult(
            intent=intent,
            explicit=explicit,
            prompt_tags=prompt_tags,
            clean_message=clean_message,
            workflow=workflow,
        )

    def _extract_tags(self, message: str) -> List[str]:
        """提取所有 #标签"""
        return [match.group(1).lower() for match in TAG_PATTERN.finditer(message)]

    def _find_explicit_intent(self, tags: List[str]) -> Optional[IntentType]:
        """查找显式 intent"""
        for tag in tags:
            if tag in VALID_INTENTS:
                return tag  # type: ignore
        return None

    def _find_workflow_tag(self, tags: List[str]) -> Optional[str]:
        """查找 workflow 标签"""
        for tag in tags:
            if tag in WORKFLOW_TAGS:
                return WORKFLOW_TAGS[tag]
        return None

    def _find_prompt_tags(self, tags: List[str]) -> List[PromptTagType]:
        """查找 prompt tags"""
        return [tag for tag in tags if tag in VALID_PROMPT_TAGS]  # type: ignore

    def _strip_tags(self, message: str) -> str:
        """移除所有标签"""
        return TAG_PATTERN.sub("", message).strip()


def parse_intent(message: str, cat_count: int) -> IntentResult:
    """便捷函数"""
    return IntentParser().parse(message, cat_count)
