"""Async background processor for post-response operations."""

import asyncio
from typing import Callable, Any, Coroutine, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class AsyncProcessor:
    """Processes tasks asynchronously in background without blocking response."""

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="async_proc_")
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self):
        """Initialize the processor."""
        self._loop = asyncio.get_event_loop()

    async def shutdown(self):
        """Gracefully shutdown the processor."""
        if self._executor:
            self._executor.shutdown(wait=True)

    def fire_and_forget(self, coro: Coroutine, name: str = "unnamed") -> None:
        """Execute a coroutine in background without awaiting result."""
        if not self._loop:
            logger.warning(f"AsyncProcessor not started, skipping {name}")
            return

        async def _wrapper():
            try:
                await coro
            except Exception as e:
                logger.debug(f"Background task {name} failed (non-critical): {e}")

        # Create task and let it run independently
        task = self._loop.create_task(_wrapper())
        # Don't hold reference - let GC clean up when done

    def run_in_thread(self, fn: Callable[..., Any], *args, name: str = "unnamed") -> None:
        """Run a blocking function in thread pool without blocking response."""
        if not self._loop or not self._executor:
            logger.warning(f"AsyncProcessor not started, skipping {name}")
            return

        def _wrapper():
            try:
                fn(*args)
            except Exception as e:
                logger.debug(f"Background thread {name} failed (non-critical): {e}")

        self._loop.run_in_executor(self._executor, _wrapper)


# Global instance
_processor: Optional[AsyncProcessor] = None


def get_processor() -> AsyncProcessor:
    """Get or create the global async processor."""
    global _processor
    if _processor is None:
        _processor = AsyncProcessor()
    return _processor


def init_processor() -> AsyncProcessor:
    """Initialize the global processor."""
    global _processor
    _processor = AsyncProcessor()
    return _processor
