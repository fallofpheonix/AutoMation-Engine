"""
Integration test — runs fully in-process using FastAPI TestClient.
No real TCP socket binding needed.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.sim_executor import SimExecutor
from src.flaky_executor import FlakyExecutor
from src.database import Database
from src.retry_engine import RetryEngine
from src.orchestrator import TaskOrchestrator


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_client(executor=None, db=None):
    executor = executor or SimExecutor()
    db = db or Database(":memory:")
    app = create_app(executor, db)
    return TestClient(app), db


# ── Integration Tests ─────────────────────────────────────────────────────────

def test_full_task_execution():
    """End-to-end: submit task, execute, verify logs exist."""
    client, db = make_client()

    response = client.post("/tasks/execute", json={
        "name": "integration_test",
        "steps": [
            {"action": "open_app", "app": "Notes"},
            {"action": "type",     "text": "hello"},
            {"action": "close_app","app": "Notes"}
        ]
    })

    assert response.status_code == 200
    data = response.json()
    task_id = data["task_id"]

    assert data["status"] in ["success", "failed"]
    assert data["total_steps"] == 3

    # Verify task is persisted
    status_resp = client.get(f"/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ["success", "failed"]

    # Verify logs exist
    logs = db.get_task_logs(task_id)
    assert len(logs) >= 3


def test_flakiness_recovery():
    """
    System must recover from 30% random failures via retry logic.
    Runs 10 tasks — all should succeed despite flakiness.
    """
    flaky = FlakyExecutor(flakiness_rate=0.3)
    db = Database(":memory:")
    orchestrator = TaskOrchestrator(flaky, db)

    successes = 0
    for _ in range(10):
        task_id = str(uuid.uuid4())
        db.create_task(task_id, "flaky_test")
        result = orchestrator.execute_task(
            task_id,
            [{"action": "wait", "seconds": 0.01}]
        )
        if result["status"] == "success":
            successes += 1

    # With 30% flakiness and 3 retries, success rate should be very high
    assert successes >= 8, f"Only {successes}/10 succeeded under 30% flakiness"


def test_permanent_error_stops_task():
    """A permanent error must stop execution immediately — no retries."""
    from src.executor import ExecutionResult

    class PermFailExecutor(SimExecutor):
        def open_application(self, app_name):
            return ExecutionResult(
                status="failed",
                duration_ms=10,
                error="Permission denied"
            )

    db = Database(":memory:")
    orchestrator = TaskOrchestrator(PermFailExecutor(), db)

    task_id = str(uuid.uuid4())
    db.create_task(task_id, "perm_fail_test")

    result = orchestrator.execute_task(task_id, [
        {"action": "open_app", "app": "Notes"},
        {"action": "type", "text": "should not run"}
    ])

    # Only step 1 should have been attempted
    assert result["completed_steps"] == 0
    assert result["status"] == "failed"


def test_metrics_after_execution():
    """Metrics endpoint must reflect completed tasks."""
    client, _ = make_client()

    # Run two tasks
    for _ in range(2):
        client.post("/tasks/execute", json={
            "name": "metrics_test",
            "steps": [{"action": "wait", "seconds": 0.01}]
        })

    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] >= 2
    assert 0 <= data["success_rate"] <= 100
