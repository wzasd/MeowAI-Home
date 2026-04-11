"""ReviewRouter — Route PRs to appropriate reviewer cats."""

import fnmatch
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from src.review.watcher import PREvent, PREventType


@dataclass
class ReviewAssignment:
    """Assignment of a PR to a reviewer cat."""
    pr_number: int
    repository: str
    assigned_cat_id: str
    reason: str  # Why this cat was assigned
    confidence: float  # 0.0-1.0


class ReviewRouter:
    """Routes PRs to reviewer cats based on file paths and labels."""

    def __init__(self):
        """Initialize the router."""
        # File path patterns -> cat_id
        self._path_rules: Dict[str, str] = {}
        # Label patterns -> cat_id
        self._label_rules: Dict[str, str] = {}
        # Default reviewer
        self._default_reviewer: Optional[str] = None
        # Breed expertise mapping
        self._breed_expertise: Dict[str, List[str]] = {
            "orange": ["*.py", "backend/*", "api/*", "models/*"],
            "inky": ["*.js", "*.ts", "*.tsx", "frontend/*", "web/*", "ui/*"],
            "patch": ["*.md", "docs/*", "*.yaml", "*.yml", "config/*"],
        }

    def register_path_rule(self, pattern: str, cat_id: str) -> None:
        """Register a file path pattern rule.

        Args:
            pattern: Glob pattern for file paths (e.g., "*.py", "backend/*")
            cat_id: Cat ID to assign
        """
        self._path_rules[pattern] = cat_id

    def register_label_rule(self, pattern: str, cat_id: str) -> None:
        """Register a label pattern rule.

        Args:
            pattern: Label pattern (exact match or regex)
            cat_id: Cat ID to assign
        """
        self._label_rules[pattern] = cat_id

    def set_default_reviewer(self, cat_id: str) -> None:
        """Set default reviewer cat."""
        self._default_reviewer = cat_id

    def register_breed_expertise(self, breed: str, patterns: List[str]) -> None:
        """Register expertise patterns for a cat breed.

        Args:
            breed: Cat breed/ID
            patterns: List of file path patterns this breed handles
        """
        self._breed_expertise[breed] = patterns

    def route(self, event: PREvent) -> Optional[ReviewAssignment]:
        """Route a PR event to a reviewer cat.

        Args:
            event: The PR event

        Returns:
            ReviewAssignment or None if no match
        """
        if not event.needs_review:
            return None

        # Try label-based routing first (highest priority)
        label_match = self._match_by_labels(event.labels)
        if label_match:
            return ReviewAssignment(
                pr_number=event.pr_number,
                repository=event.repository,
                assigned_cat_id=label_match[0],
                reason=f"Matched label rule: {label_match[1]}",
                confidence=0.9,
            )

        # Try file path-based routing
        if event.changed_files:
            path_match = self._match_by_paths(event.changed_files)
            if path_match:
                return ReviewAssignment(
                    pr_number=event.pr_number,
                    repository=event.repository,
                    assigned_cat_id=path_match[0],
                    reason=f"Matched path rule: {path_match[1]}",
                    confidence=0.85,
                )

        # Try breed expertise routing
        if event.changed_files:
            breed_match = self._match_by_breed_expertise(event.changed_files)
            if breed_match:
                return ReviewAssignment(
                    pr_number=event.pr_number,
                    repository=event.repository,
                    assigned_cat_id=breed_match,
                    reason=f"Breed expertise match based on file types",
                    confidence=0.7,
                )

        # Fall back to default reviewer
        if self._default_reviewer:
            return ReviewAssignment(
                pr_number=event.pr_number,
                repository=event.repository,
                assigned_cat_id=self._default_reviewer,
                reason="Default reviewer",
                confidence=0.5,
            )

        return None

    def _match_by_labels(self, labels: List[str]) -> Optional[tuple]:
        """Match PR labels to reviewer rules.

        Returns:
            Tuple of (cat_id, matched_pattern) or None
        """
        for pattern, cat_id in self._label_rules.items():
            # Check exact match
            if pattern in labels:
                return (cat_id, pattern)

            # Check regex match
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                for label in labels:
                    if regex.search(label):
                        return (cat_id, pattern)
            except re.error:
                continue

        return None

    def _match_by_paths(self, files: List[str]) -> Optional[tuple]:
        """Match file paths to reviewer rules.

        Returns:
            Tuple of (cat_id, matched_pattern) or None
        """
        for pattern, cat_id in self._path_rules.items():
            for file_path in files:
                if fnmatch.fnmatch(file_path, pattern):
                    return (cat_id, pattern)

        return None

    def _match_by_breed_expertise(self, files: List[str]) -> Optional[str]:
        """Match files to cat breed expertise.

        Returns:
            Cat ID with best expertise match
        """
        breed_scores: Dict[str, int] = {}

        for breed, patterns in self._breed_expertise.items():
            score = 0
            for file_path in files:
                for pattern in patterns:
                    if fnmatch.fnmatch(file_path, pattern):
                        score += 1
                        break
            if score > 0:
                breed_scores[breed] = score

        if not breed_scores:
            return None

        # Return breed with highest score
        return max(breed_scores.items(), key=lambda x: x[1])[0]

    def get_suggested_reviewers(self, files: List[str]) -> List[tuple]:
        """Get suggested reviewers ranked by expertise match.

        Args:
            files: List of changed file paths

        Returns:
            List of (cat_id, score) tuples sorted by score
        """
        scores: Dict[str, int] = {}

        for breed, patterns in self._breed_expertise.items():
            score = 0
            for file_path in files:
                for pattern in patterns:
                    if fnmatch.fnmatch(file_path, pattern):
                        score += 1
                        break
            if score > 0:
                scores[breed] = score

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def explain_routing(self, event: PREvent) -> str:
        """Explain why a PR would be routed to a specific reviewer.

        Args:
            event: The PR event

        Returns:
            Human-readable explanation
        """
        lines = [f"PR #{event.pr_number}: {event.pr_title}"]

        if event.labels:
            lines.append(f"Labels: {', '.join(event.labels)}")

        if event.changed_files:
            lines.append(f"Changed files ({len(event.changed_files)}):")
            for f in event.changed_files[:10]:
                lines.append(f"  - {f}")
            if len(event.changed_files) > 10:
                lines.append(f"  ... and {len(event.changed_files) - 10} more")

        assignment = self.route(event)
        if assignment:
            lines.append(f"\nAssigned to: {assignment.assigned_cat_id}")
            lines.append(f"Reason: {assignment.reason}")
            lines.append(f"Confidence: {assignment.confidence:.0%}")
        else:
            lines.append("\nNo reviewer assigned (no matching rules)")

        return "\n".join(lines)


class ReviewRouterBuilder:
    """Builder for creating ReviewRouter with common configurations."""

    @staticmethod
    def create_default_router() -> ReviewRouter:
        """Create a router with sensible defaults."""
        router = ReviewRouter()

        # Register default expertise
        router.register_breed_expertise("orange", [
            "*.py", "backend/**/*.py", "api/**/*.py",
            "models/**/*.py", "src/**/*.py", "tests/**/*.py",
        ])

        router.register_breed_expertise("inky", [
            "*.js", "*.ts", "*.tsx", "*.jsx",
            "frontend/**/*", "web/**/*", "ui/**/*",
            "*.css", "*.scss", "*.less",
        ])

        router.register_breed_expertise("patch", [
            "*.md", "docs/**/*", "*.yaml", "*.yml",
            "*.json", "config/**/*", "docker*",
        ])

        # Label-based routing
        router.register_label_rule("backend", "orange")
        router.register_label_rule("frontend", "inky")
        router.register_label_rule("documentation", "patch")
        router.register_label_rule("bug", "orange")
        router.register_label_rule("feature", "inky")

        # Default reviewer
        router.set_default_reviewer("orange")

        return router
