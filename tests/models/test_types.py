import pytest
from src.models.types import (
    CatConfig, CatId, VariantConfig, ContextBudget,
    AgentMessage, AgentMessageType, ProviderType,
    TokenUsage, InvocationOptions
)


def test_cat_config_creation():
    config = CatConfig(
        cat_id=CatId("opus"),
        breed_id="ragdoll",
        name="布偶猫",
        display_name="宪宪",
        provider="anthropic",
        default_model="claude-opus-4-6",
        personality="温柔但有主见",
        mention_patterns=["@opus", "@布偶猫"],
        avatar="/avatars/opus.png",
        color_primary="#9B7EBD",
        color_secondary="#E8DFF5",
        cli_command="claude",
        cli_args=["--output-format", "stream-json"],
        budget=ContextBudget(
            max_prompt_tokens=180000,
            max_context_tokens=160000,
            max_messages=200,
            max_content_length_per_msg=10000
        )
    )
    assert config.cat_id == "opus"
    assert config.provider == "anthropic"
    assert config.budget.max_prompt_tokens == 180000


def test_agent_message_types():
    msg = AgentMessage(type=AgentMessageType.TEXT, content="hello")
    assert msg.type == AgentMessageType.TEXT
    assert msg.content == "hello"


def test_token_usage_defaults():
    usage = TokenUsage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.cost_usd == 0.0


def test_token_usage_merge():
    a = TokenUsage(input_tokens=100, output_tokens=50)
    b = TokenUsage(input_tokens=200, output_tokens=30, cost_usd=0.01)
    merged = a.merge(b)
    assert merged.input_tokens == 200  # latest wins
    assert merged.output_tokens == 80  # accumulated
    assert merged.cost_usd == 0.01


def test_invocation_options():
    opts = InvocationOptions(system_prompt="test", timeout=300.0)
    assert opts.system_prompt == "test"
    assert opts.timeout == 300.0
    assert opts.session_id is None


def test_provider_types():
    assert ProviderType.ANTHROPIC == "anthropic"
    assert ProviderType.OPENAI == "openai"
    assert ProviderType.GOOGLE == "google"


def test_context_budget_defaults():
    budget = ContextBudget()
    assert budget.max_prompt_tokens == 100000
    assert budget.max_context_tokens == 60000
