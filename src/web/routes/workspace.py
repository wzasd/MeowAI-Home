"""Workspace API routes for file system access."""
import asyncio
import os
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.workspace.terminal_parsers import detect_waiting_input, parse_progress

router = APIRouter(prefix="/workspace", tags=["workspace"])

# Import worktree manager
from src.workspace import WorktreeManager

_worktree_manager = None


def get_worktree_manager():
    global _worktree_manager
    if _worktree_manager is None:
        # Allow overriding base path via environment variable for testing
        base_path = os.environ.get("MEOWAI_WORKTREE_BASE", ".claude/worktrees")
        _worktree_manager = WorktreeManager(base_path=base_path)
    return _worktree_manager


def reset_worktree_manager():
    """Reset the global worktree manager (for testing)."""
    global _worktree_manager
    _worktree_manager = None


ALLOWED_COMMANDS = {
    "git", "python", "python3", "pytest", "pnpm", "npm", "node",
    "ls", "cat", "echo", "pwd", "find", "grep", "head", "tail",
    "mkdir", "touch", "cp", "mv", "rm", "rmdir", "code", "open",
    "which", "tsc", "vite", "biome", "npx", "curl", "wget", "tree",
    "uname", "whoami", "date", "env", "ssh", "docker", "sleep",
}

SHELL_METACHARACTERS = {";", "|", "&", "`", "$", "(", ")", "<", ">"}

MAX_OUTPUT_LINES = 5000
KILL_GRACE_S = 3.0
HEARTBEAT_INTERVAL_S = 2.0
QUIET_THRESHOLD_S = 5.0
STALL_THRESHOLD_S = 30.0
MAX_JOBS = 256
JOB_TTL_S = 3600.0

# ---------------------------------------------------------------------------
# Terminal job runtime
# ---------------------------------------------------------------------------

_terminal_jobs: dict[str, "TerminalJob"] = {}


def _cleanup_terminal_jobs() -> None:
    """Evict oldest finished jobs if over capacity or TTL."""
    now = time.time()
    finished = [
        (job_id, job)
        for job_id, job in _terminal_jobs.items()
        if job.status in ("done", "failed", "timeout", "cancelled")
    ]
    # TTL eviction
    for job_id, job in finished:
        if now - job.updated_at > JOB_TTL_S:
            del _terminal_jobs[job_id]
    # Capacity eviction: remove oldest by updated_at
    if len(_terminal_jobs) > MAX_JOBS:
        excess = len(_terminal_jobs) - MAX_JOBS
        sorted_jobs = sorted(
            _terminal_jobs.items(),
            key=lambda item: item[1].updated_at,
        )
        for job_id, _ in sorted_jobs[:excess]:
            del _terminal_jobs[job_id]


@dataclass
class TerminalJob:
    id: str
    worktree_id: str
    command: str
    cwd: str
    status: str = "queued"
    process: Optional[asyncio.subprocess.Process] = None
    stdout_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)
    last_output_at: float = field(default_factory=time.time)
    returncode: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    listeners: list[asyncio.Queue] = field(default_factory=list)
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    _tasks: list[asyncio.Task] = field(default_factory=list)

    def to_snapshot(self) -> dict:
        return {
            "id": self.id,
            "worktree_id": self.worktree_id,
            "command": self.command,
            "status": self.status,
            "returncode": self.returncode,
            "stdout_tail": self.stdout_lines[-100:] if self.stdout_lines else [],
            "stderr_tail": self.stderr_lines[-100:] if self.stderr_lines else [],
            "stdout_line_count": len(self.stdout_lines),
            "stderr_line_count": len(self.stderr_lines),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "elapsed_ms": int((time.time() - self.created_at) * 1000),
        }

    async def put_event(self, event: dict) -> None:
        self.updated_at = time.time()
        for q in list(self.listeners):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


def _validate_terminal_command(command: str) -> list[str]:
    """Validate command safety and return split parts."""
    command = command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Empty command")

    for ch in SHELL_METACHARACTERS:
        if ch in command:
            raise HTTPException(status_code=400, detail=f"Shell metacharacter '{ch}' is not allowed")

    try:
        parts = shlex.split(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid command syntax: {e}")

    if not parts:
        raise HTTPException(status_code=400, detail="Empty command")

    base_cmd = parts[0]
    if base_cmd not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=400, detail=f"Command '{base_cmd}' is not allowed")

    if base_cmd == "rm":
        has_r = "-r" in parts or "--recursive" in parts or any(p.startswith("-r") and "r" in p for p in parts)
        has_f = "-f" in parts or "--force" in parts or any(p.startswith("-") and "f" in p for p in parts)
        if has_r and has_f:
            for p in parts:
                if p in ("/", "~", ".", "..") or p.startswith("~/") or p.startswith("/"):
                    raise HTTPException(status_code=400, detail="Dangerous rm operation blocked")

    return parts


