import re

__all__ = ['auto_step', 'safe_filename', 'Position']

# TODO: integrate into comet.Range
def auto_step(start, stop, step):
    """Returns positive/negative step according to start and stop value."""
    return -abs(step) if start > stop else abs(step)

# TODO: intefgrate into comet.utils
def safe_filename(filename):
    return re.sub(r'[^\w\+\-\.\_]+', '_', filename)

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

