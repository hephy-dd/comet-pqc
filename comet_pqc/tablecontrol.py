"""Table control widgets and dialogs."""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from comet import ureg
from comet.settings import SettingsMixin
from PyQt5 import QtCore, QtGui, QtWidgets, QtChart

from .components import (
    CalibrationWidget,
    PositionLabel,
    PositionWidget,
    ToggleButton,
)
from .core.position import Position
from .settings import TablePosition, settings
from .utils import format_metric, caldone_valid, format_switch, handle_exception

__all__ = ["TableControlDialog"]

DEFAULT_STEP_UP_DELAY: float = 0.
DEFAULT_STEP_UP_MULTIPLY: int = 2
DEFAULT_LCR_UPDATE_INTERVAL: float = .100
DEFAULT_MATRIX_CHANNELS: List[str] = [
    "3H01", "2B04", "1B03", "1B12", "2B06", "2B07", "2B08", "2B09",
    "2B10", "2B11", "1H04", "1H05", "1H06", "1H07", "1H08", "1H09",
    "1H10", "1H11", "2H12", "2H05", "1A01"
]

logger = logging.getLogger(__name__)


def safe_z_position(z: float) -> float:
    z_limit = settings.tableZLimit()
    if z > z_limit:
        QtWidgets.QMessageBox.warning(
            None,
            "Z Warning",
            f"Limiting Z movement to {z_limit:.3f} mm to protect probe card."
        )
        z = z_limit
    return z


class LinearTransform:
    """Linear transformation of n coordinates between two points."""

    def calculate(self, a, b, n):
        diff_x = (a[0] - b[0]) / n
        diff_y = (a[1] - b[1]) / n
        diff_z = (a[2] - b[2]) / n
        return [(a[0] - diff_x * i, a[1] - diff_y * i, a[2] - diff_z * i) for i in range(n + 1)]


class TableContactItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, contact_item) -> None:
        super().__init__()
        self._contact_item = contact_item
        self.setName(contact_item.name)
        self.setPosition(contact_item.position)
        self.setTextAlignment(2, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(3, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(4, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self):
        return self.data(2, 0x2000)

    def setPosition(self, position) -> None:
        self.setData(2, 0x2000, position)
        x, y, z = position
        self.setText(2, format(x, ".3f") if x is not None else "")
        self.setText(3, format(y, ".3f") if y is not None else "")
        self.setText(4, format(z, ".3f") if z is not None else "")

    def hasPosition(self) -> bool:
        return any((not math.isnan(value) for value in self.position()))

    def updateContactPosition(self) -> None:
        self._contact_item.position = self.position()


class TableSampleItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, sample_item) -> None:
        super().__init__()
        self._sample_item = sample_item
        self.setName("/".join([item for item in (sample_item.name, sample_item.sample_type) if item]))
        self.setPosition(sample_item.sample_position)
        for contact_item in sample_item.children:
            child = TableContactItem(contact_item)
            self.addChild(child)

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self) -> str:
        return self.text(1)

    def setPosition(self, position: str) -> None:
        self.setText(1, position)

    def allContactItems(self) -> List[TableContactItem]:
        items: List[TableContactItem] = []
        for index in range(self.childCount()):
            child = self.child(index)
            if isinstance(child, TableContactItem):
                items.append(child)
        return items

    def updateContacts(self) -> None:
        for item in self.allContactItems():
            item.updateContactPosition()
            logger.info("Updated contact position: %s %s %s", self.name(), item.name(), item.position())

    def calculatePositions(self) -> None:
        tr = LinearTransform()
        items = self.allContactItems()
        count = len(items)
        if count > 2:
            first = items[0].position()
            last = items[-1].position()
            for i, position in enumerate(tr.calculate(first, last, count - 1)):
                items[i].setPosition(position)


