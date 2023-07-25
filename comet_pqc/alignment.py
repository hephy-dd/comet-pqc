"""Table control widgets and dialogs."""

import logging
import math
from typing import Optional

from PyQt5 import QtCore, QtWidgets

import comet
import comet.ui as ui
from PyQt5 import QtCore, QtGui, QtChart

from .components import (
    CalibrationWidget,
    PositionLabel,
    PositionWidget,
    ToggleButton,
)
from .core.position import Position
from .settings import TablePosition, settings
from .utils import format_metric, caldone_valid, format_switch, handle_exception

DEFAULT_STEP_UP_DELAY = 0.
DEFAULT_STEP_UP_MULTIPLY = 2
DEFAULT_LCR_UPDATE_INTERVAL = .100
DEFAULT_MATRIX_CHANNELS = [
    "3H01", "2B04", "1B03", "1B12", "2B06", "2B07", "2B08", "2B09",
    "2B10", "2B11", "1H04", "1H05", "1H06", "1H07", "1H08", "1H09",
    "1H10", "1H11", "2H12", "2H05", "1A01"
]

logger = logging.getLogger(__name__)


def safe_z_position(z: float) -> float:
    z_limit = settings.table_z_limit
    if z > z_limit:
        QtWidgets.QMessageBox.warning(
            None,
            "Z Limit",
            f"Limiting Z movement to {z_limit:.3f} mm to protect probe card.",
        )
        z = z_limit
    return z


class LinearTransform:
    """Linear transformation of n coordinates between two points."""

    def calculate(self, a: tuple, b: tuple, n: float) -> list:
        diff_x = (a[0] - b[0]) / n
        diff_y = (a[1] - b[1]) / n
        diff_z = (a[2] - b[2]) / n
        return [(a[0] - diff_x * i, a[1] - diff_y * i, a[2] - diff_z * i) for i in range(n + 1)]


class LCRWidget(QtWidgets.QWidget):

    MaxPoints = 1000

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._chart = QtChart.QChart()
        self._chart.legend().hide()
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chart.setBackgroundRoundness(0)
        self._chart.setBackgroundVisible(False)
        self._chart.setMargins(QtCore.QMargins(0, 0, 0, 0))

        self._xAxis = QtChart.QValueAxis()
        self._xAxis.setTickCount(3)
        self._xAxis.setMinorTickCount(4)
        self._xAxis.setLabelFormat("%.3f mm")
        self._chart.addAxis(self._xAxis, QtCore.Qt.AlignBottom)

        self._yAxis = QtChart.QValueAxis()
        self._yAxis.setTickCount(2)
        self._yAxis.setMinorTickCount(3)
        self._yAxis.setLabelFormat("%.2g Ohm")
        self._chart.addAxis(self._yAxis, QtCore.Qt.AlignLeft)

        self._line = QtChart.QLineSeries()
        self._line.setColor(QtGui.QColor("magenta"))

        self._chart.addSeries(self._line)
        self._line.attachAxis(self._xAxis)
        self._line.attachAxis(self._yAxis)

        self._series = QtChart.QScatterSeries()
        self._series.setName("R")
        self._series.setMarkerSize(3)
        self._series.setBorderColor(QtGui.QColor("red"))
        self._series.setColor(QtGui.QColor("red"))

        self._chart.addSeries(self._series)
        self._series.attachAxis(self._xAxis)
        self._series.attachAxis(self._yAxis)

        self._marker = QtChart.QScatterSeries()
        self._marker.setMarkerSize(9)
        self._marker.setBorderColor(QtGui.QColor("red"))
        self._marker.setColor(QtGui.QColor("red"))

        self._chart.addSeries(self._marker)
        self._marker.attachAxis(self._xAxis)
        self._marker.attachAxis(self._yAxis)

        self.setMinimumSize(160, 60)

        self.chartView: QtChart.QChartView = QtChart.QChartView(self._chart)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chartView)

    def yLimits(self) -> list:
        limits: list = []
        for point in self._series.pointsVector():
            limits.append(point.y())
        return limits

    def clear(self) -> None:
        self._series.clear()

    def append(self, x: float, y: float) -> None:
        if self._series.count() > type(self).MaxPoints:
            self._series.remove(0)
        self._series.append(QtCore.QPointF(x, y))
        self.setMarker(x, y)

    def setLimits(self, x: float) -> None:
        self._xAxis.setRange(x - 0.050, x + 0.050)
        limits = self.yLimits()
        if limits:
            self._yAxis.setRange(min(limits), max(limits))
            self._yAxis.applyNiceNumbers()
            self._yAxis.setTickCount(2)

    def setLine(self, x: float) -> None:
        self._line.clear()
        self._line.append(x, self._yAxis.min())
        self._line.append(x, self._yAxis.max())

    def setMarker(self, x: float, y: float) -> None:
        self._marker.clear()
        self._marker.append(x, y)


class TableSampleItem(ui.TreeItem):

    def __init__(self, sample_item):
        super().__init__()
        self.sample_item = sample_item
        self.setName("/".join([item for item in (sample_item.name, sample_item.sample_type) if item]))
        self.position = sample_item.sample_position
        for contact_item in sample_item.children:
            self.append(TableContactItem(contact_item))

    def name(self) -> str:
        return self.qt.text(0)

    def setName(self, name: str) -> None:
        self.qt.setText(0, name)

    @property
    def position(self):
        return self[1].value

    @position.setter
    def position(self, value):
        self[1].value = value

    def update_contacts(self):
        for contact_item in self.children:
            contact_item.update_contact()
            logger.info("Updated contact position: %s %s %s", self.name(), contact_item.name(), contact_item.position)

    def calculate_positions(self):
        tr = LinearTransform()
        count = len(self.children)
        if count > 2:
            first = self.children[0].position
            last = list(self.children)[-1].position
            for i, position in enumerate(tr.calculate(first, last, count - 1)):
                self.children[i].position = position


