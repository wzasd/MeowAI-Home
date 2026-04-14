import asyncio
import pytest
from pathlib import Path

from src.metrics.collector import MetricsCollector, InvocationRecord
from src.metrics.sqlite_store import MetricsSQLiteStore


@pytest.fixture
async def temp_store(tmp_path):
    db_path = tmp_path / "test_metrics.db"
    store = MetricsSQLiteStore(db_path=db_path)
    yield store
    if store._db:
        await store._db.close()


@pytest.mark.asyncio
async def test_record_start_finish(temp_store):
    collector = MetricsCollector(store=temp_store)
    invocation_id = "test-1"
    collector.record_start(invocation_id)
    record = InvocationRecord(
        cat_id="orange",
        thread_id="t1",
        project_path="/tmp",
        prompt_tokens=10,
        completion_tokens=20,
        success=True,
    )
    await collector.record_finish(invocation_id, record)
    assert record.duration_ms >= 0


@pytest.mark.asyncio
async def test_save_and_query(temp_store):
    collector = MetricsCollector(store=temp_store)
    invocation_id = "test-2"
    collector.record_start(invocation_id)
    record = InvocationRecord(
        cat_id="orange",
        thread_id="t1",
        project_path="/tmp",
        prompt_tokens=100,
        completion_tokens=200,
        success=True,
    )
    await collector.record_finish(invocation_id, record)

    rows = await temp_store.list_by_cat("orange")
    assert len(rows) == 1
    assert rows[0]["cat_id"] == "orange"
    assert rows[0]["prompt_tokens"] == 100
    assert rows[0]["completion_tokens"] == 200
    assert rows[0]["success"] is True


@pytest.mark.asyncio
async def test_leaderboard_aggregation(temp_store):
    collector = MetricsCollector(store=temp_store)

    for i in range(3):
        inv_id = f"orange-{i}"
        collector.record_start(inv_id)
        await collector.record_finish(
            inv_id,
            InvocationRecord(
                cat_id="orange",
                thread_id="t1",
                project_path="/tmp",
                prompt_tokens=10,
                completion_tokens=20,
                success=True,
            ),
        )

    for i in range(2):
        inv_id = f"inky-{i}"
        collector.record_start(inv_id)
        await collector.record_finish(
            inv_id,
            InvocationRecord(
                cat_id="inky",
                thread_id="t1",
                project_path="/tmp",
                prompt_tokens=5,
                completion_tokens=10,
                success=(i == 0),
            ),
        )

    board = await temp_store.leaderboard()
    assert len(board) == 2

    orange = next(r for r in board if r["cat_id"] == "orange")
    assert orange["total_calls"] == 3
    assert orange["prompt_tokens"] == 30
    assert orange["completion_tokens"] == 60
    assert orange["success_rate"] == 1.0

    inky = next(r for r in board if r["cat_id"] == "inky")
    assert inky["total_calls"] == 2
    assert inky["success_rate"] == 0.5
