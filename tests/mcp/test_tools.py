"""Tests for MCP core tools (C2)."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.mcp.tools import (
    post_message,
    get_thread_context,
    list_threads,
    create_rich_block,
    update_task,
    list_tasks,
    multi_mention,
    _invoke_cat_single,
)


class TestPostMessage:
    def test_post_message_success(self):
        mock_thread = Mock()
        mock_thread.add_message = Mock()

        result = post_message(
            thread=mock_thread,
            content="Hello world",
            role="assistant",
        )

        assert result["success"] is True
        mock_thread.add_message.assert_called_once()

    def test_post_message_with_metadata(self):
        mock_thread = Mock()

        result = post_message(
            thread=mock_thread,
            content="Hello",
            role="assistant",
            metadata={"cat_id": "orange", "skill": "tdd"},
        )

        assert result["success"] is True
        assert result["message_id"] is not None


class TestGetThreadContext:
    def test_get_context(self):
        mock_thread = Mock()
        mock_thread.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = get_thread_context(thread=mock_thread, limit=10)

        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"

    def test_get_context_with_limit(self):
        mock_thread = Mock()
        mock_thread.messages = [
            {"role": "user", "content": f"msg{i}"} for i in range(20)
        ]

        result = get_thread_context(thread=mock_thread, limit=5)

        assert len(result["messages"]) == 5
        # Should get most recent
        assert result["messages"][0]["content"] == "msg15"


class TestListThreads:
    def test_list_threads(self):
        mock_db = Mock()
        mock_db.execute.return_value.fetchall.return_value = [
            ("thread-1", "Test 1", 10),
            ("thread-2", "Test 2", 5),
        ]

        result = list_threads(db=mock_db)

        assert len(result["threads"]) == 2
        assert result["threads"][0]["id"] == "thread-1"

    def test_list_threads_with_filter(self):
        mock_db = Mock()
        mock_db.execute.return_value.fetchall.return_value = [
            ("thread-1", "Feature X", 10),
        ]

        result = list_threads(db=mock_db, filter="Feature")

        assert len(result["threads"]) == 1


class TestCreateRichBlock:
    def test_create_code_block(self):
        result = create_rich_block(
            block_type="code",
            content="print('hello')",
            language="python",
        )

        assert result["type"] == "code"
        assert result["content"] == "print('hello')"
        assert result["language"] == "python"

    def test_create_diff_block(self):
        result = create_rich_block(
            block_type="diff",
            content="+ added\n- removed",
            old_path="old.py",
            new_path="new.py",
        )

        assert result["type"] == "diff"
        assert result["old_path"] == "old.py"

    def test_create_checklist_block(self):
        result = create_rich_block(
            block_type="checklist",
            content="",  # content is required but not used for checklist
            items=[
                {"text": "Task 1", "checked": True},
                {"text": "Task 2", "checked": False},
            ],
        )

        assert result["type"] == "checklist"
        assert len(result["items"]) == 2
        assert result["items"][0]["checked"] is True


class TestUpdateTask:
    def test_create_task(self):
        mock_store = Mock()

        result = update_task(
            store=mock_store,
            title="Implement feature",
            status="todo",
        )

        assert result["success"] is True
        assert result["task_id"] is not None
        mock_store.create_task.assert_called_once()

    def test_update_task_status(self):
        mock_store = Mock()

        result = update_task(
            store=mock_store,
            task_id="task-123",
            status="doing",
        )

        assert result["success"] is True
        mock_store.update_task.assert_called_once_with("task-123", {"status": "doing"})

    def test_update_task_blocked(self):
        mock_store = Mock()

        result = update_task(
            store=mock_store,
            task_id="task-123",
            status="blocked",
            block_reason="Waiting for API",
        )

        assert result["success"] is True
        mock_store.update_task.assert_called_once()


class TestListTasks:
    def test_list_all_tasks(self):
        mock_store = Mock()
        mock_store.list_tasks.return_value = [
            {"id": "t1", "title": "Task 1", "status": "todo"},
            {"id": "t2", "title": "Task 2", "status": "doing"},
        ]

        result = list_tasks(store=mock_store)

        assert len(result["tasks"]) == 2

    def test_list_by_status(self):
        mock_store = Mock()
        mock_store.list_tasks.return_value = [
            {"id": "t1", "title": "Task 1", "status": "doing"},
        ]

        result = list_tasks(store=mock_store, status="doing")

        mock_store.list_tasks.assert_called_once()
        assert len(result["tasks"]) == 1


class TestMultiMention:
    @patch("src.mcp.tools._invoke_cat_single")
    def test_invoke_single_cat(self, mock_invoke):
        mock_invoke.return_value = {"cat_id": "orange", "response": "Hello"}

        result = multi_mention(
            cat_ids=["orange"],
            message="Help me",
        )

        assert len(result["responses"]) == 1
        mock_invoke.assert_called_once()

    @patch("src.mcp.tools._invoke_cat_single")
    def test_invoke_multiple_cats(self, mock_invoke):
        mock_invoke.side_effect = [
            {"cat_id": "orange", "response": "From orange"},
            {"cat_id": "inky", "response": "From inky"},
        ]

        result = multi_mention(
            cat_ids=["orange", "inky"],
            message="Review this",
        )

        assert len(result["responses"]) == 2
        assert mock_invoke.call_count == 2

    def test_max_three_cats(self):
        with pytest.raises(ValueError):
            multi_mention(
                cat_ids=["orange", "inky", "patch", "extra"],
                message="Too many",
            )
