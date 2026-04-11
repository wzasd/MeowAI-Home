"""Metrics API routes for token usage and performance metrics."""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, Literal

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


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


# Mock data for cat metrics
_cat_metrics: list[CatMetrics] = [
    CatMetrics(catId="orange", totalInvocations=142, successRate=0.97, avgLatencyMs=2300, totalTokens=520000, trend="up"),
    CatMetrics(catId="inky", totalInvocations=98, successRate=0.95, avgLatencyMs=1800, totalTokens=380000, trend="stable"),
    CatMetrics(catId="patch", totalInvocations=67, successRate=0.92, avgLatencyMs=3100, totalTokens=210000, trend="down"),
]


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


@router.get("/cats", response_model=list[CatMetrics])
async def get_cat_metrics():
    """Get per-cat metrics."""
    return _cat_metrics


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard():
    """Get leaderboard data."""
    # Sort by score descending and assign ranks
    sorted_cats = sorted(_cat_metrics, key=lambda x: (x.totalInvocations * x.successRate) / (x.avgLatencyMs / 1000), reverse=True)

    entries = []
    for i, cat in enumerate(sorted_cats, 1):
        score = (cat.totalInvocations * cat.successRate) / (cat.avgLatencyMs / 1000)
        badge = None
        if i == 1:
            badge = "gold"
        elif i == 2:
            badge = "silver"
        elif i == 3:
            badge = "bronze"

        entries.append(LeaderboardEntry(
            catId=cat.catId,
            rank=i,
            score=score,
            totalInvocations=cat.totalInvocations,
            successRate=cat.successRate,
            avgLatencyMs=cat.avgLatencyMs,
            badge=badge,
        ))
    return entries
