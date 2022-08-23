import threading
from typing import Any, Callable, Optional

__all__ = ["Request", "RequestTimeout"]


class RequestTimeout(Exception):

    ...


class Request:

    timeout: float = 4.0

    def __init__(self, target: Callable) -> None:
        self._target: Callable = target
        self._ready: threading.Event = threading.Event()
        self._result: Optional[Any] = None
        self._exc: Optional[Exception] = None

    def __call__(self, *args, **kwargs) -> None:
        try:
            self._result = self._target(*args, **kwargs)
        except Exception as exc:
            self._exc = exc
        finally:
            self._ready.set()

    def get(self, timeout: float = None) -> Any:
        if timeout is None:
            timeout = self.timeout
        if self._ready.wait(timeout=timeout):
            if self._exc is not None:
                raise self._exc
            return self._result
        raise RequestTimeout(f"Request timeout: {self._target}")