class TableContactsWidget(QtWidgets.QWidget):

    positionPicked: QtCore.pyqtSignal = QtCore.pyqtSignal(object)
    absoluteMove: QtCore.pyqtSignal = QtCore.pyqtSignal(Position)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.contacts_tree = QtWidgets.QTreeWidget(self)
        self.contacts_tree.setHeaderLabels(["Contact", "Pos", "X", "Y", "Z", ""])
        self.contacts_tree.currentItemChanged.connect(self.contactSelected)

        self.pickButton = QtWidgets.QPushButton(self)
        self.pickButton.setText("Assign &Position")
        self.pickButton.setToolTip("Assign current table position to selected position item")
        self.pickButton.setEnabled(False)
        self.pickButton.clicked.connect(self.pickPosition)

        self.calculateButton = QtWidgets.QPushButton(self)
        self.calculateButton.setText("&Calculate")
        self.calculateButton.setEnabled(False)
        self.calculateButton.clicked.connect(self.calculatePositions)

        self.moveButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("&Move")
        self.moveButton.setToolTip("Move to selected position")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.moveToPosition)

        self.resetButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("&Reset")
        self.resetButton.setEnabled(False)
        self.resetButton.clicked.connect(self.resetCurrentPosition)

        self.resetAllButton = QtWidgets.QPushButton(self)
        self.resetAllButton.setText("Reset &All")
        self.resetAllButton.clicked.connect(self.resetAllPositions)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.contacts_tree, 0, 0, 6, 1)
        layout.addWidget(self.pickButton, 0, 1)
        layout.addWidget(self.moveButton, 1, 1)
        layout.addWidget(self.calculateButton, 2, 1)
        layout.addWidget(self.resetButton, 4, 1)
        layout.addWidget(self.resetAllButton, 5, 1)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(3, 1)

    def appendSampleItem(self, sample_item):
        item = TableSampleItem(sample_item)
        self.contacts_tree.addTopLevelItem(item)
        item.setExpanded(True)

    def allSampleItems(self) -> List[TableSampleItem]:
        items: List[TableSampleItem] = []
        for index in range(self.contacts_tree.topLevelItemCount()):
            item = self.contacts_tree.topLevelItem(index)
            if isinstance(item, TableSampleItem):
                items.append(item)
        return items

    def contactSelected(self, current, previous):
        self.updateButtonStates(current)

    def updateButtonStates(self, item: QtWidgets.QTreeWidgetItem = None) -> None:
        if item is None:
            item = self.contacts_tree.currentItem()
        if isinstance(item, TableContactItem):
            self.pickButton.setEnabled(True)
            self.moveButton.setEnabled(item.hasPosition())
            self.calculateButton.setEnabled(False)
            self.resetButton.setEnabled(True)
        else:
            self.pickButton.setEnabled(False)
            self.moveButton.setEnabled(False)
            self.calculateButton.setEnabled(True)
            self.resetButton.setEnabled(False)

    def pickPosition(self):
        item: Optional[TableContactItem] = self.contacts_tree.currentItem()
        if isinstance(item, TableContactItem):
            def callback(x, y, z):
                item.setPosition((x, y, z))
                for index in range(self.contacts_tree.columnCount()):
                    self.contacts_tree.resizeColumnToContents(index)
            self.positionPicked.emit(callback)

    def resetCurrentPosition(self):
        item: Optional[TableContactItem] = self.contacts_tree.currentItem()
        if isinstance(item, TableContactItem):
            item.setPosition((float("nan"), float("nan"), float("nan")))
            for index in range(self.contacts_tree.columnCount()):
                self.contacts_tree.resizeColumnToContents(index)

    def resetAllPositions(self):
        result = QtWidgets.QMessageBox.question(
            self,
            "Reset Positions?",
            "Do you want to reset all contact positions?"
        )
        if result == QtWidgets.QMessageBox.Yes:
            for sample_item in self.allSampleItems():
                for contact_item in sample_item.allContactItems():
                    contact_item.setPosition((float("nan"), float("nan"), float("nan")))
            for index in range(self.contacts_tree.columnCount()):
                self.contacts_tree.resizeColumnToContents(index)

    def moveToPosition(self):
        current_item: Optional[TableContactItem] = self.contacts_tree.currentItem()
        if isinstance(current_item, TableContactItem):
            if current_item.hasPosition():
                result = QtWidgets.QMessageBox.question(
                    self,
                    "Move Table?",
                    f"Do you want to move table to contact {current_item.name()}?"
                )
                if result == QtWidgets.QMessageBox.Yes:
                    x, y, z = current_item.position()
                    self.absoluteMove.emit(Position(x, y, z))

    def calculatePositions(self) -> None:
        current_item = self.contacts_tree.currentItem()
        if isinstance(current_item, TableSampleItem):
            current_item.calculatePositions()

    def loadSamples(self, sample_items) -> None:
        self.contacts_tree.clear()
        for sample_item in sample_items:
            self.appendSampleItem(sample_item)
        for index in range(self.contacts_tree.columnCount()):
            self.contacts_tree.resizeColumnToContents(index)

    def updateSamples(self) -> None:
        for sample_item in self.allSampleItems():
            sample_item.updateContacts()

    def setLocked(self, state: bool) -> None:
        if state:
            self.pickButton.setEnabled(False)
            self.moveButton.setEnabled(False)
            self.calculateButton.setEnabled(False)
            self.resetButton.setEnabled(False)
            self.resetAllButton.setEnabled(False)
        else:
            self.updateButtonStates()
            self.resetAllButton.setEnabled(True)


class TablePositionItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, name: str, position: Position, comment: str = None):
        super().__init__()
        self.setName(name)
        self.setPosition(position)
        self.setComment(comment or "")
        self.setTextAlignment(1, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(2, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(3, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self) -> Position:
        return self.data(1, 0x2000)

    def setPosition(self, position: Position) -> None:
        self.setData(1, 0x2000, position)
        self.setText(1, format(position.x, ".3f"))
        self.setText(2, format(position.y, ".3f"))
        self.setText(3, format(position.z, ".3f"))

    def comment(self) -> str:
        return self.text(4)

    def setComment(self, comment: str) -> None:
        self.setText(4, comment)


class PositionDialog(QtWidgets.QDialog):

    positionPicked: QtCore.pyqtSignal = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
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
        self.yLabel.setText("Y")
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
        self.assignButton.clicked.connect(self.assignPosition)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.nameLabel, 0, 0, 1, 7)
        layout.addWidget(self.nameLineEdit, 1, 0, 1, 5)
        layout.addWidget(self.xLabel, 2, 0)
        layout.addWidget(self.yLabel, 2, 1)
        layout.addWidget(self.zLabel, 2, 2)
        layout.addWidget(self.xSpinBox, 3, 0)
        layout.addWidget(self.ySpinBox, 3, 1)
        layout.addWidget(self.zSpinBox, 3, 2)
        layout.addWidget(self.assignButton, 3, 4)
        layout.addWidget(self.commentLabel, 4, 0, 1, 5)
        layout.addWidget(self.commentLineEdit, 5, 0, 1, 5)
        layout.addWidget(self.buttonBox, 7, 0, 1, 5)
        layout.setRowStretch(6, 1)

    def name(self) -> str:
        return self.nameLineEdit.text()

    def setName(self, name: str) -> None:
        self.nameLineEdit.setText(name)

    def position(self) -> Position:
        x = self.xSpinBox.value()
        y = self.ySpinBox.value()
        z = self.zSpinBox.value()
        return Position(x, y, z)

    def setPosition(self, position: Position) -> None:
        x, y, z = position
        self.xSpinBox.setValue(x)
        self.ySpinBox.setValue(y)
        self.zSpinBox.setValue(z)

    def comment(self) -> str:
        return self.commentLineEdit.text()

    def setComment(self, comment: str) -> None:
        self.commentLineEdit.setText(comment)

    def assignPosition(self) -> None:
        self.setEnabled(False)
        def callback(x, y, z):
            self.setPosition((x, y, z))
            self.setEnabled(True)
        self.positionPicked.emit(callback)


class TablePositionsWidget(QtWidgets.QWidget):

    positionPicked: QtCore.pyqtSignal = QtCore.pyqtSignal(object)
    absoluteMove: QtCore.pyqtSignal = QtCore.pyqtSignal(Position)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.positionsTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.positionsTreeWidget.setHeaderLabels(["Name", "X", "Y", "Z", "Comment"])
        self.positionsTreeWidget.setRootIsDecorated(False)
        self.positionsTreeWidget.currentItemChanged.connect(self.positionSelected)
        self.positionsTreeWidget.itemDoubleClicked.connect(self.positionDoubleClicked)

        self.addButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.addButton.setText("&Add")
        self.addButton.setToolTip("Add new position item")
        self.addButton.clicked.connect(self.addPosition)

        self.editButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.editButton.setText("&Edit")
        self.editButton.setToolTip("Edit selected position item")
        self.editButton.setEnabled(False)
        self.editButton.clicked.connect(self.editPosition)

        self.removeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("&Remove")
        self.removeButton.setToolTip("Remove selected position item")
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.removePosition)

        self.moveButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("&Move")
        self.moveButton.setToolTip("Move to selected position")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.moveToPosition)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.positionsTreeWidget, 0, 0, 5, 1)
        layout.addWidget(self.moveButton, 0, 1)
        layout.addWidget(self.addButton, 2, 1)
        layout.addWidget(self.editButton, 3, 1)
        layout.addWidget(self.removeButton, 4, 1)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(1, 1)

    def readSettings(self) -> None:
        self.positionsTreeWidget.clear()
        for position in settings.tablePositions():
            item = TablePositionItem(
                name=position.name,
                position=Position(position.x, position.y, position.z),
                comment=position.comment,
            )
            self.positionsTreeWidget.addTopLevelItem(item)
        for column in range(self.positionsTreeWidget.columnCount()):
            self.positionsTreeWidget.resizeColumnToContents(column)

    def writeSettings(self) -> None:
        positions: List[TablePosition] = []
        for index in range(self.positionsTreeWidget.topLevelItemCount()):
            item = self.positionsTreeWidget.topLevelItem(index)
            if isinstance(item, TablePositionItem):
                positions.append(TablePosition(
                    name=item.name(),
                    x=item.position().x,
                    y=item.position().y,
                    z=item.position().z,
                    comment=item.comment()
                ))
        settings.setTablePositions(positions)

    def setLocked(self, state: bool) -> None:
        self.setProperty("locked", state)
        if state:
            self.addButton.setEnabled(False)
            self.editButton.setEnabled(False)
            self.removeButton.setEnabled(False)
            self.moveButton.setEnabled(False)
        else:
            enabled = self.positionsTreeWidget.currentItem() is not None
            self.addButton.setEnabled(True)
            self.editButton.setEnabled(enabled)
            self.removeButton.setEnabled(enabled)
            self.moveButton.setEnabled(enabled)

    def positionSelected(self, current, previous) -> None:
        enabled = current is not None
        self.editButton.setEnabled(True)
        self.removeButton.setEnabled(True)
        self.moveButton.setEnabled(True)

    def positionDoubleClicked(self, item, column) -> None:
        if not self.property("locked"):
            self.moveToPosition()

    def pickPosition(self, callback) -> None:
        self.positionPicked.emit(callback)

    def addPosition(self) -> None:
        dialog = PositionDialog()
        dialog.positionPicked.connect(self.pickPosition)
        dialog.exec()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            name = dialog.name()
            position = dialog.position()
            comment = dialog.comment()
            item = TablePositionItem(name, position, comment)
            self.positionsTreeWidget.addTopLevelItem(item)
            for column in range(self.positionsTreeWidget.columnCount()):
                self.positionsTreeWidget.resizeColumnToContents(column)

    def editPosition(self) -> None:
        item: Optional[QtWidgets.QTreeWidgetItem] = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            dialog = PositionDialog()
            dialog.positionPicked.connect(self.pickPosition)
            dialog.setName(item.name())
            dialog.setPosition(item.position())
            dialog.setComment(item.comment())
            dialog.exec()
            if dialog.result() == QtWidgets.QDialog.Accepted:
                item.setName(dialog.name())
                item.setPosition(dialog.position())
                item.setComment(dialog.comment())
                for column in range(self.positionsTreeWidget.columnCount()):
                    self.positionsTreeWidget.resizeColumnToContents(column)

    def removePosition(self) -> None:
        item: Optional[QtWidgets.QTreeWidgetItem] = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            result = QtWidgets.QMessageBox.question(
                self,
                "Remove Position?",
                f"Do you want to remove position {item.name()!r}?"
            )
            if result == QtWidgets.QMessageBox.Yes:
                index = self.positionsTreeWidget.indexOfTopLevelItem(item)
                self.positionsTreeWidget.takeTopLevelItem(index)
                if not self.positionsTreeWidget.topLevelItemCount():
                    self.editButton.setEnabled(False)
                    self.removeButton.setEnabled(False)
                for column in range(self.positionsTreeWidget.columnCount()):
                    self.positionsTreeWidget.resizeColumnToContents(column)


    def moveToPosition(self) -> None:
        item: Optional[QtWidgets.QTreeWidgetItem] = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            result = QtWidgets.QMessageBox.question(
                self,
                "Move Table?",
                f"Do you want to move table to position {item.name()!r}?"
            )
            if result == QtWidgets.QMessageBox.Yes:
                self.absoluteMove.emit(item.position())


class LCRChartWidget(QtWidgets.QWidget):

    MaxPoints: int = 1000

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(160, 60)

        self._chart: QtChart.QChart = QtChart.QChart()
        self._chart.legend().hide()
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chart.setBackgroundRoundness(0)
        self._chart.setBackgroundVisible(False)
        self._chart.setMargins(QtCore.QMargins(0, 0, 0, 0))

        self._xAxis: QtChart.QValueAxis = QtChart.QValueAxis()
        self._xAxis.setTickCount(3)
        self._xAxis.setMinorTickCount(4)
        self._xAxis.setLabelFormat("%.3f mm")
        self._chart.addAxis(self._xAxis, QtCore.Qt.AlignBottom)

        self._yAxis: QtChart.QValueAxis = QtChart.QValueAxis()
        self._yAxis.setTickCount(2)
        self._yAxis.setMinorTickCount(3)
        self._yAxis.setLabelFormat("%.2g Ohm")
        self._chart.addAxis(self._yAxis, QtCore.Qt.AlignLeft)

        self._line: QtChart.QLineSeries = QtChart.QLineSeries()
        self._line.setColor(QtGui.QColor("magenta"))

        self._chart.addSeries(self._line)
        self._line.attachAxis(self._xAxis)
        self._line.attachAxis(self._yAxis)

        self._series: QtChart.QScatterSeries = QtChart.QScatterSeries()
        self._series.setName("R")
        self._series.setMarkerSize(3)
        self._series.setBorderColor(QtGui.QColor("red"))
        self._series.setColor(QtGui.QColor("red"))

        self._chart.addSeries(self._series)
        self._series.attachAxis(self._xAxis)
        self._series.attachAxis(self._yAxis)

        self._marker: QtChart.QScatterSeries = QtChart.QScatterSeries()
        self._marker.setMarkerSize(9)
        self._marker.setBorderColor(QtGui.QColor("red"))
        self._marker.setColor(QtGui.QColor("red"))

        self._chart.addSeries(self._marker)
        self._marker.attachAxis(self._xAxis)
        self._marker.attachAxis(self._yAxis)

        self._chartView: QtChart.QChartView = QtChart.QChartView(self._chart)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._chartView)

    def getYLimits(self) -> List[float]:
        limits: List[float] = []
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
        limits = self.getYLimits()
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


