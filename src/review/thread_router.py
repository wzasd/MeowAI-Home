"""ThreadRouter — Route PR events to Threads."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.review.watcher import PREvent, PREventType
from src.thread.models import Message, Thread
from src.thread.thread_manager import ThreadManager


@dataclass
class ThreadRouteResult:
    """Result of routing a PR event to a thread."""
    thread_id: str
    thread_name: str
    created: bool  # True if thread was newly created
    message_count: int


class ThreadRouter:
    """Routes PR events to threads, creating threads when needed."""

    def __init__(self, thread_manager: ThreadManager):
        """Initialize with a thread manager.

        Args:
            thread_manager: Thread manager for creating/finding threads
        """
        self._tm = thread_manager
        # repo -> thread_id cache
        self._repo_thread_map: Dict[str, str] = {}

    async def route(self, event: PREvent) -> Optional[ThreadRouteResult]:
        """Route a PR event to a thread.

        Args:
            event: The PR event

        Returns:
            ThreadRouteResult or None if routing failed
        """
        repo = event.repository
        thread_id = self._repo_thread_map.get(repo)
        thread = None
        created = False

        if thread_id:
            thread = await self._tm.get(thread_id)

        if not thread:
            # Search for existing thread by repo name
            threads = await self._tm.list(include_archived=False)
            for t in threads:
                if repo in t.name or repo in t.project_path:
                    thread = t
                    break

        if not thread:
            # Create new thread for this repo
            thread = await self._tm.create(
                name=f"PR Review: {repo}",
                project_path=repo,
            )
            created = True

        self._repo_thread_map[repo] = thread.id

        # Build message content based on event type
        content = self._format_event_message(event)
        metadata = {
            "type": "pr_event",
            "event_type": event.event_type.value,
            "pr_number": event.pr_number,
            "repository": event.repository,
            "branch": event.branch,
        }

        message = Message(
            role="assistant",
            content=content,
            cat_id="system",
            metadata=metadata,
        )
        await self._tm.add_message(thread.id, message)

        return ThreadRouteResult(
            thread_id=thread.id,
            thread_name=thread.name,
            created=created,
            message_count=len(thread.messages),
        )

    def _format_event_message(self, event: PREvent) -> str:
        """Format a PR event as a thread message."""
        et = event.event_type

        if et == PREventType.PR_OPENED:
            lines = [
                f"🔔 新 PR  opened: #{event.pr_number} {event.pr_title}",
                f"仓库: {event.repository}",
                f"分支: {event.branch}",
                f"作者: {event.author}",
            ]
            if event.labels:
                lines.append(f"标签: {', '.join(event.labels)}")
            if event.reviewers:
                lines.append(f"请求审阅者: {', '.join(event.reviewers)}")
            if event.pr_body:
                lines.append(f"\n{event.pr_body[:500]}")
            return "\n".join(lines)

        if et == PREventType.PR_SYNCHRONIZE:
            return (
                f"📝 PR #{event.pr_number} 有更新提交\n"
                f"仓库: {event.repository}\n"
                f"分支: {event.branch}"
            )

        if et == PREventType.REVIEW_SUBMITTED:
            state = event.review_state or "reviewed"
            lines = [
                f"👀 PR #{event.pr_number} 收到新的 review: {state}",
                f"审阅者: {event.author}",
            ]
            if event.review_body:
                lines.append(f"\n{event.review_body[:500]}")
            return "\n".join(lines)

        if et == PREventType.REVIEW_REQUESTED:
            return (
                f"🙏 PR #{event.pr_number} 请求审阅\n"
                f"请求审阅者: {', '.join(event.reviewers)}"
            )

        if et == PREventType.COMMENT_CREATED:
            lines = [
                f"💬 PR #{event.pr_number} 收到新评论",
                f"作者: {event.author}",
            ]
            if event.review_body:
                lines.append(f"\n{event.review_body[:500]}")
            return "\n".join(lines)

        if et == PREventType.PR_MERGED:
            return f"✅ PR #{event.pr_number} 已合并到 {event.repository}"

        if et == PREventType.PR_CLOSED:
            return f"❌ PR #{event.pr_number} 已关闭"

        return f"PR #{event.pr_number} 事件: {et.value}"

    async def get_thread_for_repo(self, repository: str) -> Optional[Thread]:
        """Get the associated thread for a repository."""
        thread_id = self._repo_thread_map.get(repository)
        if thread_id:
            return await self._tm.get(thread_id)

        threads = await self._tm.list(include_archived=False)
        for t in threads:
            if repository in t.name or repository in t.project_path:
                self._repo_thread_map[repository] = t.id
                return t
        return None
