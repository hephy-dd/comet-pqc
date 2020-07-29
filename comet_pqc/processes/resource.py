import logging
import queue
import threading
import time
import traceback

from comet.driver import Driver as DefaultDriver
from comet.process import Process
from comet.resource import ResourceMixin

__all__ = ['ResourceProcess']

class ResourceRequest:

    def __init__(self, command):
        self.command = command
        self.result = None
        #self.error = None
        self.ready = threading.Event()

    def get(self, timeout=10.0):
        t = time.time() + timeout
        while not self.ready.is_set():
            if t < time.time():
                raise RuntimeError(f"Request timeout: {self.command}")
        #if self.error is not None:
        #    raise self.error
        return self.result

    def dispatch(self, context):
        try:
            self.result = self.command(context)
        except:
            raise
        finally:
            self.ready.set()

class ResourceProcess(Process, ResourceMixin):

    Driver = DefaultDriver

    throttle_time = 0.001

    def __init__(self, name, enabled=True, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.enabled = enabled
        self.__queue = queue.Queue()
        self.__lock = threading.RLock()
        self.__context_lock = threading.RLock()

    def __enter__(self):
        self.__context_lock.acquire()
        return self

    def __exit__(self, *exc):
        self.__context_lock.release()
        return False

    @property
    def enabled(self):
        return self.__enabled

    @enabled.setter
    def enabled(self, value):
        self.__enabled = value

    def request(self, callback):
        with self.__lock:
            r = ResourceRequest(callback)
            self.__queue.put(r)
            return r.get()

    def serve(self):
        with self.resources.get(self.name) as resource:
            driver = type(self).Driver(resource)
            while True:
                if not self.running:
                    break
                if not self.enabled:
                    break
                if not self.__queue.empty():
                    r = self.__queue.get()
                    r.dispatch(driver)
                time.sleep(self.throttle_time)

    def run(self):
        while self.running:
            if self.enabled:
                self.serve()
                try:
                    self.serve()
                except Exception as exc:
                    logging.error("%s: %s", type(self).__name__, exc)
                    tb = traceback.format_exc()
                    self.emit('failed', exc, tb)
