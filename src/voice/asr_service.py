import os
from pathlib import Path
from typing import Optional

import httpx

_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
_DEFAULT_MODEL = "whisper-1"


class ASRService:
    """OpenAI Whisper API based automatic speech recognition."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")

    async def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
        prompt: Optional[str] = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        url = f"{self.base_url.rstrip('/')}/v1/audio/transcriptions"

        # Determine content type from extension
        suffix = path.suffix.lower()
        mime_map = {
            ".mp3": "audio/mpeg",
            ".mp4": "audio/mp4",
            ".m4a": "audio/m4a",
            ".ogg": "audio/ogg",
            ".wav": "audio/wav",
            ".webm": "audio/webm",
            ".flac": "audio/flac",
        }
        content_type = mime_map.get(suffix, "audio/mpeg")

        data = {"model": _DEFAULT_MODEL, "language": language}
        if prompt:
            data["prompt"] = prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(path, "rb") as f:
                files = {"file": (path.name, f, content_type)}
                response = await client.post(
                    url,
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            response.raise_for_status()
            result = response.json()

        text = result.get("text", "").strip()
        return text


asr_service = ASRService()
