import time

__all__ = ["Timer"]


class Timer:
    """Simple stop watch to measure time deltas."""

    def __init__(self) -> None:
        self._t: float = time.monotonic()

    def delta(self) -> float:
        return time.monotonic() - self._t

    def reset(self) -> None:
        self._t = time.monotonic()
