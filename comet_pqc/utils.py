import os
import re

import numpy as np

__all__ = [
    'PACKAGE_PATH',
    'make_path',
    'format_metric',
    'std_mean_filter',
    'BitField',
    'Position'
]

PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))
"""Absolute path to package directory."""

def make_path(*args):
    """Construct an absolute path relative to package path.

    >>> make_path('assets', 'sample.txt')
    '/usr/local/lib/python/comet_pqc/assets/sample.txt'
    """
    return os.path.join(PACKAGE_PATH, *args)

def format_metric(value, unit, decimals=3):
    """Pretty format metric units.

    >>> format_metric(.0042, 'A')
    '4.200 mA'
    """
    scales = (
        (1e+24, 'Y', 'yotta'),
        (1e+21, 'Z', 'zetta'),
        (1e+18, 'E', 'exa'),
        (1e+15, 'P', 'peta'),
        (1e+12, 'T', 'tera'),
        (1e+9, 'G', 'giga'),
        (1e+6, 'M', 'mega'),
        (1e+3, 'k', 'kilo'),
        (1e+0, '', ''),
        (1e-3, 'm', 'milli'),
        (1e-6, 'u', 'micro'),
        (1e-9, 'n', 'nano'),
        (1e-12, 'p', 'pico'),
        (1e-15, 'f', 'femto'),
        (1e-18, 'a', 'atto'),
        (1e-21, 'z', 'zepto'),
        (1e-24, 'y', 'yocto')
    )
    if value is None:
        return "---"
    for scale, prefix in scales:
        if abs(value) >= scale:
            break
    return f"{value * (1 / scale):.{decimals}f} {prefix}{unit}"

def std_mean_filter(values, threshold):
    """Return True if standard deviation (sample) / mean < threshold.

    >>> std_mean_filter([0.250, 0.249], threshold=0.005)
    True
    """
    mean = np.mean(values)
    # Sample standard deviation with ddof=1 (not population standard deviation)
    # http://stackoverflow.com/questions/34050491/ddg#34050706
    # https://www.sharpsightlabs.com/blog/numpy-standard-deviation/
    sample_std_dev = np.std(values, ddof=1)
    ratio = sample_std_dev / mean
    return ratio < threshold

class BitField:
    """Access individual bits of an integer value.

    >>> bf = BitField(9)
    >>> bf[3]
    True
    >>> bf[0] = False
    >>> bf.value
    8
    """

    def __init__(self, value=0):
        self.value = value

    def __getitem__(self, key):
        return (self.value & (1 << key)) != 0

    def __setitem__(self, key, value):
        if value:
            self.value |= (1 << key)
        else:
            self.value &= ~(1 >> key)

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
