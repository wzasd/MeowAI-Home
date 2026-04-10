import pytest
from src.providers.codex_provider import CodexProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.opencode_provider import OpenCodeProvider
from src.providers import create_provider
from src.models.types import CatConfig, InvocationOptions, AgentMessageType


@pytest.fixture
def codex_config():
    return CatConfig(
        cat_id="codex", breed_id="maine-coon", name="缅因猫", display_name="砚砚",
        provider="openai", default_model="gpt-5.3-codex", personality="严谨认真",
        cli_command="codex", cli_args=["exec", "--json"],
    )

@pytest.fixture
def gemini_config():
    return CatConfig(
        cat_id="gemini", breed_id="siamese", name="暹罗猫", display_name="烁烁",
        provider="google", default_model="gemini-3.1-pro-preview", personality="热血奔放",
        cli_command="gemini", cli_args=[],
    )

@pytest.fixture
def opencode_config():
    return CatConfig(
        cat_id="opencode", breed_id="golden-chinchilla", name="金渐层", display_name="金渐层",
        provider="opencode", default_model="anthropic/claude-opus-4-6", personality="沉稳可靠",
        cli_command="opencode", cli_args=["run", "--format", "json"],
    )


class TestCodexProvider:
    def test_build_args(self, codex_config):
        provider = CodexProvider(codex_config)
        args = provider._build_args("write tests", InvocationOptions(system_prompt="你是审查员"))
        assert "exec" in args
        assert "write tests" in args

    def test_transform_text_event(self, codex_config):
        provider = CodexProvider(codex_config)
        event = {"type": "message", "content": [{"type": "text", "text": "done"}]}
        msgs = provider._transform_event(event)
        assert len(msgs) == 1
        assert msgs[0].content == "done"
        assert msgs[0].type == AgentMessageType.TEXT

    def test_transform_result_event(self, codex_config):
        provider = CodexProvider(codex_config)
        event = {"type": "result"}
        msgs = provider._transform_event(event)
        assert msgs[0].type == AgentMessageType.DONE


class TestGeminiProvider:
    def test_build_args(self, gemini_config):
        provider = GeminiProvider(gemini_config)
        args = provider._build_args("设计 UI", InvocationOptions(system_prompt="你是设计师"))
        assert "设计 UI" in args
        assert "--system-instruction" in args

    def test_transform_text_event(self, gemini_config):
        provider = GeminiProvider(gemini_config)
        event = {"type": "text", "text": "这是一个设计"}
        msgs = provider._transform_event(event)
        assert len(msgs) == 1
        assert msgs[0].content == "这是一个设计"


class TestOpenCodeProvider:
    def test_build_args(self, opencode_config):
        provider = OpenCodeProvider(opencode_config)
        args = provider._build_args("refactor", InvocationOptions())
        assert "run" in args
        assert "refactor" in args


class TestProviderFactory:
    def test_create_codex(self, codex_config):
        provider = create_provider(codex_config)
        assert isinstance(provider, CodexProvider)

    def test_create_gemini(self, gemini_config):
        provider = create_provider(gemini_config)
        assert isinstance(provider, GeminiProvider)

    def test_create_opencode(self, opencode_config):
        provider = create_provider(opencode_config)
        assert isinstance(provider, OpenCodeProvider)

    def test_create_unknown_raises(self):
        config = CatConfig(
            cat_id="x", breed_id="x", name="x", display_name="x",
            provider="unknown", default_model="x", cli_command="x",
        )
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider(config)
