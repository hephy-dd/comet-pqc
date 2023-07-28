import math
import os
from typing import Optional

from comet import ui
from PyQt5 import QtCore, QtWidgets

from .core.position import Position
from .core.utils import make_path, user_home
from .settings import settings
from .utils import (
    create_icon,
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
    "PositionsComboBox"
]


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
        self.setProperty("checkedIcon", create_icon(12, "green").qt)
        self.setProperty("uncheckedIcon", create_icon(12, "grey").qt)
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

        self.xLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.xLabel.setText("X")
        self.xLabel.setToolTip("X axis position")

        self.yLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.yLabel.setText("Y")
        self.yLabel.setToolTip("Y axis position")

        self.zLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
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

        self.xLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.xLabel.setText("X")
        self.xLabel.setToolTip("X axis calibration state")

        self.yLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.yLabel.setText("Y")
        self.yLabel.setToolTip("Y axis calibration state")

        self.zLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
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

    @property
    def current_location(self):
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
        location = self.current_location
        self.remove_button.enabled = len(self.location_combo_box) > 1

    def on_select_clicked(self):
        value = ui.directory_open(
            title="Select directory",
            path=self.current_location
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
                message = f"Do you want to remove directory {self.location_combo_box.qt.currentText()!r} from the list?"
                result = QtWidgets.QMessageBox.question(self, "Remove directory", message)
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
        locations = settings.output_path
        if not locations:
            locations = [os.path.join(user_home(), "PQC")]
        for location in locations:
            self.append_location(location)
        self.location_combo_box.current = settings.current_output_path
        self.update_locations()

    def writeSettings(self):
        self.update_locations()
        settings.output_path = self.locations
        settings.current_output_path = self.location_combo_box.current


class OperatorComboBox(ui.ComboBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duplicates_enabled = False

    def readSettings(self):
        self.clear()
        for operator in settings.operators:
            self.append(operator)
        self.current = settings.current_operator

    def writeSettings(self):
        settings.current_operator = self.current
        operators = []
        for index in range(len(self)):
            operators.append(self.qt.itemText(index))
        settings.operators = operators


class OperatorWidget(ui.Row):

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
            message = f"Do you want to remove operator {self.operator_combo_box.qt.currentText()!r} from the list?"
            result = QtWidgets.QMessageBox.question(self, "Remove operator", message)
            if result == QtWidgets.QMessageBox.Yes:
                self.operator_combo_box.qt.removeItem(index)

    def readSettings(self):
        self.operator_combo_box.readSettings()

    def writeSettings(self):
        self.operator_combo_box.writeSettings()


class PositionsComboBox(ui.ComboBox):

    def readSettings(self):
        self.clear()
        for position in settings.table_positions:
            self.append(f"{position} ({position.x:.3f}, {position.y:.3f}, {position.z:.3f})")
        index = settings.settings.get("current_table_position") or 0
        if 0 <= index < len(self):
            self.current = self[index]

    def writeSettings(self):
        index = self.index(self.current or 0)
        settings.settings["current_table_position"] = index
