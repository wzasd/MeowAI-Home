import os
from enum import Enum
from typing import Dict, Optional


class AuthMode(str, Enum):
    SUBSCRIPTION = "subscription"
    API_KEY = "api_key"


SUBSCRIPTION_STRIP_KEYS = {
    "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_DEFAULT_OPUS_MODEL"],
    "openai": ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID"],
    "google": ["GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"],
    "opencode": [],
    "dare": [],
    "antigravity": [],
}

API_KEY_ENV_MAP = {
    "anthropic": {"key": "ANTHROPIC_API_KEY", "url": "ANTHROPIC_BASE_URL"},
    "openai": {"key": "OPENAI_API_KEY", "url": "OPENAI_BASE_URL"},
    "google": {"key": "GOOGLE_API_KEY", "url": None},
    "opencode": {"key": "OPENAI_API_KEY", "url": "OPENAI_BASE_URL"},
}


def resolve_runtime_env(
    provider: str,
    auth_mode: AuthMode,
    base_env: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, str]:
    env = dict(base_env or os.environ)

    if auth_mode == AuthMode.SUBSCRIPTION:
        strip_keys = SUBSCRIPTION_STRIP_KEYS.get(provider, [])
        for key in strip_keys:
            env[key] = None

    elif auth_mode == AuthMode.API_KEY:
        env_map = API_KEY_ENV_MAP.get(provider, {})
        if api_key and "key" in env_map:
            env[env_map["key"]] = api_key
        if base_url and "url" in env_map and env_map["url"]:
            env[env_map["url"]] = base_url

    return env
