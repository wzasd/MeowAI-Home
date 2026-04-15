"""Review REST API endpoints for PR automation."""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.review.watcher import ReviewWatcher, PREvent, PREventType, ReviewTracking, PRStatus
from src.review.router import ReviewRouter, ReviewRouterBuilder
from src.review.thread_router import ThreadRouter
from src.review.imap_poller import IMAPPoller, IMAPConfig
from src.review.ci_tracker import CITracker

router = APIRouter(prefix="/review", tags=["review"])


# === Helpers ===

def _get_watcher(request: Request) -> ReviewWatcher:
    watcher = getattr(request.app.state, "review_watcher", None)
    if not watcher:
        raise HTTPException(status_code=503, detail="Review watcher not initialized")
    return watcher


def _get_router(request: Request) -> ReviewRouter:
    router = getattr(request.app.state, "review_router", None)
    if not router:
        raise HTTPException(status_code=503, detail="Review router not initialized")
    return router


def _get_thread_router(request: Request) -> ThreadRouter:
    tr = getattr(request.app.state, "review_thread_router", None)
    if not tr:
        raise HTTPException(status_code=503, detail="Thread router not initialized")
    return tr


def _get_ci_tracker(request: Request) -> CITracker:
    tracker = getattr(request.app.state, "ci_tracker", None)
    if not tracker:
        raise HTTPException(status_code=503, detail="CI tracker not initialized")
    return tracker


def _get_imap_poller(request: Request) -> Optional[IMAPPoller]:
    return getattr(request.app.state, "imap_poller", None)


# === Models ===

