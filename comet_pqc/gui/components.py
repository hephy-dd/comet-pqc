import math
import os
import traceback
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.position import Position
from ..core.utils import make_path, user_home
from ..settings import settings
from ..utils import (
    format_table_unit,
    getcal,
    getrm,
)

__all__ = [
    "ToggleButton",
    "PositionLabel",
    "CalibrationLabel",
    "CalibrationWidget",
    "DirectoryWidget",
    "OperatorComboBox",
    "PositionsComboBox",
]


class ToggleButton(QtWidgets.QPushButton):
    """Colored checkable button."""

    def __init__(self, text: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton:disabled:checked{font-weight:bold;}
            QPushButton:enabled:checked{color:green;font-weight:bold;}
        """)


class PositionLabel(QtWidgets.QLabel):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("value", math.nan)
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def value(self) -> float:
        return self.property("value")

    def setValue(self, value: float) -> None:
        self.setProperty("value", value)
        if math.isfinite(value):
            self.setText(format_table_unit(value))
        else:
            self.setText(format(value))


class PositionWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Position")

        self.xPosLabel: PositionLabel = PositionLabel(self)
        self.yPosLabel: PositionLabel = PositionLabel(self)
        self.zPosLabel: PositionLabel = PositionLabel(self)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("X", self.xPosLabel)
        layout.addRow("Y", self.yPosLabel)
        layout.addRow("Z", self.zPosLabel)

    def resetPosition(self)-> None:
        self.updatePosition(Position())

    def updatePosition(self, position: Position) -> None:
        self.xPosLabel.setValue(position.x)
        self.yPosLabel.setValue(position.y)
        self.zPosLabel.setValue(position.z)


class CalibrationLabel(QtWidgets.QLabel):

    def __init__(self, prefix: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setPrefix(prefix)
        self.setValue(math.nan)

    def prefix(self) -> str:
        return self.property("prefix")

    def setPrefix(self, prefix: str) -> None:
        self.setProperty("prefix", prefix)

    def value(self) -> float:
        return self.property("value")

    def setValue(self, value: float) -> None:
        self.setProperty("value", value)
        self.setText(f"{self.prefix()} {value}")
        if math.isnan(value) or not value:
            self.setStyleSheet("QLabel:enabled{color:red;}")
        else:
            self.setStyleSheet("QLabel:enabled{color:green;}")


class CalibrationWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Calibration")
        self.xCalLabel = CalibrationLabel("cal", self)
        self.yCalLabel = CalibrationLabel("cal", self)
        self.zCalLabel = CalibrationLabel("cal", self)
        self.xRmLabel = CalibrationLabel("rm", self)
        self.yRmLabel = CalibrationLabel("rm", self)
        self.zRmLabel = CalibrationLabel("rm", self)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(QtWidgets.QLabel("X", self), 0, 0)
        layout.addWidget(QtWidgets.QLabel("Y", self), 1, 0)
        layout.addWidget(QtWidgets.QLabel("Z", self), 2, 0)
        layout.addWidget(self.xCalLabel, 0, 1)
        layout.addWidget(self.yCalLabel, 1, 1)
        layout.addWidget(self.zCalLabel, 2, 1)
        layout.addWidget(self.xRmLabel, 0, 2)
        layout.addWidget(self.yRmLabel, 1, 2)
        layout.addWidget(self.zRmLabel, 2, 2)

    def resetCalibration(self) -> None:
        self.updateCalibration(Position())

    def updateCalibration(self, position: Position) -> None:
        self.xCalLabel.setValue(getcal(position.x))
        self.yCalLabel.setValue(getcal(position.y))
        self.zCalLabel.setValue(getcal(position.z))
        self.xRmLabel.setValue(getrm(position.x))
        self.yRmLabel.setValue(getrm(position.y))
        self.zRmLabel.setValue(getrm(position.z))


class FocusComboBox(QtWidgets.QComboBox):

    focusOut = QtCore.pyqtSignal()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focusOut.emit()


class DirectoryWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.locationComboBox = FocusComboBox(self)
        self.locationComboBox.setEditable(True)
        self.locationComboBox.setDuplicatesEnabled(False)
        self.locationComboBox.focusOut.connect(self.updateLocations)
        self.locationComboBox.currentTextChanged.connect(self.updateButtons)

        self.selectButton = QtWidgets.QToolButton(self)
        self.selectButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "search.svg")))
        self.selectButton.setToolTip("Select a directory.")
        self.selectButton.clicked.connect(self.selectLocation)

        self.removeButton = QtWidgets.QToolButton(self)
        self.removeButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeButton.setToolTip("Remove directory from list.")
        self.removeButton.clicked.connect(self.removeOperator)

        layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.locationComboBox)
        layout.addWidget(self.selectButton)
        layout.addWidget(self.removeButton)

    def currentLocation(self) -> str:
        return self.locationComboBox.currentText().strip()

    @property
    def locations(self):
        locations = []
        self.updateLocations()
        for index in range(self.locationComboBox.count()):
            location = self.locationComboBox.itemText(index).strip()
            locations.append(self.locationComboBox.itemText(index).strip())
        return locations

    def clearLocations(self):
        with QtCore.QSignalBlocker(self.locationComboBox):
            self.locationComboBox.clear()
            self.updateLocations()

    def addLocation(self, value):
        self.locationComboBox.addItem(value)

    def updateButtons(self, text):
        self.removeButton.setEnabled(self.locationComboBox.count())

    def selectLocation(self):
        value = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select directory",
            self.currentLocation(),
        )
        if value:
            for index in range(self.locationComboBox.count()):
                location = self.locationComboBox.itemText(index).strip()
                if location == value:
                    self.locationComboBox.setCurrentIndex(index)
                    return
            self.updateLocations()
            self.locationComboBox.insertItem(0, value)
            self.locationComboBox.setCurrentIndex(0)

    def removeOperator(self):
        self.updateLocations()
        if self.locationComboBox.count() > 1:
            index = self.locationComboBox.currentIndex()
            if index >= 0:
                result = QtWidgets.QMessageBox.question(
                    self,
                    "Remove directory",
                    f"Do you want to remove directory {self.locationComboBox.currentText()!r} from the list?"
                )
                if result == QtWidgets.QMessageBox.Yes:
                    self.locationComboBox.removeItem(index)

    def updateLocations(self):
        self.removeButton.setEnabled(self.locationComboBox.count() > 1)
        current_text = self.locationComboBox.currentText().strip()
        for index in range(self.locationComboBox.count()):
            if self.locationComboBox.itemText(index).strip() == current_text:
                return
        if current_text:
            self.locationComboBox.insertItem(0, current_text)
            self.locationComboBox.setCurrentIndex(0)


class WorkingDirectoryWidget(DirectoryWidget):

    def readSettings(self):
        self.clearLocations()
        locations = settings.outputPath()
        if not locations:
            locations = [os.path.join(user_home(), "PQC")]
        for location in locations:
            self.addLocation(location)
        self.locationComboBox.setCurrentText(settings.currentOutputPath())
        self.updateLocations()

    def writeSettings(self):
        self.updateLocations()
        settings.setOutputPath(self.locations)
        settings.setCurrentOutputPath(self.locationComboBox.currentText())


class OperatorComboBox(QtWidgets.QComboBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setDuplicatesEnabled(False)

    def readSettings(self) -> None:
        self.clear()
        for operator in settings.operators():
            self.addItem(operator)
        self.setCurrentText(settings.currentOperator())

    def writeSettings(self):
        settings.setCurrentOperator(self.currentText())
        operators = []
        for index in range(self.count()):
            operators.append(self.itemText(index))
        settings.setOperators(operators)


class OperatorWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.operatorComboBox = OperatorComboBox(self)

        self.addButton = QtWidgets.QToolButton(self)
        self.addButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addButton.setToolTip("Add new operator.")
        self.addButton.clicked.connect(self.addOperator)

        self.removeButton = QtWidgets.QToolButton(self)
        self.removeButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeButton.setToolTip("Remove current operator from list.")
        self.removeButton.clicked.connect(self.removeOperator)

        layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.operatorComboBox)
        layout.addWidget(self.addButton)
        layout.addWidget(self.removeButton)

    def currentOperator(self) -> str:
        return self.operatorComboBox.currentText()

    def addOperator(self) -> None:
        operator, success = QtWidgets.QInputDialog.getText(
            self,
            "Add operator",
            "Enter name of operator to add.",
        )
        if success:
            # Add only if not already in list
            index = self.operatorComboBox.findText(operator)
            if index < 0:
                self.operatorComboBox.addItem(operator)
            self.operatorComboBox.setCurrentText(operator)

    def removeOperator(self) -> None:
        index = self.operatorComboBox.currentIndex()
        if index >= 0:
            result = QtWidgets.QMessageBox.question(
                self,
                "Remove operator",
                f"Do you want to remove operator {self.currentOperator()!r} from the list?"
            )
            if result == QtWidgets.QMessageBox.Yes:
                self.operatorComboBox.removeItem(index)

    def readSettings(self) -> None:
        self.operatorComboBox.readSettings()

    def writeSettings(self) -> None:
        self.operatorComboBox.writeSettings()


class PositionsComboBox(QtWidgets.QComboBox):

    def readSettings(self):
        self.clear()
        for position in settings.tablePositions():
            self.addItem(f"{position} ({position.x:.3f}, {position.y:.3f}, {position.z:.3f})")
        index = settings.settings.get("current_table_position") or 0
        if 0 <= index < self.count():
            self.setCurrentText(self.itemText(index))

    def writeSettings(self):
        index = self.currentIndex()
        settings.settings["current_table_position"] = index
