import random
import time
from src.executor import Executor, ExecutionResult


class FlakyExecutor(Executor):
    """
    Executor that randomly fails to test retry logic.
    Used for flakiness testing — proves retry system works under chaos.

    Usage:
        executor = FlakyExecutor(flakiness_rate=0.3)  # 30% of actions fail
    """

    def __init__(self, flakiness_rate: float = 0.3, base_executor: Executor = None):
        self.flakiness_rate = flakiness_rate
        self.base_executor = base_executor  # Optional real executor underneath

    def _maybe_fail(self, action_name: str) -> ExecutionResult:
        """Randomly fail based on flakiness_rate"""
        if random.random() < self.flakiness_rate:
            return ExecutionResult(
                status="failed",
                duration_ms=50,
                error=f"[FLAKY] Random failure in {action_name} (rate={self.flakiness_rate})"
            )
        return None  # No failure

    def open_application(self, app_name: str) -> ExecutionResult:
        fail = self._maybe_fail("open_application")
        if fail:
            return fail
        if self.base_executor:
            return self.base_executor.open_application(app_name)
        return ExecutionResult(status="success", duration_ms=100)

    def click(self, target) -> ExecutionResult:
        fail = self._maybe_fail("click")
        if fail:
            return fail
        if self.base_executor:
            return self.base_executor.click(target)
        return ExecutionResult(status="success", duration_ms=50)

    def type(self, text: str) -> ExecutionResult:
        fail = self._maybe_fail("type")
        if fail:
            return fail
        if self.base_executor:
            return self.base_executor.type(text)
        return ExecutionResult(status="success", duration_ms=80)

    def wait(self, seconds: float) -> ExecutionResult:
        fail = self._maybe_fail("wait")
        if fail:
            return fail
        time.sleep(seconds)
        return ExecutionResult(status="success", duration_ms=int(seconds * 1000))

    def close_application(self, app_name: str) -> ExecutionResult:
        fail = self._maybe_fail("close_application")
        if fail:
            return fail
        if self.base_executor:
            return self.base_executor.close_application(app_name)
        return ExecutionResult(status="success", duration_ms=100)
