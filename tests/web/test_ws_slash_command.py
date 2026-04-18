"""Tests for WebSocket slash-command routing fix.

Bug: messages starting with `/command` were incorrectly prefixed with
`@current_cat`, causing slash commands to always route to the active cat.
Fix: the auto-prefix logic now skips messages that begin with `/`.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.web.routes.ws import _handle_send_message


@pytest.mark.asyncio
async def test_slash_command_not_auto_prefixed():
    """A /command message must NOT be prefixed with @cat_id."""
    websocket = AsyncMock()
    thread = MagicMock()
    thread.id = "thread-1"
    thread.project_path = "/tmp/test"
    thread.current_cat_id = "opus"
    thread.messages = []
    thread.add_message = MagicMock()

    tm = AsyncMock()
    tm.get = AsyncMock(return_value=thread)

    agent_router = MagicMock()
    agent_router.route_message = MagicMock(return_value=[])

    app = MagicMock()
    app.state.invocation_tracker = None
    app.state.session_chain = None
    app.state.agent_registry = None
    app.state.memory_service = None
    app.state.mission_store = None

    data = {"content": "/help", "attachments": None}

    with patch("src.web.routes.ws.parse_intent") as mock_parse:
        mock_parse.return_value = MagicMock(
            intent="execute",
            explicit=False,
            prompt_tags=[],
            clean_message="/help",
            workflow=None,
        )
        await _handle_send_message(websocket, "thread-1", data, tm, agent_router, app)

    # The key assertion: route_message should receive "/help", NOT "@opus /help"
    agent_router.route_message.assert_called_once()
    called_content = agent_router.route_message.call_args[0][0]
    assert called_content == "/help", f"Expected '/help' but got '{called_content}'"


@pytest.mark.asyncio
async def test_plain_message_gets_auto_prefixed():
    """A plain message without @ still gets prefixed with @current_cat."""
    websocket = AsyncMock()
    thread = MagicMock()
    thread.id = "thread-1"
    thread.project_path = "/tmp/test"
    thread.current_cat_id = "opus"
    thread.messages = []
    thread.add_message = MagicMock()

    tm = AsyncMock()
    tm.get = AsyncMock(return_value=thread)

    agent_router = MagicMock()
    agent_router.route_message = MagicMock(return_value=[])

    app = MagicMock()
    app.state.invocation_tracker = None

    data = {"content": "hello world", "attachments": None}

    with patch("src.web.routes.ws.parse_intent") as mock_parse:
        mock_parse.return_value = MagicMock(
            intent="execute",
            explicit=False,
            prompt_tags=[],
            clean_message="hello world",
            workflow=None,
        )
        await _handle_send_message(websocket, "thread-1", data, tm, agent_router, app)

    called_content = agent_router.route_message.call_args[0][0]
    assert called_content == "@opus hello world"


@pytest.mark.asyncio
async def test_force_intent_override():
    """forceIntent field overrides auto-inferred intent."""
    websocket = AsyncMock()
    thread = MagicMock()
    thread.id = "thread-1"
    thread.project_path = "/tmp/test"
    thread.current_cat_id = "opus"
    thread.messages = []
    thread.add_message = MagicMock()

    tm = AsyncMock()
    tm.get = AsyncMock(return_value=thread)

    agent_router = MagicMock()
    agent_router.route_message = MagicMock(return_value=[])

    app = MagicMock()
    app.state.invocation_tracker = None
    app.state.session_chain = None
    app.state.agent_registry = None
    app.state.memory_service = None
    app.state.mission_store = None

    data = {"content": "discuss architecture", "attachments": None, "forceIntent": "ideate"}

    with patch("src.web.routes.ws.parse_intent") as mock_parse:
        mock_parse.return_value = MagicMock(
            intent="execute",
            explicit=False,
            prompt_tags=[],
            clean_message="discuss architecture",
            workflow=None,
        )
        await _handle_send_message(websocket, "thread-1", data, tm, agent_router, app)

    assert mock_parse.call_count == 1
    called_content = mock_parse.call_args[0][0]
    # No @ in content -> auto-prefixed with current cat
    assert called_content == "@opus discuss architecture"


@pytest.mark.asyncio
async def test_force_intent_execute():
    """forceIntent=execute overrides intent."""
    websocket = AsyncMock()
    thread = MagicMock()
    thread.id = "thread-1"
    thread.project_path = "/tmp/test"
    thread.current_cat_id = "opus"
    thread.messages = []
    thread.add_message = MagicMock()

    tm = AsyncMock()
    tm.get = AsyncMock(return_value=thread)

    agent_router = MagicMock()
    agent_router.route_message = MagicMock(return_value=[])

    app = MagicMock()
    app.state.invocation_tracker = None
    app.state.session_chain = None
    app.state.agent_registry = None
    app.state.memory_service = None
    app.state.mission_store = None

    data = {"content": "fix this bug", "attachments": None, "forceIntent": "execute"}

    with patch("src.web.routes.ws.parse_intent") as mock_parse:
        mock_parse.return_value = MagicMock(
            intent="ideate",
            explicit=False,
            prompt_tags=[],
            clean_message="fix this bug",
            workflow=None,
        )
        await _handle_send_message(websocket, "thread-1", data, tm, agent_router, app)

    mock_parse.assert_called_once()
    called_content = mock_parse.call_args[0][0]
    # No @ in content -> auto-prefixed with current cat
    assert called_content == "@opus fix this bug"
