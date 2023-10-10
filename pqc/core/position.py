import math
from typing import Optional

__all__ = ["Position"]


class Position:
    """Three-dimensional Cartesian coordinate."""

    def __init__(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None):
        self._x: float = math.nan if x is None else float(x)
        self._y: float = math.nan if y is None else float(y)
        self._z: float = math.nan if z is None else float(z)

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def z(self) -> float:
        return self._z

    @property
    def is_valid(self) -> bool:
        return all((not math.isnan(value) for value in self))

    def asdict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __add__(self, rhs):
        return type(self)(self.x + rhs.x, self.y + rhs.y, self.z + rhs.z)

    def __sub__(self, rhs):
        return type(self)(self.x - rhs.x, self.y - rhs.y, self.z - rhs.z)

    def __eq__(self, rhs):
        return tuple(self) == tuple(rhs)

    def __lt__(self, rhs):
        return tuple(self) < tuple(rhs)

    def __le__(self, rhs):
        return tuple(self) <= tuple(rhs)

    def __repr__(self):
        return f"{type(self).__name__}({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"
