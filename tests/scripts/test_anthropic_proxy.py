import pytest
from scripts.anthropic_proxy import strip_thinking_from_history, normalize_sse_event, ProxyConfig


def test_strip_thinking_blocks():
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "inner thoughts"},
            {"type": "text", "text": "response"},
        ]},
        {"role": "user", "content": "continue"},
    ]
    result = strip_thinking_from_history(messages)
    assert len(result[1]["content"]) == 1
    assert result[1]["content"][0]["type"] == "text"
    assert result[0] == messages[0]
    assert result[2] == messages[2]


def test_strip_redacted_thinking():
    messages = [
        {"role": "assistant", "content": [
            {"type": "redacted_thinking", "data": "xxx"},
            {"type": "text", "text": "ok"},
        ]},
    ]
    result = strip_thinking_from_history(messages)
    assert len(result[0]["content"]) == 1
    assert result[0]["content"][0]["type"] == "text"


def test_user_messages_untouched():
    messages = [
        {"role": "user", "content": "hello"},
    ]
    result = strip_thinking_from_history(messages)
    assert result == messages


def test_normalize_sse_usage():
    event = {"type": "message_start", "message": {"usage": {"input_tokens": 0, "output_tokens": 0}}}
    result = normalize_sse_event(event)
    assert result is not None


def test_normalize_sse_strips_extra_fields():
    event = {"type": "content_block_start", "content_block": {"type": "text", "text": "hi", "extra_field": "bad"}}
    result = normalize_sse_event(event)
    assert "extra_field" not in result["content_block"]


def test_proxy_config_defaults():
    config = ProxyConfig()
    assert config.port == 9877
    assert config.max_retries == 3


def test_normalize_sse_none_input():
    assert normalize_sse_event(None) is None
