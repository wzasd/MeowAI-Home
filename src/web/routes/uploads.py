"""Upload API routes for file attachments."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.thread import ThreadManager
from src.web.dependencies import get_thread_manager

router = APIRouter(prefix="/threads", tags=["uploads"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/{thread_id}/uploads")
async def upload_file(
    thread_id: str,
    file: UploadFile = File(...),
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Upload a file attachment for a thread."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if not thread.project_path:
        raise HTTPException(status_code=400, detail="Thread has no project path")

    # Sanitize filename to prevent path traversal
    filename = Path(file.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Read content and enforce size limit
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Build target directory: {project_path}/.meowai/uploads/{thread_id}
    upload_dir = Path(thread.project_path) / ".meowai" / "uploads" / thread_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    target_path = upload_dir / filename
    target_path.write_bytes(content)

    return {
        "name": filename,
        "size": len(content),
        "mimeType": file.content_type or "application/octet-stream",
        "url": f"/api/threads/{thread_id}/uploads/{filename}",
    }


@router.get("/{thread_id}/uploads/{filename}")
async def download_file(
    thread_id: str,
    filename: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Download an uploaded file."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if not thread.project_path:
        raise HTTPException(status_code=400, detail="Thread has no project path")

    upload_dir = Path(thread.project_path) / ".meowai" / "uploads" / thread_id
    file_path = upload_dir / filename

    # Security check: resolved path must be within upload_dir
    resolved_path = file_path.resolve()
    resolved_dir = upload_dir.resolve()
    if not str(resolved_path).startswith(str(resolved_dir)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(str(file_path), filename=filename)
