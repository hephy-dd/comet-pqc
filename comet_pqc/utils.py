import logging
import math
import os
import traceback
from typing import Any, Callable, Iterable, Optional, Union

from comet import ureg
from PyQt5 import QtCore, QtGui

from .core.utils import make_path

__all__ = [
    "make_path",
    "format_metric",
    "format_switch",
    "format_table_unit",
    "from_table_unit",
    "to_table_unit",
    "create_dir",
]

logger = logging.getLogger(__name__)


def format_metric(value: Optional[float], unit: str, decimals: int = 3) -> str:
    """Pretty format metric units.

    >>> format_metric(.0042, "A")
    '4.200 mA'
    """
    scales = (
        (1e+24, "Y", "yotta"),
        (1e+21, "Z", "zetta"),
        (1e+18, "E", "exa"),
        (1e+15, "P", "peta"),
        (1e+12, "T", "tera"),
        (1e+9, "G", "giga"),
        (1e+6, "M", "mega"),
        (1e+3, "k", "kilo"),
        (1e+0, "", ""),
        (1e-3, "m", "milli"),
        (1e-6, "u", "micro"),
        (1e-9, "n", "nano"),
        (1e-12, "p", "pico"),
        (1e-15, "f", "femto"),
        (1e-18, "a", "atto"),
        (1e-21, "z", "zepto"),
        (1e-24, "y", "yocto")
    )
    if value is None:
        return "---"
    for scale, prefix, _ in scales:
        if abs(value) >= scale:
            return f"{value * (1 / scale):.{decimals}f} {prefix}{unit}"
    return f"{value:.{decimals}f} {unit}"


def format_switch(value: Optional[bool], default: Optional[str] = None) -> str:
    """Pretty format for instrument output states.

    >>> format_switch(False)
    'OFF'
    """
    if value is None:
        return default or ""
    return "ON" if value else "OFF"


def format_table_unit(value: float) -> str:
    """Formatted table unit to millimeters."""
    return f"{value:.3f} mm"


def from_table_unit(value: float) -> float:
    """Convert table unit (micron) to millimeters."""
    return round((value * ureg("um")).to("mm").m, 3)


def to_table_unit(value: float) -> float:
    """Convert millimeters to table unit (micron)."""
    return round((value * ureg("mm")).to("um").m, 0)


def getcal(value: float) -> Union[int, float]:
    if not math.isnan(value):
        return int(value) & 0x1
    return value


def getrm(value: float) -> Union[int, float]:
    if not math.isnan(value):
        return (int(value) >> 1) & 0x1
    return value


def caldone_valid(position: Iterable) -> bool:
    return all(getcal(value) == 1 and getrm(value) == 1 for value in position)


def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        return True
    return False


def safe_value(type: Callable, value: Any, default: Any) -> Any:
    try:
        return type(value)
    except (ValueError, TypeError):
        return type(default)


def safe_bool(value, default: bool = False) -> bool:
    return safe_value(bool, value, default)


def safe_int(value, default: int = 0) -> int:
    return safe_value(int, value, default)


def safe_float(value, default: float = 0) -> float:
    return safe_value(float, value, default)
