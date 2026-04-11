"""ReviewWatcher — GitHub PR webhook listener and event processor."""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Coroutine


class PREventType(str, Enum):
    """GitHub PR event types."""
    PR_OPENED = "pull_request_opened"
    PR_SYNCHRONIZE = "pull_request_synchronize"
    PR_CLOSED = "pull_request_closed"
    PR_MERGED = "pull_request_merged"
    REVIEW_SUBMITTED = "pull_request_review_submitted"
    REVIEW_REQUESTED = "pull_request_review_requested"
    COMMENT_CREATED = "pull_request_review_comment_created"


class PRStatus(str, Enum):
    """PR review status."""
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENTED = "commented"
    MERGED = "merged"
    CLOSED = "closed"


@dataclass
class PREvent:
    """A GitHub PR event."""
    event_type: PREventType
    pr_number: int
    pr_title: str
    pr_body: Optional[str]
    repository: str
    branch: str
    author: str
    changed_files: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    review_state: Optional[str] = None
    review_body: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    raw_payload: Optional[Dict[str, Any]] = None

    @property
    def is_new_pr(self) -> bool:
        """Check if this is a new PR."""
        return self.event_type == PREventType.PR_OPENED

    @property
    def is_update(self) -> bool:
        """Check if this is a PR update (new commits)."""
        return self.event_type == PREventType.PR_SYNCHRONIZE

    @property
    def needs_review(self) -> bool:
        """Check if this PR needs review."""
        return self.event_type in (
            PREventType.PR_OPENED,
            PREventType.PR_SYNCHRONIZE,
            PREventType.REVIEW_REQUESTED,
        )


@dataclass
class ReviewTracking:
    """Tracking information for a PR under review."""
    pr_number: int
    repository: str
    pr_title: str
    status: PRStatus
    assigned_cat_id: Optional[str]
    created_at: float
    updated_at: float
    last_event_type: Optional[PREventType] = None
    review_count: int = 0
    comments_count: int = 0


