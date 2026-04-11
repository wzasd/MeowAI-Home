"""TaskExtractor — Extract actionable tasks from messages."""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    BLOCKED = "blocked"
    DONE = "done"


@dataclass
class ExtractedTask:
    """An extracted task from conversation."""
    title: str
    why: str  # Context/reason for the task
    owner_cat_id: Optional[str]  # Assigned cat, None if unassigned
    status: TaskStatus
    source_message: str  # Original message excerpt
    confidence: float  # 0.0-1.0, extraction confidence
    extracted_by: str  # "llm" or "pattern"


class TaskExtractor:
    """Extract tasks from conversation messages."""

    # Pattern-based extraction patterns
    PATTERNS = {
        "markdown_task": re.compile(r"- \[([ x])\] (.+?)(?:\n|$)", re.IGNORECASE),
        "todo_keyword": re.compile(r"(?:^|\n)(?:TODO|FIXME|HACK):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        "action_item": re.compile(r"(?:^|\n)(?:Action Item|行动项):?\s*(.+?)(?:\n|$)", re.IGNORECASE),
        "task_tag": re.compile(r"#task\s+(.+?)(?:\n|$)", re.IGNORECASE),
        "assigned_task": re.compile(
            r"(?:@(\w+)\s+)?(.+?)(?:\s+\(?(?:due|截止|by)\s*:?\s*(.+?)\)?)?(?:\n|$)",
            re.IGNORECASE
        ),
    }

    # Cat mention patterns
    CAT_MENTIONS = {
        "orange": ["@orange", "@阿橘", "阿橘"],
        "inky": ["@inky", "@墨点", "墨点"],
        "patch": ["@patch", "@花花", "花花"],
    }

    def __init__(self, use_llm: bool = False, llm_client=None):
        """Initialize extractor.

        Args:
            use_llm: Whether to use LLM for extraction
            llm_client: LLM client for extraction (if use_llm=True)
        """
        self._use_llm = use_llm
        self._llm_client = llm_client

    def extract(self, messages: List[Dict[str, Any]]) -> List[ExtractedTask]:
        """Extract tasks from messages.

        Args:
            messages: List of message dicts with 'role', 'content', 'cat_id'

        Returns:
            List of extracted tasks
        """
        tasks = []

        # Try LLM extraction if enabled
        if self._use_llm and self._llm_client:
            llm_tasks = self._extract_with_llm(messages)
            tasks.extend(llm_tasks)

        # Always do pattern extraction as fallback/supplement
        pattern_tasks = self._extract_with_patterns(messages)
        tasks.extend(pattern_tasks)

        # Deduplicate by title similarity
        return self._deduplicate(tasks)

    def _extract_with_llm(self, messages: List[Dict[str, Any]]) -> List[ExtractedTask]:
        """Extract tasks using LLM."""
        # TODO: Implement LLM extraction when llm_client is available
        # For now, return empty list
        return []

    def _extract_with_patterns(self, messages: List[Dict[str, Any]]) -> List[ExtractedTask]:
        """Extract tasks using pattern matching."""
        tasks = []

        for msg in messages:
            content = msg.get("content", "")
            if not content:
                continue

            # Extract markdown tasks: - [ ] task
            for match in self.PATTERNS["markdown_task"].finditer(content):
                checked = match.group(1).lower() == "x"
                title = match.group(2).strip()

                # Try to find owner from context
                owner = self._extract_owner(content, msg.get("cat_id"))

                tasks.append(ExtractedTask(
                    title=title,
                    why="From task list",
                    owner_cat_id=owner,
                    status=TaskStatus.DONE if checked else TaskStatus.TODO,
                    source_message=content[:200],
                    confidence=0.9 if checked else 0.8,
                    extracted_by="pattern",
                ))

            # Extract TODO/FIXME keywords
            for match in self.PATTERNS["todo_keyword"].finditer(content):
                title = match.group(1).strip()
                owner = self._extract_owner(content, msg.get("cat_id"))

                tasks.append(ExtractedTask(
                    title=title,
                    why="Marked as TODO",
                    owner_cat_id=owner,
                    status=TaskStatus.TODO,
                    source_message=content[:200],
                    confidence=0.7,
                    extracted_by="pattern",
                ))

            # Extract Action Items
            for match in self.PATTERNS["action_item"].finditer(content):
                title = match.group(1).strip()
                owner = self._extract_owner(content, msg.get("cat_id"))

                tasks.append(ExtractedTask(
                    title=title,
                    why="Action item from discussion",
                    owner_cat_id=owner,
                    status=TaskStatus.TODO,
                    source_message=content[:200],
                    confidence=0.85,
                    extracted_by="pattern",
                ))

            # Extract #task tags
            for match in self.PATTERNS["task_tag"].finditer(content):
                title = match.group(1).strip()
                owner = self._extract_owner(content, msg.get("cat_id"))

                tasks.append(ExtractedTask(
                    title=title,
                    why="Tagged as #task",
                    owner_cat_id=owner,
                    status=TaskStatus.TODO,
                    source_message=content[:200],
                    confidence=0.9,
                    extracted_by="pattern",
                ))

        return tasks

    def _extract_owner(self, content: str, default_cat_id: Optional[str]) -> Optional[str]:
        """Extract task owner from content."""
        content_lower = content.lower()

        for cat_id, mentions in self.CAT_MENTIONS.items():
            for mention in mentions:
                if mention.lower() in content_lower:
                    return cat_id

        return default_cat_id

    def _deduplicate(self, tasks: List[ExtractedTask]) -> List[ExtractedTask]:
        """Remove duplicate tasks based on title similarity."""
        seen_titles: Dict[str, ExtractedTask] = {}

        for task in tasks:
            # Normalize title for comparison
            normalized = self._normalize_title(task.title)

            if normalized in seen_titles:
                # Keep higher confidence one
                if task.confidence > seen_titles[normalized].confidence:
                    seen_titles[normalized] = task
            else:
                seen_titles[normalized] = task

        return list(seen_titles.values())

    def _normalize_title(self, title: str) -> str:
        """Normalize title for deduplication."""
        # Remove punctuation, lowercase, strip whitespace
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        return ' '.join(normalized.split())

    def get_tasks_by_status(self, tasks: List[ExtractedTask], status: TaskStatus) -> List[ExtractedTask]:
        """Filter tasks by status."""
        return [t for t in tasks if t.status == status]

    def get_tasks_by_owner(self, tasks: List[ExtractedTask], cat_id: str) -> List[ExtractedTask]:
        """Filter tasks by owner."""
        return [t for t in tasks if t.owner_cat_id == cat_id]

    def format_task_list(self, tasks: List[ExtractedTask]) -> str:
        """Format tasks as markdown list."""
        if not tasks:
            return "暂无任务"

        lines = []
        for task in tasks:
            checkbox = "[x]" if task.status == TaskStatus.DONE else "[ ]"
            owner = f" @{task.owner_cat_id}" if task.owner_cat_id else ""
            lines.append(f"- {checkbox} {task.title}{owner}")

        return "\n".join(lines)
