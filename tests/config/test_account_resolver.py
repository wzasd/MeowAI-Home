import pytest
from src.config.account_resolver import resolve_runtime_env, AuthMode


def test_subscription_mode_strips_api_keys():
    base_env = {"ANTHROPIC_API_KEY": "sk-xxx", "ANTHROPIC_BASE_URL": "https://api.example.com", "PATH": "/usr/bin"}
    result = resolve_runtime_env("anthropic", AuthMode.SUBSCRIPTION, base_env)
    assert result.get("ANTHROPIC_API_KEY") is None
    assert result.get("ANTHROPIC_BASE_URL") is None
    assert result["PATH"] == "/usr/bin"


def test_api_key_mode_preserves_key():
    base_env = {"PATH": "/usr/bin"}
    result = resolve_runtime_env("anthropic", AuthMode.API_KEY, base_env, api_key="sk-test", base_url="https://proxy.example.com")
    assert result["ANTHROPIC_API_KEY"] == "sk-test"
    assert result["ANTHROPIC_BASE_URL"] == "https://proxy.example.com"


def test_openai_subscription_strips_keys():
    base_env = {"OPENAI_API_KEY": "sk-xxx", "PATH": "/usr/bin"}
    result = resolve_runtime_env("openai", AuthMode.SUBSCRIPTION, base_env)
    assert result.get("OPENAI_API_KEY") is None


def test_google_subscription_strips_keys():
    base_env = {"GOOGLE_API_KEY": "xxx", "PATH": "/usr/bin"}
    result = resolve_runtime_env("google", AuthMode.SUBSCRIPTION, base_env)
    assert result.get("GOOGLE_API_KEY") is None


def test_api_key_mode_no_url():
    base_env = {"PATH": "/usr/bin"}
    result = resolve_runtime_env("google", AuthMode.API_KEY, base_env, api_key="test-key")
    assert result["GOOGLE_API_KEY"] == "test-key"
