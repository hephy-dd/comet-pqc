"""Estimate remaining time."""

import datetime

__all__ = ["Estimate"]


class Estimate:
    """Estiamte remaining time.

    >>> e = Estimate(42)
    >>> for i in range(42):
    ...     operation()
    ...     e.advance()
    ...     print(e.elapsed)
    ...     print(e.remaining)
    ...     print(e.progress)
    """

    def __init__(self, count):
        self.reset(count)

    def reset(self, count):
        self._count = count
        self._deltas = []
        self._start = datetime.datetime.now()
        self._prev = datetime.datetime.now()

    def advance(self):
        now = datetime.datetime.now()
        self._deltas.append(now - self._prev)
        self._prev = now

    @property
    def count(self):
        return self._count

    @property
    def passed(self):
        return len(self._deltas)

    @property
    def average(self):
        return sum(self._deltas, datetime.timedelta(0)) / max(1, len(self._deltas))

    @property
    def elapsed(self):
        return datetime.datetime.now() - self._start

    @property
    def remaining(self):
        return max(datetime.timedelta(0), (self.average * self.count) - self.elapsed)

    @property
    def progress(self):
        return self.passed, self.count
