import os

__all__ = ["PACKAGE_PATH", "make_path", "user_home"]

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
