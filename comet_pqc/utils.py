import logging
import os
import traceback
import math

import numpy as np

from qutie.qutie import QtCore, QtGui
from comet import ui
from comet import ureg

__all__ = [
    'PACKAGE_PATH',
    'make_path',
    'user_home',
    'format_metric',
    'format_switch',
    'std_mean_filter',
    'stitch_pixmaps',
    'create_icon',
    'handle_exception',
    'format_table_unit',
    'from_table_unit',
    'to_table_unit'
]

logger = logging.getLogger(__name__)

PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))
"""Absolute path to package directory."""

def make_path(*args):
    """Construct an absolute path relative to package path.

    >>> make_path('assets', 'sample.txt')
    '/usr/local/lib/python/comet_pqc/assets/sample.txt'
    """
    return os.path.join(PACKAGE_PATH, *args)

def user_home():
    """Return absolute path of user home directory.

    >>> user_home()
    '/home/user'
    """
    return os.path.expanduser("~")

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
    for scale, prefix, _ in scales:
        if abs(value) >= scale:
            return f"{value * (1 / scale):.{decimals}f} {prefix}{unit}"
    return f"{value:.{decimals}f} {unit}"

def format_switch(value, default=None):
    """Pretty format for instrument output states.

    >>> format_switch(False)
    'OFF'
    """
    return {False: "OFF", True: "ON"}.get(value) or default

def format_table_unit(value):
    """Formatted table unit to millimeters."""
    return f"{value:.3f} mm"

def from_table_unit(value):
    """Convert table unit (micron) to millimeters."""
    return round((value * ureg("um")).to("mm").m, 3)

def to_table_unit(value):
    """Convert millimeters to table unit (micron)."""
    return round((value * ureg("mm")).to("um").m, 0)

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

def stitch_pixmaps(pixmaps, vertical=True):
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

def create_icon(size, color):
    """Return circular colored icon."""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtGui.QColor("transparent"))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setPen(QtGui.QColor(color))
    painter.setBrush(QtGui.QColor(color))
    painter.drawEllipse(1, 1, size-2, size-2)
    del painter
    return ui.Icon(qt=pixmap)

def handle_exception(func):
    def catch_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(exc)
            logger.error(tb)
            ui.show_exception(exc, tb)
    return catch_exception_wrapper

def getcal(value):
    if not math.isnan(value):
        return int(value) & 0x1
    return value

def getrm(value):
    if not math.isnan(value):
        return (int(value) >> 1) & 0x1
    return value

def caldone_valid(position):
    return all(getcal(value) == 1 and getrm(value) == 1 for value in position)
