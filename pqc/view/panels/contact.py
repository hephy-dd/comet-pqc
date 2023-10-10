import math
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from pqc.core.position import Position
from ..components import PositionWidget
from .panel import BasicPanel

__all__ = ["ContactPanel"]


class ContactPanel(BasicPanel):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.isTableEnabled: bool = False
        self.isPositionValid: bool = False

        self.positionWidget = PositionWidget()
        self.positionWidget.setTitle("Contact Position")

        centralLayout = QtWidgets.QHBoxLayout()
        centralLayout.addWidget(self.positionWidget)
        centralLayout.addStretch(1)

        self.layout().insertLayout(2, centralLayout)

    def setTableEnabled(self, enabled: bool) -> None:
        self.isTableEnabled = enabled

    def updatePosition(self) -> None:
        if self.context is None:
            position = Position()
        else:
            position = Position(*self.context.position)
        self.positionWidget.setPosition(position)
        self.isPositionValid = not math.isnan(position.z)

    def mount(self, context) -> None:
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"Contact &rarr; {context.name()}")
        self.setDescription(context.description() or "")
        self.updatePosition()
