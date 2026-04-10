from typing import Optional

CONTEXT_WINDOW_SIZES = {
    "claude-opus-4-6": 200000,
    "claude-opus-4-5-20251101": 200000,
    "claude-sonnet-4-6": 200000,
    "claude-sonnet-4-5-20251001": 200000,
    "claude-haiku-4-5-20251001": 200000,
    "gpt-5.3-codex": 240000,
    "gpt-5.3-codex-spark": 128000,
    "gpt-5.4": 400000,
    "gemini-3.1-pro-preview": 1000000,
    "gemini-2.5-pro": 1000000,
}


def get_context_window_size(model: str) -> Optional[int]:
    if model in CONTEXT_WINDOW_SIZES:
        return CONTEXT_WINDOW_SIZES[model]
    for key, size in CONTEXT_WINDOW_SIZES.items():
        if model.startswith(key):
            return size
    return None
