"""Tests for HandoffDigest (B3)."""
import pytest
from src.session.handoff import HandoffDigest, DigestSection


class TestDigestSection:
    def test_section_creation(self):
        section = DigestSection(
            title="Decisions",
            content="- Decision 1\n- Decision 2",
        )
        assert section.title == "Decisions"
        assert "Decision 1" in section.content


class TestHandoffDigestBasic:
    def test_empty_conversation(self):
        digest = HandoffDigest()
        result = digest.generate([])
        assert result["decisions"] == []
        assert result["open_questions"] == []
        assert result["key_files"] == []
        assert result["next_steps"] == []

    def test_single_message(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "user", "content": "Hello"},
        ])
        assert result["decisions"] == []

    def test_respects_max_chars(self):
        digest = HandoffDigest(max_chars=100)
        long_content = "x" * 1000
        result = digest.generate([
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": "Response"},
        ])
        # Should truncate and still include structure
        assert "decisions" in result


class TestDecisionExtraction:
    def test_extract_decision_keywords(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "We decided to use Python for the backend."},
            {"role": "assistant", "content": "The decision is to use SQLite for storage."},
        ])
        assert len(result["decisions"]) >= 2

    def test_extract_agreed_statements(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "We agreed on using FastAPI instead of Flask."},
        ])
        assert len(result["decisions"]) == 1
        assert "FastAPI" in result["decisions"][0]

    def test_extract_concluded_items(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Conclusion: we will use pytest for testing."},
        ])
        assert len(result["decisions"]) == 1
        assert "pytest" in result["decisions"][0]


class TestOpenQuestionsExtraction:
    def test_extract_question_marks(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Should we use async or sync?"},
            {"role": "assistant", "content": "What about the database schema?"},
        ])
        assert len(result["open_questions"]) >= 2

    def test_extract_todo_questions(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "TODO: figure out the caching strategy."},
        ])
        assert len(result["open_questions"]) == 1

    def test_extract_open_items(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Open: performance optimization approach."},
        ])
        assert len(result["open_questions"]) == 1


class TestKeyFilesExtraction:
    def test_extract_file_paths(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Edit src/main.py and tests/test_main.py"},
        ])
        assert "src/main.py" in result["key_files"]
        assert "tests/test_main.py" in result["key_files"]

    def test_extract_multiple_extensions(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Check config.yaml, app.py, and styles.css"},
        ])
        assert "config.yaml" in result["key_files"]
        assert "app.py" in result["key_files"]
        assert "styles.css" in result["key_files"]

    def test_deduplicates_files(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Edit src/main.py"},
            {"role": "assistant", "content": "Also update src/main.py again"},
        ])
        assert result["key_files"].count("src/main.py") == 1


class TestNextStepsExtraction:
    def test_extract_action_items(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Action item: write more tests."},
        ])
        assert len(result["next_steps"]) == 1
        assert "write more tests" in result["next_steps"][0]

    def test_extract_next_steps(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Next step is to deploy to staging."},
        ])
        assert len(result["next_steps"]) == 1

    def test_extract_follow_ups(self):
        digest = HandoffDigest()
        result = digest.generate([
            {"role": "assistant", "content": "Follow-up: review the PR tomorrow."},
        ])
        assert len(result["next_steps"]) == 1


class TestIntegration:
    def test_full_conversation_digest(self):
        digest = HandoffDigest()
        messages = [
            {"role": "user", "content": "Let's design the API"},
            {"role": "assistant", "content": "We decided to use REST with JSON."},
            {"role": "assistant", "content": "Open question: should we use FastAPI or Flask?"},
            {"role": "assistant", "content": "Edit src/api.py and src/models.py"},
            {"role": "assistant", "content": "Next step: implement the endpoints."},
        ]
        result = digest.generate(messages)

        assert len(result["decisions"]) >= 1
        assert len(result["open_questions"]) >= 1
        assert len(result["key_files"]) >= 2
        assert len(result["next_steps"]) >= 1

    def test_with_invocation_summaries(self):
        digest = HandoffDigest()
        messages = [
            {"role": "user", "content": "Start implementation"},
        ]
        invocation_summaries = [
            "CAT_INVOKED: orange with tdd skill",
            "TOOL_CALL: read_file(src/main.py)",
            "CAT_RESPONDED: wrote 50 lines",
        ]
        result = digest.generate(messages, invocation_summaries=invocation_summaries)

        assert result["invocation_summary"] is not None
        assert "orange" in result["invocation_summary"]
        assert "tdd" in result["invocation_summary"]
