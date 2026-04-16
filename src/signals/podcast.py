"""Podcast generator for signal articles — converts article content to audio via TTS."""

from pathlib import Path
from typing import Optional

from src.voice.tts_service import TTSService, tts_service


def _build_script(title: str, content: str, max_words: int = 300) -> str:
    """Build a simple podcast narration script from article content."""
    # Use summary if available, else truncate content
    words = content.split()
    body = " ".join(words[:max_words])
    if len(words) > max_words:
        body += "……"

    script = (
        f"今天来聊聊这篇文章：《{title}》。\n\n"
        f"{body}\n\n"
        f"以上就是今天的分享，我们下期再见。"
    )
    return script


class PodcastGenerator:
    """Generate podcast audio files from signal articles."""

    def __init__(self, tts: Optional[TTSService] = None):
        self.tts = tts or tts_service

    async def generate(
        self,
        article_id: str,
        title: str,
        content: str,
        cat_id: str = "patch",
    ) -> str:
        """Generate a podcast MP3 for an article. Returns file path."""
        script = _build_script(title, content)
        file_path = await self.tts.synthesize(
            text=script,
            cat_id=cat_id,
            thread_id=f"signal-{article_id}",
        )
        return file_path


podcast_generator = PodcastGenerator()
