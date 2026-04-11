"""AutoSummarizer — Generate thread summaries without LLM calls."""

import re
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ThreadSummary:
    """A summary of a thread conversation."""
    thread_id: str
    generated_at: float
    message_count: int
    conclusions: List[str]
    open_questions: List[str]
    key_files: List[str]
    next_steps: List[str]
    summary_text: str


class AutoSummarizer:
    """Generate thread summaries using pattern matching (no LLM)."""

    # Patterns for extracting conclusions
    CONCLUSION_PATTERNS = [
        re.compile(r"(?:^|\n)(?:结论|结论:|conclusion|conclusion:|最终决定|decided|decision):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:总结|summary):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:达成一致|agreed on|we agree):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:方案|solution|approach):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
    ]

    # Patterns for open questions
    QUESTION_PATTERNS = [
        re.compile(r"(?:^|\n)(?:待解决|open question|pending):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:问题|question):\s*(.+?)(?:\n|\?|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:需要确认|need to confirm|待确认):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
    ]

    # Patterns for next steps
    NEXT_STEP_PATTERNS = [
        re.compile(r"(?:^|\n)(?:下一步|next step|接下来):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:行动计划|action plan):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        re.compile(r"(?:^|\n)(?:后续|follow.up|TODO):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
    ]

    # File path patterns
    FILE_PATTERN = re.compile(
        r"(?:^|\s)([\w\-./]+\.(?:py|js|ts|jsx|tsx|java|go|rs|cpp|c|h|hpp|yaml|yml|json|md|txt|sh|sql))(?:\s|$)",
        re.IGNORECASE
    )

    def __init__(self, min_messages: int = 20, cooldown_seconds: float = 600.0):
        """Initialize summarizer.

        Args:
            min_messages: Minimum messages since last summary to trigger
            cooldown_seconds: Minimum time between summaries
        """
        self._min_messages = min_messages
        self._cooldown = cooldown_seconds
        self._last_summary: Dict[str, float] = {}  # thread_id -> timestamp
        self._last_message_count: Dict[str, int] = {}  # thread_id -> count

    def should_summarize(self, thread_id: str, current_message_count: int) -> bool:
        """Check if thread should be summarized.

        Args:
            thread_id: Thread ID
            current_message_count: Current number of messages

        Returns:
            True if summary should be generated
        """
        now = time.time()
        last_time = self._last_summary.get(thread_id, 0)
        last_count = self._last_message_count.get(thread_id, 0)

        # Check cooldown
        if now - last_time < self._cooldown:
            return False

        # Check message count threshold
        messages_since = current_message_count - last_count
        if messages_since < self._min_messages:
            return False

        return True

    def summarize(self, thread_id: str, messages: List[Dict[str, Any]]) -> Optional[ThreadSummary]:
        """Generate summary for thread.

        Args:
            thread_id: Thread ID
            messages: List of messages

        Returns:
            ThreadSummary or None if not enough data
        """
        if len(messages) < 5:
            return None

        if not self.should_summarize(thread_id, len(messages)):
            return None

        # Extract information
        conclusions = self._extract_conclusions(messages)
        open_questions = self._extract_open_questions(messages)
        key_files = self._extract_key_files(messages)
        next_steps = self._extract_next_steps(messages)

        # Generate summary text
        summary_text = self._generate_summary_text(
            len(messages),
            conclusions,
            open_questions,
            key_files,
            next_steps,
        )

        summary = ThreadSummary(
            thread_id=thread_id,
            generated_at=time.time(),
            message_count=len(messages),
            conclusions=conclusions,
            open_questions=open_questions,
            key_files=key_files,
            next_steps=next_steps,
            summary_text=summary_text,
        )

        # Update tracking
        self._last_summary[thread_id] = time.time()
        self._last_message_count[thread_id] = len(messages)

        return summary

    def _extract_conclusions(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract conclusions from messages."""
        conclusions = []

        for msg in messages:
            content = msg.get("content", "")
            for pattern in self.CONCLUSION_PATTERNS:
                for match in pattern.finditer(content):
                    conclusion = match.group(1).strip()
                    if conclusion and len(conclusion) > 5:
                        conclusions.append(conclusion)

        # Deduplicate and limit
        return self._deduplicate(conclusions)[:5]

    def _extract_open_questions(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract open questions from messages."""
        questions = []

        for msg in messages:
            content = msg.get("content", "")
            for pattern in self.QUESTION_PATTERNS:
                for match in pattern.finditer(content):
                    question = match.group(1).strip()
                    if question and len(question) > 5:
                        questions.append(question)

        # Also look for actual question marks
        for msg in messages:
            content = msg.get("content", "")
            # Find sentences ending with ?
            for match in re.finditer(r"[^.!?\n]+\?", content):
                question = match.group(0).strip()
                if len(question) > 10 and len(question) < 200:
                    questions.append(question)

        return self._deduplicate(questions)[:5]

    def _extract_key_files(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract file references from messages."""
        files = []

        for msg in messages:
            content = msg.get("content", "")
            for match in self.FILE_PATTERN.finditer(content):
                file_path = match.group(1)
                if file_path not in files:
                    files.append(file_path)

        return files[:10]

    def _extract_next_steps(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract next steps from messages."""
        steps = []

        for msg in messages:
            content = msg.get("content", "")
            for pattern in self.NEXT_STEP_PATTERNS:
                for match in pattern.finditer(content):
                    step = match.group(1).strip()
                    if step and len(step) > 5:
                        steps.append(step)

        return self._deduplicate(steps)[:5]

    def _generate_summary_text(
        self,
        message_count: int,
        conclusions: List[str],
        open_questions: List[str],
        key_files: List[str],
        next_steps: List[str],
    ) -> str:
        """Generate human-readable summary text."""
        lines = [f"本对话共 {message_count} 条消息。", ""]

        if conclusions:
            lines.append("## 结论")
            for c in conclusions:
                lines.append(f"- {c}")
            lines.append("")

        if open_questions:
            lines.append("## 待解决问题")
            for q in open_questions:
                lines.append(f"- {q}")
            lines.append("")

        if key_files:
            lines.append("## 涉及文件")
            for f in key_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if next_steps:
            lines.append("## 下一步行动")
            for s in next_steps:
                lines.append(f"- {s}")
            lines.append("")

        return "\n".join(lines)

    def _deduplicate(self, items: List[str]) -> List[str]:
        """Remove duplicate items while preserving order."""
        seen = set()
        result = []
        for item in items:
            normalized = item.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                result.append(item)
        return result

    def get_last_summary_time(self, thread_id: str) -> Optional[float]:
        """Get timestamp of last summary for thread."""
        return self._last_summary.get(thread_id)

    def reset(self, thread_id: Optional[str] = None) -> None:
        """Reset summary tracking."""
        if thread_id:
            self._last_summary.pop(thread_id, None)
            self._last_message_count.pop(thread_id, None)
        else:
            self._last_summary.clear()
            self._last_message_count.clear()
