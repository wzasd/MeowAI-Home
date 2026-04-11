"""Tests for RemoteLimbNode."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from src.limb.remote import RemoteLimbNode, HealthStatus


@pytest.fixture
def remote_node():
    """Create remote node for testing."""
    return RemoteLimbNode(
        endpoint="http://192.168.1.100:8080",
        auth_token="test-token",
        timeout=5.0,
    )


def create_mock_response(json_data=None, raise_error=None):
    """Helper to create mock response for async context manager."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    if raise_error:
        mock_response.raise_for_status.side_effect = raise_error

    async_mock = AsyncMock()
    async_mock.__aenter__ = AsyncMock(return_value=mock_response)
    async_mock.__aexit__ = AsyncMock(return_value=None)

    if json_data is not None:
        mock_response.json = AsyncMock(return_value=json_data)

    return async_mock


class TestRemoteLimbNodeInit:
    """Test RemoteLimbNode initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        node = RemoteLimbNode(endpoint="http://localhost:8080")

        assert node._endpoint == "http://localhost:8080"
        assert node._auth_token is None
        assert node._timeout == 30.0

    def test_init_with_auth(self):
        """Test initialization with auth token."""
        node = RemoteLimbNode(
            endpoint="http://localhost:8080",
            auth_token="bearer-token-123",
        )

        assert node._auth_token == "bearer-token-123"

    def test_init_strips_trailing_slash(self):
        """Test endpoint trailing slash is stripped."""
        node = RemoteLimbNode(endpoint="http://localhost:8080/")

        assert node._endpoint == "http://localhost:8080"

    def test_init_custom_timeout(self):
        """Test custom timeout setting."""
        node = RemoteLimbNode(
            endpoint="http://localhost:8080",
            timeout=10.0,
        )

        assert node._timeout == 10.0


class TestGetHeaders:
    """Test header generation."""

    def test_get_headers_without_auth(self):
        """Test headers without auth token."""
        node = RemoteLimbNode(endpoint="http://localhost:8080")
        headers = node._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_get_headers_with_auth(self):
        """Test headers with auth token."""
        node = RemoteLimbNode(
            endpoint="http://localhost:8080",
            auth_token="test-token",
        )
        headers = node._get_headers()

        assert headers["Authorization"] == "Bearer test-token"


class TestInvoke:
    """Test invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_success(self, remote_node):
        """Test successful invocation."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"status": "ok", "value": 42})

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            result = await remote_node.invoke("turn_on", {"brightness": 50})

        assert result["status"] == "ok"
        assert result["value"] == 42

    @pytest.mark.asyncio
    async def test_invoke_updates_health_on_success(self, remote_node):
        """Test health status updated on success."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"status": "ok"})

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            await remote_node.invoke("turn_on")

        health = remote_node.get_last_health()
        assert health is not None
        assert health.is_healthy is True

    @pytest.mark.asyncio
    async def test_invoke_updates_health_on_timeout(self, remote_node):
        """Test health status updated on timeout."""
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            with pytest.raises(asyncio.TimeoutError):
                await remote_node.invoke("turn_on")

        health = remote_node.get_last_health()
        assert health is not None
        assert health.is_healthy is False
        assert "timeout" in health.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_updates_health_on_client_error(self, remote_node):
        """Test health status updated on client error."""
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            with pytest.raises(aiohttp.ClientError):
                await remote_node.invoke("turn_on")

        health = remote_node.get_last_health()
        assert health is not None
        assert health.is_healthy is False


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, remote_node):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            health = await remote_node.health_check()

        assert health.is_healthy is True
        assert health.latency_ms >= 0
        assert health.error is None

    @pytest.mark.asyncio
    async def test_health_check_failure(self, remote_node):
        """Test failed health check."""
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            health = await remote_node.health_check()

        assert health.is_healthy is False
        assert health.error is not None

    @pytest.mark.asyncio
    async def test_health_check_callback_on_success(self, remote_node):
        """Test status callback triggered on success."""
        callback = MagicMock()
        remote_node._status_callback = callback

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            await remote_node.health_check()

        callback.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_health_check_callback_on_failure(self, remote_node):
        """Test status callback triggered on failure."""
        callback = MagicMock()
        remote_node._status_callback = callback

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            await remote_node.health_check()

        callback.assert_called_once_with(False)


class TestHealthPolling:
    """Test health polling loop."""

    @pytest.mark.asyncio
    async def test_start_health_polling(self, remote_node):
        """Test starting health polling."""
        callback = MagicMock()

        with patch.object(remote_node, '_health_poll_loop', AsyncMock()) as mock_loop:
            await remote_node.start_health_polling(callback)

        assert remote_node._status_callback == callback
        assert remote_node._health_check_task is not None

    @pytest.mark.asyncio
    async def test_stop_health_polling(self, remote_node):
        """Test stopping health polling."""
        # Create a real task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)

        remote_node._health_check_task = asyncio.create_task(dummy_task())

        await remote_node.stop_health_polling()

        assert remote_node._health_check_task is None


class TestGetInfo:
    """Test get_info method."""

    @pytest.mark.asyncio
    async def test_get_info(self, remote_node):
        """Test getting device info."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "name": "Smart Light",
            "capabilities": ["actuator"],
            "version": "1.0.0",
        })

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            info = await remote_node.get_info()

        assert info["name"] == "Smart Light"
        assert info["version"] == "1.0.0"


class TestHealthProperties:
    """Test health-related properties."""

    def test_get_last_health_none_initially(self, remote_node):
        """Test get_last_health returns None initially."""
        assert remote_node.get_last_health() is None

    def test_is_healthy_false_initially(self, remote_node):
        """Test is_healthy returns False initially."""
        assert remote_node.is_healthy() is False

    @pytest.mark.asyncio
    async def test_is_healthy_true_after_check(self, remote_node):
        """Test is_healthy returns True after successful check."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch.object(remote_node, '_get_session', AsyncMock(return_value=mock_session)):
            await remote_node.health_check()

        assert remote_node.is_healthy() is True


class TestClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_stops_polling(self, remote_node):
        """Test close stops health polling."""
        async def dummy_task():
            await asyncio.sleep(10)

        remote_node._health_check_task = asyncio.create_task(dummy_task())

        await remote_node.close()

        assert remote_node._health_check_task is None

    @pytest.mark.asyncio
    async def test_close_closes_session(self, remote_node):
        """Test close closes HTTP session."""
        mock_session = AsyncMock()
        mock_session.closed = False
        remote_node._session = mock_session

        await remote_node.close()

        mock_session.close.assert_called_once()
        assert remote_node._session is None
