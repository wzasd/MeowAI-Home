"""Tests for MCP Session Chain tools (C3)."""
import pytest
from unittest.mock import Mock, MagicMock

from src.mcp.tools.session_chain import (
    list_session_chain,
    read_session_events,
    read_session_digest,
    read_invocation_detail,
)


class TestListSessionChain:
    def test_list_sessions_for_thread(self):
        mock_manager = Mock()
        mock_manager.list_by_thread.return_value = [
            Mock(session_id="s1", cat_id="orange", status="active"),
            Mock(session_id="s2", cat_id="inky", status="sealed"),
        ]

        result = list_session_chain(thread_id="t1", manager=mock_manager)

        assert len(result["sessions"]) == 2
        assert result["sessions"][0]["session_id"] == "s1"

    def test_empty_thread(self):
        mock_manager = Mock()
        mock_manager.list_by_thread.return_value = []

        result = list_session_chain(thread_id="empty", manager=mock_manager)

        assert result["sessions"] == []


class TestReadSessionEvents:
    def test_read_all_views(self):
        mock_transcript = Mock()
        mock_transcript.read.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        # raw view
        result = read_session_events(
            session_id="s1",
            view="raw",
            transcript=mock_transcript,
        )
        assert len(result["events"]) == 2

        # chat view
        result = read_session_events(
            session_id="s1",
            view="chat",
            transcript=mock_transcript,
        )
        assert result["format"] == "chat"

    def test_with_limit(self):
        mock_transcript = Mock()
        mock_transcript.read.return_value = [
            {"role": "user", "content": f"msg{i}"} for i in range(10)
        ]

        result = read_session_events(
            session_id="s1",
            limit=5,
            transcript=mock_transcript,
        )

        mock_transcript.read.assert_called_with("s1", limit=5)


class TestReadSessionDigest:
    def test_read_digest(self):
        mock_transcript = Mock()
        mock_transcript.digest.return_value = {
            "tool_names": ["read_file", "write_file"],
            "file_paths": ["src/main.py"],
            "errors": [],
            "message_count": 10,
        }

        result = read_session_digest(session_id="s1", transcript=mock_transcript)

        assert "tool_names" in result
        assert "file_paths" in result
        assert result["message_count"] == 10


class TestReadInvocationDetail:
    def test_read_invocation(self):
        mock_record = Mock()
        mock_record.cat_id = "orange"
        mock_record.thread_id = "t1"
        mock_record.status = "completed"
        mock_record.started_at = 1000
        mock_record.completed_at = 2500
        mock_record.duration_ms = 1500

        mock_tracker = Mock()
        mock_tracker.get.return_value = mock_record

        result = read_invocation_detail(
            invocation_id="inv-123",
            tracker=mock_tracker,
        )

        assert result["invocation_id"] == "inv-123"
        assert result["cat_id"] == "orange"

    def test_invocation_not_found(self):
        mock_tracker = Mock()
        mock_tracker.get.return_value = None

        result = read_invocation_detail(
            invocation_id="inv-999",
            tracker=mock_tracker,
        )

        assert result is None
