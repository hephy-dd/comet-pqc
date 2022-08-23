from typing import List

from .timer import Timer


class Benchmark:
    """Bench mark context manager."""

    def __init__(self, name: str) -> str:
        self.name: str = name
        self.history: List[float] = []
        self.timer: Timer = Timer()

    def __enter__(self) -> "Benchmark":
        self.timer.reset()
        return self

    def __exit__(self, *exc):
        delta = self.timer.delta()
        self.history.append(delta)
        return False

    def clear(self) -> None:
        self.history.clear()

    @property
    def count(self) -> int:
        return len(self.history)

    @property
    def average(self) -> float:
        if self.history:
            return sum(self.history) / len(self.history)
        return 0.

    @property
    def minimum(self) -> float:
        return min(self.history or [0.])

    @property
    def maximum(self) -> float:
        return max(self.history or [0.])

    def __str__(self) -> str:
        return f"{type(self).__name__}[{self.name}](n={self.count:d}, avg={self.average:.6f}s, min={self.minimum:.6f}s, max={self.maximum:.6f}s)"
