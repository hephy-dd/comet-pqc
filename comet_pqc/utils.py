import logging
import math
import traceback
from typing import Callable, Iterable, List, Optional, Union

from PyQt5 import QtGui

from comet import ui
from comet import ureg
from PyQt5 import QtCore, QtGui, QtWidgets

from .core.utils import make_path

__all__ = [
    "make_path",
    "join_channels",
    "split_channels",
    "format_metric",
    "format_switch",
    "stitch_pixmaps",
    "create_icon",
    "format_table_unit",
    "from_table_unit",
    "to_table_unit"
]

logger = logging.getLogger(__name__)


def join_channels(channels: List[str]) -> str:
    """Return string containing comma separated channels."""
    return ", ".join([channel.strip() for channel in channels if channel.strip()])


def split_channels(channels: str) -> List[str]:
    """Return list of channels from comma separated string."""
    return [channel.strip() for channel in channels.split(",") if channel.strip()]


def format_metric(value: float, unit: str, decimals: int = 3) -> str:
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


def format_switch(value: bool, default: Optional[str] = None) -> str:
    """Pretty format for instrument output states.

    >>> format_switch(False)
    'OFF'
    """
    return {False: "OFF", True: "ON"}.get(value) or (default or "")


def format_table_unit(value: float) -> str:
    """Formatted table unit to millimeters."""
    return f"{value:.3f} mm"


def from_table_unit(value: float) -> float:
    """Convert table unit (micron) to millimeters."""
    return round((value * ureg("um")).to("mm").m, 3)


def to_table_unit(value: float) -> float:
    """Convert millimeters to table unit (micron)."""
    return round((value * ureg("mm")).to("um").m, 0)


def stitch_pixmaps(pixmaps: Iterable[QtGui.QPixmap], vertical: bool = True) -> QtGui.QPixmap:
    """Stitch together multiple QPixmaps to a single QPixmap."""
    # Calculate size of stitched image
    if vertical:
        width = max([pixmap.width() for pixmap in pixmaps])
        height = sum([pixmap.height() for pixmap in pixmaps])
    else:
        width = sum([pixmap.width() for pixmap in pixmaps])
        height = max([pixmap.height() for pixmap in pixmaps])
    canvas = QtGui.QPixmap(width, height)
    canvas.fill(QtCore.Qt.white)
    painter = QtGui.QPainter(canvas)
    offset = 0
    for pixmap in pixmaps:
        if vertical:
            painter.drawPixmap(0, offset, pixmap)
            offset += pixmap.height()
        else:
            painter.drawPixmap(offset, 0, pixmap)
            offset += pixmap.height()
    painter.end()
    return canvas


def create_icon(size: int, color: str) -> QtGui.QIcon:
    """Return circular colored icon."""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtGui.QColor("transparent"))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setPen(QtGui.QColor(color))
    painter.setBrush(QtGui.QColor(color))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    del painter
    return QtGui.QIcon(pixmap)


def getcal(value: float) -> Union[int, float]:
    if not math.isnan(value):
        return int(value) & 0x1
    return value


def getrm(value: float) -> Union[int, float]:
    if not math.isnan(value):
        return (int(value) >> 1) & 0x1
    return value


def caldone_valid(position: Iterable[float]) -> bool:
    return all(getcal(value) == 1 and getrm(value) == 1 for value in position)
