"""Tests for DegradationPolicy (A3)."""
import pytest
from src.invocation.degradation import (
    DegradationPolicy,
    BudgetLevel,
    ExtractionLevel,
)


class TestContextBudget:
    def test_full_budget_within_limits(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(100_000, 80_000)
        assert result == BudgetLevel.FULL

    def test_full_budget_at_exact_limit(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(
            DegradationPolicy.MAX_PROMPT_TOKENS,
            DegradationPolicy.MAX_CONTEXT_TOKENS,
        )
        assert result == BudgetLevel.FULL

    def test_truncated_when_prompt_exceeds_limit(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(190_000, 100_000)
        assert result == BudgetLevel.TRUNCATED

    def test_truncated_when_context_exceeds_limit(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(100_000, 170_000)
        assert result == BudgetLevel.TRUNCATED

    def test_truncated_at_1_2x_boundary(self):
        policy = DegradationPolicy()
        # Exactly at 1.2x prompt limit should still be truncated
        result = policy.check_context_budget(
            int(DegradationPolicy.MAX_PROMPT_TOKENS * 1.2),
            DegradationPolicy.MAX_CONTEXT_TOKENS,
        )
        assert result == BudgetLevel.TRUNCATED

    def test_abort_when_way_over_limit(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(250_000, 200_000)
        assert result == BudgetLevel.ABORT

    def test_abort_when_prompt_beyond_1_2x(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(
            int(DegradationPolicy.MAX_PROMPT_TOKENS * 1.2) + 1,
            DegradationPolicy.MAX_CONTEXT_TOKENS,
        )
        assert result == BudgetLevel.ABORT

    def test_zero_tokens_is_full(self):
        policy = DegradationPolicy()
        result = policy.check_context_budget(0, 0)
        assert result == BudgetLevel.FULL


class TestShouldRetry:
    def test_retry_stale_session_first_attempt(self):
        policy = DegradationPolicy()
        assert policy.should_retry(0, "stale_session") is True

    def test_retry_timeout_second_attempt(self):
        policy = DegradationPolicy()
        assert policy.should_retry(1, "timeout") is True

    def test_retry_prompt_limit_first_attempt(self):
        policy = DegradationPolicy()
        assert policy.should_retry(0, "prompt_limit") is True

    def test_no_retry_at_max_attempts(self):
        policy = DegradationPolicy()
        assert policy.should_retry(DegradationPolicy.MAX_RETRY_ATTEMPTS, "timeout") is False

    def test_no_retry_for_unknown_error(self):
        policy = DegradationPolicy()
        assert policy.should_retry(0, "unknown_error") is False

    def test_no_retry_for_auth_error(self):
        policy = DegradationPolicy()
        assert policy.should_retry(0, "auth_failure") is False

    def test_no_retry_beyond_max(self):
        policy = DegradationPolicy()
        assert policy.should_retry(5, "stale_session") is False

    def test_retry_last_allowed_attempt(self):
        policy = DegradationPolicy()
        assert policy.should_retry(DegradationPolicy.MAX_RETRY_ATTEMPTS - 1, "timeout") is True


class TestOverflow:
    def test_overflow_at_threshold(self):
        policy = DegradationPolicy()
        assert policy.check_overflow(DegradationPolicy.OVERFLOW_THRESHOLD) is True

    def test_no_overflow_below_threshold(self):
        policy = DegradationPolicy()
        assert policy.check_overflow(DegradationPolicy.OVERFLOW_THRESHOLD - 1) is False

    def test_overflow_at_high_count(self):
        policy = DegradationPolicy()
        assert policy.check_overflow(10) is True

    def test_no_overflow_at_zero(self):
        policy = DegradationPolicy()
        assert policy.check_overflow(0) is False


class TestDegradationMessages:
    def test_truncated_message(self):
        policy = DegradationPolicy()
        msg = policy.format_degradation_message(BudgetLevel.TRUNCATED)
        assert "截断" in msg
        assert len(msg) > 0

    def test_abort_message(self):
        policy = DegradationPolicy()
        msg = policy.format_degradation_message(BudgetLevel.ABORT)
        assert "超出" in msg or "限制" in msg
        assert len(msg) > 0

    def test_full_returns_empty_string(self):
        policy = DegradationPolicy()
        msg = policy.format_degradation_message(BudgetLevel.FULL)
        assert msg == ""
