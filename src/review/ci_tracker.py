"""CI tracker — poll CI status for tracked PRs."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Coroutine


class CIStatus(str, Enum):
    """CI check status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CICheck:
    """A single CI check result."""
    name: str
    status: CIStatus
    conclusion: Optional[str] = None
    url: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class PRCIState:
    """CI state for a PR."""
    pr_number: int
    repository: str
    overall_status: CIStatus
    checks: List[CICheck] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


class CITracker:
    """Tracks CI status for pull requests."""

    def __init__(self, poll_interval: int = 60):
        """Initialize the tracker.

        Args:
            poll_interval: How often to poll CI status in seconds
        """
        self._poll_interval = poll_interval
        self._handlers: List[Callable[[PRCIState], Coroutine]] = []
        self._states: Dict[str, PRCIState] = {}  # "repo#pr" -> state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._github_token: Optional[str] = None

    def set_github_token(self, token: str) -> None:
        """Set GitHub API token for CI checks."""
        self._github_token = token

    def add_handler(self, handler: Callable[[PRCIState], Coroutine]) -> None:
        """Add a state change handler."""
        self._handlers.append(handler)

    def track_pr(self, repository: str, pr_number: int) -> None:
        """Start tracking a PR."""
        key = f"{repository}#{pr_number}"
        if key not in self._states:
            self._states[key] = PRCIState(
                pr_number=pr_number,
                repository=repository,
                overall_status=CIStatus.PENDING,
            )

    def untrack_pr(self, repository: str, pr_number: int) -> None:
        """Stop tracking a PR."""
        key = f"{repository}#{pr_number}"
        self._states.pop(key, None)

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
                await self.poll_all()
            except Exception as e:
                print(f"CI tracker poll error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def poll_all(self) -> List[PRCIState]:
        """Poll CI status for all tracked PRs.

        Returns:
            List of updated states
        """
        updated: List[PRCIState] = []
        for key, state in list(self._states.items()):
            new_state = await self._fetch_ci_status(state.repository, state.pr_number)
            if new_state:
                # Only notify if status changed
                if new_state.overall_status != state.overall_status:
                    self._states[key] = new_state
                    updated.append(new_state)
                    for handler in self._handlers:
                        try:
                            await handler(new_state)
                        except Exception as e:
                            print(f"CI handler error: {e}")
                else:
                    # Update checks even if overall didn't change
                    self._states[key] = new_state
        return updated

    async def _fetch_ci_status(self, repository: str, pr_number: int) -> Optional[PRCIState]:
        """Fetch CI status from GitHub API.

        In a real implementation, this would call the GitHub Checks API.
        For now, returns a simulated pending state.
        """
        import aiohttp

        headers = {"Accept": "application/vnd.github+json"}
        if self._github_token:
            headers["Authorization"] = f"Bearer {self._github_token}"

        url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

                    # Map state to our enum
                    state_str = data.get("state", "")
                    merged = data.get("merged", False)

                    if merged:
                        overall = CIStatus.SUCCESS
                    elif state_str == "closed":
                        overall = CIStatus.SKIPPED
                    else:
                        # For open PRs, we would check the checks API
                        # Simplified: assume pending if open
                        overall = CIStatus.PENDING

                    # Try to fetch check runs
                    checks_url = data.get("statuses_url")
                    checks: List[CICheck] = []

                    if checks_url:
                        async with session.get(checks_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as checks_resp:
                            if checks_resp.status == 200:
                                statuses = await checks_resp.json()
                                for status in statuses[:10]:
                                    status_map = {
                                        "success": CIStatus.SUCCESS,
                                        "failure": CIStatus.FAILURE,
                                        "error": CIStatus.ERROR,
                                        "pending": CIStatus.PENDING,
                                    }
                                    checks.append(CICheck(
                                        name=status.get("context", "Unknown"),
                                        status=status_map.get(status.get("state"), CIStatus.PENDING),
                                        conclusion=status.get("state"),
                                        url=status.get("target_url"),
                                    ))

                    return PRCIState(
                        pr_number=pr_number,
                        repository=repository,
                        overall_status=overall,
                        checks=checks,
                        updated_at=time.time(),
                    )
        except Exception as e:
            print(f"Failed to fetch CI status for {repository}#{pr_number}: {e}")
            return None

    def get_state(self, repository: str, pr_number: int) -> Optional[PRCIState]:
        """Get CI state for a PR."""
        key = f"{repository}#{pr_number}"
        return self._states.get(key)

    def list_tracked(self) -> List[PRCIState]:
        """List all tracked PR CI states."""
        return list(self._states.values())

    def get_status(self) -> Dict[str, Any]:
        """Get tracker status."""
        return {
            "running": self._running,
            "tracked_count": len(self._states),
            "poll_interval": self._poll_interval,
        }
