"""Estimate remaining time."""

from datetime import datetime, timedelta
from typing import List, Tuple

__all__ = ['Estimate']


class Estimate:
    """Estiamte remaining time.
    >>> e = Estimate(42)
    >>> for i in range(42):
    ...     heavy_operation()
    ...     e.advance()
    ...     print(e.elapsed)
    ...     print(e.remaining)
    ...     print(e.progress)
    """

    def __init__(self, count: int) -> None:
        self._count: int = count
        self._deltas: List[timedelta] = []
        self._start: datetime = datetime.now()
        self._prev: datetime = datetime.now()

    def reset(self, count: int = None) -> None:
        if count is not None:
            self._count = count
        self._deltas = []
        self._start = datetime.now()
        self._prev = datetime.now()

    def advance(self) -> None:
        now = datetime.now()
        self._deltas.append(now - self._prev)
        self._prev = now

    @property
    def count(self) -> int:
        return self._count

    @property
    def passed(self) -> int:
        return len(self._deltas)

    @property
    def average(self) -> timedelta:
        return sum(self._deltas, timedelta(0)) / max(1, len(self._deltas))

    @property
    def elapsed(self) -> timedelta:
        return datetime.now() - self._start

    @property
    def remaining(self) -> timedelta:
        return max(timedelta(0), (self.average * self.count) - self.elapsed)

    @property
    def progress(self) -> Tuple[int, int]:
        return self.passed, self.count