class TableControlDialog(QtWidgets.QDialog, SettingsMixin):

    default_steps: List[Dict[str, Any]] = [
        {"step_size": 1.0, "step_color": "green"}, # microns!
        {"step_size": 10.0, "step_color": "orange"},
        {"step_size": 100.0, "step_color": "red"},
    ]

    probecardLightToggled: QtCore.pyqtSignal = QtCore.pyqtSignal(bool)
    microscopeLightToggled: QtCore.pyqtSignal = QtCore.pyqtSignal(bool)
    boxLightToggled: QtCore.pyqtSignal = QtCore.pyqtSignal(bool)

    def __init__(self, process, lcr_process, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.process = None
        self.maximum_z_step_size: float = 0.025 # mm
        self.z_limit: float = 0.0

        self.lcr_process = lcr_process
        self.lcr_process.failed = self.setLCRFailed
        self.lcr_process.reading = self.setLCRReading

        self.setProcess(process)
        self.resize(640, 480)
        self.setWindowTitle("Table Control")

        self.addXButton: KeypadButton = KeypadButton("+X", self)
        self.addXButton.clicked.connect(self.on_add_x)

        self.subXButton: KeypadButton = KeypadButton("-X", self)
        self.subXButton.clicked.connect(self.on_sub_x)

        self.addYButton: KeypadButton = KeypadButton("+Y", self)
        self.addYButton.clicked.connect(self.on_add_y)

        self.subYButton: KeypadButton = KeypadButton("-Y", self)
        self.subYButton.clicked.connect(self.on_sub_y)

        self.addZButton: KeypadButton = KeypadButton("+Z", self)
        self.addZButton.clicked.connect(self.on_add_z)

        self.subZButton: KeypadButton = KeypadButton("-Z", self)
        self.subZButton.clicked.connect(self.on_sub_z)

        self.stepUpButton: KeypadButton = KeypadButton("↑⇵", self)
        self.stepUpButton.setToolTip("Move single step up then double step down and double step up (experimental).")
        self.stepUpButton.clicked.connect(self.on_step_up)

        self.controlButtons: List[KeypadButton] = [
            self.addXButton,
            self.subXButton,
            self.addYButton,
            self.subYButton,
            self.addZButton,
            self.subZButton,
            self.stepUpButton
        ]

        # Contact Quality

        self.lcrPrimaryLabel: QtWidgets.QLabel = QtWidgets.QLabel("Cp", self)

        self.lcrPrimaryLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrPrimaryLineEdit.setReadOnly(True)

        self.lcrSecondaryLabel: QtWidgets.QLabel = QtWidgets.QLabel("Rp", self)

        self.lcrSecondaryLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrSecondaryLineEdit.setReadOnly(True)

        self.lcrChartWidget: LCRChartWidget = LCRChartWidget(self)

        self.lcrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("Contact Quality (LCR)")
        self.lcrGroupBox.setCheckable(True)
        self.lcrGroupBox.setChecked(False)
        self.lcrGroupBox.toggled.connect(self.toggleLCR)

        lcrGroupBoxLayout = QtWidgets.QGridLayout(self.lcrGroupBox)
        lcrGroupBoxLayout.addWidget(self.lcrPrimaryLabel, 0, 0)
        lcrGroupBoxLayout.addWidget(self.lcrPrimaryLineEdit, 0, 1)
        lcrGroupBoxLayout.addWidget(self.lcrSecondaryLabel, 1, 0)
        lcrGroupBoxLayout.addWidget(self.lcrSecondaryLineEdit, 1, 1)
        lcrGroupBoxLayout.addWidget(self.lcrChartWidget, 2, 0, 1, 2)

        self.probecardLightButton: ToggleButton = ToggleButton("PC Light", self)
        self.probecardLightButton.setToolTip("Toggle probe card light")
        self.probecardLightButton.setEnabled(False)
        self.probecardLightButton.toggled.connect(self.on_probecard_light_clicked)

        self.microscopeLightButton: ToggleButton = ToggleButton("Mic Light", self)
        self.microscopeLightButton.setToolTip("Toggle microscope light")
        self.microscopeLightButton.setEnabled(False)
        self.microscopeLightButton.toggled.connect(self.on_microscope_light_clicked)

        self.boxLightButton: ToggleButton = ToggleButton("Box Light", self)
        self.boxLightButton.setToolTip("Toggle box light")
        self.boxLightButton.setEnabled(False)
        self.boxLightButton.toggled.connect(self.on_box_light_clicked)

        # Create movement radio buttons
        self.stepWidthButtons: List[QtWidgets.QRadioButton] = []
        self.stepWidthButtonsLayout = QtWidgets.QVBoxLayout()
        for item in self.load_table_step_sizes():
            step_size = item.get("step_size") * ureg("um")
            step_color = item.get("step_color")
            step_size_label = format_metric(step_size.to("m").m, "m", decimals=1)
            button = QtWidgets.QRadioButton()
            button.setText(step_size_label)
            button.setToolTip(f"Move in {step_size_label} steps.")
            button.setStyleSheet(f"QRadioButton:enabled{{color:{step_color};}}")
            button.setChecked(len(self.stepWidthButtons) == 0)
            button.toggled.connect(self.on_step_toggled)
            button.setProperty("movement_width", step_size.to("mm").m)
            button.setProperty("movement_color", step_color)
            self.stepWidthButtons.append(button)
            self.stepWidthButtonsLayout.addWidget(button)

        self.controlGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.controlGroupBox.setTitle("Table Control")

        controlLayout = QtWidgets.QGridLayout(self.controlGroupBox)
        controlLayout.addWidget(self.addXButton, 3, 1)
        controlLayout.addWidget(self.subXButton, 1, 1)
        controlLayout.addWidget(self.addYButton, 2, 2)
        controlLayout.addWidget(self.subYButton, 2, 0)
        controlLayout.addWidget(self.addZButton, 1, 4)
        controlLayout.addWidget(self.subZButton, 3, 4)
        controlLayout.addWidget(self.stepUpButton, 1, 5)
        controlLayout.setColumnMinimumWidth(3, 32)
        controlLayout.setRowStretch(0, 1)
        controlLayout.setRowStretch(4, 1)

        self.positions_widget = TablePositionsWidget(self)
        self.positions_widget.setEnabled(False)
        self.positions_widget.positionPicked.connect(self.pickPosition)
        self.positions_widget.absoluteMove.connect(self.requestAbsoluteMove)

        self.contacts_widget = TableContactsWidget(self)
        self.contacts_widget.setEnabled(False)
        self.contacts_widget.positionPicked.connect(self.pickPosition)
        self.contacts_widget.absoluteMove.connect(self.requestAbsoluteMove)

        self.positionWidget: PositionWidget = PositionWidget(self)

        self.calibrationWidget: CalibrationWidget = CalibrationWidget(self)

        self.zLimitLabel: PositionLabel = PositionLabel(self)

        self.xHardLimitLabel: PositionLabel = PositionLabel(self)
        self.yHardLimitLabel: PositionLabel = PositionLabel(self)
        self.zHardLimitLabel: PositionLabel = PositionLabel(self)

        self.laserLabel: SwitchLabel = SwitchLabel(self)

        self.calibrateButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.calibrateButton.setText("Calibrate")
        self.calibrateButton.clicked.connect(self.requestCalibrate)

        self.updateIntervalSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.updateIntervalSpinBox.setDecimals(2)
        self.updateIntervalSpinBox.setRange(0.5, 10.0)
        self.updateIntervalSpinBox.setSingleStep(0.25)
        self.updateIntervalSpinBox.setSuffix(" s")
        self.updateIntervalSpinBox.setValue(settings.tableControlUpdateInterval())
        self.updateIntervalSpinBox.editingFinished.connect(lambda: self.setUpdateInterval(self.updateIntervalSpinBox.value()))

        self.intervalGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.intervalGroupBox.setTitle("Update Interval")

        intervalGroupBoxLayout = QtWidgets.QHBoxLayout(self.intervalGroupBox)
        intervalGroupBoxLayout.addWidget(self.updateIntervalSpinBox)
        intervalGroupBoxLayout.addStretch()

        self.dodgeHeightSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.dodgeHeightSpinBox.setToolTip("Doge height in microns.")
        self.dodgeHeightSpinBox.setRange(0, 10000)
        self.dodgeHeightSpinBox.setSingleStep(1)
        self.dodgeHeightSpinBox.setSuffix(" um")

        self.dodgeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.dodgeGroupBox.setTitle("X/Y Dodge")
        self.dodgeGroupBox.setToolTip("Enables -/+ Z dodge for XY movements.")
        self.dodgeGroupBox.setCheckable(True)

        dodgeGroupBoxLayout = QtWidgets.QHBoxLayout(self.dodgeGroupBox)
        dodgeGroupBoxLayout.addWidget(QtWidgets.QLabel("Height"))
        dodgeGroupBoxLayout.addWidget(self.dodgeHeightSpinBox)

        self.lcrResetOnMoveCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.lcrResetOnMoveCheckBox.setText("Reset graph on X/Y move")

        self.contactQualityGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.contactQualityGroupBox.setTitle("Contact Quality (LCR)")

        contactQualityGroupBoxLayout = QtWidgets.QHBoxLayout(self.contactQualityGroupBox)
        contactQualityGroupBoxLayout.addWidget(self.lcrResetOnMoveCheckBox)

        self.stepUpDelaySpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.stepUpDelaySpinBox.setRange(0, 1000)
        self.stepUpDelaySpinBox.setSingleStep(25)
        self.stepUpDelaySpinBox.setSuffix(" ms")

        self.stepUpMultiplySpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.stepUpMultiplySpinBox.setRange(1, 10)
        self.stepUpMultiplySpinBox.setSuffix(" x")

        self.stepUpGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepUpGroupBox.setTitle("Step Up (↑⇵)")

        stepUpGroupBoxLayout = QtWidgets.QGridLayout(self.stepUpGroupBox)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Delay"), 0, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpDelaySpinBox, 0, 1)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Multiplicator (⇵)"), 1, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpMultiplySpinBox, 1, 1)
        stepUpGroupBoxLayout.setColumnStretch(2, 1)

        self.lcrUpdateIntervalSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.lcrUpdateIntervalSpinBox.setRange(0, 1000)
        self.lcrUpdateIntervalSpinBox.setSingleStep(25)
        self.lcrUpdateIntervalSpinBox.setSuffix(" ms")

        self.lcrMatrixChannelsLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.lcrOptionsGroupBox = QtWidgets.QGroupBox(self)
        self.lcrOptionsGroupBox.setTitle("Contact Quality (LCR)")

        lcrOptionsGroupBoxLayout = QtWidgets.QGridLayout(self.lcrOptionsGroupBox)
        lcrOptionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Reading Interval"), 0, 0)
        lcrOptionsGroupBoxLayout.addWidget(self.lcrUpdateIntervalSpinBox, 0, 1)
        lcrOptionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Matrix Channels"), 1, 0)
        lcrOptionsGroupBoxLayout.addWidget(self.lcrMatrixChannelsLineEdit, 1, 1, 1, 10)
        stepUpGroupBoxLayout.setColumnStretch(0, 0)
        stepUpGroupBoxLayout.setColumnStretch(1, 0)
        stepUpGroupBoxLayout.setColumnStretch(9, 1)

        self.progressBar: QtWidgets.QProgressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setVisible(False)

        self.messageLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)

        self.stopButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("&Stop")
        self.stopButton.setDefault(False)
        self.stopButton.setAutoDefault(False)
        self.stopButton.setEnabled(False)
        self.stopButton.clicked.connect(self.requestStop)

        self.closeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.closeButton.setText("&Close")
        self.closeButton.setDefault(False)
        self.closeButton.setAutoDefault(False)
        self.closeButton.clicked.connect(self.close)

        self.stepWidthGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepWidthGroupBox.setTitle("Step Width")

        stepWidthGroupBoxLayout = QtWidgets.QVBoxLayout(self.stepWidthGroupBox)
        stepWidthGroupBoxLayout.addLayout(self.stepWidthButtonsLayout)
        stepWidthGroupBoxLayout.addStretch()

        self.lightsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lightsGroupBox.setTitle("Lights")

        lightsLayout = QtWidgets.QVBoxLayout(self.lightsGroupBox)
        lightsLayout.addWidget(self.probecardLightButton)
        lightsLayout.addWidget(self.microscopeLightButton)
        lightsLayout.addWidget(self.boxLightButton)
        lightsLayout.addStretch()

        controlsLayout = QtWidgets.QHBoxLayout()
        controlsLayout.addWidget(self.controlGroupBox)
        controlsLayout.addWidget(self.stepWidthGroupBox)
        controlsLayout.addWidget(self.lcrGroupBox)
        controlsLayout.addWidget(self.lightsGroupBox)
        controlsLayout.addStretch()

        self.calibrateGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.calibrateGroupBox.setTitle("Table Calibration")

        calibrateLayout = QtWidgets.QVBoxLayout(self.calibrateGroupBox)
        calibrateLayout.addWidget(self.calibrateButton)
        calibrateLayout.addWidget(QtWidgets.QLabel(
            "Calibrate table by moving into cal/rm switches\nof every axis in" \
            " a safe manner to protect the probe card."
        ))

        self.calibrateWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        calibrateTabLayout = QtWidgets.QVBoxLayout(self.calibrateWidget)
        calibrateTabLayout.addWidget(self.calibrateGroupBox, 0)
        calibrateTabLayout.addStretch()

        self.optionsWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        optionsTabLayout = QtWidgets.QGridLayout(self.optionsWidget)
        optionsTabLayout.addWidget(self.intervalGroupBox, 0, 0)
        optionsTabLayout.addWidget(self.dodgeGroupBox, 0, 1)
        optionsTabLayout.addWidget(self.contactQualityGroupBox, 0, 2)
        optionsTabLayout.addWidget(self.stepUpGroupBox, 1, 0, 1, 3)
        optionsTabLayout.addWidget(self.lcrOptionsGroupBox, 2, 0, 1, 3)
        optionsTabLayout.setRowStretch(3, 1)
        optionsTabLayout.setColumnStretch(2, 1)

        self.tabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.positions_widget, "Move")
        self.tabWidget.addTab(self.contacts_widget, "Contacts")
        self.tabWidget.addTab(self.calibrateWidget, "Calibrate")
        self.tabWidget.addTab(self.optionsWidget, "Options")

        topLeftLayout = QtWidgets.QVBoxLayout()
        topLeftLayout.addLayout(controlsLayout, 0)
        topLeftLayout.addWidget(self.tabWidget, 1)


        self.softLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.softLimitsGroupBox.setTitle("Soft Limits")

        softLimitsGroupBoxLayout = QtWidgets.QFormLayout(self.softLimitsGroupBox)
        softLimitsGroupBoxLayout.addRow("Z", self.zLimitLabel)

        self.hardLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hardLimitsGroupBox.setTitle("Hard Limits")

        hardLimitsGroupBoxLayout = QtWidgets.QFormLayout(self.hardLimitsGroupBox)
        hardLimitsGroupBoxLayout.addRow("X", self.xHardLimitLabel)
        hardLimitsGroupBoxLayout.addRow("Y", self.yHardLimitLabel)
        hardLimitsGroupBoxLayout.addRow("Z", self.zHardLimitLabel)

        self.safetyGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.safetyGroupBox.setTitle("Safety")

        safetyGroupBoxLayout = QtWidgets.QHBoxLayout(self.safetyGroupBox)
        safetyGroupBoxLayout.addWidget(QtWidgets.QLabel("Laser Sensor"))
        safetyGroupBoxLayout.addWidget(self.laserLabel)

        topRightLayout = QtWidgets.QVBoxLayout()
        topRightLayout.addWidget(self.positionWidget)
        topRightLayout.addWidget(self.calibrationWidget)
        topRightLayout.addWidget(self.softLimitsGroupBox)
        topRightLayout.addWidget(self.hardLimitsGroupBox)
        topRightLayout.addWidget(self.safetyGroupBox)
        topRightLayout.addStretch()

        topLayout = QtWidgets.QHBoxLayout()
        topLayout.addLayout(topLeftLayout, 1)
        topLayout.addLayout(topRightLayout, 0)

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addWidget(self.progressBar)
        bottomLayout.addWidget(self.messageLabel)
        bottomLayout.addStretch()
        bottomLayout.addWidget(self.stopButton)
        bottomLayout.addWidget(self.closeButton)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(topLayout, 1)
        layout.addLayout(bottomLayout, 0)

        self.reset_position()
        self.reset_caldone()
        self.update_limits()
        self.reset_safety()
        self.update_control_buttons()

    @property
    def step_width(self):
        for button in self.stepWidthButtons:
            if button.isChecked():
                return abs(button.property("movement_width"))
        return 0

    @property
    def step_color(self):
        for button in self.stepWidthButtons:
            if button.isChecked():
                return button.property("movement_color")
        return "black"

    @property
    def update_interval(self) -> float:
        return self.updateIntervalSpinBox.value()

    @update_interval.setter
    def update_interval(self, value: float) -> None:
        self.updateIntervalSpinBox.setValue(value)

    @property
    def dodge_enabled(self):
        return self.dodgeGroupBox.isChecked()

    @dodge_enabled.setter
    def dodge_enabled(self, value):
        self.dodgeGroupBox.setChecked(value)

    @property
    def dodge_height(self):
        return (self.dodgeHeightSpinBox.value() * ureg("um")).to("mm").m

    @dodge_height.setter
    def dodge_height(self, value):
        self.dodgeHeightSpinBox.setValue((value * ureg("mm")).to("um").m)

    @property
    def lcr_reset_on_move(self):
        return self.lcrResetOnMoveCheckBox.isChecked()

    @lcr_reset_on_move.setter
    def lcr_reset_on_move(self, value):
        self.lcrResetOnMoveCheckBox.setChecked(value)

    @property
    def step_up_delay(self) -> float:
        """Return step up delay in seconds."""
        return (self.stepUpDelaySpinBox.value() * ureg("ms")).to("s").m

    @step_up_delay.setter
    def step_up_delay(self, value: float) -> None:
        self.stepUpDelaySpinBox.setValue((value * ureg("s")).to("ms").m)

    @property
    def step_up_multiply(self) -> int:
        """Return step up delay in seconds."""
        return self.stepUpMultiplySpinBox.value()

    @step_up_multiply.setter
    def step_up_multiply(self, value: int) -> None:
        self.stepUpMultiplySpinBox.setValue(value)

    @property
    def lcr_update_interval(self):
        """LCR update interval in seconds."""
        return (self.lcrUpdateIntervalSpinBox.value() * ureg("ms")).to("s").m

    @lcr_update_interval.setter
    def lcr_update_interval(self, value):
        self.lcrUpdateIntervalSpinBox.setValue((value * ureg("s")).to("ms").m)

    @property
    def lcr_matrix_channels(self):
        """Matrix channels used for LCR readings."""
        tokens = []
        for token in self.lcrMatrixChannelsLineEdit.text().split(","):
            token = token.strip()
            if token:
                tokens.append(token)
        return tokens

    @lcr_matrix_channels.setter
    def lcr_matrix_channels(self, value):
        self.lcrMatrixChannelsLineEdit.setText(", ".join([token for token in value]))

    def load_table_step_sizes(self):
        return self.settings.get("table_step_sizes") or self.default_steps

    def reset_position(self):
        self.update_position(Position())

    def update_position(self, position: Position) -> None:
        self.current_position = position
        self.positionWidget.updatePosition(position)
        self.update_limits()
        self.update_control_buttons()
        if math.isfinite(position.z):
            self.lcrChartWidget.setLimits(position.z)
            self.lcrChartWidget.setLine(position.z)

    def reset_caldone(self):
        self.calibrationWidget.resetCalibration()

    def update_caldone(self, position):
        self.current_caldone = position
        self.positions_widget.setEnabled(caldone_valid(position))
        self.contacts_widget.setEnabled(caldone_valid(position))
        self.controlGroupBox.setEnabled(caldone_valid(position))
        self.calibrationWidget.updateCalibration(position)

    def update_limits(self):
        x, y, z = self.current_position
        self.zLimitLabel.setStyleSheet("")
        if not math.isnan(z):
            if z >= self.z_limit:
                self.zLimitLabel.setStyleSheet("QLabel:enabled{color:red;}")

    def reset_safety(self):
        self.laserLabel.clear()

    def update_safety(self, laser_sensor) -> None:
        self.laserLabel.setState(laser_sensor)

    def update_control_buttons(self):
        x, y, z = self.current_position
        self.update_x_buttons(x)
        self.update_y_buttons(y)
        self.update_z_buttons(z)
        for button in self.controlButtons:
            button.setStyleSheet(f"QPushButton:enabled{{color:{self.step_color or 'black'}}}")

    def update_x_buttons(self, x):
        x_enabled = True
        if not math.isnan(x):
            if (x - self.step_width) < 0:
                x_enabled = False
        self.subXButton.setEnabled(x_enabled)

    def update_y_buttons(self, y):
        y_enabled = True
        if not math.isnan(y):
            if (y - self.step_width) < 0:
                y_enabled = False
        self.subYButton.setEnabled(y_enabled)

    def update_z_buttons(self, z):
        # Disable move up button for large step sizes
        z_enabled = False
        if not math.isnan(z):
            if (z + self.step_width) <= self.z_limit:
                z_enabled = True
            else:
                z_enabled = self.step_width <= self.maximum_z_step_size
        self.addZButton.setEnabled(z_enabled)
        step_up_limit = ureg("10.0 um").to("mm").m
        self.stepUpButton.setEnabled(z_enabled and (self.step_width <= step_up_limit))  # TODO

    def relative_move_xy(self, x, y):
        # Dodge on X/Y movements.
        if self.dodge_enabled:
            dodge_height = self.dodge_height
            current_position = self.current_position
            if current_position.z < dodge_height:
                dodge_height = max(0, current_position.z)
            vector = [(0, 0, -dodge_height), (x, y, 0), (0, 0, +dodge_height)]
        else:
            vector = [(x, y, 0)]
        # Clear contact quality graph on X/Y movements.
        if self.lcr_reset_on_move:
            self.lcrChartWidget.clear()
        self.process.relative_move_vector(vector)
        # Clear contact quality graph on X/Y movements.
        if self.lcr_reset_on_move:
            self.lcrChartWidget.clear()

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
        multiply = self.step_up_multiply
        vector = (
            [0, 0, +step_width],
            [0, 0, -step_width * multiply],
            [0, 0, +step_width * multiply],
        )
        self.process.relative_move_vector(vector, delay=self.step_up_delay)

    def on_step_toggled(self, state):
        logger.info("set table step width to %.3f mm", self.step_width)
        self.update_control_buttons()

    def on_probecard_light_clicked(self, state):
        self.probecardLightToggled.emit(state)

    def on_microscope_light_clicked(self, state):
        self.microscopeLightToggled.emit(state)

    def on_box_light_clicked(self, state):
        self.boxLightToggled.emit(state)

    def update_probecard_light(self, state):
        self.probecardLightButton.setChecked(state)

    def update_microscope_light(self, state):
        self.microscopeLightButton.setChecked(state)

    def update_box_light(self, state: bool) -> None:
        self.boxLightButton.setChecked(state)

    def update_lights_enabled(self, state: bool) -> None:
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

    @QtCore.pyqtSlot(str)
    def setMessage(self, message: str) -> None:
        self.messageLabel.setText(message)
        logger.info(message)

    @QtCore.pyqtSlot(int, int)
    def setProgress(self, value: int, maximum: int) -> None:
        self.progressBar.setValue(value)
        self.progressBar.setRange(0, maximum)
        self.progressBar.setVisible(True)

    @QtCore.pyqtSlot(float)
    def setUpdateInterval(self, interval: float) -> None:
        logger.info("Set update interval: %.2f s", interval)
        self.process.update_interval = interval  # type: ignore

    def pickPosition(self, callback):
        x, y, z = self.current_position
        callback(x, y, z)

    def requestAbsoluteMove(self, position):
        # Update to safe Z position
        position = Position(position.x, position.y, safe_z_position(position.z))
        self.setLocked(True)
        # Clear contact quality graph on X/Y movements.
        self.lcrChartWidget.clear()
        self.stopButton.setEnabled(True)
        self.process.safe_absolute_move(position.x, position.y, position.z)

    def requestCalibrate(self):
        self.setLocked(True)
        self.stopButton.setEnabled(True)
        self.process.calibrate_table()

    def requestStop(self):
        self.stopButton.setEnabled(False)
        self.process.stop_current_action()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        if self.process:
            self.process.wait()
        event.accept()

    def loadSamples(self, sample_items) -> None:
        self.contacts_widget.loadSamples(sample_items)

    def updateSamples(self) -> None:
        self.contacts_widget.updateSamples()

    def readSettings(self) -> None:
        self.positions_widget.readSettings()
        self.z_limit = settings.tableZLimit()
        self.zLimitLabel.setValue(self.z_limit)
        x, y, z = settings.tableProbecardMaximumLimits()
        self.xHardLimitLabel.setValue(x)
        self.yHardLimitLabel.setValue(y)
        self.zHardLimitLabel.setValue(z)
        self.step_up_delay = self.settings.get("tablecontrol_step_up_delay", DEFAULT_STEP_UP_DELAY)
        self.step_up_multiply = self.settings.get("tablecontrol_step_up_multiply", DEFAULT_STEP_UP_MULTIPLY)
        self.lcr_update_interval = self.settings.get("tablecontrol_lcr_update_delay", DEFAULT_LCR_UPDATE_INTERVAL)
        matrix_channels = self.settings.get("tablecontrol_lcr_matrix_channels") or DEFAULT_MATRIX_CHANNELS
        self.lcr_matrix_channels = matrix_channels
        self.lcr_process.update_interval = self.lcr_update_interval
        self.lcr_process.matrix_channels = self.lcr_matrix_channels
        self.update_interval = settings.tableControlUpdateInterval()
        self.dodge_enabled = settings.tableControlDodgeEnabled()
        self.dodge_height = settings.tableControlDodgeHeight()
        self.lcr_reset_on_move = self.settings.get("tablecontrol_lcr_reset_on_move", True)

        settings_ = QtCore.QSettings()
        settings_.beginGroup("TableControlDialog")
        geometry = settings_.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreGeometry(geometry)
        settings_.endGroup()

    def writeSettings(self) -> None:
        self.settings["tablecontrol_step_up_multiply"] = self.step_up_multiply
        self.settings["tablecontrol_lcr_update_delay"] = self.lcr_update_interval
        self.settings["tablecontrol_lcr_matrix_channels"] = self.lcr_matrix_channels
        self.positions_widget.writeSettings()
        settings.setTableControlUpdateInterval(self.update_interval)
        settings.setTableControlDodgeEnabled(self.dodge_enabled)
        settings.setTableControlDodgeHeight(self.dodge_height)
        self.settings["tablecontrol_lcr_reset_on_move"] = self.lcr_reset_on_move

        settings_ = QtCore.QSettings()
        settings_.beginGroup("TableControlDialog")
        settings_.setValue("geometry", self.saveGeometry())
        settings_.endGroup()

    def setLocked(self, state: bool) -> None:
        if state:
            self.controlGroupBox.setEnabled(False)
            self.positions_widget.setLocked(True)
            self.contacts_widget.setLocked(True)
            self.closeButton.setEnabled(False)
            self.progressBar.setVisible(True)
            self.progressBar.setRange(0, 0)
            self.progressBar.setValue(0)
        else:
            self.controlGroupBox.setEnabled(True)
            self.positions_widget.setLocked(False)
            self.contacts_widget.setLocked(False)
            self.closeButton.setEnabled(True)
            self.progressBar.setVisible(False)

    def setProcess(self, process):
        """Set table process and connect signals."""
        self.removeProcess()
        self.process = process
        self.process.message_changed = self.setMessage
        self.process.progress_changed = self.setProgress
        self.process.position_changed = self.update_position
        self.process.caldone_changed = self.update_caldone
        self.process.relative_move_finished = self.on_move_finished
        self.process.absolute_move_finished = self.on_move_finished
        self.process.calibration_finished = self.on_calibration_finished
        self.process.stopped = self.on_calibration_finished

    def removeProcess(self) -> None:
        """Remove table process."""
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
    def toggleLCR(self, state):
        self.lcrPrimaryLineEdit.setEnabled(state)
        self.lcrSecondaryLineEdit.setEnabled(state)
        self.lcrChartWidget.setEnabled(state)
        if state:
            self.lcrChartWidget.clear()
            self.lcr_process.update_interval = self.lcr_update_interval
            self.lcr_process.matrix_channels = self.lcr_matrix_channels
            self.lcr_process.start()
        else:
            self.lcr_process.stop()

    def setLCRFailed(self, *args):
        self.lcrPrimaryLineEdit.setText("ERROR")
        self.lcrSecondaryLineEdit.setText("ERROR")

    def setLCRReading(self, prim, sec):
        self.lcrPrimaryLineEdit.setText(format_metric(prim, unit="F"))
        self.lcrSecondaryLineEdit.setText(format_metric(sec, unit="Ohm"))
        _, _, z = self.current_position
        if math.isfinite(z) and math.isfinite(sec):
            # Append only absolute Rp readings
            self.lcrChartWidget.append(z, abs(sec))
            self.lcrChartWidget.setLine(z)


class SwitchLabel(QtWidgets.QLabel):

    def setState(self, state):
        if state is None:
            self.setText(format(float("nan")))
            self.setStyleSheet("")
        else:
            self.setText(format_switch(state))
            self.setStyleSheet("QLabel:enabled{color:green}" if state else "QLabel:enabled{color:red}")


class KeypadButton(QtWidgets.QPushButton):

    def __init__(self, text: str, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setText(text)
        self.setDefault(False)
        self.setAutoDefault(False)
