import time
import asyncio
from typing import Callable, Awaitable, Union
from src.executor import ExecutionResult
from src.error_classifier import ErrorClassifier, ErrorType
from src.timeout import execute_with_timeout, execute_with_timeout_sync


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 16.0,
        backoff_multiplier: float = 2.0,
        action_timeout_seconds: int = 10
    ):
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.backoff_multiplier = backoff_multiplier
        self.action_timeout_seconds = action_timeout_seconds


class RetryEngine:
    """Executes actions with exponential backoff retry logic"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.classifier = ErrorClassifier()
    
    def execute_with_retry(
        self,
        action: Callable[[], ExecutionResult],
        action_name: str = "action"
    ) -> ExecutionResult:
        """
        Execute action with retry logic
        
        Args:
            action: Callable that returns ExecutionResult
            action_name: Name of action (for logging)
            
        Returns:
            Final ExecutionResult after retries exhausted or success
        """
        result = None
        
        for attempt in range(self.config.max_retries):
            # Execute action
            result = execute_with_timeout_sync(
                action,
                timeout=self.config.action_timeout_seconds
            )
            result.retry_count = attempt
            
            # Success - return immediately
            if result.status == "success":
                return result
            
            # Classify error
            error_type = self.classifier.classify(result.error or "")
            
            # Permanent error - don't retry
            if error_type == ErrorType.PERMANENT:
                return result
            
            # Last attempt - don't wait
            if attempt == self.config.max_retries - 1:
                return result
            
            # Calculate backoff
            backoff = self.config.initial_backoff_seconds * (
                self.config.backoff_multiplier ** attempt
            )
            backoff = min(backoff, self.config.max_backoff_seconds)
            
            # Wait before retry
            time.sleep(backoff)
        
        return result
    
    async def execute_with_timeout(
        self,
        action: Union[
            Callable[[], ExecutionResult],
            Callable[[], Awaitable[ExecutionResult]]
        ],
        timeout_seconds: float = 10.0,
        action_name: str = "action"
    ) -> ExecutionResult:
        """
        Execute action with timeout
        
        Args:
            action: Callable that returns ExecutionResult
            timeout_seconds: Timeout in seconds
            action_name: Name of action (for logging)
            
        Returns:
            ExecutionResult with status=timeout if exceeded
        """
        # Check if action is async
        if asyncio.iscoroutinefunction(action):
            result = await execute_with_timeout(
                action(),
                timeout=timeout_seconds
            )
        else:
            # Run sync action in executor (non-blocking)
            loop = asyncio.get_event_loop()
            result = await execute_with_timeout(
                loop.run_in_executor(None, action),
                timeout=timeout_seconds
            )
        return result
