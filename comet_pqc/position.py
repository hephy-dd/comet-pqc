__all__ = [
    'Position'
]

class Position:
    """Three-dimensional Cartesian coordinate."""

    __slots__ = ['x', 'y', 'z']

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def asdict(self):
        return dict(x=self.x, y=self.y, z=self.z)

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
        return f"{self.__class__.__name__}({self.x}, {self.y}, {self.z})"
