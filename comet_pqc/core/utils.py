import os
from typing import Tuple

__all__ = [
    "PACKAGE_PATH",
    "make_path",
    "user_home",
    "LinearTransform",
]

PACKAGE_PATH: str = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
"""Absolute path to package directory."""


def make_path(*args) -> str:
    """Construct an absolute path relative to package path.

    >>> make_path("assets", "sample.txt")
    '/usr/local/lib/python/comet_pqc/assets/sample.txt'
    """
    return os.path.join(PACKAGE_PATH, *args)


def user_home() -> str:
    """Return absolute path of user home directory.

    >>> user_home()
    '/home/user'
    """
    return os.path.expanduser("~")


class LinearTransform:
    """Linear transformation of n coordinates between two points."""

    def calculate(self, a: Tuple[float, float, float], b: Tuple[float, float, float], n: int) -> list:
        diff_x = (a[0] - b[0]) / n
        diff_y = (a[1] - b[1]) / n
        diff_z = (a[2] - b[2]) / n
        return [(a[0] - diff_x * i, a[1] - diff_y * i, a[2] - diff_z * i) for i in range(n + 1)]
