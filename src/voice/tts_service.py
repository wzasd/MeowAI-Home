import hashlib
import os
from pathlib import Path
from typing import Optional

import edge_tts

_DEFAULT_VOICES = {
    "orange": "zh-CN-XiaoxiaoNeural",
    "inky": "zh-CN-YunxiNeural",
    "patch": "zh-CN-XiaoyiNeural",
}

_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class TTSService:
    """Edge-TTS based text-to-speech service with per-cat voice mapping and file caching."""

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".meowai" / "voice"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _voice_for_cat(self, cat_id: str) -> str:
        return _DEFAULT_VOICES.get(cat_id, _DEFAULT_VOICE)

    def _cache_path(self, text: str, voice: str, rate: str, volume: str, pitch: str, thread_id: str) -> Path:
        content = f"{text}:{voice}:{rate}:{volume}:{pitch}"
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        thread_dir = self.cache_dir / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        return thread_dir / f"{file_hash}.mp3"

    async def synthesize(
        self,
        text: str,
        cat_id: str,
        thread_id: str,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> str:
        if not text or not text.strip():
            raise ValueError("TTS text cannot be empty")
        voice = self._voice_for_cat(cat_id)
        cache_file = self._cache_path(text, voice, rate, volume, pitch, thread_id)
        if cache_file.exists():
            return str(cache_file)
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
        await communicate.save(str(cache_file))
        return str(cache_file)

    def list_cached_files(self, thread_id: str) -> list:
        thread_dir = self.cache_dir / thread_id
        if not thread_dir.exists():
            return []
        return [str(p) for p in thread_dir.glob("*.mp3")]

    def clear_cache(self, thread_id: str) -> int:
        thread_dir = self.cache_dir / thread_id
        if not thread_dir.exists():
            return 0
        removed = 0
        for p in thread_dir.glob("*.mp3"):
            p.unlink()
            removed += 1
        return removed


tts_service = TTSService()