async def _read_stream(stream: asyncio.StreamReader, job: TerminalJob, stream_name: str) -> None:
    """Read stdout or stderr and broadcast events."""
    buffer = ""
    while True:
        try:
            chunk = await stream.read(4096)
        except Exception:
            break
        if not chunk:
            break
        decoded = chunk.decode("utf-8", errors="replace")
        buffer += decoded
        lines = buffer.split("\n")
        buffer = lines.pop()  # keep incomplete line in buffer
        for line in lines:
            job.last_output_at = time.time()
            if job.status in ("quiet", "stalled"):
                job.status = "running"
            if stream_name == "stdout":
                job.stdout_lines.append(line)
                if len(job.stdout_lines) > MAX_OUTPUT_LINES:
                    job.stdout_lines.pop(0)
            else:
                job.stderr_lines.append(line)
                if len(job.stderr_lines) > MAX_OUTPUT_LINES:
                    job.stderr_lines.pop(0)

            await job.put_event({"type": stream_name, "text": line})

            progress = parse_progress(line)
            if progress:
                await job.put_event({"type": "progress", **progress})

            if detect_waiting_input(line):
                job.status = "waiting_input"
                await job.put_event({"type": "waiting_input", "text": line})

    if buffer:
        job.last_output_at = time.time()
        if stream_name == "stdout":
            job.stdout_lines.append(buffer)
        else:
            job.stderr_lines.append(buffer)
        await job.put_event({"type": stream_name, "text": buffer})


async def _heartbeat(job: TerminalJob) -> None:
    """Send periodic heartbeats and detect quiet/stall states."""
    while True:
        try:
            await asyncio.wait_for(job._cancel_event.wait(), timeout=HEARTBEAT_INTERVAL_S)
            return
        except asyncio.TimeoutError:
            pass

        if job.status in ("done", "failed", "timeout", "cancelled"):
            return

        elapsed = time.time() - job.last_output_at
        state = "active"
        if elapsed >= STALL_THRESHOLD_S:
            state = "stalled"
        elif elapsed >= QUIET_THRESHOLD_S:
            state = "quiet"

        if state == "quiet" and job.status not in ("waiting_input",):
            job.status = "quiet"
        elif state == "stalled" and job.status not in ("waiting_input",):
            job.status = "stalled"

        await job.put_event({
            "type": "heartbeat",
            "elapsed_since_output_ms": int(elapsed * 1000),
            "state": state,
        })


