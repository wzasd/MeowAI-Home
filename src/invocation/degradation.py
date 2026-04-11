"""DegradationPolicy — context budget, retry, overflow circuit breaker."""
from enum import Enum
from typing import Dict, Any, Optional, Set
import time


class BudgetLevel(Enum):
    FULL = "full"
    TRUNCATED = "truncated"
    ABORT = "abort"


class ExtractionLevel(Enum):
    NONE = "none"
    ESSENTIAL = "essential"
    FULL = "full"


class RetryRecord:
    """Record of retry attempts for an operation."""

    def __init__(self):
        self.attempt_count = 0
        self.consecutive_failures = 0
        self.last_error: Optional[str] = None
        self.last_attempt_at: Optional[float] = None


class CircuitBreaker:
    """Circuit breaker for overflow protection."""

    def __init__(self, threshold: int = 3):
        self._threshold = threshold
        self._failure_count: Dict[str, int] = {}
        self._is_open: Set[str] = set()

    def record_success(self, key: str) -> None:
        """Record successful operation."""
        self._failure_count[key] = 0
        self._is_open.discard(key)

    def record_failure(self, key: str) -> bool:
        """Record failed operation. Returns True if circuit is now open."""
        self._failure_count[key] = self._failure_count.get(key, 0) + 1

        if self._failure_count[key] >= self._threshold:
            self._is_open.add(key)
            return True
        return False

    def is_open(self, key: str) -> bool:
        """Check if circuit breaker is open for key."""
        return key in self._is_open

    def reset(self, key: Optional[str] = None) -> None:
        """Reset circuit breaker."""
        if key:
            self._failure_count.pop(key, None)
            self._is_open.discard(key)
        else:
            self._failure_count.clear()
            self._is_open.clear()


class DegradationPolicy:
    """Manages context budget limits, retry logic, and overflow handling."""

    MAX_PROMPT_TOKENS = 180_000
    MAX_CONTEXT_TOKENS = 150_000
    MAX_RETRY_ATTEMPTS = 2
    OVERFLOW_THRESHOLD = 3

    RETRYABLE_ERRORS = {"stale_session", "timeout", "prompt_limit", "rate_limit"}

    def __init__(
        self,
        max_prompt_tokens: int = MAX_PROMPT_TOKENS,
        max_context_tokens: int = MAX_CONTEXT_TOKENS,
        max_retry_attempts: int = MAX_RETRY_ATTEMPTS,
        overflow_threshold: int = OVERFLOW_THRESHOLD,
    ):
        self._max_prompt_tokens = max_prompt_tokens
        self._max_context_tokens = max_context_tokens
        self._max_retry_attempts = max_retry_attempts
        self._overflow_threshold = overflow_threshold
        self._circuit_breaker = CircuitBreaker(threshold=overflow_threshold)
        self._retry_records: Dict[str, RetryRecord] = {}

    def check_context_budget(self, prompt_tokens: int, context_tokens: int) -> BudgetLevel:
        """Check if context is within budget limits.

        - FULL: within normal limits
        - TRUNCATED: within 1.2x limits (can proceed with truncation)
        - ABORT: beyond 1.2x limits
        """
        prompt_limit_1_2x = int(self._max_prompt_tokens * 1.2)
        context_limit_1_2x = int(self._max_context_tokens * 1.2)

        # Within normal limits
        if prompt_tokens <= self._max_prompt_tokens and context_tokens <= self._max_context_tokens:
            return BudgetLevel.FULL

        # Within 1.2x limits - can truncate
        if prompt_tokens <= prompt_limit_1_2x and context_tokens <= context_limit_1_2x:
            return BudgetLevel.TRUNCATED

        # Beyond limits - abort
        return BudgetLevel.ABORT

    def should_retry(self, attempt_count: int, error_code: str) -> bool:
        """Check if error is retryable and within max attempts."""
        if attempt_count >= self._max_retry_attempts:
            return False
        if error_code not in self.RETRYABLE_ERRORS:
            return False
        return True

    def get_retry_record(self, operation_id: str) -> RetryRecord:
        """Get or create retry record for operation."""
        if operation_id not in self._retry_records:
            self._retry_records[operation_id] = RetryRecord()
        return self._retry_records[operation_id]

    def record_attempt(self, operation_id: str, error_code: Optional[str] = None) -> bool:
        """Record an attempt. Returns True if should retry."""
        record = self.get_retry_record(operation_id)
        record.attempt_count += 1
        record.last_attempt_at = time.time()

        if error_code:
            record.last_error = error_code
            record.consecutive_failures += 1

            # Check circuit breaker
            if self._circuit_breaker.record_failure(operation_id):
                return False  # Circuit open

            return self.should_retry(record.attempt_count - 1, error_code)
        else:
            # Success
            record.consecutive_failures = 0
            self._circuit_breaker.record_success(operation_id)
            return False

    def check_overflow(self, consecutive_failures: int) -> bool:
        """Check if overflow threshold is reached (circuit breaker)."""
        return consecutive_failures >= self._overflow_threshold

    def is_circuit_open(self, key: str) -> bool:
        """Check if circuit breaker is open for key."""
        return self._circuit_breaker.is_open(key)

    def reset_circuit(self, key: Optional[str] = None) -> None:
        """Reset circuit breaker."""
        self._circuit_breaker.reset(key)

    def truncate_context(self, context: str, target_tokens: int) -> str:
        """Truncate context to target token count.

        Uses a simple heuristic: ~4 chars per token.
        """
        chars_per_token = 4
        max_chars = target_tokens * chars_per_token

        if len(context) <= max_chars:
            return context

        # Try to truncate at a sentence boundary
        truncated = context[:max_chars]
        last_sentence = max(
            truncated.rfind(". "),
            truncated.rfind("! "),
            truncated.rfind("? "),
        )

        if last_sentence > max_chars * 0.8:
            return truncated[:last_sentence + 1] + "\n\n[...内容已截断...]"

        return truncated + "\n\n[...内容已截断...]"

    def format_degradation_message(self, level: BudgetLevel) -> str:
        """Format user-facing message for degradation level."""
        if level == BudgetLevel.TRUNCATED:
            return "上下文已截断以符合长度限制"
        elif level == BudgetLevel.ABORT:
            return "请求超出上下文长度限制，已中止"
        return ""

    def get_stats(self) -> Dict[str, Any]:
        """Get policy statistics."""
        return {
            "max_prompt_tokens": self._max_prompt_tokens,
            "max_context_tokens": self._max_context_tokens,
            "max_retry_attempts": self._max_retry_attempts,
            "overflow_threshold": self._overflow_threshold,
            "active_retry_records": len(self._retry_records),
            "open_circuits": len(self._circuit_breaker._is_open),
        }
