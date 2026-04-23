import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from src.models import ExecutionResult


async def execute_with_timeout(coro, timeout: int):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return ExecutionResult(
            status="timeout",
            duration_ms=timeout * 1000,
            error="Action timed out"
        )


def execute_with_timeout_sync(func, timeout: int):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            return ExecutionResult(
                status="timeout",
                duration_ms=timeout * 1000,
                error="Action timed out"
            )