class WebhookPayload(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


class AssignReviewerBody(BaseModel):
    cat_id: str


class CreatePRBody(BaseModel):
    repository: str
    pr_number: int
    pr_title: str
    pr_body: Optional[str] = None
    branch: str = "main"
    author: str = "unknown"
    labels: List[str] = Field(default_factory=list)
    reviewers: List[str] = Field(default_factory=list)


class IMAPConfigBody(BaseModel):
    host: str
    port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    folder: str = "INBOX"
    poll_interval: int = 300


class ReviewTrackingResponse(BaseModel):
    pr_number: int
    repository: str
    pr_title: str
    status: str
    assigned_cat_id: Optional[str] = None
    created_at: float
    updated_at: float
    last_event_type: Optional[str] = None
    review_count: int
    comments_count: int


# === Endpoints ===

@router.get("/pending")
async def list_pending_reviews(request: Request) -> Dict[str, Any]:
    """List all pending PR reviews."""
    watcher = _get_watcher(request)
    pending = watcher.list_pending_reviews()
    return {
        "reviews": [
            {
                "pr_number": t.pr_number,
                "repository": t.repository,
                "pr_title": t.pr_title,
                "status": t.status.value,
                "assigned_cat_id": t.assigned_cat_id,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "review_count": t.review_count,
                "comments_count": t.comments_count,
            }
            for t in pending
        ],
    }


@router.get("/tracking/{repository:path}/{pr_number}")
async def get_tracking(repository: str, pr_number: int, request: Request) -> Dict[str, Any]:
    """Get tracking info for a specific PR."""
    watcher = _get_watcher(request)
    tracking = watcher.get_tracking(repository, pr_number)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")

    ci_state = None
    ci_tracker = _get_ci_tracker(request)
    state = ci_tracker.get_state(repository, pr_number)
    if state:
        ci_state = {
            "overall_status": state.overall_status.value,
            "checks": [
                {"name": c.name, "status": c.status.value, "conclusion": c.conclusion, "url": c.url}
                for c in state.checks
            ],
            "updated_at": state.updated_at,
        }

    return {
        "pr_number": tracking.pr_number,
        "repository": tracking.repository,
        "pr_title": tracking.pr_title,
        "status": tracking.status.value,
        "assigned_cat_id": tracking.assigned_cat_id,
        "created_at": tracking.created_at,
        "updated_at": tracking.updated_at,
        "review_count": tracking.review_count,
        "comments_count": tracking.comments_count,
        "ci_state": ci_state,
    }


@router.post("/tracking/{repository:path}/{pr_number}/assign")
async def assign_reviewer(
    repository: str,
    pr_number: int,
    body: AssignReviewerBody,
    request: Request,
) -> Dict[str, Any]:
    """Assign a cat as reviewer for a PR."""
    watcher = _get_watcher(request)
    success = watcher.assign_reviewer(repository, pr_number, body.cat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return {"success": True, "repository": repository, "pr_number": pr_number, "assigned_cat_id": body.cat_id}


@router.delete("/tracking/{repository:path}/{pr_number}")
async def delete_tracking(repository: str, pr_number: int, request: Request) -> Dict[str, Any]:
    """Remove tracking for a PR."""
    watcher = _get_watcher(request)
    success = watcher.remove_tracking(repository, pr_number)
    if not success:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return {"success": True}


@router.post("/webhook")
async def receive_webhook(request: Request) -> Dict[str, Any]:
    """Receive a native GitHub webhook."""
    import json
    watcher = _get_watcher(request)
    event_type = request.headers.get("X-GitHub-Event", "")
    signature = request.headers.get("X-Hub-Signature-256")
    raw = await request.body()
    result = await watcher.handle_webhook(event_type, raw, signature)

    # Route to thread if event was processed
    if result.get("status") == "processed":
        data = json.loads(raw) if raw else {}
        event = watcher.parse_event(event_type, data)
        if event:
            thread_router = _get_thread_router(request)
            route_result = await thread_router.route(event)
            if route_result:
                result["thread_id"] = route_result.thread_id
                result["thread_created"] = route_result.created

            review_router = _get_router(request)
            assignment = review_router.route(event)
            if assignment:
                watcher.assign_reviewer(event.repository, event.pr_number, assignment.assigned_cat_id)
                result["assigned_cat_id"] = assignment.assigned_cat_id
                result["assignment_reason"] = assignment.reason

    return result


@router.post("/pr")
async def create_pr(body: CreatePRBody, request: Request) -> Dict[str, Any]:
    """Manually create a PR tracking entry."""
    watcher = _get_watcher(request)
    event = PREvent(
        event_type=PREventType.PR_OPENED,
        pr_number=body.pr_number,
        pr_title=body.pr_title,
        pr_body=body.pr_body,
        repository=body.repository,
        branch=body.branch,
        author=body.author,
        labels=body.labels,
        reviewers=body.reviewers,
    )
    watcher._update_tracking(event)

    # Route to thread
    thread_router = _get_thread_router(request)
    route_result = await thread_router.route(event)

    # Assign reviewer
    review_router = _get_router(request)
    assignment = review_router.route(event)
    if assignment:
        watcher.assign_reviewer(body.repository, body.pr_number, assignment.assigned_cat_id)

    # Start CI tracking
    ci_tracker = _get_ci_tracker(request)
    ci_tracker.track_pr(body.repository, body.pr_number)

    return {
        "success": True,
        "pr_number": body.pr_number,
        "repository": body.repository,
        "thread_id": route_result.thread_id if route_result else None,
        "assigned_cat_id": assignment.assigned_cat_id if assignment else None,
    }


@router.get("/ci/status")
async def get_ci_status(request: Request) -> Dict[str, Any]:
    """Get CI tracker status and tracked PRs."""
    tracker = _get_ci_tracker(request)
    states = tracker.list_tracked()
    return {
        "status": tracker.get_status(),
        "prs": [
            {
                "pr_number": s.pr_number,
                "repository": s.repository,
                "overall_status": s.overall_status.value,
                "checks": [
                    {"name": c.name, "status": c.status.value, "conclusion": c.conclusion, "url": c.url}
                    for c in s.checks
                ],
                "updated_at": s.updated_at,
            }
            for s in states
        ],
    }


@router.post("/ci/poll")
async def poll_ci_now(request: Request) -> Dict[str, Any]:
    """Manually trigger a CI status poll."""
    tracker = _get_ci_tracker(request)
    updated = await tracker.poll_all()
    return {"success": True, "updated_count": len(updated)}


@router.get("/imap/status")
async def get_imap_status(request: Request) -> Dict[str, Any]:
    """Get IMAP poller status."""
    poller = _get_imap_poller(request)
    if not poller:
        return {"enabled": False}
    return {"enabled": True, **poller.get_status()}


@router.post("/imap/start")
async def start_imap(body: IMAPConfigBody, request: Request) -> Dict[str, Any]:
    """Start the IMAP poller with given config."""
    existing = _get_imap_poller(request)
    if existing:
        await existing.stop()

    config = IMAPConfig(
        host=body.host,
        port=body.port,
        username=body.username,
        password=body.password,
        use_ssl=body.use_ssl,
        folder=body.folder,
        poll_interval=body.poll_interval,
    )
    poller = IMAPPoller(config)

    async def _on_email(event):
        # Convert email event to PR event and route
        thread_router = _get_thread_router(request)
        if event.pr_number and event.repository:
            pr_event = PREvent(
                event_type=PREventType.PR_OPENED,
                pr_number=event.pr_number,
                pr_title=event.subject,
                pr_body=event.body_text,
                repository=event.repository,
                branch="",
                author=event.sender,
            )
            await thread_router.route(pr_event)

    poller.add_handler(_on_email)
    await poller.start()
    request.app.state.imap_poller = poller
    return {"success": True, "status": poller.get_status()}


@router.post("/imap/stop")
async def stop_imap(request: Request) -> Dict[str, Any]:
    """Stop the IMAP poller."""
    poller = _get_imap_poller(request)
    if poller:
        await poller.stop()
        request.app.state.imap_poller = None
    return {"success": True}


@router.get("/suggest-reviewers")
async def suggest_reviewers(repository: str, files: str, request: Request) -> Dict[str, Any]:
    """Suggest reviewers based on changed files."""
    review_router = _get_router(request)
    file_list = [f.strip() for f in files.split(",") if f.strip()]
    suggestions = review_router.get_suggested_reviewers(file_list)
    return {
        "repository": repository,
        "files": file_list,
        "suggestions": [{"cat_id": cat_id, "score": score} for cat_id, score in suggestions],
    }
