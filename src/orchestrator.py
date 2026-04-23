import uuid
from typing import List, Dict, Any
from src.executor import Executor, ExecutionResult
from src.retry_engine import RetryEngine, RetryConfig
from src.error_classifier import ErrorClassifier
from src.database import Database


class TaskOrchestrator:
    """Orchestrates task execution: API -> Retry -> Executor -> DB -> Logging"""
    
    def __init__(self, executor: Executor, db: Database):
        self.executor = executor
        self.db = db
        self.retry_engine = RetryEngine(RetryConfig())
        self.classifier = ErrorClassifier()
    
    def execute_task(self, task_id: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a complete task with all steps
        
        Args:
            task_id: Unique task identifier
            steps: List of step dictionaries with 'action' and parameters
            
        Returns:
            Final task status with all results
        """
        # Mark task as running
        self.db.update_task_status(task_id, "running")
        self.db.log(
            task_id,
            f"Starting task execution with {len(steps)} steps",
            action="task_execute",
            params={"step_count": len(steps)},
            status="running",
            duration_ms=0,
            error=None
        )
        
        task_results = {
            'task_id': task_id,
            'total_steps': len(steps),
            'completed_steps': 0,
            'status': 'running',
            'step_results': []
        }
        
        # Execute each step
        for step_num, step in enumerate(steps, 1):
            step_result = self._execute_single_step(
                task_id=task_id,
                step_num=step_num,
                step_data=step
            )
            
            task_results['step_results'].append(step_result)
            
            # Sequential execution: stop on first failed or timed out step.
            if step_result['status'] in ['failed', 'timeout']:
                self.db.log(
                    task_id,
                    f"Step {step_num} stopped task execution: {step_result.get('error')}",
                    severity='error',
                    action="task_execute",
                    params={"failed_step": step_num, "step_action": step_result.get("action")},
                    status=step_result['status'],
                    duration_ms=step_result.get('duration_ms'),
                    error=step_result.get('error')
                )
                break
            
            # Count completed steps
            if step_result['status'] == 'success':
                task_results['completed_steps'] += 1
        
        # Determine final status
        if task_results['completed_steps'] == len(steps):
            final_status = 'success'
        else:
            final_status = 'failed'
        
        task_results['status'] = final_status
        self.db.update_task_status(task_id, final_status)
        self.db.log(
            task_id,
            f"Task execution completed: {final_status} ({task_results['completed_steps']}/{len(steps)} steps)",
            action="task_execute",
            params={
                "step_count": len(steps),
                "completed_steps": task_results['completed_steps']
            },
            status=final_status,
            duration_ms=sum(step.get('duration_ms', 0) for step in task_results['step_results']),
            error=None
        )
        
        return task_results
    
    def _execute_single_step(
        self,
        task_id: str,
        step_num: int,
        step_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single step with retry logic
        
        Args:
            task_id: Parent task ID
            step_num: Step number (for logging)
            step_data: Step data with 'action' and parameters
            
        Returns:
            Step result with status, duration, error info
        """
        action_name = step_data.get('action', 'unknown')
        step_id = f"step_{task_id}_{step_num}"
        
        # Create step record in DB
        self.db.create_step(
            step_id=step_id,
            task_id=task_id,
            step_number=step_num,
            action=action_name,
            action_params=step_data
        )
        
        self.db.log(
            task_id,
            f"Starting step {step_num}: {action_name}",
            step_id=step_id,
            action=action_name,
            params=step_data,
            status="running",
            duration_ms=0,
            error=None
        )

        self.db.update_step_status(step_id, "running")
        
        # Define the action to execute
        def execute_action() -> ExecutionResult:
            if action_name == 'open_app':
                return self.executor.open_application(step_data.get('app'))
            elif action_name == 'click':
                target = step_data.get('target')
                # Handle both string targets and coordinate tuples
                if isinstance(target, list):
                    target = tuple(target)
                return self.executor.click(target)
            elif action_name == 'type':
                return self.executor.type(step_data.get('text', ''))
            elif action_name == 'wait':
                return self.executor.wait(step_data.get('seconds', 1))
            elif action_name == 'close_app':
                return self.executor.close_application(step_data.get('app'))
            else:
                return ExecutionResult(
                    status='failed',
                    duration_ms=0,
                    error=f"Unknown action: {action_name}"
                )
        
        # Execute with retry
        result = self.retry_engine.execute_with_retry(
            action=execute_action,
            action_name=action_name
        )
        
        # Update database
        self.db.update_step_status(step_id, result.status)
        self.db.update_step_result(
            step_id=step_id,
            duration_ms=result.duration_ms,
            error_message=result.error,
            retry_count=result.retry_count
        )
        
        # Log result
        log_msg = (
            f"Step {step_num} ({action_name}): {result.status} "
            f"({result.duration_ms:.0f}ms, retries: {result.retry_count})"
        )
        if result.error:
            log_msg += f" - Error: {result.error}"
        
        severity = 'error' if result.status == 'failed' else 'info'
        self.db.log(
            task_id,
            log_msg,
            severity=severity,
            step_id=step_id,
            action=action_name,
            params=step_data,
            status=result.status,
            duration_ms=result.duration_ms,
            error=result.error
        )
        
        return {
            'step_number': step_num,
            'action': action_name,
            'status': result.status,
            'duration_ms': result.duration_ms,
            'retry_count': result.retry_count,
            'error': result.error
        }
