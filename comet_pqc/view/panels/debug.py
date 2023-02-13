from typing import Optional

import comet
from PyQt5 import QtWidgets

from .panel import MeasurementPanel

__all__ = ["DebugPanel"]


class DebugPanel(MeasurementPanel):
    """Panel for IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "Debug"
