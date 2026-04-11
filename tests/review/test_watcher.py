"""Tests for ReviewWatcher."""

import pytest
from src.review.watcher import (
    ReviewWatcher,
    PREvent,
    PREventType,
    PRStatus,
)


class TestReviewWatcher:
    """Test GitHub webhook handling."""

    @pytest.fixture
    def watcher(self):
        return ReviewWatcher(webhook_secret=None)

    def test_parse_pr_opened_event(self, watcher):
        payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "body": "This PR adds a cool feature",
                "head": {"ref": "feature-branch"},
                "user": {"login": "developer1"},
                "labels": [{"name": "enhancement"}],
                "requested_reviewers": [],
            },
            "repository": {"full_name": "owner/repo"},
        }

        event = watcher.parse_event("pull_request", payload)

        assert event is not None
        assert event.event_type == PREventType.PR_OPENED
        assert event.pr_number == 42
        assert event.pr_title == "Add new feature"
        assert event.repository == "owner/repo"
        assert event.branch == "feature-branch"
        assert event.author == "developer1"
        assert event.labels == ["enhancement"]
        assert event.needs_review

    def test_parse_pr_synchronize_event(self, watcher):
        payload = {
            "action": "synchronize",
            "number": 42,
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "head": {"ref": "feature-branch"},
                "user": {"login": "developer1"},
                "labels": [],
            },
            "repository": {"full_name": "owner/repo"},
        }

        event = watcher.parse_event("pull_request", payload)

        assert event is not None
        assert event.event_type == PREventType.PR_SYNCHRONIZE
        assert event.is_update
        assert event.needs_review

    def test_parse_review_submitted_event(self, watcher):
        payload = {
            "action": "submitted",
            "review": {
                "state": "approved",
                "body": "LGTM!",
                "user": {"login": "reviewer1"},
            },
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "head": {"ref": "feature-branch"},
                "labels": [],
            },
            "repository": {"full_name": "owner/repo"},
        }

        event = watcher.parse_event("pull_request_review", payload)

        assert event is not None
        assert event.event_type == PREventType.REVIEW_SUBMITTED
        assert event.review_state == "approved"
        assert event.review_body == "LGTM!"

    def test_parse_unhandled_event(self, watcher):
        payload = {"action": "labeled"}

        event = watcher.parse_event("pull_request", payload)

        assert event is None

    def test_update_tracking_new_pr(self, watcher):
        event = PREvent(
            event_type=PREventType.PR_OPENED,
            pr_number=42,
            pr_title="Test PR",
            pr_body=None,
            repository="owner/repo",
            branch="main",
            author="dev1",
        )

        watcher._update_tracking(event)

        tracking = watcher.get_tracking("owner/repo", 42)
        assert tracking is not None
        assert tracking.pr_number == 42
        assert tracking.status == PRStatus.PENDING
        assert tracking.assigned_cat_id is None

    def test_list_pending_reviews(self, watcher):
        # Create PRs
        watcher._update_tracking(PREvent(
            event_type=PREventType.PR_OPENED,
            pr_number=1,
            pr_title="Pending PR",
            pr_body=None,
            repository="owner/repo",
            branch="main",
            author="dev1",
        ))

        watcher._update_tracking(PREvent(
            event_type=PREventType.PR_OPENED,
            pr_number=2,
            pr_title="Another pending",
            pr_body=None,
            repository="owner/repo",
            branch="main",
            author="dev2",
        ))

        pending = watcher.list_pending_reviews()

        assert len(pending) == 2
