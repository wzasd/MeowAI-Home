"""Tests for TaskExtractor."""

import pytest
from src.orchestration.task_extractor import TaskExtractor, ExtractedTask, TaskStatus


class TestTaskExtractor:
    """Test task extraction functionality."""

    @pytest.fixture
    def extractor(self):
        return TaskExtractor(use_llm=False)

    def test_extract_markdown_task(self, extractor):
        messages = [
            {"role": "assistant", "content": "- [ ] Fix the bug in login.py\n- [x] Update docs", "cat_id": "orange"}
        ]

        tasks = extractor.extract(messages)

        assert len(tasks) == 2
        assert tasks[0].title == "Fix the bug in login.py"
        assert tasks[0].status == TaskStatus.TODO
        assert tasks[1].title == "Update docs"
        assert tasks[1].status == TaskStatus.DONE

    def test_extract_todo_keyword(self, extractor):
        messages = [
            {"role": "assistant", "content": "TODO: Refactor the database module", "cat_id": "inky"}
        ]

        tasks = extractor.extract(messages)

        assert len(tasks) == 1
        assert tasks[0].title == "Refactor the database module"
        assert tasks[0].status == TaskStatus.TODO
        assert tasks[0].owner_cat_id == "inky"

    def test_extract_action_item(self, extractor):
        messages = [
            {"role": "assistant", "content": "Action Item: Review the PR by tomorrow", "cat_id": "patch"}
        ]

        tasks = extractor.extract(messages)

        assert len(tasks) == 1
        assert "Review the PR" in tasks[0].title

    def test_extract_task_tag(self, extractor):
        messages = [
            {"role": "assistant", "content": "#task Implement caching layer for better performance", "cat_id": "orange"}
        ]

        tasks = extractor.extract(messages)

        assert len(tasks) == 1
        assert "Implement caching layer" in tasks[0].title
        assert tasks[0].confidence == 0.9

    def test_empty_messages(self, extractor):
        tasks = extractor.extract([])
        assert tasks == []

    def test_no_tasks_in_message(self, extractor):
        messages = [
            {"role": "assistant", "content": "This is just a normal message without any tasks", "cat_id": "orange"}
        ]

        tasks = extractor.extract(messages)
        assert tasks == []