class ReviewWatcher:
    """Watches GitHub PR events and routes them for review."""

    def __init__(self, webhook_secret: Optional[str] = None):
        """Initialize the watcher.

        Args:
            webhook_secret: GitHub webhook secret for signature verification
        """
        self._webhook_secret = webhook_secret
        self._handlers: List[Callable[[PREvent], Coroutine]] = []
        self._tracking: Dict[str, ReviewTracking] = {}  # "repo#pr" -> tracking

    def add_handler(self, handler: Callable[[PREvent], Coroutine]) -> None:
        """Add an event handler."""
        self._handlers.append(handler)

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self._webhook_secret:
            # No secret configured, accept all (not recommended for production)
            return True

        if not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            self._webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature[7:], expected)

    def parse_event(self, event_type: str, payload: Dict[str, Any]) -> Optional[PREvent]:
        """Parse GitHub webhook payload into PREvent.

        Args:
            event_type: X-GitHub-Event header value
            payload: Parsed JSON payload

        Returns:
            PREvent or None if not a relevant event
        """
        if event_type == "pull_request":
            return self._parse_pr_event(payload)
        elif event_type == "pull_request_review":
            return self._parse_review_event(payload)
        elif event_type == "pull_request_review_comment":
            return self._parse_comment_event(payload)

        return None

    def _parse_pr_event(self, payload: Dict[str, Any]) -> Optional[PREvent]:
        """Parse pull request event."""
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})

        if action not in ("opened", "synchronize", "closed", "reopened"):
            return None

        # Map action to event type
        if action == "opened":
            event_type = PREventType.PR_OPENED
        elif action == "synchronize":
            event_type = PREventType.PR_SYNCHRONIZE
        elif action == "closed":
            if pr_data.get("merged"):
                event_type = PREventType.PR_MERGED
            else:
                event_type = PREventType.PR_CLOSED
        else:
            return None  # reopened not handled

        repo = payload.get("repository", {}).get("full_name", "unknown")

        # Get changed files (may need to fetch separately in real implementation)
        changed_files = self._extract_changed_files(pr_data)

        return PREvent(
            event_type=event_type,
            pr_number=pr_data.get("number", 0),
            pr_title=pr_data.get("title", ""),
            pr_body=pr_data.get("body"),
            repository=repo,
            branch=pr_data.get("head", {}).get("ref", ""),
            author=pr_data.get("user", {}).get("login", ""),
            changed_files=changed_files,
            labels=[l.get("name", "") for l in pr_data.get("labels", [])],
            reviewers=[r.get("login", "") for r in pr_data.get("requested_reviewers", [])],
            raw_payload=payload,
        )

    def _parse_review_event(self, payload: Dict[str, Any]) -> Optional[PREvent]:
        """Parse pull request review event."""
        action = payload.get("action")
        if action != "submitted":
            return None

        review = payload.get("review", {})
        pr_data = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "unknown")

        return PREvent(
            event_type=PREventType.REVIEW_SUBMITTED,
            pr_number=pr_data.get("number", 0),
            pr_title=pr_data.get("title", ""),
            pr_body=pr_data.get("body"),
            repository=repo,
            branch=pr_data.get("head", {}).get("ref", ""),
            author=review.get("user", {}).get("login", ""),
            changed_files=[],
            labels=[l.get("name", "") for l in pr_data.get("labels", [])],
            review_state=review.get("state"),
            review_body=review.get("body"),
            raw_payload=payload,
        )

    def _parse_comment_event(self, payload: Dict[str, Any]) -> Optional[PREvent]:
        """Parse pull request review comment event."""
        action = payload.get("action")
        if action != "created":
            return None

        comment = payload.get("comment", {})
        pr_data = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "unknown")

        return PREvent(
            event_type=PREventType.COMMENT_CREATED,
            pr_number=pr_data.get("number", 0),
            pr_title=pr_data.get("title", ""),
            pr_body=pr_data.get("body"),
            repository=repo,
            branch=pr_data.get("head", {}).get("ref", ""),
            author=comment.get("user", {}).get("login", ""),
            changed_files=[],
            review_body=comment.get("body"),
            raw_payload=payload,
        )

    def _extract_changed_files(self, pr_data: Dict[str, Any]) -> List[str]:
        """Extract list of changed files from PR data."""
        # In real implementation, this would fetch from GitHub API
        # For now, return empty list
        return []

    async def handle_webhook(self, event_type: str, payload: bytes, signature: Optional[str] = None) -> Dict[str, Any]:
        """Handle incoming webhook.

        Args:
            event_type: X-GitHub-Event header
            payload: Raw request body
            signature: X-Hub-Signature-256 header (optional)

        Returns:
            Dict with processing result
        """
        # Verify signature if configured
        if signature and not self.verify_signature(payload, signature):
            return {"status": "error", "message": "Invalid signature"}

        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON: {e}"}

        # Parse event
        event = self.parse_event(event_type, data)
        if not event:
            return {"status": "ignored", "message": "Event type not handled"}

        # Update tracking
        self._update_tracking(event)

        # Dispatch to handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                # Log error but continue with other handlers
                print(f"Handler error: {e}")

        return {
            "status": "processed",
            "event_type": event.event_type.value,
            "pr_number": event.pr_number,
            "repository": event.repository,
        }

    def _update_tracking(self, event: PREvent) -> None:
        """Update review tracking for the PR."""
        key = f"{event.repository}#{event.pr_number}"
        now = time.time()

        if key not in self._tracking:
            self._tracking[key] = ReviewTracking(
                pr_number=event.pr_number,
                repository=event.repository,
                pr_title=event.pr_title,
                status=PRStatus.PENDING,
                assigned_cat_id=None,
                created_at=now,
                updated_at=now,
            )

        tracking = self._tracking[key]
        tracking.updated_at = now
        tracking.last_event_type = event.event_type

        # Update status based on event
        if event.event_type == PREventType.REVIEW_SUBMITTED:
            tracking.review_count += 1
            if event.review_state == "approved":
                tracking.status = PRStatus.APPROVED
            elif event.review_state == "changes_requested":
                tracking.status = PRStatus.CHANGES_REQUESTED
            else:
                tracking.status = PRStatus.COMMENTED
        elif event.event_type == PREventType.PR_MERGED:
            tracking.status = PRStatus.MERGED
        elif event.event_type == PREventType.PR_CLOSED:
            tracking.status = PRStatus.CLOSED

    def get_tracking(self, repository: str, pr_number: int) -> Optional[ReviewTracking]:
        """Get tracking info for a PR."""
        key = f"{repository}#{pr_number}"
        return self._tracking.get(key)

    def list_pending_reviews(self) -> List[ReviewTracking]:
        """List all PRs pending review."""
        return [
            t for t in self._tracking.values()
            if t.status == PRStatus.PENDING
        ]

    def assign_reviewer(self, repository: str, pr_number: int, cat_id: str) -> bool:
        """Assign a cat as reviewer for a PR."""
        key = f"{repository}#{pr_number}"
        if key not in self._tracking:
            return False

        self._tracking[key].assigned_cat_id = cat_id
        return True

    def remove_tracking(self, repository: str, pr_number: int) -> bool:
        """Remove tracking for a PR."""
        key = f"{repository}#{pr_number}"
        if key in self._tracking:
            del self._tracking[key]
            return True
        return False
