"""Why-First Protocol tests"""
from src.evolution.why_first import (
    HandoffNote, parse_handoff_note, build_handoff_prompt, format_handoff_note,
)


class TestParseHandoffNote:
    def test_parse_full_note(self):
        text = """一些前言文字

### What
实现了用户登录 API 端点

### Why
需要支持多端登录，要求 JWT token 认证

### Tradeoff
考虑过 session 方案但放弃了，因为不支持跨域

### Open Questions
token 过期时间应该是多久？

### Next Action
请编写登录 API 的集成测试"""
        note = parse_handoff_note(text)
        assert note is not None
        assert "登录" in note.what
        assert "JWT" in note.why
        assert "session" in note.tradeoff
        assert "过期" in note.open_questions
        assert "集成测试" in note.next_action

    def test_parse_english_headers(self):
        text = """
### What
Implemented login API

### Why
Need JWT authentication

### Tradeoff
Considered session auth but rejected

### Open Questions
Token expiry time?

### Next Action
Write integration tests"""
        note = parse_handoff_note(text)
        assert note is not None
        assert "login" in note.what.lower()

    def test_parse_minimal_note_what_and_why_only(self):
        text = """
### What
Fixed the bug

### Why
It was causing crashes"""
        note = parse_handoff_note(text)
        assert note is not None
        assert "Fixed" in note.what
        assert "crashes" in note.why
        assert note.tradeoff == "无"
        assert note.open_questions == "无"
        assert note.next_action == "无"

    def test_parse_missing_what_returns_none(self):
        text = """
### Why
Some reason

### Tradeoff
None"""
        note = parse_handoff_note(text)
        assert note is None

    def test_parse_no_handoff_in_text(self):
        text = "This is just a regular response without any structured notes."
        note = parse_handoff_note(text)
        assert note is None


class TestBuildHandoffPrompt:
    def test_returns_prompt_string(self):
        prompt = build_handoff_prompt()
        assert "Why-First" in prompt
        assert "What" in prompt
        assert "Why" in prompt
        assert "Tradeoff" in prompt
        assert "Open" in prompt
        assert "Next Action" in prompt

    def test_prompt_is_non_empty(self):
        assert len(build_handoff_prompt()) > 50


class TestFormatHandoffNote:
    def test_format_full_note(self):
        note = HandoffNote(
            what="Added login endpoint",
            why="Need auth",
            tradeoff="Session rejected",
            open_questions="Token expiry",
            next_action="Write tests",
        )
        formatted = format_handoff_note(note)
        assert "## 交接笔记" in formatted
        assert "### What" in formatted
        assert "Added login endpoint" in formatted
        assert "### Next Action" in formatted
        assert "Write tests" in formatted

    def test_format_with_empty_fields(self):
        note = HandoffNote(what="did something", why="reason", tradeoff="", open_questions="", next_action="")
        formatted = format_handoff_note(note)
        assert "### What" in formatted
        assert "### Why" in formatted

    def test_roundtrip(self):
        """Format then parse should preserve key content"""
        original = HandoffNote(
            what="Refactored auth module",
            why="Security requirements",
            tradeoff="Simple auth rejected",
            open_questions="Rate limiting",
            next_action="Update docs",
        )
        formatted = format_handoff_note(original)
        parsed = parse_handoff_note(formatted)
        assert parsed is not None
        assert "Refactored" in parsed.what
        assert "Security" in parsed.why
