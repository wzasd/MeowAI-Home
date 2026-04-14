import pytest
from src.config.account_resolver import resolve_runtime_env, resolve_account_env, AuthMode
from src.config.account_store import AccountStore
from pathlib import Path


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


def test_resolve_account_env_api_key(tmp_path, monkeypatch):
    """resolve_account_env looks up account and injects API key."""
    store = AccountStore(tmp_path / "acc.json", tmp_path / "cred.json")
    store.create_account(id="my-claude", displayName="My Claude", protocol="anthropic",
                         authType="api_key", apiKey="sk-resolved-key")
    import src.config.account_store as mod
    monkeypatch.setattr(mod, "_store_instance", store)

    env = resolve_account_env("my-claude", "anthropic")
    assert env.get("ANTHROPIC_API_KEY") == "sk-resolved-key"


def test_resolve_account_env_subscription(tmp_path, monkeypatch):
    """resolve_account_env for subscription strips keys."""
    store = AccountStore(tmp_path / "acc2.json", tmp_path / "cred2.json")
    import src.config.account_store as mod
    monkeypatch.setattr(mod, "_store_instance", store)

    env = resolve_account_env("builtin-anthropic", "anthropic")
    assert env.get("ANTHROPIC_API_KEY") is None


def test_resolve_account_env_unknown_returns_empty(tmp_path, monkeypatch):
    """resolve_account_env returns empty dict for unknown account."""
    store = AccountStore(tmp_path / "acc3.json", tmp_path / "cred3.json")
    import src.config.account_store as mod
    monkeypatch.setattr(mod, "_store_instance", store)

    env = resolve_account_env("nonexistent", "anthropic")
    assert env == {}
