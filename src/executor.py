from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union, Optional
import time


@dataclass
class ExecutionResult:
    """Result of executing an action"""
    status: str  # "success", "failed", "timeout"
    duration_ms: float
    error: Optional[str] = None
    retry_count: int = 0


class Executor(ABC):
    """Abstract base class for OS executors"""
    
    @abstractmethod
    def open_application(self, app_name: str) -> ExecutionResult:
        """Open an application by name"""
        pass
    
    @abstractmethod
    def click(self, target: Union[str, tuple]) -> ExecutionResult:
        """Click on target (string name or coordinates tuple)"""
        pass
    
    @abstractmethod
    def type(self, text: str) -> ExecutionResult:
        """Type text into focused field"""
        pass
    
    @abstractmethod
    def wait(self, seconds: float) -> ExecutionResult:
        """Wait for specified seconds"""
        pass
    
    @abstractmethod
    def close_application(self, app_name: str) -> ExecutionResult:
        """Close an application"""
        pass


class MacExecutor(Executor):
    """macOS implementation of executor"""
    
    def open_application(self, app_name: str) -> ExecutionResult:
        import subprocess
        
        start_time = time.time()
        try:
            subprocess.call(['open', '-a', app_name])
            time.sleep(1)  # Wait for app to open
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(status="success", duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                status="failed",
                duration_ms=duration,
                error=f"Failed to open {app_name}: {str(e)}"
            )
    
    def click(self, target: Union[str, tuple]) -> ExecutionResult:
        """
        Click implementation for macOS
        For now, returns success (full implementation requires accessibility APIs)
        """
        start_time = time.time()
        try:
            # Placeholder: In real implementation, use PyObjC or accessibility APIs
            time.sleep(0.5)  # Simulate click duration
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(status="success", duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                status="failed",
                duration_ms=duration,
                error=str(e)
            )
    
    def type(self, text: str) -> ExecutionResult:
        """
        Type implementation for macOS
        """
        start_time = time.time()
        try:
            # Placeholder: Full implementation would use PyObjC
            time.sleep(0.1 * len(text))  # Simulate typing speed
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(status="success", duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                status="failed",
                duration_ms=duration,
                error=str(e)
            )
    
    def wait(self, seconds: float) -> ExecutionResult:
        start_time = time.time()
        try:
            time.sleep(seconds)
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(status="success", duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                status="failed",
                duration_ms=duration,
                error=str(e)
            )
    
    def close_application(self, app_name: str) -> ExecutionResult:
        import subprocess
        
        start_time = time.time()
        try:
            subprocess.call(['killall', app_name])
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(status="success", duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                status="failed",
                duration_ms=duration,
                error=f"Failed to close {app_name}: {str(e)}"
            )


class WindowsExecutor(Executor):
    """
    Windows implementation using pywinauto + UIAutomation
    
    Note: This is designed but not tested on Windows.
    Testing requires Windows environment or VM.
    """
    
    def open_application(self, app_name: str) -> ExecutionResult:
        """
        Windows implementation plan:
        
        from pywinauto import Application
        app = Application(backend='uia').start(app_name)
        
        Challenges:
        - App path varies by installation location
        - Solution: Store in config.json or env var
        - May require admin privileges
        
        Error handling:
        - "not found" -> temporary (retry)
        - "permission denied" -> permanent (don't retry)
        """
        raise NotImplementedError("Requires Windows environment for testing")
    
    def click(self, target: Union[str, tuple]) -> ExecutionResult:
        """
        Windows implementation plan:
        
        if isinstance(target, tuple):
            # Click by coordinates
            pyautogui.click(target[0], target[1])
        else:
            # Click by element name using UIAutomation
            element = app[window_name].child_window(
                title_re=target,
                control_type='Button'
            )
            element.click_input()
        
        Challenges:
        - UIAutomation tree varies per application
        - Solution: Use Inspect.exe to explore UI
        - May need fallback to coordinates
        """
        raise NotImplementedError("Requires Windows environment for testing")
    
    def type(self, text: str) -> ExecutionResult:
        """
        Windows implementation plan:
        
        window.type_keys(text)
        # Special keys: {ENTER}, {BACKSPACE}, {ESCAPE}
        # Example: window.type_keys('Hello{ENTER}')
        """
        raise NotImplementedError("Requires Windows environment for testing")
    
    def wait(self, seconds: float) -> ExecutionResult:
        """Windows implementation: Same as macOS"""
        raise NotImplementedError("Requires Windows environment for testing")
    
    def close_application(self, app_name: str) -> ExecutionResult:
        """
        Windows implementation plan:
        
        from pywinauto import Application
        app = Application().connect(title_re=f'.*{app_name}.*')
        app.kill()
        
        Or use taskkill:
        subprocess.call(['taskkill', '/IM', f'{app_name}.exe'])
        """
        raise NotImplementedError("Requires Windows environment for testing")


class SimulationMode(Executor):
    """
    Executor that simulates behavior without actually executing.
    Useful for testing Windows paths on macOS.
    """
    
    def __init__(self, target_os: str = "windows"):
        self.target_os = target_os
    
    def open_application(self, app_name: str) -> ExecutionResult:
        if self.target_os == "windows":
            message = (
                f"[SIMULATION - WINDOWS] Would execute: "
                f"Application(backend='uia').start('{app_name}')"
            )
        else:
            message = f"[SIMULATION - MAC] Would execute: open -a {app_name}"
        
        return ExecutionResult(
            status="success",
            duration_ms=0,
            error=message  # Store simulation info in error field for now
        )
    
    def click(self, target: Union[str, tuple]) -> ExecutionResult:
        if isinstance(target, tuple):
            message = (
                f"[SIMULATION - {self.target_os.upper()}] "
                f"Would click at coordinates {target}"
            )
        else:
            message = (
                f"[SIMULATION - {self.target_os.upper()}] "
                f"Would find and click element: {target}"
            )
        
        return ExecutionResult(status="success", duration_ms=0, error=message)
    
    def type(self, text: str) -> ExecutionResult:
        message = f"[SIMULATION - {self.target_os.upper()}] Would type: '{text}'"
        return ExecutionResult(status="success", duration_ms=0, error=message)
    
    def wait(self, seconds: float) -> ExecutionResult:
        message = f"[SIMULATION - {self.target_os.upper()}] Would wait {seconds} seconds"
        return ExecutionResult(status="success", duration_ms=0, error=message)
    
    def close_application(self, app_name: str) -> ExecutionResult:
        message = f"[SIMULATION - {self.target_os.upper()}] Would close: {app_name}"
        return ExecutionResult(status="success", duration_ms=0, error=message)
