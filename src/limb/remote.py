"""RemoteLimbNode — HTTP proxy for remote device communication."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
import aiohttp


@dataclass
class HealthStatus:
    """Device health check result."""
    is_healthy: bool
    latency_ms: float
    last_check: float
    error: Optional[str] = None


class RemoteLimbNode:
    """HTTP client for communicating with remote limb devices.

    Features:
    - Async HTTP calls to device endpoints
    - Health check polling
    - Bearer token authentication
    - Connection pooling
    """

    def __init__(
        self,
        endpoint: str,
        auth_token: Optional[str] = None,
        health_check_interval: float = 60.0,
        timeout: float = 30.0,
    ):
        self._endpoint = endpoint.rstrip("/")
        self._auth_token = auth_token
        self._health_check_interval = health_check_interval
        self._timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_health: Optional[HealthStatus] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._status_callback: Optional[Callable[[bool], None]] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    async def invoke(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invoke an action on the remote device.

        Args:
            action: Action name
            params: Action parameters

        Returns:
            Response from device
        """
        session = await self._get_session()

        url = f"{self._endpoint}/invoke"
        payload = {
            "action": action,
            "params": params or {},
        }

        start_time = time.time()
        try:
            async with session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as response:
                response.raise_for_status()
                result = await response.json()

                # Update health on success
                self._last_health = HealthStatus(
                    is_healthy=True,
                    latency_ms=(time.time() - start_time) * 1000,
                    last_check=time.time(),
                )

                return result

        except asyncio.TimeoutError:
            self._last_health = HealthStatus(
                is_healthy=False,
                latency_ms=(time.time() - start_time) * 1000,
                last_check=time.time(),
                error="Request timeout",
            )
            raise

        except aiohttp.ClientError as e:
            self._last_health = HealthStatus(
                is_healthy=False,
                latency_ms=(time.time() - start_time) * 1000,
                last_check=time.time(),
                error=str(e),
            )
            raise

    async def health_check(self) -> HealthStatus:
        """Perform health check on device.

        Returns:
            HealthStatus
        """
        session = await self._get_session()

        url = f"{self._endpoint}/health"
        start_time = time.time()

        try:
            async with session.get(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()

                latency_ms = (time.time() - start_time) * 1000

                self._last_health = HealthStatus(
                    is_healthy=True,
                    latency_ms=latency_ms,
                    last_check=time.time(),
                )

                # Notify status change
                if self._status_callback:
                    self._status_callback(True)

                return self._last_health

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            self._last_health = HealthStatus(
                is_healthy=False,
                latency_ms=latency_ms,
                last_check=time.time(),
                error=str(e),
            )

            # Notify status change
            if self._status_callback:
                self._status_callback(False)

            return self._last_health

    async def start_health_polling(self, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Start periodic health check polling.

        Args:
            callback: Function to call on status change
        """
        self._status_callback = callback

        if self._health_check_task:
            self._health_check_task.cancel()

        self._health_check_task = asyncio.create_task(self._health_poll_loop())

    async def stop_health_polling(self) -> None:
        """Stop health check polling."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    async def _health_poll_loop(self) -> None:
        """Health check polling loop."""
        while True:
            try:
                await self.health_check()
            except Exception:
                pass  # Error already recorded in health status

            await asyncio.sleep(self._health_check_interval)

    def get_last_health(self) -> Optional[HealthStatus]:
        """Get last health check result."""
        return self._last_health

    def is_healthy(self) -> bool:
        """Check if device appears healthy."""
        if not self._last_health:
            return False
        return self._last_health.is_healthy

    async def get_info(self) -> Dict[str, Any]:
        """Get device information.

        Returns:
            Device info from /info endpoint
        """
        session = await self._get_session()

        url = f"{self._endpoint}/info"
        async with session.get(
            url,
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def close(self) -> None:
        """Close HTTP session."""
        await self.stop_health_polling()

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
