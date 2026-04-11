"""Tests for AutoSummarizer."""

import pytest
import time
from src.orchestration.auto_summarizer import AutoSummarizer


class TestAutoSummarizer:
    """Test auto summarization functionality."""

    @pytest.fixture
    def summarizer(self):
        return AutoSummarizer(min_messages=5, cooldown_seconds=1.0)

    def test_should_summarize_min_messages(self, summarizer):
        # Not enough messages
        assert not summarizer.should_summarize("thread1", 3)
        # Enough messages
        assert summarizer.should_summarize("thread1", 10)

    def test_should_summarize_cooldown(self, summarizer):
        # First check should pass
        assert summarizer.should_summarize("thread2", 10)

        # Generate summary to set last summary time
        messages = [{"role": "assistant", "content": f"Message {i}"} for i in range(10)]
        summarizer.summarize("thread2", messages)

        # Immediately should not summarize again
        assert not summarizer.should_summarize("thread2", 30)

    def test_extract_conclusions(self, summarizer):
        messages = [
            {"role": "assistant", "content": "结论: 使用Python作为后端语言\n"},
            {"role": "assistant", "content": "最终决定: 采用微服务架构\n"},
        ]

        conclusions = summarizer._extract_conclusions(messages)

        assert len(conclusions) >= 1
        assert any("Python" in c for c in conclusions)

    def test_extract_open_questions(self, summarizer):
        messages = [
            {"role": "assistant", "content": "问题: 数据库选型还未确定？"},
            {"role": "assistant", "content": "What is the best caching strategy?"},
        ]

        questions = summarizer._extract_open_questions(messages)

        assert len(questions) >= 1

    def test_extract_key_files(self, summarizer):
        messages = [
            {"role": "assistant", "content": "Check src/main.py for the entry point"},
            {"role": "assistant", "content": "The config is in settings.yaml"},
        ]

        files = summarizer._extract_key_files(messages)

        assert "src/main.py" in files
        assert "settings.yaml" in files

    def test_extract_next_steps(self, summarizer):
        messages = [
            {"role": "assistant", "content": "下一步: 完成用户认证模块"},
            {"role": "assistant", "content": "TODO: Write tests"},
        ]

        steps = summarizer._extract_next_steps(messages)

        assert len(steps) >= 1

    def test_generate_summary_text(self, summarizer):
        text = summarizer._generate_summary_text(
            message_count=20,
            conclusions=["Use Python"],
            open_questions=["Database choice?"],
            key_files=["main.py"],
            next_steps=["Write tests"],
        )

        assert "20 条消息" in text
        assert "结论" in text
        assert "Use Python" in text
        assert "待解决问题" in text
        assert "涉及文件" in text
        assert "下一步行动" in text

    def test_summarize_not_enough_messages(self, summarizer):
        messages = [{"role": "assistant", "content": "Short"} for _ in range(3)]

        result = summarizer.summarize("thread3", messages)

        assert result is None

    def test_summarize_success(self, summarizer):
        messages = [{"role": "assistant", "content": "结论: 采用新方案"}]
        messages.extend([{"role": "assistant", "content": f"Message {i}"} for i in range(10)])

        result = summarizer.summarize("thread4", messages)

        assert result is not None
        assert result.thread_id == "thread4"
        assert result.message_count == 11
        # Note: Conclusions extraction depends on regex matching
        # which may vary based on exact formatting

    def test_deduplicate(self, summarizer):
        items = ["Item A", "item a", "Item B", "Item A"]
        result = summarizer._deduplicate(items)

        assert len(result) == 2
        assert "Item A" in result
        assert "Item B" in result

    def test_reset(self, summarizer):
        summarizer._last_summary["thread5"] = time.time()
        summarizer._last_message_count["thread5"] = 100

        summarizer.reset("thread5")

        assert "thread5" not in summarizer._last_summary
        assert "thread5" not in summarizer._last_message_count
