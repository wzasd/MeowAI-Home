"""Tests for ReviewRouter."""

import pytest
from src.review.router import ReviewRouter, ReviewRouterBuilder
from src.review.watcher import PREvent, PREventType


class TestReviewRouter:
    """Test PR routing logic."""

    @pytest.fixture
    def router(self):
        return ReviewRouter()

    def test_route_by_label_exact_match(self, router):
        router.register_label_rule("backend", "orange")

        event = PREvent(
            event_type=PREventType.PR_OPENED,
            pr_number=42,
            pr_title="Test PR",
            pr_body=None,
            repository="owner/repo",
            branch="main",
            author="dev1",
            labels=["backend", "feature"],
        )

        assignment = router.route(event)

        assert assignment is not None
        assert assignment.assigned_cat_id == "orange"

    def test_route_by_file_path(self, router):
        router.register_path_rule("*.py", "orange")

        event = PREvent(
            event_type=PREventType.PR_OPENED,
            pr_number=42,
            pr_title="Test PR",
            pr_body=None,
            repository="owner/repo",
            branch="main",
            author="dev1",
            changed_files=["src/main.py", "tests/test_main.py"],
        )

        assignment = router.route(event)

        assert assignment is not None
        assert assignment.assigned_cat_id == "orange"

    def test_route_default_reviewer(self, router):
        router.set_default_reviewer("patch")

        event = PREvent(
            event_type=PREventType.PR_OPENED,
            pr_number=42,
            pr_title="Test PR",
            pr_body=None,
            repository="owner/repo",
            branch="main",
            author="dev1",
        )

        assignment = router.route(event)

        assert assignment is not None
        assert assignment.assigned_cat_id == "patch"
