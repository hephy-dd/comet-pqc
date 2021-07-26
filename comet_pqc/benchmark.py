import time

class Benchmark:
    """Bench mark context manager."""

    def __init__(self, name):
        self.name = name
        self.history = []
        self.t0 = None

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        delta = time.time() - self.t0
        self.history.append(delta)
        self.t0 = None
        return False

    def clear(self):
        self.history.clear()

    @property
    def count(self):
        return len(self.history)

    @property
    def average(self):
        if self.history:
            return sum(self.history) / len(self.history)
        return 0.

    @property
    def minimum(self):
        return min(self.history or [0.])

    @property
    def maximum(self):
        return max(self.history or [0.])

    def __str__(self):
        return f"{self.__class__.__name__}[{self.name}](n={self.count:d}, avg={self.average:.6f}s, min={self.minimum:.6f}s, max={self.maximum:.6f}s)"
