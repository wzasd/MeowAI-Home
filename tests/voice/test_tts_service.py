"""Tests for TTSService."""
import hashlib
from pathlib import Path
from unittest.mock import patch, AsyncMock

import edge_tts
import pytest

from src.voice.tts_service import TTSService, _DEFAULT_VOICES, _DEFAULT_VOICE


@pytest.fixture
def tts(tmp_path):
    return TTSService(cache_dir=tmp_path)


def test_voice_for_cat_known(tts):
    assert tts._voice_for_cat("orange") == _DEFAULT_VOICES["orange"]
    assert tts._voice_for_cat("inky") == _DEFAULT_VOICES["inky"]
    assert tts._voice_for_cat("patch") == _DEFAULT_VOICES["patch"]


def test_voice_for_cat_unknown(tts):
    assert tts._voice_for_cat("unknown") == _DEFAULT_VOICE


def test_cache_path(tts):
    path = tts._cache_path("hello", "voice1", "+0%", "+0%", "+0Hz", "thread-1")
    expected_hash = hashlib.sha256("hello:voice1:+0%:+0%:+0Hz".encode("utf-8")).hexdigest()[:16]
    assert path.name == f"{expected_hash}.mp3"
    assert path.parent.name == "thread-1"
    assert path.parent.parent == tts.cache_dir


@pytest.mark.asyncio
async def test_synthesize_caches_result(tts):
    text = "你好世界"
    cat_id = "orange"
    thread_id = "t1"

    async def _save(path: str):
        Path(path).write_bytes(b"fake mp3")

    with patch.object(edge_tts, "Communicate") as MockComm:
        mock_instance = AsyncMock()
        mock_save = AsyncMock(side_effect=_save)
        mock_instance.save = mock_save
        MockComm.return_value = mock_instance

        path1 = await tts.synthesize(text, cat_id, thread_id)
        path2 = await tts.synthesize(text, cat_id, thread_id)

        MockComm.assert_called_once()
        mock_save.assert_called_once()
        assert path1 == path2
        assert Path(path1).exists()


@pytest.mark.asyncio
async def test_synthesize_empty_text_raises(tts):
    with pytest.raises(ValueError, match="cannot be empty"):
        await tts.synthesize("   ", "orange", "t1")


@pytest.mark.asyncio
async def test_list_cached_files(tts):
    text = "test"
    cat_id = "patch"
    thread_id = "t2"

    async def _save(path: str):
        Path(path).write_bytes(b"fake mp3")

    with patch.object(edge_tts, "Communicate") as MockComm:
        mock_instance = AsyncMock()
        mock_instance.save = _save
        MockComm.return_value = mock_instance
        await tts.synthesize(text, cat_id, thread_id)

    files = tts.list_cached_files(thread_id)
    assert len(files) == 1
    assert files[0].endswith(".mp3")


@pytest.mark.asyncio
async def test_clear_cache(tts):
    text = "test"
    cat_id = "inky"
    thread_id = "t3"

    async def _save(path: str):
        Path(path).write_bytes(b"fake mp3")

    with patch.object(edge_tts, "Communicate") as MockComm:
        mock_instance = AsyncMock()
        mock_instance.save = _save
        MockComm.return_value = mock_instance
        await tts.synthesize(text, cat_id, thread_id)

    assert len(tts.list_cached_files(thread_id)) == 1
    removed = tts.clear_cache(thread_id)
    assert removed == 1
    assert tts.list_cached_files(thread_id) == []


def test_clear_cache_missing_thread(tts):
    assert tts.clear_cache("nonexistent") == 0
