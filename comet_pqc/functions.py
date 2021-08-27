"""Functions module."""

from decimal import Context, Decimal
from typing import Generator

__all__ = ['LinearRange']

ctx: Context = Context(prec=4)


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
        self.begin: float = begin
        self.end: float = end
        self.step: float = step

    @property
    def distance(self) -> float:
        """Return distance of linear range.

        >>> LinearRange(-2.5, 2.5, 0.5).distance
        5.0
        """
        begin: Decimal = ctx.create_decimal(self.begin)
        end: Decimal = ctx.create_decimal(self.end)
        return abs(float(end - begin))

    def __len__(self) -> int:
        step: Decimal = ctx.create_decimal(self.step)
        distance: Decimal = ctx.create_decimal(self.distance)
        if step:
            return int(abs(round(distance / step)))
        return 0

    def __iter__(self) -> Generator[float, None, None]:
        begin: Decimal = ctx.create_decimal(self.begin)
        end: Decimal = ctx.create_decimal(self.end)
        step: Decimal = ctx.create_decimal(self.step)
        ascending: bool = begin < end
        step = abs(step) if ascending else -abs(step)
        count: int = len(self)
        if count:
            value: Decimal = ctx.create_decimal('NaN')
            for i in range(count + 1):
                value = begin + (i * step)
                # Mangle value not to exceed valid range.
                if ascending:
                    value = min(value, end)
                else:
                    value = max(value, end)
                yield float(value)
            # Yield end if range is incomplete (last odd step).
            if value != end:
                yield float(end)
