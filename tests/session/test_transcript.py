"""Tests for TranscriptWriter (B1)."""
import json
import os
import time
import pytest
from pathlib import Path

from src.session.transcript import TranscriptWriter, TranscriptEntry


@pytest.fixture
def transcript_dir(tmp_path):
    """Provide a temporary directory for transcripts."""
    return str(tmp_path / "transcripts")


@pytest.fixture
def writer(transcript_dir):
    return TranscriptWriter(base_dir=transcript_dir)


class TestTranscriptEntry:
    def test_entry_creation(self):
        entry = TranscriptEntry(
            role="user",
            content="hello",
            timestamp=time.time(),
        )
        assert entry.role == "user"
        assert entry.content == "hello"
        assert entry.tool_calls is None

    def test_entry_with_tool_calls(self):
        entry = TranscriptEntry(
            role="assistant",
            content="calling tool",
            timestamp=time.time(),
            tool_calls=[{"name": "read_file", "args": {"path": "/tmp/test"}}],
        )
        assert len(entry.tool_calls) == 1
        assert entry.tool_calls[0]["name"] == "read_file"


class TestTranscriptWriterAppend:
    def test_append_creates_file(self, writer, transcript_dir):
        writer.append("session-1", role="user", content="hello")
        session_dir = Path(transcript_dir) / "session-1"
        assert session_dir.exists()
        assert (session_dir / "events.jsonl").exists()

    def test_append_writes_ndjson(self, writer, transcript_dir):
        writer.append("session-1", role="user", content="hello")
        events_file = Path(transcript_dir) / "session-1" / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["role"] == "user"
        assert data["content"] == "hello"

    def test_append_multiple_entries(self, writer, transcript_dir):
        writer.append("session-1", role="user", content="msg1")
        writer.append("session-1", role="assistant", content="msg2")
        writer.append("session-1", role="user", content="msg3")
        events_file = Path(transcript_dir) / "session-1" / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_different_sessions_isolated(self, writer, transcript_dir):
        writer.append("session-a", role="user", content="a")
        writer.append("session-b", role="user", content="b")
        dir_a = Path(transcript_dir) / "session-a"
        dir_b = Path(transcript_dir) / "session-b"
        assert (dir_a / "events.jsonl").exists()
        assert (dir_b / "events.jsonl").exists()


class TestTranscriptIndex:
    def test_index_created_every_100_entries(self, writer, transcript_dir):
        # Append 150 entries
        for i in range(150):
            writer.append("session-1", role="user", content=f"msg{i}")

        index_file = Path(transcript_dir) / "session-1" / "index.json"
        assert index_file.exists()

        index = json.loads(index_file.read_text())
        # Should have entries at stride 100
        assert "offsets" in index
        assert len(index["offsets"]) >= 1  # At least one index entry

    def test_index_contains_correct_offsets(self, writer, transcript_dir):
        # Write 101 entries (index created after 100th, points to start of 101st)
        for i in range(101):
            writer.append("session-1", role="user", content=f"msg{i:04d}")

        index_file = Path(transcript_dir) / "session-1" / "index.json"
        index = json.loads(index_file.read_text())

        # Check offset points to correct position (start of 101st message)
        events_file = Path(transcript_dir) / "session-1" / "events.jsonl"
        with open(events_file, "rb") as f:
            f.seek(index["offsets"]["100"])
            line = f.readline().decode("utf-8")
            data = json.loads(line)
            assert data["content"] == "msg0100"  # 101st message (0-indexed)


class TestTranscriptDigest:
    def test_digest_extracts_tool_names(self, writer, transcript_dir):
        writer.append("session-1", role="assistant", content="result",
                     tool_calls=[{"name": "read_file"}, {"name": "write_file"}])
        writer.append("session-1", role="assistant", content="done")

        digest = writer.digest("session-1")
        assert "read_file" in digest["tool_names"]
        assert "write_file" in digest["tool_names"]

    def test_digest_extracts_file_paths(self, writer, transcript_dir):
        writer.append("session-1", role="user",
                     content="check /tmp/test.py and /home/user/main.py")
        writer.append("session-1", role="assistant", content="ok")

        digest = writer.digest("session-1")
        assert "/tmp/test.py" in digest["file_paths"]
        assert "/home/user/main.py" in digest["file_paths"]

    def test_digest_extracts_errors(self, writer, transcript_dir):
        writer.append("session-1", role="assistant",
                     content="Error: file not found")
        writer.append("session-1", role="assistant",
                     content="Success: done")

        digest = writer.digest("session-1")
        assert len(digest["errors"]) == 1
        assert "file not found" in digest["errors"][0]

    def test_digest_empty_session(self, writer):
        digest = writer.digest("session-empty")
        assert digest["tool_names"] == []
        assert digest["file_paths"] == []
        assert digest["errors"] == []

    def test_digest_counts(self, writer, transcript_dir):
        for i in range(5):
            writer.append("session-1", role="user", content=f"u{i}")
            writer.append("session-1", role="assistant", content=f"a{i}")

        digest = writer.digest("session-1")
        assert digest["message_count"] == 10
        assert digest["user_count"] == 5
        assert digest["assistant_count"] == 5


class TestTranscriptRead:
    def test_read_all_events(self, writer, transcript_dir):
        writer.append("session-1", role="user", content="hello")
        writer.append("session-1", role="assistant", content="hi")

        events = writer.read("session-1")
        assert len(events) == 2
        assert events[0]["role"] == "user"
        assert events[1]["role"] == "assistant"

    def test_read_with_limit(self, writer, transcript_dir):
        for i in range(10):
            writer.append("session-1", role="user", content=f"msg{i}")

        events = writer.read("session-1", limit=3)
        assert len(events) == 3
        assert events[0]["content"] == "msg7"  # Last 3

    def test_read_empty_session(self, writer):
        events = writer.read("session-nonexistent")
        assert events == []


class TestTranscriptPersistence:
    def test_persisted_data_survives_recreate(self, transcript_dir):
        writer1 = TranscriptWriter(base_dir=transcript_dir)
        writer1.append("session-1", role="user", content="hello")

        # Create new writer instance
        writer2 = TranscriptWriter(base_dir=transcript_dir)
        events = writer2.read("session-1")
        assert len(events) == 1
        assert events[0]["content"] == "hello"
