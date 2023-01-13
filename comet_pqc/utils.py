import logging
import math
import os
import traceback
from typing import Callable, Iterable, Optional, Union

from PyQt5 import QtCore, QtGui, QtWidgets

from comet import ureg

from .core.formatter import CSVFormatter
from .core.utils import make_path

__all__ = [
    "make_path",
    "format_metric",
    "format_switch",
    "stitch_pixmaps",
    "handle_exception",
    "format_table_unit",
    "from_table_unit",
    "to_table_unit"
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
    return {False: "OFF", True: "ON"}.get(value, default or "")


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


class ExceptionHandler:

    def __init__(self, parent):
        self.parent = parent

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        logging.exception(exc_val)
        show_exception(exc_val)
        return True


def handle_exception(func: Callable) -> Callable:
    def catch_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.exception(exc)
            show_exception(exc)
    return catch_exception_wrapper


def show_exception(exc):
    ExceptionDialog(exc).exec()


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


def append_summary(data: dict, filename: str) -> None:
    has_header = os.path.exists(filename)
    with open(filename, "a") as fp:
        fmt = CSVFormatter(fp)
        for key in data.keys():
            fmt.add_column(key)
        if not has_header:
            fmt.write_header()
        fmt.write_row(data)


class ExceptionDialog(QtWidgets.QMessageBox):

    def __init__(self, exc: Exception, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exception occured")
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.setDefaultButton(QtWidgets.QMessageBox.Ok)
        # Fix message box width
        spacer = QtWidgets.QSpacerItem(448, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(spacer, self.layout().rowCount(), 0, 1, self.layout().columnCount())
        # Set exception
        self.setException(exc)

    def setException(self, exc: Exception) -> None:
        details = "".join(traceback.format_tb(exc.__traceback__))
        self.setText(format(exc))
        self.setDetailedText(details)
