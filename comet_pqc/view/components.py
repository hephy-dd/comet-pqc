import math
import os
from typing import Iterable, List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.position import Position
from ..core.utils import make_path, user_home
from ..settings import settings
from ..utils import (
    format_table_unit,
    getcal,
    getrm,
)
from .metric import Metric

__all__ = [
    "ToggleButton",
    "PositionLabel",
    "CalibrationLabel",
    "CalibrationWidget",
    "DirectoryWidget",
    "OperatorWidget",
    "PositionsComboBox"
]


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


class MessageBox(QtWidgets.QMessageBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        # Fix message box width
        width = 420
        layout = self.layout()
        if isinstance(layout, QtWidgets.QGridLayout):
            rows = layout.rowCount()
            columns = layout.columnCount()
            spacer = QtWidgets.QSpacerItem(width, 0)
            layout.addItem(spacer, rows, 0, 1, columns)


class ToggleButton(QtWidgets.QPushButton):
    """Checkable button with color icon."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setProperty("checkedIcon", create_icon(12, "green"))
        self.setProperty("uncheckedIcon", create_icon(12, "grey"))
        self.updateIcon(self.isChecked())
        self.toggled.connect(self.updateIcon)

    def updateIcon(self, state: bool) -> None:
        icon = self.property("checkedIcon") if state else self.property("uncheckedIcon")
        self.setIcon(icon)


class PositionLabel(QtWidgets.QLabel):  # TODO

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.setValue(None)

    def value(self) -> Optional[float]:
        return self.__value

    def setValue(self, value: Optional[float]) -> None:
        self.__value = value
        if value is None:
            self.setText(format(float("nan")))
        else:
            self.setText(format_table_unit(value))


class PositionWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Position")

        self.xLabel = QtWidgets.QLabel(self)
        self.xLabel.setText("X")
        self.xLabel.setToolTip("X axis position")

        self.yLabel = QtWidgets.QLabel(self)
        self.yLabel.setText("Y")
        self.yLabel.setToolTip("Y axis position")

        self.zLabel = QtWidgets.QLabel(self)
        self.zLabel.setText("Z")
        self.zLabel.setToolTip("Z axis position")

        self.xValueLabel = PositionLabel(self)
        self.yValueLabel = PositionLabel(self)
        self.zValueLabel = PositionLabel(self)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.xLabel, 0, 0)
        layout.addWidget(self.yLabel, 1, 0)
        layout.addWidget(self.zLabel, 2, 0)
        layout.addWidget(self.xValueLabel, 0, 1)
        layout.addWidget(self.yValueLabel, 1, 1)
        layout.addWidget(self.zValueLabel, 2, 1)

    def reset(self) -> None:
        self.setPosition(Position())

    def setPosition(self, position: Position) -> None:
        self.xValueLabel.setValue(position.x)
        self.yValueLabel.setValue(position.y)
        self.zValueLabel.setValue(position.z)


class CalibrationLabel(QtWidgets.QLabel):

    def __init__(self, prefix: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.prefix = prefix
        self.setValue(None)

    def value(self):
        return self._value

    def setValue(self, value):
        self._value = value or float("nan")
        self.setText(f"{self.prefix} {self._value}")
        if math.isnan(self._value) or self._value is None:
            self.setStyleSheet("QLabel:enabled{color:red}")
        else:
            self.setStyleSheet("QLabel:enabled{color:green}")


class CalibrationWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Calibration")

        self.xLabel = QtWidgets.QLabel(self)
        self.xLabel.setText("X")
        self.xLabel.setToolTip("X axis calibration state")

        self.yLabel = QtWidgets.QLabel(self)
        self.yLabel.setText("Y")
        self.yLabel.setToolTip("Y axis calibration state")

        self.zLabel = QtWidgets.QLabel(self)
        self.zLabel.setText("Z")
        self.zLabel.setToolTip("Z axis calibration state")

        self.xCalLabel = CalibrationLabel("cal", self)
        self.yCalLabel = CalibrationLabel("cal", self)
        self.zCalLabel = CalibrationLabel("cal", self)

        self.xRmLabel = CalibrationLabel("rm", self)
        self.yRmLabel = CalibrationLabel("rm", self)
        self.zRmLabel = CalibrationLabel("rm", self)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.xLabel, 0, 0)
        layout.addWidget(self.yLabel, 1, 0)
        layout.addWidget(self.zLabel, 2, 0)
        layout.addWidget(self.xCalLabel, 0, 1)
        layout.addWidget(self.yCalLabel, 1, 1)
        layout.addWidget(self.zCalLabel, 2, 1)
        layout.addWidget(self.xRmLabel, 0, 2)
        layout.addWidget(self.yRmLabel, 1, 2)
        layout.addWidget(self.zRmLabel, 2, 2)

    def reset(self) -> None:
        self.setCalibration(Position())

    def setCalibration(self, position: Position) -> None:
        self.xCalLabel.setValue(getcal(position.x))
        self.yCalLabel.setValue(getcal(position.y))
        self.zCalLabel.setValue(getcal(position.z))
        self.xRmLabel.setValue(getrm(position.x))
        self.yRmLabel.setValue(getrm(position.y))
        self.zRmLabel.setValue(getrm(position.z))


class DirectoryWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.locationComboBox = QtWidgets.QComboBox(self)
        self.locationComboBox.setEditable(True)
        self.locationComboBox.setDuplicatesEnabled(False)
        self.locationComboBox.currentIndexChanged.connect(self.updateButtons)
        self.locationComboBox.focusOutEvent = lambda event: self.updateLocations()  # type: ignore

        self.selectButton = QtWidgets.QToolButton(self)
        self.selectButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "search.svg")))
        self.selectButton.setToolTip("Select a directory.")
        self.selectButton.clicked.connect(self.selectLocation)

        self.removeButton = QtWidgets.QToolButton(self)
        self.removeButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeButton.setToolTip("Remove directory from list.")
        self.removeButton.clicked.connect(self.removeCurrentLocation)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.locationComboBox, 1)
        layout.addWidget(self.selectButton)
        layout.addWidget(self.removeButton)

    def currentLocation(self) -> str:
        index = self.locationComboBox.currentIndex()
        return self.locationComboBox.itemText(index).strip()

    def locations(self) -> List[str]:
        locations = []
        self.updateLocations()
        for index in range(self.locationComboBox.count()):
            location = self.locationComboBox.itemText(index).strip()
            locations.append(self.locationComboBox.itemText(index).strip())
        return locations

    def clearLocations(self) -> None:
        with QtCore.QSignalBlocker(self.locationComboBox):
            self.locationComboBox.clear()
            self.updateLocations()

    def addLocation(self, location: str) -> None:
        self.locationComboBox.addItem(location)

    def updateButtons(self, _) -> None:
        location = self.currentLocation()
        self.removeButton.setEnabled(self.locationComboBox.count() > 1)

    def selectLocation(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select directory",
            self.currentLocation()
        ).strip()
        if path:
            for index in range(self.locationComboBox.count()):
                location = self.locationComboBox.itemText(index).strip()
                if location == path:
                    self.locationComboBox.setCurrentIndex(index)
                    return
            self.updateLocations()
            self.locationComboBox.insertItem(0, path)
            self.locationComboBox.setCurrentIndex(0)

    def removeCurrentLocation(self) -> None:
        self.updateLocations()
        if self.locationComboBox.count() > 1:
            index = self.locationComboBox.currentIndex()
            if index >= 0:
                message = f"Do you want to remove directory {self.locationComboBox.itemText(index)!r} from the list?"
                result = QtWidgets.QMessageBox.question(self, "Remove directory", message)
                if result == QtWidgets.QMessageBox.Yes:
                    self.locationComboBox.removeItem(index)

    def updateLocations(self) -> None:  # TODO
        self.removeButton.setEnabled(self.locationComboBox.count() > 1)
        current_text = self.locationComboBox.currentText().strip()
        for index in range(self.locationComboBox.count()):
            if self.locationComboBox.itemText(index).strip() == current_text:
                return
        if current_text:
            self.locationComboBox.insertItem(0, current_text)
            self.locationComboBox.setCurrentIndex(0)


class WorkingDirectoryWidget(DirectoryWidget):

    def readSettings(self) -> None:
        self.clearLocations()
        locations = settings.output_path
        if not locations:
            locations = [os.path.join(user_home(), "PQC")]
        for location in locations:
            self.addLocation(location)
        index = self.locationComboBox.findText(settings.current_output_path)
        self.locationComboBox.setCurrentIndex(max(0, index))
        self.updateLocations()

    def writeSettings(self) -> None:
        self.updateLocations()
        settings.output_path = self.locations()
        settings.current_output_path = self.currentLocation()


class OperatorWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Operator")

        self.operatorComboBox = QtWidgets.QComboBox(self)
        self.operatorComboBox.setDuplicatesEnabled(False)

        self.addButton = QtWidgets.QToolButton(self)
        self.addButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addButton.setToolTip("Add new operator.")
        self.addButton.clicked.connect(self.addOperator)

        self.removeButton = QtWidgets.QToolButton(self)
        self.removeButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeButton.setToolTip("Remove current operator from list.")
        self.removeButton.clicked.connect(self.removeCurrent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.operatorComboBox, 1)
        layout.addWidget(self.addButton)
        layout.addWidget(self.removeButton)

    def currentOperator(self) -> str:
        index = self.operatorComboBox.currentIndex()
        return self.operatorComboBox.itemText(index).strip()

    def addOperator(self) -> None:
        operator, ok = QtWidgets.QInputDialog.getText(
            self,
            "Add operator",
            "Enter name of operator to add."
        )
        if ok:
            operator = operator.strip()
            index = self.operatorComboBox.findText(operator)
            if index < 0:
                self.operatorComboBox.addItem(operator)
                index = self.operatorComboBox.findText(operator)
            self.operatorComboBox.setCurrentIndex(index)

    def removeCurrent(self) -> None:
        index = self.operatorComboBox.currentIndex()
        if index >= 0:
            message = f"Do you want to remove operator {self.operatorComboBox.itemText(index)!r} from the list?"
            result = QtWidgets.QMessageBox.question(self, "Remove operator", message)
            if result == QtWidgets.QMessageBox.Yes:
                self.operatorComboBox.removeItem(index)

    def readSettings(self) -> None:
        self.operatorComboBox.clear()
        for operator in settings.operators:
            self.operatorComboBox.addItem(operator.strip())
        index = self.operatorComboBox.findText(settings.current_operator)
        self.operatorComboBox.setCurrentIndex(index)

    def writeSettings(self) -> None:
        settings.current_operator = self.operatorComboBox.currentText()
        operators = []
        for index in range(self.operatorComboBox.count()):
            operators.append(self.operatorComboBox.itemText(index).strip())
        settings.operators = operators


class PositionsComboBox(QtWidgets.QComboBox):

    def readSettings(self) -> None:
        self.clear()
        for position in settings.table_positions:
            self.addItem(f"{position} ({position.x:.3f}, {position.y:.3f}, {position.z:.3f})")
        index = settings.settings.get("current_table_position") or 0
        self.setCurrentIndex(index)

    def writeSettings(self) -> None:
        settings.settings["current_table_position"] = self.currentIndex()
