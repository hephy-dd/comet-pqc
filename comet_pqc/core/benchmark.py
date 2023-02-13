from typing import List

from .timer import Timer

__all__ = ["Benchmark"]


class Benchmark:
    """Aggregating bench mark context manager."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self._series: List[float] = []
        self._timer: Timer = Timer()

    def __enter__(self) -> "Benchmark":
        self._timer.reset()
        return self

    def __exit__(self, *exc):
        delta = self._timer.delta()
        self._series.append(delta)
        return False

    def clear(self) -> None:
        self._series.clear()

    @property
    def count(self) -> int:
        return len(self._series)

    @property
    def average(self) -> float:
        if self._series:
            return sum(self._series) / len(self._series)
        return 0.

    @property
    def minimum(self) -> float:
        return min(self._series or [0.])

    @property
    def maximum(self) -> float:
        return max(self._series or [0.])

    def __str__(self) -> str:
        return f"{type(self).__name__}[{self.name}](n={self.count:d}, avg={self.average:.6f}s, min={self.minimum:.6f}s, max={self.maximum:.6f}s)"
