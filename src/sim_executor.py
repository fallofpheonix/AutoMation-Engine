from src.executor import Executor, ExecutionResult
import time


class SimExecutor(Executor):
    def open_application(self, app_name: str):
        return self._simulate("open_app", {"app": app_name})

    def click(self, target):
        return self._simulate("click", {"target": target})

    def type(self, text: str):
        return self._simulate("type", {"text": text})

    def wait(self, seconds: float):
        time.sleep(seconds)
        return ExecutionResult(status="success", duration_ms=int(seconds * 1000), error=None)

    def close_application(self, app_name: str):
        return self._simulate("close_app", {"app": app_name})

    def _simulate(self, action, params):
        start = time.time()
        # no real execution
        return ExecutionResult(
            status="success",
            duration_ms=int((time.time() - start) * 1000),
            error=None
        )
