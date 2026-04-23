from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from src.executor import MacExecutor
from src.database import Database
from src.orchestrator import TaskOrchestrator

# ========== Pydantic Models ==========


class StepInput(BaseModel):
    action: str = Field(..., description="Action name: open_app, click, type, wait, close_app")
    app: Optional[str] = Field(None, description="For open_app and close_app")
    target: Optional[Any] = Field(None, description="For click: string name or [x, y] coordinates")
    text: Optional[str] = Field(None, description="For type action")
    seconds: Optional[float] = Field(None, description="For wait action")


class TaskInput(BaseModel):
    name: Optional[str] = Field("Unnamed Task", description="Task name")
    steps: List[StepInput] = Field(..., description="List of steps to execute")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    name: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class TaskExecutionResponse(BaseModel):
    task_id: str
    status: str
    total_steps: int
    completed_steps: int
    step_results: List[Dict[str, Any]]


class MetricsResponse(BaseModel):
    total_tasks: int
    successful_tasks: int
    success_rate: float
    avg_execution_time_ms: float


class LogEntry(BaseModel):
    timestamp: str
    task_id: str
    step_id: Optional[str]
    action: Optional[str]
    params: Optional[Dict[str, Any]]
    status: Optional[str]
    duration_ms: Optional[float]
    error: Optional[str]
    message: str
    severity: str


# ========== Create FastAPI App ==========


def create_app(executor=None, db=None):
    """Factory function to create FastAPI app"""
    
    app = FastAPI(
        title="Task Automation Engine",
        description="Production-grade task automation system",
        version="1.0.0"
    )
    
    # Initialize components
    _executor = executor or MacExecutor()
    _db = db or Database("tasks.db")
    _orchestrator = TaskOrchestrator(_executor, _db)
    
    # ========== API Endpoints ==========
    
    @app.post("/tasks", response_model=TaskResponse)
    async def create_task(task_input: TaskInput):
        """
        Submit a task for execution
        
        Example:
        {
            "name": "open_notes",
            "steps": [
                {"action": "open_app", "app": "Notes"},
                {"action": "type", "text": "Hello World"}
            ]
        }
        """
        try:
            # Validate steps
            if not task_input.steps:
                raise HTTPException(status_code=400, detail="Task must have at least one step")
            
            # Create task
            task_id = f"task_{str(uuid.uuid4())[:8]}"
            success = _db.create_task(task_id, task_input.name)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create task")
            
            return TaskResponse(
                task_id=task_id,
                status="queued",
                message="Task queued for execution"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
    async def get_task_status(task_id: str):
        """Get task status and details"""
        try:
            task = _db.get_task(task_id)
            
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return TaskStatusResponse(
                task_id=task['id'],
                name=task['name'],
                status=task['status'],
                created_at=task['created_at'],
                started_at=task['started_at'],
                completed_at=task['completed_at']
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tasks/{task_id}/execute", response_model=TaskExecutionResponse)
    async def execute_task(task_id: str):
        """
        Execute a task (runs all steps)
        
        Note: In production, this would be asynchronous job queue.
        For demo, it's synchronous.
        """
        try:
            task = _db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Get steps (in real app, would fetch from DB)
            # For now, return error since we need to fetch steps
            raise HTTPException(
                status_code=400,
                detail="Steps must be provided in task creation. Use POST /tasks with steps."
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tasks/execute", response_model=TaskExecutionResponse)
    async def execute_task_inline(task_input: TaskInput):
        """
        Submit and execute task in one call
        
        Example:
        {
            "name": "test",
            "steps": [
                {"action": "wait", "seconds": 1}
            ]
        }
        """
        try:
            # Validate
            if not task_input.steps:
                raise HTTPException(status_code=400, detail="Task must have at least one step")
            
            # Create task
            task_id = f"task_{str(uuid.uuid4())[:8]}"
            _db.create_task(task_id, task_input.name)
            
            # Convert Pydantic models to dicts for orchestrator
            steps_list = [step.model_dump() for step in task_input.steps]
            
            # Execute
            result = _orchestrator.execute_task(task_id, steps_list)
            
            return TaskExecutionResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/tasks/{task_id}/logs")
    async def get_task_logs(task_id: str):
        """Get all logs for a task"""
        try:
            task = _db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            logs = _db.get_task_logs(task_id)
            
            return {
                'task_id': task_id,
                'log_count': len(logs),
                'logs': [
                    LogEntry(
                        timestamp=log['timestamp'],
                        task_id=log['task_id'],
                        step_id=log['step_id'],
                        action=log['action'],
                        params=log['params'],
                        status=log['status'],
                        duration_ms=log['duration_ms'],
                        error=log['error'],
                        message=log['message'],
                        severity=log['severity']
                    ).model_dump()
                    for log in logs
                ]
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/metrics", response_model=MetricsResponse)
    async def get_metrics():
        """Get system metrics"""
        try:
            metrics = _db.get_metrics()
            return MetricsResponse(**metrics)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}
    
    return app


# Create the app instance
app = create_app()
