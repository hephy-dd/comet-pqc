import math
import os
from typing import Optional

from comet import ui
from comet.settings import SettingsMixin
from PyQt5 import QtCore, QtWidgets

from ..core.position import Position
from ..core.utils import make_path, user_home
from ..settings import settings
from ..utils import (
    format_table_unit,
    getcal,
    getrm,
)

from .metric import Metric
from .plots import PlotWidget

__all__ = [
    "ToggleButton",
    "PositionLabel",
    "CalibrationLabel",
    "CalibrationWidget",
    "DirectoryWidget",
    "OperatorComboBox",
    "PositionsComboBox",
    "Metric",
    "PlotWidget",
]


class ToggleButton(QtWidgets.QPushButton):
    """Colored checkable button."""

    def __init__(self, text: str, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton:disabled:checked{font-weight:bold;}
            QPushButton:enabled:checked{color:green;font-weight:bold;}
        """)


class PositionLabel(QtWidgets.QLabel):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
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

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
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

    def __init__(self, prefix: str, parent: QtWidgets.QWidget = None) -> None:
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

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
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


class DirectoryWidget(ui.Row):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location_combo_box = ui.ComboBox(
            editable=True,
            focus_out=self.update_locations,
            changed=self.on_location_changed,
        )
        self.location_combo_box.duplicates_enabled = False
        self.select_button = ui.ToolButton(
            icon=make_path("assets", "icons", "search.svg"),
            tool_tip="Select a directory.",
            clicked=self.on_select_clicked
        )
        self.remove_button = ui.ToolButton(
            icon=make_path("assets", "icons", "delete.svg"),
            tool_tip="Remove directory from list.",
            clicked=self.on_remove_clicked
        )
        self.append(self.location_combo_box)
        self.append(self.select_button)
        self.append(self.remove_button)

    def currentLocation(self) -> str:
        return self.location_combo_box.qt.currentText().strip()

    @property
    def locations(self):
        locations = []
        self.update_locations()
        for i in range(len(self.location_combo_box)):
            location = self.location_combo_box.qt.itemText(i).strip()
            locations.append(self.location_combo_box.qt.itemText(i).strip())
        return locations

    def clear_locations(self):
        changed = self.location_combo_box.changed
        self.location_combo_box.changed = None
        self.location_combo_box.clear()
        self.update_locations()
        self.location_combo_box.changed = changed

    def append_location(self, value):
        self.location_combo_box.append(value)

    def on_location_changed(self, _):
        self.remove_button.enabled = len(self.location_combo_box) > 1

    def on_select_clicked(self):
        value = ui.directory_open(
            title="Select directory",
            path=self.currentLocation()
        )
        if value:
            for i in range(self.location_combo_box.qt.count()):
                location = self.location_combo_box.qt.itemText(i).strip()
                if location == value:
                    self.location_combo_box.qt.setCurrentIndex(i)
                    return
            self.update_locations()
            self.location_combo_box.qt.insertItem(0, value)
            self.location_combo_box.qt.setCurrentIndex(0)

    def on_remove_clicked(self):
        self.update_locations()
        if len(self.location_combo_box) > 1:
            index = self.location_combo_box.qt.currentIndex()
            if index >= 0:
                result = QtWidgets.QMessageBox.question(
                    self.qt,
                    "Remove directory",
                    f"Do you want to remove directory {self.location_combo_box.qt.currentText()!r} from the list?"
                )
                if result == QtWidgets.QMessageBox.Yes:
                    self.location_combo_box.qt.removeItem(index)

    def update_locations(self):
        self.remove_button.enabled = len(self.location_combo_box) > 1
        current_text = self.location_combo_box.qt.currentText().strip()
        for i in range(self.location_combo_box.qt.count()):
            if self.location_combo_box.qt.itemText(i).strip() == current_text:
                return
        if current_text:
            self.location_combo_box.qt.insertItem(0, current_text)
            self.location_combo_box.qt.setCurrentIndex(0)


class WorkingDirectoryWidget(DirectoryWidget):

    def readSettings(self):
        self.clear_locations()
        locations = settings.outputPath()
        if not locations:
            locations = [os.path.join(user_home(), "PQC")]
        for location in locations:
            self.append_location(location)
        self.location_combo_box.current = settings.currentOutputPath()
        self.update_locations()

    def writeSettings(self):
        self.update_locations()
        settings.setOutputPath(self.locations)
        settings.setCurrentOutputPath(self.location_combo_box.current)


class OperatorComboBox(ui.ComboBox, SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duplicates_enabled = False

    def readSettings(self):
        self.clear()
        for operator in settings.operators():
            self.append(operator)
        self.current = settings.currentOperator()

    def writeSettings(self):
        settings.setCurrentOperator(self.current)
        operators = []
        for index in range(len(self)):
            operators.append(self.qt.itemText(index))
        settings.setOperators(operators)


class OperatorWidget(ui.Row, SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operator_combo_box = OperatorComboBox()
        self.add_button = ui.ToolButton(
            icon=make_path("assets", "icons", "add.svg"),
            tool_tip="Add new operator.",
            clicked=self.on_add_clicked
        )
        self.remove_button = ui.ToolButton(
            icon=make_path("assets", "icons", "delete.svg"),
            tool_tip="Remove current operator from list.",
            clicked=self.on_remove_clicked
        )
        self.append(self.operator_combo_box)
        self.append(self.add_button)
        self.append(self.remove_button)

    def on_add_clicked(self):
        operator = ui.get_text(
            text="",
            title="Add operator",
            label="Enter name of operator to add."
        )
        if operator:
            if operator not in self.operator_combo_box:
                self.operator_combo_box.append(operator)
            self.operator_combo_box.current = operator

    def on_remove_clicked(self):
        index = self.operator_combo_box.qt.currentIndex()
        if index >= 0:
            result = QtWidgets.QMessageBox.question(
                self.qt,
                "Remove operator",
                f"Do you want to remove operator {self.operator_combo_box.qt.currentText()!r} from the list?"
            )
            if result == QtWidgets.QMessageBox.Yes:
                self.operator_combo_box.qt.removeItem(index)

    def readSettings(self):
        self.operator_combo_box.readSettings()

    def writeSettings(self):
        self.operator_combo_box.writeSettings()


class PositionsComboBox(ui.ComboBox, SettingsMixin):

    def readSettings(self):
        self.clear()
        for position in settings.tablePositions():
            self.append(f"{position} ({position.x:.3f}, {position.y:.3f}, {position.z:.3f})")
        index = self.settings.get("current_table_position") or 0
        if 0 <= index < len(self):
            self.current = self[index]

    def writeSettings(self):
        index = self.index(self.current or 0)
        self.settings["current_table_position"] = index