class TableContactItem(ui.TreeItem):

    def __init__(self, contact_item):
        super().__init__()
        for i in range(2, 5):
            self[i].qt.setTextAlignment(i, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.contact_item = contact_item
        self.setName(contact_item.name)
        self.position = contact_item.position

    def name(self) -> str:
        return self.qt.text(0)

    def setName(self, name: str) -> None:
        self.qt.setText(0, name)

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        x, y, z = value
        self.__position = x, y, z
        self[2].value = format(x, ".3f") if x is not None else None
        self[3].value = format(y, ".3f") if y is not None else None
        self[4].value = format(z, ".3f") if z is not None else None

    @property
    def has_position(self):
        return any((not math.isnan(value) for value in self.__position))

    def update_contact(self):
        self.contact_item.position = self.position

    def reset(self) -> None:
        self.position = (float("nan"), float("nan"), float("nan"))


class TableContactsWidget(ui.Row):

    def __init__(self, position_picked=None, absolute_move=None, **kwargs):
        super().__init__(**kwargs)
        self.position_picked = position_picked
        self.absolute_move = absolute_move
        self.contacts_tree = ui.Tree(
            header=("Contact", "Pos", "X", "Y", "Z", None),
            selected=self.on_contacts_selected
        )
        self.contacts_tree.fit()
        self.pick_button = ui.Button(
            text="Assign &Position",
            tool_tip="Assign current table position to selected position item",
            clicked=self.on_pick_position,
            enabled=False
        )
        self.calculate_button= ui.Button(
            text="&Calculate",
            clicked=self.on_calculate,
            enabled=False
        )
        self.move_button= ui.Button(
            text="&Move",
            tool_tip="Move to selected position",
            clicked=self.on_move,
            enabled=False
        )
        self.reset_button = ui.Button(
            text="&Reset",
            clicked=self.on_reset,
            enabled=False
        )
        self.reset_all_button = ui.Button(
            text="Reset &All",
            clicked=self.on_reset_all
        )
        self.append(self.contacts_tree)
        self.append(ui.Column(
            self.pick_button,
            self.move_button,
            self.calculate_button,
            ui.Spacer(),
            self.reset_button,
            self.reset_all_button
        ))
        self.stretch = 1, 0

    def append_sample(self, sample_item):
        self.contacts_tree.append(TableSampleItem(sample_item))

    def on_contacts_selected(self, item):
        self.update_button_states(item)

    def update_button_states(self, item=None):
        if item is None:
            item = self.contacts_tree.current
        is_contact = isinstance(item, TableContactItem)
        self.pick_button.enabled = is_contact
        self.move_button.enabled = item.has_position if is_contact else False
        self.calculate_button.enabled = not is_contact
        self.reset_button.enabled = is_contact

    def on_pick_position(self):
        item = self.contacts_tree.current
        if isinstance(item, TableContactItem):
            def callback(x, y, z):
                item.position = x, y, z
                self.contacts_tree.fit()
            self.emit(self.position_picked, callback)

    def on_reset(self):
        item = self.contacts_tree.current
        if isinstance(item, TableContactItem):
            item.reset()
            self.contacts_tree.fit()

    def on_reset_all(self):
        if ui.show_question("Do you want to reset all contact positions?"):
            for sample_item in self.contacts_tree:
                for contact_item in sample_item.children:
                    contact_item.reset()
            self.contacts_tree.fit()

    def on_move(self):
        current_item = self.contacts_tree.current
        if isinstance(current_item, TableContactItem):
            if current_item.has_position:
                if ui.show_question(f"Do you want to move table to contact {current_item.name()}?"):
                    x, y, z = current_item.position
                    self.emit(self.absolute_move, Position(x, y, z))

    def on_calculate(self):
        current_item = self.contacts_tree.current
        if isinstance(current_item, TableSampleItem):
            current_item.calculate_positions()

    def loadSamples(self, sample_items) -> None:
        self.contacts_tree.clear()
        for sample_item in sample_items:
            self.append_sample(sample_item)
        self.contacts_tree.fit()

    def updateSamples(self) -> None:
        for sample_item in self.contacts_tree:
            sample_item.update_contacts()

    def setLocked(self, locked: bool) -> None:
        if locked:
            self.pick_button.qt.setEnabled(False)
            self.move_button.qt.setEnabled(False)
            self.calculate_button.qt.setEnabled(False)
            self.reset_button.qt.setEnabled(False)
        else:
            self.update_button_states()
        self.reset_all_button.qt.setEnabled(not locked)


class TablePositionItem(ui.TreeItem):

    def __init__(self):
        super().__init__()
        for i in range(1, 4):
            self[i].qt.setTextAlignment(i, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.setPosition(0, 0, 0)

    def name(self) -> str:
        return self.qt.text(0)

    def setName(self, name: str) -> None:
        self.qt.setText(0, name)

    def position(self) -> tuple:
        return self.__position

    def setPosition(self, x, y, z) -> None:
        self.__position = x, y, z
        self.qt.setText(1, format(x, ".3f"))
        self.qt.setText(2, format(y, ".3f"))
        self.qt.setText(3, format(z, ".3f"))

    def comment(self) -> str:
        return self.qt.text(4)

    def setComment(self, comment: str) -> None:
        self.qt.setText(4, comment)


class PositionDialog(QtWidgets.QDialog):

    positionPicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.nameLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.nameLabel.setText("Name")
        self.nameLabel.setToolTip("Position name")

        self.nameLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.nameLineEdit.setText("Unnamed")

        self.xLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.xLabel.setText("X")
        self.xLabel.setToolTip("Position X coordinate")

        self.xSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.xSpinBox.setRange(0, 1000)
        self.xSpinBox.setDecimals(3)
        self.xSpinBox.setSuffix(" mm")

        self.yLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.yLabel.setText("X")
        self.yLabel.setToolTip("Position Y coordinate")

        self.ySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.ySpinBox.setRange(0, 1000)
        self.ySpinBox.setDecimals(3)
        self.ySpinBox.setSuffix(" mm")

        self.zLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.zLabel.setText("Z")
        self.zLabel.setToolTip("Position Z coordinate")

        self.zSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zSpinBox.setRange(0, 1000)
        self.zSpinBox.setDecimals(3)
        self.zSpinBox.setSuffix(" mm")

        self.commentLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.commentLabel.setText("Comment")
        self.commentLabel.setToolTip("Optional position comment")

        self.commentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.assignButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.assignButton.setText("Assign Position")
        self.assignButton.setToolTip("Assign current table position.")
        self.assignButton.clicked.connect(self.positionPicked.emit)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        gridLayout = QtWidgets.QGridLayout()
        gridLayout.addWidget(self.xLabel, 0, 0)
        gridLayout.addWidget(self.xSpinBox, 1, 0)
        gridLayout.addWidget(self.yLabel, 0, 1)
        gridLayout.addWidget(self.ySpinBox, 1, 1)
        gridLayout.addWidget(self.zLabel, 0, 2)
        gridLayout.addWidget(self.zSpinBox, 1, 2)
        gridLayout.addWidget(self.assignButton, 1, 3)
        gridLayout.setColumnStretch(3, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.nameLabel)
        layout.addWidget(self.nameLineEdit)
        layout.addLayout(gridLayout)
        layout.addWidget(self.commentLabel)
        layout.addWidget(self.commentLineEdit)
        layout.addStretch()
        layout.addWidget(self.buttonBox)

    def name(self) -> None:
        return self.nameLineEdit.text()

    def setName(self, name: str) -> None:
        self.nameLineEdit.setText(name)

    def position(self) -> tuple:
        x = self.xSpinBox.value()
        y = self.ySpinBox.value()
        z = self.zSpinBox.value()
        return x, y, z

    def setPosition(self, x: float, y: float, z: float) -> None:
        self.xSpinBox.setValue(x)
        self.ySpinBox.setValue(y)
        self.zSpinBox.setValue(z)

    def comment(self) -> str:
        return self.commentLineEdit.text()

    def setComment(self, comment: str) -> None:
        self.commentLineEdit.setText(comment)


class TablePositionsWidget(ui.Row):

    def __init__(self, position_picked=None, absolute_move=None, **kwargs):
        super().__init__(**kwargs)
        self.position_picked = position_picked
        self.absolute_move = absolute_move
        self.positions_tree = ui.Tree(
            header=("Name", "X", "Y", "Z", "Comment"),
            root_is_decorated=False,
            selected=self.on_position_selected,
            double_clicked=self.on_position_double_clicked
        )
        self.add_button = ui.Button(
            text="&Add",
            tool_tip="Add new position item",
            clicked=self.on_add_position
        )
        self.edit_button = ui.Button(
            text="&Edit",
            tool_tip="Edit selected position item",
            clicked=self.on_edit_position,
            enabled=False
        )
        self.remove_button = ui.Button(
            text="&Remove",
            tool_tip="Remove selected position item",
            clicked=self.on_remove_position,
            enabled=False
        )
        self.move_button= ui.Button(
            text="&Move",
            tool_tip="Move to selected position",
            clicked=self.on_move,
            enabled=False
        )
        self.import_button = ui.Button(
            text="Import...",
            tool_tip="Import from CSV",
            clicked=self.on_import,
        )
        self.export_button = ui.Button(
            text="Export...",
            tool_tip="Export to CSV",
            clicked=self.on_export,
        )
        self.append(self.positions_tree)
        self.append(ui.Column(
            self.move_button,
            ui.Spacer(),
            self.add_button,
            self.edit_button,
            self.remove_button,
            self.import_button,
            self.export_button,

        ))
        self.stretch = 1, 0

    def readSettings(self) -> None:
        self.positions_tree.clear()
        for position in settings.table_positions:
            item = TablePositionItem()
            item.setName(position.name)
            item.setPosition(position.x,position.y, position.z)
            item.setComment(position.comment)
            self.positions_tree.append(item)
        self.positions_tree.fit()

    def writeSettings(self) -> None:
        positions: list = []
        for item in self.positions_tree:
            x, y, z = item.position()
            positions.append(TablePosition(
                name=item.name(),
                x=x,
                y=y,
                z=z,
                comment=item.comment()
            ))
        settings.table_positions = positions

    def setLocked(self, locked: bool) -> None:
        if locked:
            self.add_button.enabled = False
            self.edit_button.enabled = False
            self.remove_button.enabled = False
            self.move_button.enabled = False
            # Remove event
            self.positions_tree.double_clicked = None
        else:
            enabled = self.positions_tree.current is not None
            self.add_button.enabled = True
            self.edit_button.enabled = enabled
            self.remove_button.enabled = enabled
            self.move_button.enabled = enabled
            # Restore event
            self.positions_tree.double_clicked = self.on_position_double_clicked

    def on_import(self) -> None:
        filename, ok = QtWidgets.QFileDialog.getOpenFileName(self.qt, "Import CSV", "", "CSV (*.csv);;All files (*)")
        if ok:
            ...


    def on_export(self) -> None:
        filename, ok = QtWidgets.QFileDialog.getSaveFileName(self.qt, "Export CSV", "", "CSV (*.csv);;All files (*)")
        if ok:
            ...

    def on_position_selected(self, item):
        enabled = item is not None
        self.edit_button.enabled = True
        self.remove_button.enabled = True
        self.move_button.enabled = True

    def on_position_double_clicked(self, *args):
        self.on_move()

    def on_position_picked(self, callback):
        self.emit(self.position_picked, callback)

    def on_add_position(self):
        dialog = PositionDialog()
        dialog.positionPicked.connect(lambda dialog=dialog: self.on_position_picked(dialog.setPosition))  # TODO
        if dialog.exec() == dialog.Accepted:
            name = dialog.name()
            x, y, z = dialog.position()
            comment = dialog.comment()
            item = TablePositionItem()
            item.setName()
            item.setPosition(x, y, z)
            item.setComment(comment)
            self.positions_tree.append(item)
            self.positions_tree.fit()

    def on_edit_position(self):
        item = self.positions_tree.current
        if isinstance(item, TablePositionItem):
            dialog = PositionDialog()
            dialog.positionPicked.connect(lambda dialog=dialog: self.on_position_picked(dialog.setPosition))  # TODO
            dialog.setName(item.name())
            dialog.setPosition(*item.position())
            dialog.setComment(item.comment())
            if dialog.exec() == dialog.Accepted:
                item.setName(dialog.name())
                item.setPosition(*dialog.position())
                item.setComment(dialog.comment())
                self.positions_tree.fit()

    def on_remove_position(self):
        item = self.positions_tree.current
        if isinstance(item, TablePositionItem):
            if ui.show_question(f"Do you want to remove position {item.name()!r}?"):
                self.positions_tree.remove(item)
                if not len(self.positions_tree):
                    self.edit_button.enabled = False
                    self.remove_button.enabled = False
                self.positions_tree.fit()

    def on_move(self):
        item = self.positions_tree.current
        if isinstance(item, TablePositionItem):
            if ui.show_question(f"Do you want to move table to position {item.name()!r}?"):
                x, y ,z = item.position()
                self.emit(self.absolute_move, Position(x, y, z))


class CalibrateWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.calibrateButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.calibrateButton.setText("Calibrate")

        self.calibrateLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.calibrateLabel.setText(
            "Calibrate table by moving into cal/rm switches\n"
            "of every axis in a safe manner to protect the probe card."
        )

        self.calibrateGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.calibrateGroupBox.setTitle("Table Calibration")

        calibrateGroupBoxLayout = QtWidgets.QHBoxLayout(self.calibrateGroupBox)
        calibrateGroupBoxLayout.addWidget(self.calibrateButton, 0)
        calibrateGroupBoxLayout.addWidget(self.calibrateLabel, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.calibrateGroupBox)
        layout.addStretch()


class OptionsWidget(QtWidgets.QWidget):

    updateIntervalChanged = QtCore.pyqtSignal(float)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Update interval

        self.updateIntervalSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.updateIntervalSpinBox.setDecimals(2)
        self.updateIntervalSpinBox.setSingleStep(0.25)
        self.updateIntervalSpinBox.setRange(0.5, 10.0)
        self.updateIntervalSpinBox.setSuffix(" s")
        self.updateIntervalSpinBox.valueChanged.connect(self.updateIntervalChanged.emit)

        self.updateIntervalGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.updateIntervalGroupBox.setTitle("Update Interval")

        updateIntervalGroupBoxLayout = QtWidgets.QHBoxLayout(self.updateIntervalGroupBox)
        updateIntervalGroupBoxLayout.addWidget(self.updateIntervalSpinBox)
        updateIntervalGroupBoxLayout.addStretch()

        # Dodge

        self.dodgeHeightSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.dodgeHeightSpinBox.setToolTip("Dodge height in microns.")
        self.dodgeHeightSpinBox.setDecimals(0)
        self.dodgeHeightSpinBox.setRange(0, 10_000)
        self.dodgeHeightSpinBox.setSingleStep(1)
        self.dodgeHeightSpinBox.setSuffix(" um")

        self.dodgeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.dodgeGroupBox.setTitle("X/Y Dodge")
        self.dodgeGroupBox.setToolTip("Enables -/+ Z dodge for XY movements.")
        self.dodgeGroupBox.setCheckable(True)

        dodgeGroupBoxLayout = QtWidgets.QVBoxLayout(self.dodgeGroupBox)
        dodgeGroupBoxLayout.addWidget(QtWidgets.QLabel("Height"))
        dodgeGroupBoxLayout.addWidget(self.dodgeHeightSpinBox)
        dodgeGroupBoxLayout.addStretch()

        # Contact quality

        self.lcrResetOnMoveCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.lcrResetOnMoveCheckBox.setText("Reset graph on X/Y move")

        self.contactQualityGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.contactQualityGroupBox.setTitle("Contact Quality (LCR)")

        contactQualityGroupBoxLayout = QtWidgets.QHBoxLayout(self.contactQualityGroupBox)
        contactQualityGroupBoxLayout.addWidget(self.lcrResetOnMoveCheckBox)
        contactQualityGroupBoxLayout.addStretch()

        # Step up

        self.stepUpDelaySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.stepUpDelaySpinBox.setDecimals(0)
        self.stepUpDelaySpinBox.setRange(0, 1_000)
        self.stepUpDelaySpinBox.setSingleStep(25)
        self.stepUpDelaySpinBox.setSuffix(" ms")

        self.stepUpMulitplySpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.stepUpMulitplySpinBox.setRange(1, 10)
        self.stepUpMulitplySpinBox.setSingleStep(1)
        self.stepUpMulitplySpinBox.setSuffix(" x")

        self.stepUpGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepUpGroupBox.setTitle("Step Up (↑⇵)")

        stepUpGroupBoxLayout = QtWidgets.QGridLayout(self.stepUpGroupBox)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Delay"), 0, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpDelaySpinBox, 0, 1)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Multiplicator (⇵)"), 1, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpMulitplySpinBox, 1, 1)
        stepUpGroupBoxLayout.setColumnStretch(2, 1)

        # LCR options

        self.lcrUpdateIntervalSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrUpdateIntervalSpinBox.setDecimals(0)
        self.lcrUpdateIntervalSpinBox.setRange(0, 1_000)
        self.lcrUpdateIntervalSpinBox.setSingleStep(25)
        self.lcrUpdateIntervalSpinBox.setSuffix(" ms")

        self.lcrMatrixChannelsLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.lcrOptionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrOptionsGroupBox.setTitle("Contact Quality (LCR)")

        lcrOptionsGroupBoxLayout = QtWidgets.QGridLayout(self.lcrOptionsGroupBox)
        lcrOptionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Reading Interval"), 0, 0)
        lcrOptionsGroupBoxLayout.addWidget(self.lcrUpdateIntervalSpinBox, 0, 1)
        lcrOptionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Matrix Channels"), 1, 0)
        lcrOptionsGroupBoxLayout.addWidget(self.lcrMatrixChannelsLineEdit, 1, 1)

        # Layout

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.updateIntervalGroupBox, 0, 0)
        layout.addWidget(self.dodgeGroupBox, 0, 1)
        layout.addWidget(self.contactQualityGroupBox, 0, 2)
        layout.addWidget(self.stepUpGroupBox, 1, 0, 1, 3)
        layout.addWidget(self.lcrOptionsGroupBox, 2, 0, 1, 3)
        layout.setRowStretch(3, 1)
        layout.setColumnStretch(2, 1)

    def updateInterval(self) -> float:
        return self.updateIntervalSpinBox.value()

    def setUpdateInterval(self, seconds: float) -> None:
        self.updateIntervalSpinBox.setValue(seconds)

    def isDodgeEnabled(self) -> bool:
        return self.dodgeGroupBox.isChecked()

    def setDodgeEnabled(self, enabled: bool) -> None:
        self.dodgeGroupBox.setChecked(enabled)

    def dodgeHeight(self) -> float:
        """Return dodge height in millimeters."""
        return (self.dodgeHeightSpinBox.value() * comet.ureg("um")).to("mm").m

    def setDodgeHeight(self, height: float) -> None:
        """Set dodge height in millimeters."""
        self.dodgeHeightSpinBox.setValue((height * comet.ureg("mm")).to("um").m)

    def isLcrResetOnMove(self) -> bool:
        return self.lcrResetOnMoveCheckBox.isChecked()

    def setLcrResetOnMove(self, enabled: bool) -> None:
        self.lcrResetOnMoveCheckBox.setChecked(enabled)

    def stepUpDelay(self) -> float:
        """Return step up delay in seconds."""
        return (self.stepUpDelaySpinBox.value() * comet.ureg("ms")).to("s").m

    def setStepUpDelay(self, seconds: float) -> None:
        self.stepUpDelaySpinBox.setValue((seconds * comet.ureg("s")).to("ms").m)

    def stepUpMultiply(self) -> int:
        """Return step up delay in seconds."""
        return self.stepUpMulitplySpinBox.value()

    def setStepUpMultiply(self, factor: int) -> None:
        self.stepUpMulitplySpinBox.setValue(factor)

    def lcrUpdateInterval(self) -> float:
        """LCR update interval in seconds."""
        return (self.lcrUpdateIntervalSpinBox.value() * comet.ureg("ms")).to("s").m

    def setLcrUpdateInterval(self, seconds: float) -> None:
        self.lcrUpdateIntervalSpinBox.setValue((seconds * comet.ureg("s")).to("ms").m)

    def lcrMatrixChannels(self) -> list:
        """Matrix channels used for LCR readings."""
        tokens: list = []
        for token in self.lcrMatrixChannelsLineEdit.text().split(","):
            token = token.strip()
            if token:
                tokens.append(token)
        return tokens

    def setLcrMatrixChannels(self, channels: list) -> None:
        self.lcrMatrixChannelsLineEdit.setText(", ".join([token for token in channels]))


