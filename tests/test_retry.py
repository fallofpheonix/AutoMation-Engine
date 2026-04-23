from src.executor import ExecutionResult
from src.retry_engine import RetryConfig, RetryEngine


def test_max_retries_exhaustion_stops_after_configured_attempts():
    engine = RetryEngine(
        RetryConfig(
            max_retries=3,
            initial_backoff_seconds=0.001,
            max_backoff_seconds=0.01,
            backoff_multiplier=2.0,
        )
    )

    call_count = 0

    def always_fail():
        nonlocal call_count
        call_count += 1
        return ExecutionResult(status="failed", duration_ms=1, error="timeout")

    result = engine.execute_with_retry(always_fail, "always_fail")

    assert result.status == "failed"
    assert call_count == 3
    assert result.retry_count == 2


def test_exponential_backoff_sequence_is_applied(monkeypatch):
    config = RetryConfig(
        max_retries=4,
        initial_backoff_seconds=1.0,
        max_backoff_seconds=16.0,
        backoff_multiplier=2.0,
    )
    engine = RetryEngine(config)

    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("src.retry_engine.time.sleep", fake_sleep)

    def always_fail():
        return ExecutionResult(status="failed", duration_ms=1, error="timeout")

    result = engine.execute_with_retry(always_fail, "always_fail")

    assert result.status == "failed"
    assert sleeps == [1.0, 2.0, 4.0]


def test_unknown_errors_are_retried_until_attempt_limit():
    engine = RetryEngine(
        RetryConfig(
            max_retries=3,
            initial_backoff_seconds=0.001,
            max_backoff_seconds=0.01,
            backoff_multiplier=2.0,
        )
    )

    call_count = 0

    def unknown_fail():
        nonlocal call_count
        call_count += 1
        return ExecutionResult(status="failed", duration_ms=1, error="mystery failure")

    result = engine.execute_with_retry(unknown_fail, "unknown_fail")

    assert result.status == "failed"
    assert call_count == 3
    assert result.retry_count == 2
