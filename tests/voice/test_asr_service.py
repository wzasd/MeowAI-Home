"""Tests for ASRService."""
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.voice.asr_service import ASRService


@pytest.fixture
def asr(tmp_path):
    return ASRService(api_key="test-key", base_url="https://api.openai.com")


@pytest.mark.asyncio
async def test_transcribe_success(asr, tmp_path):
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio")

    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "  Hello world  "}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        text = await asr.transcribe(str(audio_path), language="en")

    assert text == "Hello world"


@pytest.mark.asyncio
async def test_transcribe_missing_api_key(tmp_path):
    service = ASRService(api_key=None)
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not configured"):
        await service.transcribe(str(audio_path))


@pytest.mark.asyncio
async def test_transcribe_missing_file(asr):
    with pytest.raises(FileNotFoundError):
        await asr.transcribe("/nonexistent/file.mp3")


@pytest.mark.asyncio
async def test_transcribe_http_error(asr, tmp_path):
    audio_path = tmp_path / "test.wav"
    audio_path.write_bytes(b"fake audio")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(Exception, match="API error"):
            await asr.transcribe(str(audio_path))