class AlignmentDialog(QtWidgets.QDialog):

    process = None

    default_steps = [
        {"step_size": 1.0, "step_color": "green"}, # microns!
        {"step_size": 10.0, "step_color": "orange"},
        {"step_size": 100.0, "step_color": "red"},
    ]

    maximum_z_step_size = 0.025 # mm
    z_limit = 0.0

    probecardLightToggled = QtCore.pyqtSignal(bool)
    microscopeLightToggled = QtCore.pyqtSignal(bool)
    boxLightToggled = QtCore.pyqtSignal(bool)

    lcrFailed = QtCore.pyqtSignal(Exception, object)
    lcrReadingChanged = QtCore.pyqtSignal(float, float)

    def __init__(self, process, lcr_process, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Alignment")

        self.lcr_process = lcr_process
        self.lcr_process.failed = self.lcrFailed.emit
        self.lcr_process.reading = self.lcrReadingChanged.emit

        self.lcrFailed.connect(self.setLcrFailed)
        self.lcrReadingChanged.connect(self.setLcrReading)

        self.mount(process)

        # Control group box

        self.xAddButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.xAddButton.setText("+X")
        self.xAddButton.setFixedSize(32, 32)
        self.xAddButton.clicked.connect(self.on_add_x)

        self.xSubButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.xSubButton.setText("-X")
        self.xSubButton.setFixedSize(32, 32)
        self.xSubButton.clicked.connect(self.on_sub_x)

        self.yAddButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.yAddButton.setText("+Y")
        self.yAddButton.setFixedSize(32, 32)
        self.yAddButton.clicked.connect(self.on_add_y)

        self.ySubButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.ySubButton.setText("-Y")
        self.ySubButton.setFixedSize(32, 32)
        self.ySubButton.clicked.connect(self.on_sub_y)

        self.zAddButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.zAddButton.setText("+Z")
        self.zAddButton.setFixedSize(32, 32)
        self.zAddButton.clicked.connect(self.on_add_z)

        self.zSubButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.zSubButton.setText("-Z")
        self.zSubButton.setFixedSize(32, 32)
        self.zSubButton.clicked.connect(self.on_sub_z)

        self.stepUpButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.stepUpButton.setText("↑⇵")
        self.stepUpButton.setFixedSize(32, 32)
        self.stepUpButton.setToolTip("Step up, move single step up then double step down and double step up (experimental).")
        self.stepUpButton.clicked.connect(self.on_step_up)

        self.allKeypadButtons: list = [
            self.xAddButton,
            self.xSubButton,
            self.yAddButton,
            self.ySubButton,
            self.zAddButton,
            self.zSubButton,
            self.stepUpButton
        ]

        self.keypadGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.keypadGroupBox.setTitle("Control")

        keypadGroupBoxLayout = QtWidgets.QGridLayout(self.keypadGroupBox)
        keypadGroupBoxLayout.addWidget(self.xSubButton, 1, 2)
        keypadGroupBoxLayout.addWidget(self.zAddButton, 1, 5)
        keypadGroupBoxLayout.addWidget(self.stepUpButton, 1, 6)
        keypadGroupBoxLayout.addWidget(self.ySubButton, 2, 1)
        keypadGroupBoxLayout.addWidget(self.yAddButton, 2, 3)
        keypadGroupBoxLayout.addWidget(self.xAddButton, 3, 2)
        keypadGroupBoxLayout.addWidget(self.zSubButton, 3, 5)
        keypadGroupBoxLayout.setRowStretch(0, 1)
        keypadGroupBoxLayout.setRowStretch(4, 1)

        # Step width group box

        self.stepWidthGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepWidthGroupBox.setTitle("Step Width")

        stepWidthGroupBoxLayout = QtWidgets.QVBoxLayout(self.stepWidthGroupBox)

        self.stepWidthButtonGroup: QtWidgets.QButtonGroup = QtWidgets.QButtonGroup(self)
        self.stepWidthButtonGroup.buttonToggled.connect(self.toggleStepWidth)

        # Create step width radio buttons
        for item in self.load_table_step_sizes():
            step_size = item.get("step_size") * comet.ureg("um")
            step_color = item.get("step_color")
            step_size_label = format_metric(step_size.to("m").m, "m", decimals=1)
            button = QtWidgets.QRadioButton(self)
            button.setText(step_size_label)
            button.setToolTip(f"Move in {step_size_label} steps.")
            button.setStyleSheet(f"QRadioButton:enabled{{color:{step_color};}}")
            button.setChecked(len(self.stepWidthButtonGroup.buttons()) == 0)
            button.movement_width = step_size.to("mm").m
            button.movement_color = step_color
            self.stepWidthButtonGroup.addButton(button)
            stepWidthGroupBoxLayout.addWidget(button)
        stepWidthGroupBoxLayout.addStretch()

        # Lights group box

        self.probecardLightButton = ToggleButton().qt
        self.probecardLightButton.setText("PC Light")
        self.probecardLightButton.setToolTip("Toggle probe card light")
        self.probecardLightButton.setCheckable(True)
        self.probecardLightButton.setChecked(False)
        self.probecardLightButton.toggled.connect(self.probecardLightToggled.emit)

        self.microscopeLightButton = ToggleButton().qt
        self.microscopeLightButton.setText("Mic Light")
        self.microscopeLightButton.setToolTip("Toggle microscope light")
        self.microscopeLightButton.setCheckable(True)
        self.microscopeLightButton.setChecked(False)
        self.microscopeLightButton.toggled.connect(self.microscopeLightToggled.emit)

        self.boxLightButton = ToggleButton().qt
        self.boxLightButton.setText("Box Light")
        self.boxLightButton.setToolTip("Toggle box light")
        self.boxLightButton.setCheckable(True)
        self.boxLightButton.setChecked(False)
        self.boxLightButton.toggled.connect(self.boxLightToggled.emit)

        self.lightsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lightsGroupBox.setTitle("Lights")

        lightsGroupBoxLayout = QtWidgets.QVBoxLayout(self.lightsGroupBox)
        lightsGroupBoxLayout.addWidget(self.probecardLightButton)
        lightsGroupBoxLayout.addWidget(self.microscopeLightButton)
        lightsGroupBoxLayout.addWidget(self.boxLightButton)
        lightsGroupBoxLayout.addStretch()

        # LCR group box

        self.lcrPrimLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrPrimLineEdit.setReadOnly(True)

        self.lcrSecLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrSecLineEdit.setReadOnly(True)

        self.lcrWidget: LCRWidget = LCRWidget(self)

        self.lcrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("Contact Quality (LCR)")
        self.lcrGroupBox.setCheckable(True)
        self.lcrGroupBox.setChecked(False)
        self.lcrGroupBox.toggled.connect(self.on_lcr_toggled)

        self.lcrPrimLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.lcrPrimLabel.setText("Cp")

        self.lcrSecLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.lcrSecLabel.setText("Rp")

        lcrGroupBoxLayout = QtWidgets.QGridLayout(self.lcrGroupBox)
        lcrGroupBoxLayout.addWidget(self.lcrPrimLabel, 0, 0)
        lcrGroupBoxLayout.addWidget(self.lcrPrimLineEdit, 0, 1)
        lcrGroupBoxLayout.addWidget(self.lcrSecLabel, 1, 0)
        lcrGroupBoxLayout.addWidget(self.lcrSecLineEdit, 1, 1)
        lcrGroupBoxLayout.addWidget(self.lcrWidget, 2, 0, 1, 2)

        # Position group box

        self.positions_widget = TablePositionsWidget(
            position_picked=self.on_position_picked,
            absolute_move=self.on_absolute_move
        )
        self.positions_widget.qt.setEnabled(False)

        # Contact group box

        self.contacts_widget = TableContactsWidget(
            position_picked=self.on_position_picked,
            absolute_move=self.on_absolute_move
        )
        self.contacts_widget.qt.setEnabled(False)

        self._position_widget = PositionWidget()

        self._calibration_widget = CalibrationWidget()

        # Soft limits group box

        self.zSoftLimitLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.zSoftLimitLabel.setText("Z")

        self.z_limit_label = PositionLabel()

        self.softLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.softLimitsGroupBox.setTitle("Soft Limits")

        softLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.softLimitsGroupBox)
        softLimitsGroupBoxLayout.addWidget(self.zSoftLimitLabel, 0, 0)
        softLimitsGroupBoxLayout.addWidget(self.z_limit_label.qt, 0, 1)

        # Hard limits group box

        self.xHardLimitLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.xHardLimitLabel.setText("X")

        self.x_hard_limit_label = PositionLabel()

        self.yHardLimitLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.yHardLimitLabel.setText("Y")

        self.y_hard_limit_label = PositionLabel()

        self.zHardLimitLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.zHardLimitLabel.setText("Z")

        self.z_hard_limit_label = PositionLabel()

        self.hardLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hardLimitsGroupBox.setTitle("Hard Limits")

        hardLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.hardLimitsGroupBox)
        hardLimitsGroupBoxLayout.addWidget(self.xHardLimitLabel, 0, 0)
        hardLimitsGroupBoxLayout.addWidget(self.x_hard_limit_label.qt, 0, 1)
        hardLimitsGroupBoxLayout.addWidget(self.yHardLimitLabel, 1, 0)
        hardLimitsGroupBoxLayout.addWidget(self.y_hard_limit_label.qt, 1, 1)
        hardLimitsGroupBoxLayout.addWidget(self.zHardLimitLabel, 2, 0)
        hardLimitsGroupBoxLayout.addWidget(self.z_hard_limit_label.qt, 2, 1)

        # Safety group box

        self.laserSensorLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.laserSensorLabel.setText("Laser Sensor")

        self.laserSensorSwitch = SwitchLabel(self)

        self.safetyGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.safetyGroupBox.setTitle("Safety")

        safetyGroupBoxLayout = QtWidgets.QVBoxLayout(self.safetyGroupBox)
        safetyGroupBoxLayout.addWidget(self.laserSensorLabel)
        safetyGroupBoxLayout.addWidget(self.laserSensorSwitch)

        # Calibrate tab

        self.calibrateWidget = CalibrateWidget(self)
        self.calibrateWidget.calibrateButton.clicked.connect(self.on_calibrate)

        # Options tab

        self.optionsWidget = OptionsWidget(self)
        self.optionsWidget.updateIntervalChanged.connect(self.on_update_interval_changed)

        self.topLayout = QtWidgets.QHBoxLayout()
        self.topLayout.addWidget(self.keypadGroupBox)
        self.topLayout.addWidget(self.stepWidthGroupBox)
        self.topLayout.addWidget(self.lcrGroupBox)
        self.topLayout.addWidget(self.lightsGroupBox)
        self.topLayout.addStretch()

        self.rightLayout = QtWidgets.QVBoxLayout()
        self.rightLayout.addWidget(self._position_widget.qt)
        self.rightLayout.addWidget(self._calibration_widget.qt)
        self.rightLayout.addWidget(self.softLimitsGroupBox)
        self.rightLayout.addWidget(self.hardLimitsGroupBox)
        self.rightLayout.addWidget(self.safetyGroupBox)
        self.rightLayout.addStretch()

        # Tab widget

        self.tabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.positions_widget.qt, "Move")
        self.tabWidget.addTab(self.contacts_widget.qt, "Contacts")
        self.tabWidget.addTab(self.calibrateWidget, "Calibrate")
        self.tabWidget.addTab(self.optionsWidget, "Options")

        # Bottom bar

        self.progressBar: QtWidgets.QProgressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setVisible(False)

        self.messageLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)

        self.stopButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("&Stop")
        self.stopButton.setDefault(False)
        self.stopButton.setAutoDefault(False)
        self.stopButton.setEnabled(False)
        self.stopButton.clicked.connect(self.stop)

        self.closeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.closeButton.setText("&Close")
        self.closeButton.setDefault(False)
        self.closeButton.setAutoDefault(False)
        self.closeButton.clicked.connect(self.close)

        self.bottomLayout = QtWidgets.QHBoxLayout()
        self.bottomLayout.addWidget(self.progressBar)
        self.bottomLayout.addWidget(self.messageLabel)
        self.bottomLayout.addStretch()
        self.bottomLayout.addWidget(self.stopButton)
        self.bottomLayout.addWidget(self.closeButton)

        # Layout

        layout = QtWidgets.QGridLayout(self)
        layout.addLayout(self.topLayout, 0, 0, 1, 1)
        layout.addWidget(self.tabWidget, 1, 0, 1, 1)
        layout.addLayout(self.rightLayout, 0, 1, 2, 1)
        layout.addLayout(self.bottomLayout, 2, 0, 1, 2)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(1, 1)

        self.resetPosition()
        self.resetCaldone()
        self.updateLimits()
        self.resetSafety()
        self.updateKeypadButtons()

    @property
    def step_width(self):
        for button in self.stepWidthButtonGroup.buttons():
            if button.isChecked():
                return abs(button.movement_width)
        return 0

    @property
    def step_color(self):
        for button in self.stepWidthButtonGroup.buttons():
            if button.isChecked():
                return button.movement_color
        return "black"

    def load_table_step_sizes(self):
        return settings.settings.get("table_step_sizes") or self.default_steps

    def resetPosition(self) -> None:
        self.setPosition(Position())

    def setPosition(self, position: Position) -> None:
        self.current_position = position
        self._position_widget.setPosition(position)
        self.updateLimits()
        self.updateKeypadButtons()
        if math.isfinite(position.z):
            self.lcrWidget.setLimits(position.z)
            self.lcrWidget.setLine(position.z)

    def resetCaldone(self) -> None:
        self._calibration_widget.reset()

    def setCaldone(self, position: Position) -> None:
        self.current_caldone = position
        self.positions_widget.qt.setEnabled(caldone_valid(position))
        self.contacts_widget.qt.setEnabled(caldone_valid(position))
        self.keypadGroupBox.setEnabled(caldone_valid(position))
        self._calibration_widget.setCalibration(position)

    def updateLimits(self) -> None:
        x, y, z = self.current_position
        self.z_limit_label.qt.setStyleSheet("")
        if not math.isnan(z):
            if z >= self.z_limit:
                self.z_limit_label.qt.setStyleSheet("QLabel:enabled{color:red;}")

    def resetSafety(self) -> None:
        self.laserSensorSwitch.setValue(None)

    def updateSafety(self, value) -> None:
        self.laserSensorSwitch.setValue(value)

    def updateKeypadButtons(self) -> None:
        x, y, z = self.current_position
        self.update_x_buttons(x)
        self.update_y_buttons(y)
        self.update_z_buttons(z)
        for button in self.allKeypadButtons:
            button.setStyleSheet(f"QPushButton:enabled{{color:{self.step_color or 'black'}}}")

    def update_x_buttons(self, x):
        x_enabled = True
        if not math.isnan(x):
            if (x - self.step_width) < 0:
                x_enabled = False
        self.xSubButton.setEnabled(x_enabled)

    def update_y_buttons(self, y):
        y_enabled = True
        if not math.isnan(y):
            if (y - self.step_width) < 0:
                y_enabled = False
        self.ySubButton.setEnabled(y_enabled)

    def update_z_buttons(self, z):
        # Disable move up button for large step sizes
        z_enabled = False
        if not math.isnan(z):
            if (z + self.step_width) <= self.z_limit:
                z_enabled = True
            else:
                z_enabled = self.step_width <= self.maximum_z_step_size
        self.zAddButton.setEnabled(z_enabled)
        step_up_limit = comet.ureg("10.0 um").to("mm").m
        self.stepUpButton.setEnabled(z_enabled and (self.step_width <= step_up_limit))  # TODO

    def relative_move_xy(self, x, y):
        # Dodge on X/Y movements.
        if self.optionsWidget.isDodgeEnabled():
            dodgeHeight = self.optionsWidget.dodgeHeight()
            current_position = self.current_position
            if current_position.z < dodgeHeight:
                dodgeHeight = max(0, current_position.z)
            vector = [(0, 0, -dodgeHeight), (x, y, 0), (0, 0, +dodgeHeight)]
        else:
            vector = [(x, y, 0)]
        # Clear contact quality graph on X/Y movements.
        if self.optionsWidget.isLcrResetOnMove():
            self.lcrWidget.clear()
        self.process.relative_move_vector(vector)
        # Clear contact quality graph on X/Y movements.
        if self.optionsWidget.isLcrResetOnMove():
            self.lcrWidget.clear()

    def on_add_x(self):
        self.setLocked(True)
        self.relative_move_xy(+self.step_width, 0)

    def on_sub_x(self):
        self.setLocked(True)
        self.relative_move_xy(-self.step_width, 0)

    def on_add_y(self):
        self.setLocked(True)
        self.relative_move_xy(0, +self.step_width)

    def on_sub_y(self):
        self.setLocked(True)
        self.relative_move_xy(0, -self.step_width)

    def on_add_z(self):
        self.setLocked(True)
        self.process.relative_move(0, 0, +self.step_width)

    def on_sub_z(self):
        self.setLocked(True)
        self.process.relative_move(0, 0, -self.step_width)

    def on_step_up(self):
        self.setLocked(True)
        step_width = self.step_width
        multiply = self.optionsWidget.stepUpMultiply()
        vector = (
            [0, 0, +step_width],
            [0, 0, -step_width * multiply],
            [0, 0, +step_width * multiply],
        )
        self.process.relative_move_vector(vector, delay=self.optionsWidget.stepUpDelay())

    def toggleStepWidth(self, button, state: bool) -> None:
        logger.info("set table step width to %.3f mm", self.step_width)
        self.updateKeypadButtons()

    def update_probecard_light(self, state):
        self.probecardLightButton.setChecked(state)

    def update_microscope_light(self, state):
        self.microscopeLightButton.setChecked(state)

    def update_box_light(self, state):
        self.boxLightButton.setChecked(state)

    def update_lights_enabled(self, state):
        self.probecardLightButton.setEnabled(state)
        self.microscopeLightButton.setEnabled(state)
        self.boxLightButton.setEnabled(state)

    def on_move_finished(self):
        self.progressBar.setVisible(False)
        self.stopButton.setEnabled(False)
        self.setLocked(False)

    def on_calibration_finished(self):
        self.progressBar.setVisible(False)
        self.stopButton.setEnabled(False)
        self.setLocked(False)

    def setMessage(self, message: str) -> None:
        self.messageLabel.setText(message)
        logger.info(message)

    def setProgress(self, value: int, maximum: int) -> None:
        self.progressBar.setValue(value)
        self.progressBar.setMaximum(maximum)
        self.progressBar.setVisible(True)

    def on_update_interval_changed(self, seconds: float) -> None:
        self.process.update_interval = seconds

    def on_position_picked(self, callback):
        x, y, z = self.current_position
        callback(x, y, z)

    def on_absolute_move(self, position):
        # Update to safe Z position
        position = Position(position.x, position.y, safe_z_position(position.z))
        self.setLocked(True)
        # Clear contact quality graph on X/Y movements.
        self.lcrWidget.clear()
        self.stopButton.setEnabled(True)
        self.process.safe_absolute_move(position.x, position.y, position.z)

    def on_calibrate(self):
        self.setLocked(True)
        self.stopButton.setEnabled(True)
        self.process.calibrate_table()

    def stop(self) -> None:
        self.stopButton.setEnabled(False)
        self.process.stop_current_action()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        self.process.wait()
        event.accept()

    def loadSamples(self, sample_items):
        self.contacts_widget.loadSamples(sample_items)

    def updateSamples(self):
        self.contacts_widget.updateSamples()

    def readSettings(self) -> None:
        settings_ = QtCore.QSettings()
        settings_.beginGroup("tablecontrol")
        geometry = settings_.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)
        settings_.endGroup()

        self.positions_widget.readSettings()
        self.z_limit = settings.table_z_limit
        self.z_limit_label.value = self.z_limit
        x, y, z = settings.table_probecard_maximum_limits
        self.x_hard_limit_label.value = x
        self.y_hard_limit_label.value = y
        self.z_hard_limit_label.value = z
        self.optionsWidget.setStepUpDelay(settings.settings.get("tablecontrol_step_up_delay", DEFAULT_STEP_UP_DELAY))
        self.optionsWidget.setStepUpMultiply(settings.settings.get("tablecontrol_step_up_multiply", DEFAULT_STEP_UP_MULTIPLY))
        self.optionsWidget.setLcrUpdateInterval(settings.settings.get("tablecontrol_lcr_update_delay", DEFAULT_LCR_UPDATE_INTERVAL))
        matrix_channels = settings.settings.get("tablecontrol_lcr_matrix_channels") or DEFAULT_MATRIX_CHANNELS
        self.optionsWidget.setLcrMatrixChannels(matrix_channels)
        self.lcr_process.update_interval = self.optionsWidget.lcrUpdateInterval()
        self.lcr_process.matrix_channels = self.optionsWidget.lcrMatrixChannels()
        self.optionsWidget.setUpdateInterval(settings.table_control_update_interval)
        self.optionsWidget.setDodgeEnabled(settings.table_control_dodge_enabled)
        self.optionsWidget.setDodgeHeight(settings.table_control_dodge_height)
        self.optionsWidget.setLcrResetOnMove(settings.settings.get("tablecontrol_lcr_reset_on_move", True))

    def writeSettings(self) -> None:
        settings_ = QtCore.QSettings()
        settings_.beginGroup("tablecontrol")
        settings_.setValue("geometry", self.saveGeometry())
        settings_.endGroup()

        settings.settings["tablecontrol_step_up_delay"] = self.optionsWidget.stepUpDelay()
        settings.settings["tablecontrol_step_up_multiply"] = self.optionsWidget.stepUpMultiply()
        settings.settings["tablecontrol_lcr_update_delay"] = self.optionsWidget.lcrUpdateInterval()
        settings.settings["tablecontrol_lcr_matrix_channels"] = self.optionsWidget.lcrMatrixChannels()
        self.positions_widget.writeSettings()
        settings.table_control_update_interval = self.optionsWidget.updateInterval()
        settings.table_control_dodge_enabled = self.optionsWidget.isDodgeEnabled()
        settings.table_control_dodge_height = self.optionsWidget.dodgeHeight()
        settings.settings["tablecontrol_lcr_reset_on_move"] = self.optionsWidget.isLcrResetOnMove()

    def setLocked(self, locked: bool) -> None:
        self.keypadGroupBox.setEnabled(not locked)
        self.positions_widget.setLocked(locked)
        self.contacts_widget.setLocked(locked)
        self.closeButton.setEnabled(not locked)
        self.progressBar.setVisible(locked)
        if locked:
            self.progressBar.setRange(0, 0)
            self.progressBar.setValue(0)

    def mount(self, process):
        """Mount table process."""
        self.unmount()
        self.process = process
        self.process.message_changed = self.setMessage
        self.process.progress_changed = self.setProgress
        self.process.position_changed = self.setPosition
        self.process.caldone_changed = self.setCaldone
        self.process.relative_move_finished = self.on_move_finished
        self.process.absolute_move_finished = self.on_move_finished
        self.process.calibration_finished = self.on_calibration_finished
        self.process.stopped = self.on_calibration_finished

    def unmount(self):
        """Unmount table process."""
        if self.process:
            self.process.message_changed = None
            self.process.progress_changed = None
            self.process.position_changed = None
            self.process.caldone_changed = None
            self.process.relative_move_finished = None
            self.process.absolute_move_finished = None
            self.process.stopped = None
            self.process = None

    @handle_exception
    def on_lcr_toggled(self, state):
        self.lcrPrimLineEdit.setEnabled(state)
        self.lcrSecLineEdit.setEnabled(state)
        self.lcrWidget.setEnabled(state)
        if state:
            self.lcrWidget.clear()
            self.lcr_process.update_interval = self.optionsWidget.lcrUpdateInterval()
            self.lcr_process.matrix_channels = self.optionsWidget.lcrMatrixChannels()
            self.lcr_process.start()
        else:
            self.lcr_process.stop()

    def setLcrFailed(self, exc: Exception, tb=None) -> None:
        self.lcrPrimLineEdit.setText("ERROR")
        self.lcrSecLineEdit.setText("ERROR")

    def setLcrReading(self, prim: float, sec: float) -> None:
        self.lcrPrimLineEdit.setText(format_metric(prim, unit="F"))
        self.lcrSecLineEdit.setText(format_metric(sec, unit="Ohm"))
        _, _, z = self.current_position
        if math.isfinite(z) and math.isfinite(sec):
            # Append only absolute Rp readings
            self.lcrWidget.append(z, abs(sec))
            self.lcrWidget.setLine(z)


class SwitchLabel(QtWidgets.QLabel):

    def setValue(self, value) -> None:
        if value is None:
            self.setText(format(float("nan")))
            self.setStyleSheet("")
        else:
            self.setText(format_switch(value))
            if value:
                self.setStyleSheet("QLabel:enabled{color:green}" )
            else:
                self.setStyleSheet("QLabel:enabled{color:red}")
