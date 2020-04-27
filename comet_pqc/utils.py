import re

__all__ = ['Position']

class Position:
    """Three-dimensional Cartesian coordinate."""

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, rhs):
        return type(self)(self.x + rhs.x, self.y + rhs.y, self.z + rhs.z)

    def __sub__(self, rhs):
        return type(self)(self.x - rhs.x, self.y - rhs.y, self.z - rhs.z)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.x}, {self.y}, {self.z})"
