"""Skill chain execution for sequential skill activation"""
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChainContext:
    """Context for a running skill chain."""
    thread_id: str
    chain_id: str
    skills: List[str]           # Ordered list of skill names in chain
    current_index: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_skill(self) -> Optional[str]:
        """Get the current skill to execute."""
        if self.current_index < len(self.skills):
            return self.skills[self.current_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all skills in chain have been executed."""
        return self.current_index >= len(self.skills)

    def advance(self, result: Dict[str, Any]):
        """Move to next skill in chain, recording the result."""
        self.results.append(result)
        self.current_index += 1


class ChainTracker:
    """Tracks active skill chains across threads."""

    def __init__(self, max_depth: int = 5):
        self._chains: Dict[str, ChainContext] = {}  # thread_id -> ChainContext
        self.max_depth = max_depth

    def start_chain(self, thread_id: str, skills: List[str],
                    metadata: Dict[str, Any] = None) -> ChainContext:
        """Start a new skill chain for a thread.

        Raises:
            ValueError: If chain depth exceeds max_depth.
        """
        if len(skills) > self.max_depth:
            raise ValueError(f"Chain depth {len(skills)} exceeds max {self.max_depth}")

        chain = ChainContext(
            thread_id=thread_id,
            chain_id=str(uuid.uuid4())[:8],
            skills=skills,
            metadata=metadata or {},
        )
        self._chains[thread_id] = chain
        return chain

    def get_active(self, thread_id: str) -> Optional[ChainContext]:
        """Get the active chain for a thread if one exists and is not complete."""
        chain = self._chains.get(thread_id)
        if chain and not chain.is_complete:
            return chain
        return None

    def advance(self, thread_id: str, result: Dict[str, Any]) -> Optional[ChainContext]:
        """Advance the chain for a thread to next skill.

        Returns:
            Updated ChainContext, or None if no active chain.
        """
        chain = self._chains.get(thread_id)
        if chain and not chain.is_complete:
            chain.advance(result)
            if chain.is_complete:
                del self._chains[thread_id]
                return None
            return chain
        return None

    def cancel_chain(self, thread_id: str) -> bool:
        """Cancel the active chain for a thread.

        Returns:
            True if a chain was cancelled, False otherwise.
        """
        if thread_id in self._chains:
            del self._chains[thread_id]
            return True
        return False

    def list_active(self) -> List[str]:
        """List thread IDs with active chains."""
        return list(self._chains.keys())
