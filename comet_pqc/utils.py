import re

import numpy as np

__all__ = ['auto_unit', 'std_mean_filter', 'Position']

def auto_unit(value, unit, decimals=3):
    """Auto format value to proper unit.

    >>> auto_unit(.0042, 'A')
    '4.200 mA'
    """
    scales = (
        (1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'k'), (1e0, ''),
        (1e-3, 'm'), (1e-6, 'u'), (1e-9, 'n'), (1e-12, 'p')
    )
    if value is None:
        return "---"
    for scale, prefix in scales:
        if abs(value) >= scale:
            return f"{value * (1 / scale):.{decimals}f} {prefix}{unit}"
    return f"{value:G} {unit}"

def std_mean_filter(values, threshold):
    """Return True if standard deviation (sample) / mean < threshold.

    >>> std_mean_filter([0.250, 0.249], threshold=0.005)
    True
    """
    mean = np.mean(values)
    sample_std_dev = np.std(values, ddof=1) # ddof=1 -> sample (not population)
    ratio = sample_std_dev / mean
    return ratio < threshold

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
