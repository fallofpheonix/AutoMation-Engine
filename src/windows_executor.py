from typing import Union

from src.executor import Executor


class WindowsExecutor(Executor):
    """
    Uses pywinauto backend.

    TODO:
    - Implement Application().connect(...)
    - Handle UAC elevation
    """

    def open_application(self, app_name: str):
        raise NotImplementedError

    def click(self, target: Union[str, tuple]):
        raise NotImplementedError

    def type(self, text: str):
        raise NotImplementedError

    def wait(self, seconds: float):
        raise NotImplementedError

    def close_application(self, app_name: str):
        raise NotImplementedError
