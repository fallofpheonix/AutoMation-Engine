import pytest
import uuid
from src.executor import MacExecutor, SimulationMode, ExecutionResult
from src.error_classifier import ErrorClassifier, ErrorType
from src.retry_engine import RetryEngine, RetryConfig
from src.database import Database
from src.orchestrator import TaskOrchestrator
from src.api import create_app
from fastapi.testclient import TestClient


# ========== Executor Tests ==========


class TestExecutor:
    def test_wait_success(self):
        executor = MacExecutor()
        result = executor.wait(0.1)
        assert result.status == "success"
        assert result.duration_ms > 50  # At least 50ms

    def test_simulation_mode(self):
        sim = SimulationMode('windows')
        result = sim.open_application('Outlook')
        assert result.status == "success"
        assert "[SIMULATION - WINDOWS]" in str(result.error)


# ========== Error Classifier Tests ==========


class TestErrorClassifier:
    def setup_method(self):
        self.classifier = ErrorClassifier()
    
    def test_temporary_error(self):
        result = self.classifier.classify("Element not found")
        assert result == ErrorType.TEMPORARY
    
    def test_permanent_error(self):
        result = self.classifier.classify("Permission denied")
        assert result == ErrorType.PERMANENT
    
    def test_unknown_error(self):
        result = self.classifier.classify("Some random error")
        assert result == ErrorType.UNKNOWN


# ========== Retry Engine Tests ==========


class TestRetryEngine:
    def setup_method(self):
        self.engine = RetryEngine()
    
    def test_success_first_try(self):
        result = self.engine.execute_with_retry(
            lambda: ExecutionResult(status="success", duration_ms=100),
            "test"
        )
        assert result.status == "success"
        assert result.retry_count == 0
    
    def test_retry_on_temporary_error(self):
        call_count = 0
        
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return ExecutionResult(
                    status="failed",
                    duration_ms=100,
                    error="timeout"
                )
            return ExecutionResult(status="success", duration_ms=100)
        
        result = self.engine.execute_with_retry(flaky, "flaky_action")
        assert result.status == "success"
        assert call_count == 2
    
    def test_no_retry_on_permanent_error(self):
        call_count = 0
        
        def permanent_fail():
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status="failed",
                duration_ms=100,
                error="Permission denied"
            )
        
        result = self.engine.execute_with_retry(permanent_fail, "perm")
        assert result.status == "failed"
        assert call_count == 1  # No retry


# ========== Database Tests ==========


class TestDatabase:
    def setup_method(self):
        self.db = Database(':memory:')
    
    def test_create_task(self):
        task_id = str(uuid.uuid4())
        result = self.db.create_task(task_id, "test")
        assert result is True
    
    def test_get_task(self):
        task_id = str(uuid.uuid4())
        self.db.create_task(task_id, "test")
        task = self.db.get_task(task_id)
        assert task is not None
        assert task['status'] == "pending"
    
    def test_update_task_status(self):
        task_id = str(uuid.uuid4())
        self.db.create_task(task_id, "test")
        self.db.update_task_status(task_id, "running")
        task = self.db.get_task(task_id)
        assert task['status'] == "running"
    
    def test_logging(self):
        task_id = str(uuid.uuid4())
        self.db.create_task(task_id, "test")
        self.db.log(task_id, "Test message")
        logs = self.db.get_task_logs(task_id)
        assert len(logs) >= 1


# ========== Orchestrator Tests ==========


class TestOrchestrator:
    def setup_method(self):
        self.executor = SimulationMode('windows')
        self.db = Database(':memory:')
        self.orchestrator = TaskOrchestrator(self.executor, self.db)
    
    def test_execute_single_step(self):
        task_id = str(uuid.uuid4())
        self.db.create_task(task_id, "test")
        
        result = self.orchestrator._execute_single_step(
            task_id,
            1,
            {'action': 'wait', 'seconds': 0.1}
        )
        
        assert result['status'] == 'success'
        assert result['step_number'] == 1
    
    def test_execute_full_task(self):
        task_id = str(uuid.uuid4())
        self.db.create_task(task_id, "test")
        
        steps = [
            {'action': 'wait', 'seconds': 0.05},
            {'action': 'wait', 'seconds': 0.05}
        ]
        
        result = self.orchestrator.execute_task(task_id, steps)
        
        assert result['status'] == 'success'
        assert result['completed_steps'] == 2


# ========== API Tests ==========


class TestAPI:
    def setup_method(self):
        executor = SimulationMode('windows')
        db = Database(':memory:')
        self.app = create_app(executor, db)
        self.client = TestClient(self.app)
    
    def test_health_check(self):
        response = self.client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'
    
    def test_create_task(self):
        response = self.client.post('/tasks', json={
            'name': 'test',
            'steps': [{'action': 'wait', 'seconds': 0.1}]
        })
        assert response.status_code == 200
        assert 'task_id' in response.json()
    
    def test_execute_task(self):
        response = self.client.post('/tasks/execute', json={
            'name': 'test',
            'steps': [
                {'action': 'wait', 'seconds': 0.05},
                {'action': 'open_app', 'app': 'Notes'}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['completed_steps'] == 2
    
    def test_get_metrics(self):
        # Execute one task first
        self.client.post('/tasks/execute', json={
            'name': 'test',
            'steps': [{'action': 'wait', 'seconds': 0.05}]
        })
        
        # Get metrics
        response = self.client.get('/metrics')
        assert response.status_code == 200
        data = response.json()
        assert data['total_tasks'] >= 1
        assert 0 <= data['success_rate'] <= 100