async def _run_terminal_job(job: TerminalJob) -> None:
    """Main coroutine that runs a terminal job."""
    try:
        job.status = "starting"
        await job.put_event({"type": "started", "command": job.command})

        parts = _validate_terminal_command(job.command)

        process = await asyncio.create_subprocess_exec(
            *parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=job.cwd,
        )
        job.process = process
        job.status = "running"

        stdout_task = asyncio.create_task(_read_stream(process.stdout, job, "stdout"))
        stderr_task = asyncio.create_task(_read_stream(process.stderr, job, "stderr"))
        heartbeat_task = asyncio.create_task(_heartbeat(job))
        job._tasks = [stdout_task, stderr_task, heartbeat_task]

        # Wait for process completion or cancellation
        cancel_task = asyncio.create_task(job._cancel_event.wait())
        done, pending = await asyncio.wait(
            [asyncio.create_task(process.wait()), cancel_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        if cancel_task in done:
            # Cancel requested
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=KILL_GRACE_S)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            job.returncode = -1
            job.status = "cancelled"
            await job.put_event({"type": "exited", "returncode": -1, "status": "cancelled"})
        else:
            # Process finished naturally
            for t in [stdout_task, stderr_task]:
                try:
                    await asyncio.wait_for(t, timeout=2.0)
                except asyncio.TimeoutError:
                    t.cancel()

            job.returncode = process.returncode
            if job.returncode == 0:
                job.status = "done"
            else:
                job.status = "failed"
            await job.put_event({
                "type": "exited",
                "returncode": job.returncode,
                "status": job.status,
            })

    except asyncio.TimeoutError:
        if job.process:
            job.process.terminate()
            try:
                await asyncio.wait_for(job.process.wait(), timeout=KILL_GRACE_S)
            except asyncio.TimeoutError:
                job.process.kill()
                await job.process.wait()
        job.returncode = -1
        job.status = "timeout"
        await job.put_event({"type": "timeout", "status": "timeout"})
    except Exception as e:
        job.returncode = -1
        job.status = "failed"
        await job.put_event({"type": "error", "message": str(e)})
    finally:
        for t in job._tasks:
            if not t.done():
                t.cancel()
        job.process = None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class WorktreeListResponse(BaseModel):
    worktrees: list[dict]


class TreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"
    children: Optional[list["TreeNode"]] = None


class TreeResponse(BaseModel):
    tree: list[TreeNode]


class FileData(BaseModel):
    path: str
    content: str
    sha256: str
    size: int
    mime: str
    truncated: bool
    binary: bool = False


class SearchResult(BaseModel):
    path: str
    line: int
    content: str
    context_before: str = ""
    context_after: str = ""


class SearchResponse(BaseModel):
    results: list[SearchResult]


class TerminalRequest(BaseModel):
    worktreeId: str = Field(..., description="Worktree ID")
    command: str = Field(..., description="Shell command to execute")


class TerminalResponse(BaseModel):
    stdout: str
    stderr: str
    returncode: int


class TerminalJobCreateRequest(BaseModel):
    worktreeId: str = Field(..., description="Worktree ID")
    command: str = Field(..., description="Shell command to execute")


class TerminalJobCreateResponse(BaseModel):
    job_id: str
    status: str


class GitStatusItem(BaseModel):
    status: str
    path: str
    original_path: Optional[str] = None


class GitStatusResponse(BaseModel):
    branch: str
    ahead: int = 0
    behind: int = 0
    clean: bool
    files: list[GitStatusItem]


class GitDiffResponse(BaseModel):
    diff: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/worktrees", response_model=WorktreeListResponse)
async def list_worktrees():
    """List all available worktrees."""
    manager = get_worktree_manager()
    entries = manager.list_all()
    return {
        "worktrees": [
            {
                "id": e.id,
                "root": e.root,
                "branch": e.branch,
                "head": e.head,
            }
            for e in entries
        ]
    }


@router.get("/tree", response_model=TreeResponse)
async def get_tree(
    worktreeId: str = Query(..., description="Worktree ID"),
    path: str = Query("", description="Subdirectory path"),
    depth: int = Query(3, description="Depth to fetch"),
):
    """Get file tree for a worktree."""
    manager = get_worktree_manager()
    entry = manager.get(worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    base_path = Path(entry.root)
    if path:
        base_path = base_path / path

    # Resolve path and check for traversal
    resolved_path = base_path.resolve()
    resolved_root = Path(entry.root).resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    def build_tree(p: Path, current_depth: int) -> list[TreeNode]:
        if current_depth <= 0:
            return []

        nodes = []
        try:
            for item in sorted(p.iterdir()):
                if item.name.startswith(".") and item.name != ".git":
                    continue

                rel_path = str(item.relative_to(entry.root))
                if item.is_dir():
                    children = build_tree(item, current_depth - 1) if current_depth > 1 else None
                    nodes.append(TreeNode(
                        name=item.name,
                        path=rel_path,
                        type="directory",
                        children=children,
                    ))
                else:
                    nodes.append(TreeNode(
                        name=item.name,
                        path=rel_path,
                        type="file",
                    ))
        except PermissionError:
            pass
        return nodes

    tree = build_tree(base_path, depth)
    return {"tree": tree}


@router.get("/file")
async def get_file(
    worktreeId: str = Query(...),
    path: str = Query(...),
):
    """Get file content."""
    manager = get_worktree_manager()
    entry = manager.get(worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    file_path = Path(entry.root) / path
    resolved_path = file_path.resolve()
    resolved_root = Path(entry.root).resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    import hashlib
    import mimetypes

    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"

    # Check if binary
    is_binary = False
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                is_binary = True
    except Exception:
        pass

    if is_binary:
        return FileData(
            path=path,
            content="",
            sha256="",
            size=file_path.stat().st_size,
            mime=mime,
            truncated=True,
            binary=True,
        )

    # Read text content (max 1MB)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    truncated = len(content) > 1000000
    if truncated:
        content = content[:1000000]

    sha256 = hashlib.sha256(content.encode()).hexdigest()

    return FileData(
        path=path,
        content=content,
        sha256=sha256,
        size=len(content),
        mime=mime,
        truncated=truncated,
        binary=False,
    )


@router.post("/search", response_model=SearchResponse)
async def search_workspace(request: dict):
    """Search files in workspace."""
    worktree_id = request.get("worktreeId")
    query = request.get("query", "")
    search_type = request.get("type", "content")

    manager = get_worktree_manager()
    entry = manager.get(worktree_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    results = []
    root = Path(entry.root)

    if search_type == "filename":
        for item in root.rglob("*"):
            if query.lower() in item.name.lower():
                rel_path = str(item.relative_to(root))
                results.append(SearchResult(
                    path=rel_path,
                    line=0,
                    content=item.name,
                ))
    else:  # content search
        for item in root.rglob("*"):
            if item.is_file() and item.stat().st_size < 1024 * 1024:
                try:
                    content = item.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            rel_path = str(item.relative_to(root))
                            results.append(SearchResult(
                                path=rel_path,
                                line=i,
                                content=line.strip()[:200],
                                context_before=lines[max(0, i-2):i-1][0] if i > 1 else "",
                                context_after=lines[i:i+1][0] if i < len(lines) else "",
                            ))
                except Exception:
                    continue

    return {"results": results[:100]}


@router.post("/terminal", response_model=TerminalResponse)
async def run_terminal_command(request: TerminalRequest):
    """Execute a safe command in the worktree directory. (Legacy synchronous endpoint)"""
    manager = get_worktree_manager()
    entry = manager.get(request.worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    root = Path(entry.root).resolve()
    parts = _validate_terminal_command(request.command)

    try:
        result = subprocess.run(
            parts,
            shell=False,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        stdout = result.stdout
        stderr = result.stderr
        # Truncate large outputs
        if len(stdout) > 100_000:
            stdout = stdout[:100_000] + "\n[stdout truncated]"
        if len(stderr) > 100_000:
            stderr = stderr[:100_000] + "\n[stderr truncated]"
        return TerminalResponse(stdout=stdout, stderr=stderr, returncode=result.returncode)
    except subprocess.TimeoutExpired:
        return TerminalResponse(stdout="", stderr="Command timed out after 30s", returncode=-1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {e}")


@router.post("/terminal/jobs", response_model=TerminalJobCreateResponse)
async def create_terminal_job(request: TerminalJobCreateRequest):
    """Create a new terminal job and start it asynchronously."""
    manager = get_worktree_manager()
    entry = manager.get(request.worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    root = Path(entry.root).resolve()
    # Validate command syntax early (but do not run yet)
    _validate_terminal_command(request.command)

    _cleanup_terminal_jobs()

    job_id = str(uuid.uuid4())
    job = TerminalJob(
        id=job_id,
        worktree_id=request.worktreeId,
        command=request.command,
        cwd=str(root),
    )
    _terminal_jobs[job_id] = job
    asyncio.create_task(_run_terminal_job(job))
    return {"job_id": job_id, "status": job.status}


@router.get("/terminal/jobs/{job_id}")
async def get_terminal_job(job_id: str):
    """Get the current snapshot of a terminal job."""
    job = _terminal_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_snapshot()


@router.get("/terminal/jobs/{job_id}/stream")
async def stream_terminal_job(job_id: str):
    """Stream terminal job events via Server-Sent Events."""
    import json

    job = _terminal_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    job.listeners.append(queue)

    async def event_generator():
        try:
            # Replay latest state so client immediately knows what's happening
            await queue.put({"type": "status", "status": job.status, "command": job.command})
            # Replay historical stdout/stderr for late subscribers
            for line in job.stdout_lines:
                await queue.put({"type": "stdout", "text": line})
            for line in job.stderr_lines:
                await queue.put({"type": "stderr", "text": line})
            # If job already finished, emit terminal event so stream closes
            if job.status in ("done", "failed", "timeout", "cancelled"):
                await queue.put({"type": "exited", "returncode": job.returncode, "status": job.status})
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    event = {"type": "heartbeat", "silent": True}
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("exited", "error", "timeout"):
                    break
        finally:
            if queue in job.listeners:
                job.listeners.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/terminal/jobs/{job_id}/cancel")
async def cancel_terminal_job(job_id: str):
    """Cancel a running terminal job."""
    job = _terminal_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ("done", "failed", "timeout", "cancelled"):
        return {"success": True, "status": job.status}

    job._cancel_event.set()
    if job.process:
        job.process.terminate()
    return {"success": True, "status": "cancelling"}


@router.get("/git-status", response_model=GitStatusResponse)
async def git_status(
    worktreeId: str = Query(..., description="Worktree ID"),
):
    """Get git status for a worktree."""
    manager = get_worktree_manager()
    entry = manager.get(worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    root = Path(entry.root).resolve()

    def run_git(args: list[str]) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    branch = run_git(["branch", "--show-current"]) or "HEAD"
    ahead_behind = run_git(["rev-list", "--left-right", "--count", f"origin/{branch}...{branch}"])
    ahead = 0
    behind = 0
    if ahead_behind and "\t" in ahead_behind:
        parts = ahead_behind.split("\t")
        try:
            ahead = int(parts[1])
            behind = int(parts[0])
        except ValueError:
            pass

    porcelain = run_git(["status", "--porcelain"])
    files: list[GitStatusItem] = []
    for line in porcelain.splitlines():
        if len(line) < 3:
            continue
        status = line[:2]
        rest = line[3:]
        if " -> " in rest:
            original, current = rest.split(" -> ", 1)
            files.append(GitStatusItem(status=status, path=current, original_path=original))
        else:
            files.append(GitStatusItem(status=status, path=rest))

    return GitStatusResponse(
        branch=branch,
        ahead=ahead,
        behind=behind,
        clean=len(files) == 0,
        files=files,
    )


@router.get("/git-diff")
async def git_diff(
    worktreeId: str = Query(..., description="Worktree ID"),
    path: str = Query("", description="Optional file path"),
):
    """Get git diff for a worktree or specific file."""
    manager = get_worktree_manager()
    entry = manager.get(worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    root = Path(entry.root).resolve()
    if path:
        file_path = (root / path).resolve()
        if not str(file_path).startswith(str(root)):
            raise HTTPException(status_code=403, detail="Path traversal detected")

    args = ["diff"]
    if path:
        args.append(path)

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        diff = result.stdout
        if len(diff) > 500_000:
            diff = diff[:500_000] + "\n[diff truncated]"
        return GitDiffResponse(diff=diff)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git diff failed: {e}")


@router.post("/reveal")
async def reveal_in_finder(request: dict):
    """Reveal file in system file manager."""
    worktree_id = request.get("worktreeId")
    path = request.get("path", "")

    manager = get_worktree_manager()
    entry = manager.get(worktree_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    file_path = Path(entry.root) / path
    resolved_path = file_path.resolve()
    resolved_root = Path(entry.root).resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    import platform

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", "-R", str(file_path)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(file_path.parent)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", "/select,", str(file_path)], check=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reveal: {e}")

    return {"success": True}


@router.get("/pick-directory")
async def pick_directory():
    """Open a native directory picker dialog and return the selected absolute path."""
    import platform

    system = platform.system()
    selected_path = ""
    try:
        if system == "Darwin":
            script = 'POSIX path of (choose folder with prompt "请选择一个项目目录")'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
            )
            selected_path = result.stdout.strip().rstrip("/")
        elif system == "Linux":
            for cmd in [
                ["zenity", "--file-selection", "--directory", "--title=请选择一个项目目录"],
                ["kdialog", "--getexistingdirectory", "."],
            ]:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    selected_path = result.stdout.strip().rstrip("/")
                    break
                except FileNotFoundError:
                    continue
            else:
                raise HTTPException(
                    status_code=501,
                    detail="No directory picker available. Please install zenity or kdialog.",
                )
        elif system == "Windows":
            ps_script = (
                'Add-Type -AssemblyName System.Windows.Forms; '
                '$dlg = New-Object System.Windows.Forms.FolderBrowserDialog; '
                '$dlg.Description = "请选择一个项目目录"; '
                '$dlg.ShowNewFolderButton = $true; '
                'if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { '
                '$dlg.SelectedPath }'
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=True,
            )
            selected_path = result.stdout.strip().rstrip("/")
        else:
            raise HTTPException(status_code=501, detail=f"Unsupported platform: {system}")
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=400, detail="Directory picker cancelled")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pick directory: {e}")

    if not selected_path:
        raise HTTPException(status_code=400, detail="No directory selected")

    return {"path": selected_path}
