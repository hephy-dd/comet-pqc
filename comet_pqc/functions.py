from typing import Generator

__all__ = ['LinearRange']

class LinearRange:
    """Linear range function generator class.
    Range is bound to [begin, end].
    >>> list(LinearRange(0, 10, 2.5)) # positive ramp
    [0.0, 2.5, 5.0, 7.5, 10.0]
    >>> list(LinearRange(10, 0, -2.5)) # negative ramp
    [10.0, 7.5, 5.0, 2.5, 0.0]
    >>> list(LinearRange(0, 4, -1)) # auto corrected step
    [0.0, 1.0, 2.0, 3.0, 4.0]
    """

    __slots__ = (
        'begin',
        'end',
        'step'
    )

    def __init__(self, begin: float, end: float, step: float):
        self.begin = begin
        self.end = end
        self.step = step

    @property
    def distance(self) -> int:
        return abs(self.end - self.begin)

    def __len__(self) -> int:
        if self.step:
            return int(abs(round(self.distance / self.step)))
        return 0

    def __iter__(self) -> Generator:
        begin, end, step = self.begin, self.end, self.step
        step = -abs(step) if end < begin else abs(step)
        count = len(self)
        if count:
            for i in range(len(self) + 1):
                yield begin + (i * step)
