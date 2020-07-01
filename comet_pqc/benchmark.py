import time

class Benchmark:
    """Bench mark context manager."""

    def __init__(self, name, verbose=False):
        self.name = name
        self.verbose = verbose
        self.history = []
        self.t0 = None

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        delta = time.time() - self.t0
        self.history.append(delta)
        self.t0 = None
        if self.verbose:
            logging.info(format(self))
        return False

    def clear(self):
        self.history.clear()

    @property
    def average(self):
        if self.history:
            return sum(self.history) / len(self.history)
        return 0

    @property
    def count(self):
        return len(self.history)

    def __str__(self):
        return f"{self.__class__.__name__}[{self.name}](average={self.average:.6f} s, count={self.count:d})"
