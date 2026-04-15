"""Voice API routes for TTS and ASR."""
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.thread import ThreadManager
from src.voice import tts_service, asr_service
from src.web.dependencies import get_thread_manager
from fastapi import Depends

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB Whisper limit


@router.post("/tts")
async def synthesize_tts(
    text: str = Form(...),
    cat_id: str = Form(...),
    thread_id: str = Form(...),
    rate: str = Form("+0%"),
    volume: str = Form("+0%"),
    pitch: str = Form("+0Hz"),
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Synthesize text to speech and return the MP3 file."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        file_path = await tts_service.synthesize(
            text=text,
            cat_id=cat_id,
            thread_id=thread_id,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=f"{cat_id}_tts.mp3",
    )


@router.post("/asr")
async def transcribe_asr(
    audio: UploadFile = File(...),
    language: str = Form("zh"),
    prompt: Optional[str] = Form(None),
):
    """Transcribe an audio file using Whisper API."""
    content = await audio.read()
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Audio too large (max 25MB)")

    # Save to temporary file
    suffix = Path(audio.filename).suffix.lower() if audio.filename else ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = await asr_service.transcribe(
            audio_path=tmp_path,
            language=language,
            prompt=prompt,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR transcription failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"text": text, "language": language}
