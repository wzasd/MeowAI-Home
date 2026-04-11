"""Tests for TaskRunner scheduler."""

import asyncio
import pytest
import tempfile
import os
from src.scheduler.runner import (
    TaskRunner,
    ScheduledTask,
    TaskTrigger,
    TaskStatus,
    TaskGovernance,
)


class TestTaskGovernance:
    """Test task governance controls."""

    def test_global_pause(self):
        gov = TaskGovernance()
        assert not gov.is_paused()

        gov.pause_all()
        assert gov.is_paused()

        gov.resume_all()
        assert not gov.is_paused()

    def test_task_switches(self):
        gov = TaskGovernance()

        # Default enabled
        assert gov.is_task_enabled("task1")

        # Disable task
        gov.disable_task("task1")
        assert not gov.is_task_enabled("task1")

        # Re-enable
        gov.enable_task("task1")
        assert gov.is_task_enabled("task1")


class TestTaskRunner:
    """Test TaskRunner functionality."""

    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path
        os.unlink(path)

    @pytest.fixture
    def runner(self, temp_db):
        return TaskRunner(db_path=temp_db)

    def test_register_task(self, runner):
        task = ScheduledTask(
            id="test_task",
            name="Test Task",
            description="A test task",
            trigger=TaskTrigger.INTERVAL,
            schedule="60",
            enabled=True,
        )

        async def handler(t):
            pass

        runner.register_task(task, handler)

        retrieved = runner.get_task("test_task")
        assert retrieved is not None
        assert retrieved.name == "Test Task"

    def test_unregister_task(self, runner):
        task = ScheduledTask(
            id="test_task",
            name="Test Task",
            description="A test task",
            trigger=TaskTrigger.INTERVAL,
            schedule="60",
        )

        async def handler(t):
            pass

        runner.register_task(task, handler)
        assert runner.get_task("test_task") is not None

        success = runner.unregister_task("test_task")
        assert success
        assert runner.get_task("test_task") is None

    def test_enable_disable_task(self, runner):
        task = ScheduledTask(
            id="test_task",
            name="Test Task",
            description="A test task",
            trigger=TaskTrigger.INTERVAL,
            schedule="60",
            enabled=True,
        )

        async def handler(t):
            pass

        runner.register_task(task, handler)

        # Disable
        runner.disable_task("test_task")
        retrieved = runner.get_task("test_task")
        assert not retrieved.enabled
        assert retrieved.status == TaskStatus.DISABLED

        # Enable
        runner.enable_task("test_task")
        retrieved = runner.get_task("test_task")
        assert retrieved.enabled

    def test_calculate_next_run_interval(self, runner):
        import time

        task = ScheduledTask(
            id="test_task",
            name="Test Task",
            description="A test task",
            trigger=TaskTrigger.INTERVAL,
            schedule="60",
        )

        next_run = runner._calculate_next_run(task)
        now = time.time()

        # Should be ~60 seconds from now
        assert next_run is not None
        assert 58 < next_run - now < 62

    def test_persistence(self, temp_db):
        """Test that tasks are persisted to database."""
        # Create runner and add task
        runner1 = TaskRunner(db_path=temp_db)
        task = ScheduledTask(
            id="persisted_task",
            name="Persisted Task",
            description="Should persist",
            trigger=TaskTrigger.INTERVAL,
            schedule="300",
        )

        async def handler(t):
            pass

        runner1.register_task(task, handler)

        # Create new runner with same DB
        runner2 = TaskRunner(db_path=temp_db)
        retrieved = runner2.get_task("persisted_task")

        assert retrieved is not None
        assert retrieved.name == "Persisted Task"

    @pytest.mark.asyncio
    async def test_execute_task(self, runner):
        executed = []

        task = ScheduledTask(
            id="exec_task",
            name="Execute Task",
            description="Should execute",
            trigger=TaskTrigger.INTERVAL,
            schedule="60",
            enabled=True,
        )

        async def handler(t):
            executed.append(t.id)

        runner.register_task(task, handler)

        # Manually execute
        await runner._execute_task(task)

        assert len(executed) == 1
        assert executed[0] == "exec_task"

        retrieved = runner.get_task("exec_task")
        assert retrieved.run_count == 1

    @pytest.mark.asyncio
    async def test_task_error_handling(self, runner):
        task = ScheduledTask(
            id="error_task",
            name="Error Task",
            description="Should handle error",
            trigger=TaskTrigger.INTERVAL,
            schedule="60",
            enabled=True,
        )

        async def error_handler(t):
            raise ValueError("Test error")

        runner.register_task(task, error_handler)

        # Execute should not raise
        await runner._execute_task(task)

        retrieved = runner.get_task("error_task")
        assert retrieved.error_count == 1
        assert retrieved.status == TaskStatus.ERROR
        assert "Test error" in retrieved.last_error
