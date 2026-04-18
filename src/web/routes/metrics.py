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


@router.get("/token-usage", response_model=TokenUsageResponse)
async def get_token_usage(threadId: Optional[str] = None):
    """Get token usage for a thread or global from real metrics store."""
    if threadId:
        usage = await store.get_thread_usage(threadId)
    else:
        usage = await store.get_global_usage()

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
    """Track token usage for a thread by saving into the real metrics store."""
    import time
    db = await store._get_db()
    await db.execute(
        """
        INSERT INTO invocation_metrics
        (timestamp, cat_id, thread_id, project_path, prompt_tokens, completion_tokens, success, duration_ms, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (time.time(), "", threadId, "", promptTokens, completionTokens, 1, 0, cost),
    )
    await db.commit()
    return {"success": True}


@router.get("/cats")
async def get_cat_metrics(cat_id: str = Query(...), days: Optional[int] = Query(default=7)):
    rows = await store.list_by_cat(cat_id, days=days if days and days > 0 else None)
    return {"cat_id": cat_id, "days": days, "data": rows}


@router.get("/leaderboard")
async def get_leaderboard(days: Optional[int] = Query(default=7)):
    rows = await store.leaderboard(days=days if days and days > 0 else None)
    return {"days": days, "leaderboard": rows}
