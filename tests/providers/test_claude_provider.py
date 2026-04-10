import pytest
from src.providers.claude_provider import ClaudeProvider
from src.models.types import CatConfig, ContextBudget, InvocationOptions, AgentMessageType


@pytest.fixture
def opus_config():
    return CatConfig(
        cat_id="opus", breed_id="ragdoll", name="布偶猫", display_name="宪宪",
        provider="anthropic", default_model="claude-opus-4-6",
        personality="温柔但有主见", cli_command="claude",
        cli_args=["--output-format", "stream-json"],
        budget=ContextBudget(max_prompt_tokens=180000, max_context_tokens=160000),
    )


def test_build_system_prompt(opus_config):
    provider = ClaudeProvider(opus_config)
    prompt = provider.build_system_prompt()
    assert "布偶猫" in prompt
    assert "温柔但有主见" in prompt


def test_build_cli_args_basic(opus_config):
    provider = ClaudeProvider(opus_config)
    args = provider._build_args("你好", InvocationOptions())
    assert "--output-format" in args
    assert "stream-json" in args
    assert "你好" in args


def test_build_cli_args_with_system_prompt(opus_config):
    provider = ClaudeProvider(opus_config)
    args = provider._build_args("你好", InvocationOptions(system_prompt="你是架构师"))
    assert "--append-system-prompt" in args
    assert "你是架构师" in args


def test_build_cli_args_with_session_id(opus_config):
    provider = ClaudeProvider(opus_config)
    args = provider._build_args("继续", InvocationOptions(session_id="abc123"))
    assert "--resume" in args
    assert "abc123" in args


def test_transform_event_text(opus_config):
    provider = ClaudeProvider(opus_config)
    event = {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}]}}
    msgs = provider._transform_event(event)
    assert len(msgs) == 1
    assert msgs[0].type == AgentMessageType.TEXT
    assert msgs[0].content == "hello"


def test_transform_event_thinking(opus_config):
    provider = ClaudeProvider(opus_config)
    event = {"type": "assistant", "message": {"content": [{"type": "thinking", "text": "hmm"}]}}
    msgs = provider._transform_event(event)
    assert msgs[0].type == AgentMessageType.THINKING


def test_transform_event_usage(opus_config):
    provider = ClaudeProvider(opus_config)
    event = {"type": "assistant", "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}}
    msgs = provider._transform_event(event)
    assert msgs[0].type == AgentMessageType.USAGE
    assert msgs[0].usage.input_tokens == 100


def test_transform_event_done(opus_config):
    provider = ClaudeProvider(opus_config)
    event = {"type": "result", "subtype": "success"}
    msgs = provider._transform_event(event)
    assert msgs[0].type == AgentMessageType.DONE


def test_factory_creates_claude(opus_config):
    from src.providers import create_provider
    provider = create_provider(opus_config)
    assert isinstance(provider, ClaudeProvider)
