import logging
import queue
import threading
import time
import traceback

from comet.driver import Driver as DefaultDriver
from comet.process import Process
from comet.resource import ResourceMixin

__all__ = ["ResourceProcess", "async_request"]

logger = logging.getLogger(__name__)


def async_request(method):
    def async_request(self, *args, **kwargs):
        self.async_request(lambda context: method(self, context, *args, **kwargs))
    return async_request


class ResourceRequest:

    def __init__(self, command):
        self.command = command
        self.ready = threading.Event()
        self.result = None
        self.error = None

    def get(self, timeout=10.0):
        t = time.time() + timeout
        while not self.ready.is_set():
            if t < time.time():
                raise RuntimeError(f"Request timeout: {self.command}")
        if self.error is not None:
            raise self.error
        return self.result

    def __call__(self, context):
        try:
            self.result = self.command(context)
        except Exception as exc:
            self.error = exc
            raise
        finally:
            self.ready.set()


class ResourceProcess(Process, ResourceMixin):

    Driver = DefaultDriver

    throttle_time = 0.001

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
            r = ResourceRequest(callback)
            self._queue.put(r)

    def request(self, callback):
        with self._lock:
            if not self.enabled:
                raise RuntimeError("service not enabled")
            r = ResourceRequest(callback)
            self._queue.put(r)
            return r.get()

    def serve(self):
        logger.info("start serving %s", self.name)
        try:
            with self.resources.get(self.name) as resource:
                driver = type(self).Driver(resource)
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
