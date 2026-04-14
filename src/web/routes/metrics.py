"""Metrics API routes for token usage and performance metrics."""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, Literal

from src.metrics.sqlite_store import MetricsSQLiteStore

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
store = MetricsSQLiteStore()


class CatMetrics(BaseModel):
    catId: str
    totalInvocations: int
    successRate: float
    avgLatencyMs: int
    totalTokens: int
    trend: Literal["up", "down", "stable"]


class LeaderboardEntry(BaseModel):
    catId: str
    rank: int
    score: float
    totalInvocations: int
    successRate: float
    avgLatencyMs: int
    badge: Optional[Literal["gold", "silver", "bronze"]] = None


class TokenUsageResponse(BaseModel):
    promptTokens: int
    completionTokens: int
    cacheHitRate: float
    totalCost: float


# In-memory metrics storage (replace with real tracking in production)
_thread_usage: dict[str, dict] = {}
_global_usage = {
    "promptTokens": 45230,
    "completionTokens": 12840,
    "cacheHitRate": 0.72,
    "totalCost": 0.38,
}


def get_thread_usage(thread_id: str) -> dict:
    """Get or create usage record for a thread."""
    if thread_id not in _thread_usage:
        _thread_usage[thread_id] = {
            "promptTokens": 0,
            "completionTokens": 0,
            "cacheHitRate": 0.0,
            "totalCost": 0.0,
        }
    return _thread_usage[thread_id]


@router.get("/token-usage", response_model=TokenUsageResponse)
async def get_token_usage(threadId: Optional[str] = None):
    """Get token usage for a thread or global."""
    if threadId:
        usage = get_thread_usage(threadId)
    else:
        usage = _global_usage

    return TokenUsageResponse(
        promptTokens=usage["promptTokens"],
        completionTokens=usage["completionTokens"],
        cacheHitRate=usage["cacheHitRate"],
        totalCost=usage["totalCost"],
    )


@router.post("/token-usage/track")
async def track_usage(
    threadId: str,
    promptTokens: int,
    completionTokens: int,
    cost: float = 0.0,
):
    """Track token usage for a thread."""
    usage = get_thread_usage(threadId)
    usage["promptTokens"] += promptTokens
    usage["completionTokens"] += completionTokens
    usage["totalCost"] += cost

    # Update cache hit rate (simplified)
    total = usage["promptTokens"] + usage["completionTokens"]
    if total > 0:
        usage["cacheHitRate"] = min(0.95, usage["promptTokens"] / total * 0.8)

    return {"success": True}


@router.get("/cats")
async def get_cat_metrics(cat_id: str = Query(...), days: Optional[int] = Query(default=7)):
    rows = await store.list_by_cat(cat_id, days=days if days and days > 0 else None)
    return {"cat_id": cat_id, "days": days, "data": rows}


@router.get("/leaderboard")
async def get_leaderboard(days: Optional[int] = Query(default=7)):
    rows = await store.leaderboard(days=days if days and days > 0 else None)
    return {"days": days, "leaderboard": rows}
