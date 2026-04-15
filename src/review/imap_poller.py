"""IMAP poller for GitHub email notifications."""

import asyncio
import email
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Coroutine


@dataclass
class IMAPConfig:
    """IMAP server configuration."""
    host: str
    port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    folder: str = "INBOX"
    poll_interval: int = 300  # seconds


@dataclass
class GitHubEmailEvent:
    """Parsed GitHub notification email."""
    subject: str
    sender: str
    pr_number: Optional[int]
    repository: Optional[str]
    event_type: str  # e.g., "pull_request", "review_requested"
    body_text: str
    received_at: float


class IMAPPoller:
    """Polls IMAP inbox for GitHub notification emails."""

    def __init__(self, config: IMAPConfig):
        """Initialize the poller.

        Args:
            config: IMAP configuration
        """
        self._config = config
        self._handlers: List[Callable[[GitHubEmailEvent], Coroutine]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_poll: float = 0

    def add_handler(self, handler: Callable[[GitHubEmailEvent], Coroutine]) -> None:
        """Add an event handler."""
        self._handlers.append(handler)

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self.poll_once()
            except Exception as e:
                print(f"IMAP poll error: {e}")
            await asyncio.sleep(self._config.poll_interval)

    async def poll_once(self) -> List[GitHubEmailEvent]:
        """Perform a single poll.

        Returns:
            List of parsed GitHub email events
        """
        self._last_poll = time.time()
        events: List[GitHubEmailEvent] = []

        # Try to import imaplib (may not be available in all environments)
        try:
            import imaplib
        except ImportError:
            # imaplib is part of stdlib, but guard anyway
            return events

        try:
            if self._config.use_ssl:
                mail = imaplib.IMAP4_SSL(self._config.host, self._config.port)
            else:
                mail = imaplib.IMAP4(self._config.host, self._config.port)

            if self._config.username:
                mail.login(self._config.username, self._config.password)

            mail.select(self._config.folder)

            # Search for unread emails from GitHub
            status, messages = mail.search(None, '(UNSEEN FROM "notifications@github.com")')

            if status == "OK" and messages[0]:
                for num in messages[0].split():
                    status, data = mail.fetch(num, "(RFC822)")
                    if status == "OK" and data and data[0]:
                        raw_email = data[0][1]
                        event = self._parse_email(raw_email)
                        if event:
                            events.append(event)
                            for handler in self._handlers:
                                try:
                                    await handler(event)
                                except Exception as e:
                                    print(f"IMAP handler error: {e}")

            mail.close()
            mail.logout()
        except Exception as e:
            print(f"IMAP connection error: {e}")

        return events

    def _parse_email(self, raw_email: bytes) -> Optional[GitHubEmailEvent]:
        """Parse a raw email into a GitHubEmailEvent."""
        try:
            msg = email.message_from_bytes(raw_email)
        except Exception:
            return None

        subject = msg.get("Subject", "")
        sender = msg.get("From", "")

        # Only process GitHub notification emails
        if "github.com" not in sender.lower() and "notifications@github.com" not in sender.lower():
            return None

        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode("utf-8", errors="ignore")

        pr_number = self._extract_pr_number(subject, body_text)
        repository = self._extract_repository(subject, body_text)
        event_type = self._classify_event(subject)

        return GitHubEmailEvent(
            subject=subject,
            sender=sender,
            pr_number=pr_number,
            repository=repository,
            event_type=event_type,
            body_text=body_text[:2000],
            received_at=time.time(),
        )

    def _extract_pr_number(self, subject: str, body: str) -> Optional[int]:
        """Extract PR number from email content."""
        # Match patterns like "#123" or "PR #123"
        for text in (subject, body):
            match = re.search(r"#(\d+)", text)
            if match:
                return int(match.group(1))
        return None

    def _extract_repository(self, subject: str, body: str) -> Optional[str]:
        """Extract repository name from email content."""
        # Match patterns like "owner/repo" in body
        for text in (subject, body):
            match = re.search(r"([\w.-]+/[\w.-]+)", text)
            if match:
                return match.group(1)
        return None

    def _classify_event(self, subject: str) -> str:
        """Classify the event type from the subject line."""
        subject_lower = subject.lower()
        if "review requested" in subject_lower:
            return "review_requested"
        if "approved" in subject_lower:
            return "review_submitted"
        if "comment" in subject_lower:
            return "comment_created"
        if "merged" in subject_lower:
            return "pr_merged"
        if "closed" in subject_lower:
            return "pr_closed"
        return "pull_request"

    def get_status(self) -> Dict[str, Any]:
        """Get current poller status."""
        return {
            "running": self._running,
            "last_poll": self._last_poll,
            "config": {
                "host": self._config.host,
                "port": self._config.port,
                "folder": self._config.folder,
                "poll_interval": self._config.poll_interval,
            },
        }
