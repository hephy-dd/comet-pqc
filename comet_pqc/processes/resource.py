import logging
import queue
import threading
import time
import traceback
from typing import Any, Callable, Optional

from comet.driver import Driver as DefaultDriver
from comet.process import Process
from comet.resource import ResourceMixin

from ..core.request import Request
from ..core.timer import Timer

__all__ = ["ResourceProcess", "async_request"]

logger = logging.getLogger(__name__)


def async_request(method):
    def async_request(self, *args, **kwargs):
        self.async_request(lambda context: method(self, context, *args, **kwargs))
    return async_request


class ResourceProcess(Process, ResourceMixin):

    Driver = DefaultDriver

    throttle_time: float = 0.001

    update_monitoring_interval: float = 1.0

    def __init__(self, name: str, enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.name: str = name
        self.enabled: bool = enabled
        self._failed_retries: int = 0
        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.RLock()
        self._context_lock = threading.RLock()

    def __enter__(self):
        self._context_lock.acquire()
        return self

    def __exit__(self, *exc):
        self._context_lock.release()
        return False

    def async_request(self, callback):
        with self._lock:
            if not self.enabled:
                raise RuntimeError("service not enabled")
            request = Request(callback)
            self._queue.put_nowait(request)
            return request

    def update_monitoring(self):
        ...

    def serve(self):
        logger.info("start serving %s", self.name)
        try:
            with self.resources.get(self.name) as resource:
                driver = type(self).Driver(resource)
                t = Timer()
                while True:
                    if not self.running:
                        break
                    if not self.enabled:
                        break
                    try:
                        request = self._queue.get(timeout=self.throttle_time)
                    except queue.Empty:
                        ...
                    else:
                        try:
                            request(driver)
                        finally:
                            self._queue.task_done()
                    # Update monitoring in periodic intervals
                    if t.delta() >= self.update_monitoring_interval:
                        self.update_monitoring()
                        t.reset()
        finally:
            logger.info("stopped serving %s", self.name)

    def run(self):
        while self.running:
            if self.enabled:
                try:
                    self.serve()
                except Exception as exc:
                    logger.error("%s: %s", type(self).__name__, exc)
                    #tb = traceback.format_exc()
                    #self.emit("failed", exc, tb)
            time.sleep(self.throttle_time)
