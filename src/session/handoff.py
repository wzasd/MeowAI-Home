"""HandoffDigest — generate structured summary for session handoff."""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DigestSection:
    title: str
    content: str


class HandoffDigest:
    """Generates structured digest from conversation history."""

    def __init__(self, max_chars: int = 16000):
        self._max_chars = max_chars

    def generate(
        self,
        messages: List[Dict[str, str]],
        invocation_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate digest from messages.

        Args:
            messages: List of {role, content} dicts
            invocation_summaries: Optional list of invocation summary strings

        Returns:
            Dict with decisions, open_questions, key_files, next_steps
        """
        # Collect all content
        all_content = []
        for msg in messages:
            content = msg.get("content", "")
            if content:
                all_content.append(content)

        full_text = "\n\n".join(all_content)

        # Cap at max_chars
        if len(full_text) > self._max_chars:
            full_text = full_text[-self._max_chars:]

        # Extract items
        decisions = self._extract_decisions(full_text)
        open_questions = self._extract_questions(full_text)
        key_files = self._extract_files(full_text)
        next_steps = self._extract_next_steps(full_text)

        result = {
            "decisions": decisions,
            "open_questions": open_questions,
            "key_files": key_files,
            "next_steps": next_steps,
        }

        if invocation_summaries:
            result["invocation_summary"] = "\n".join(invocation_summaries)

        return result

    def _extract_decisions(self, text: str) -> List[str]:
        """Extract decisions/agreements/conclusions."""
        decisions = []

        # Pattern: "decided to ...", "we decided..."
        patterns = [
            r"[Ww]e (?:decided|agreed)(?: on| to)?[:\s]+([^\.\n]+)",
            r"[Dd]ecision(?: is)?[:\s]+([^\.\n]+)",
            r"[Cc]onclusion[:\s]+([^\.\n]+)",
            r"[Aa]greed(?: on)?[:\s]+([^\.\n]+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                decision = match.group(1).strip()
                if decision and len(decision) > 5:
                    decisions.append(decision)

        return self._deduplicate(decisions)[:10]  # Cap at 10

    def _extract_questions(self, text: str) -> List[str]:
        """Extract open questions/todos."""
        questions = []

        # Direct questions
        for match in re.finditer(r"[^.\n]+\?", text):
            q = match.group(0).strip()
            if len(q) > 10:  # Filter out short fragments
                questions.append(q)

        # Pattern: TODO, OPEN, FIXME
        patterns = [
            r"(?:TODO|FIXME|XXX)[:\s]+([^\.\n]+)",
            r"[Oo]pen(?: question)?[:\s]+([^\.\n]+)",
            r"[Nn]eed to (?:figure out|decide|resolve)[:\s]+([^\.\n]+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                item = match.group(1).strip()
                if item:
                    questions.append(item)

        return self._deduplicate(questions)[:10]

    def _extract_files(self, text: str) -> List[str]:
        """Extract file paths mentioned."""
        files = []

        # Pattern: path/to/file.ext
        pattern = r"[\w\-/.]+\.(?:py|js|ts|jsx|tsx|json|yaml|yml|md|txt|sql|css|scss|html|xml|sh|rb|go|rs|java|kt|swift|c|cpp|h|hpp)\b"

        for match in re.finditer(pattern, text):
            path = match.group(0)
            # Filter out common false positives
            if not any(path.startswith(x) for x in ["http", "www", "com.", "org."]):
                files.append(path)

        return self._deduplicate(files)[:20]  # Cap at 20

    def _extract_next_steps(self, text: str) -> List[str]:
        """Extract action items and next steps."""
        steps = []

        patterns = [
            r"[Aa]ction (?:item|step)[:\s]+([^\.\n]+)",
            r"[Nn]ext step(?: is)?[:\s]+([^\.\n]+)",
            r"[Ff]ollow[- ]up[:\s]+([^\.\n]+)",
            r"[Ww]e (?:need|should) ([^\.\n]+)",
            r"[Ll]et['']?s ([^\.\n]+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                step = match.group(1).strip()
                if step and len(step) > 5:
                    steps.append(step)

        return self._deduplicate(steps)[:10]

    def _deduplicate(self, items: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        seen = set()
        result = []
        for item in items:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result
