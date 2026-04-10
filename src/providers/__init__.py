from src.providers.base import BaseProvider
from src.providers.claude_provider import ClaudeProvider
from src.providers.codex_provider import CodexProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.opencode_provider import OpenCodeProvider

PROVIDER_MAP = {
    "anthropic": ClaudeProvider,
    "openai": CodexProvider,
    "google": GeminiProvider,
    "opencode": OpenCodeProvider,
}


def create_provider(config) -> BaseProvider:
    provider_cls = PROVIDER_MAP.get(config.provider)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {config.provider}")
    return provider_cls(config)
