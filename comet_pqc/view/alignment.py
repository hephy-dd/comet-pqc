"""Table control widgets and dialogs."""

import logging
import math
from typing import List, Optional, Tuple

from comet import ureg
from PyQt5 import QtCore, QtGui, QtWidgets, QtChart

from .components import (
    CalibrationWidget,
    PositionLabel,
    PositionWidget,
    ToggleButton,
)
from ..core.position import Position
from ..core.utils import LinearTransform
from ..settings import TablePosition, settings
from ..utils import format_metric, caldone_valid, format_switch

DEFAULT_STEP_UP_DELAY = 0.
DEFAULT_STEP_UP_MULTIPLY = 2
DEFAULT_LCR_UPDATE_INTERVAL = .100
DEFAULT_MATRIX_CHANNELS = [
    "3H01", "2B04", "1B03", "1B12", "2B06", "2B07", "2B08", "2B09",
    "2B10", "2B11", "1H04", "1H05", "1H06", "1H07", "1H08", "1H09",
    "1H10", "1H11", "2H12", "2H05", "1A01"
]

logger = logging.getLogger(__name__)


def format_sample_item(sample_item) -> str:
    return "/".join([item for item in [sample_item.name(), sample_item.sampleType()] if item])


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


class LCRWidget(QtWidgets.QWidget):

    MaxPoints = 1000

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        chart = QtChart.QChart()
        chart.legend().hide()
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundVisible(False)
        chart.setMargins(QtCore.QMargins(0, 0, 0, 0))

        self._xAxis = QtChart.QValueAxis()
        self._xAxis.setTickCount(3)
        self._xAxis.setMinorTickCount(4)
        self._xAxis.setLabelFormat("%.3f mm")
        chart.addAxis(self._xAxis, QtCore.Qt.AlignBottom)

        self._yAxis = QtChart.QValueAxis()
        self._yAxis.setTickCount(2)
        self._yAxis.setMinorTickCount(3)
        self._yAxis.setLabelFormat("%.2g Ohm")
        chart.addAxis(self._yAxis, QtCore.Qt.AlignLeft)

        self.lineSeries = QtChart.QLineSeries()
        self.lineSeries.setColor(QtGui.QColor("magenta"))

        chart.addSeries(self.lineSeries)
        self.lineSeries.attachAxis(self._xAxis)
        self.lineSeries.attachAxis(self._yAxis)

        self._series = QtChart.QScatterSeries()
        self._series.setName("R")
        self._series.setMarkerSize(3)
        self._series.setBorderColor(QtGui.QColor("red"))
        self._series.setColor(QtGui.QColor("red"))

        chart.addSeries(self._series)
        self._series.attachAxis(self._xAxis)
        self._series.attachAxis(self._yAxis)

        self.markerSeries = QtChart.QScatterSeries()
        self.markerSeries.setMarkerSize(9)
        self.markerSeries.setBorderColor(QtGui.QColor("red"))
        self.markerSeries.setColor(QtGui.QColor("red"))

        chart.addSeries(self.markerSeries)
        self.markerSeries.attachAxis(self._xAxis)
        self.markerSeries.attachAxis(self._yAxis)

        self.setMinimumSize(160, 60)

        self.chartView = QtChart.QChartView(chart)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chartView)

    def yValues(self) -> List[float]:
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
        self.setMarkerPos(x, y)

    def setLimits(self, x: float) -> None:
        offset = 0.050
        self._xAxis.setRange(x - offset, x + offset)
        values = self.yValues()
        if values:
            self._yAxis.setRange(min(values), max(values))
            self._yAxis.applyNiceNumbers()
            self._yAxis.setTickCount(2)

    def setLinePos(self, x: float) -> None:
        self.lineSeries.clear()
        self.lineSeries.append(x, self._yAxis.min())
        self.lineSeries.append(x, self._yAxis.max())

    def setMarkerPos(self, x: float, y: float) -> None:
        self.markerSeries.clear()
        self.markerSeries.append(x, y)


class TableSampleItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, sample_item) -> None:
        super().__init__()
        self.sample_item = sample_item
        self.setName(format_sample_item(sample_item))
        self.setPositionLabel(sample_item.samplePositionLabel())
        for contact_item in sample_item.children():
            self.addChild(TableContactItem(contact_item))

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def positionLabel(self) -> str:
        return self.text(1)

    def setPositionLabel(self, value: str) -> None:
        self.setText(1, value)

    def contactItems(self) -> List["TableContactItem"]:
        items: list = []
        for index in range(self.childCount()):
            item = self.child(index)
            if isinstance(item, TableContactItem):
                items.append(item)
        return items

    def updateContacts(self) -> None:
        for item in self.contactItems():
            item.updateContact()
            logger.info("Updated contact position: %s %s %s", self.name(), item.name(), item.position())

    def calculatePositions(self) -> None:
        items = self.contactItems()
        count = len(items)
        if count > 2:
            first = items[0].position()
            last = items[-1].position()
            tr = LinearTransform()
            for i, (x, y, z) in enumerate(tr.calculate(first, last, count - 1)):
                items[i].setPosition(x, y, z)


class TableContactItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, contact_item) -> None:
        super().__init__()
        self.contact_item = contact_item
        self.setTextAlignment(2, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore[arg-type]
        self.setTextAlignment(3, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore[arg-type]
        self.setTextAlignment(4, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore[arg-type]
        self.setName(contact_item.name())
        x, y, z = contact_item.position
        self.setPosition(x, y, z)

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self) -> Tuple[float, float, float]:
        x = self.data(2, 0x2000)
        y = self.data(3, 0x2000)
        z = self.data(4, 0x2000)
        return x, y, z

    def setPosition(self, x: float, y: float, z: float) -> None:
        self.setData(2, 0x2000, x)
        self.setData(3, 0x2000, y)
        self.setData(4, 0x2000, z)
        self.setText(2, format(x, ".3f") if x is not None else "")
        self.setText(3, format(y, ".3f") if y is not None else "")
        self.setText(4, format(z, ".3f") if z is not None else "")

    def hasPosition(self) -> bool:
        return any((not math.isnan(value) for value in self.position()))

    def updateContact(self) -> None:
        self.contact_item.position = self.position()

    def reset(self) -> None:
        self.setPosition(float("nan"), float("nan"), float("nan"))


class TableContactsWidget(QtWidgets.QWidget):

    positionPicked = QtCore.pyqtSignal(object)
    absoluteMove = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.contactsTreeWidget = QtWidgets.QTreeWidget(self)
        self.contactsTreeWidget.setHeaderLabels(["Contact", "Pos", "X", "Y", "Z", ""])
        self.contactsTreeWidget.resizeColumnToContents(0)
        self.contactsTreeWidget.resizeColumnToContents(1)
        self.contactsTreeWidget.resizeColumnToContents(2)
        self.contactsTreeWidget.resizeColumnToContents(3)
        self.contactsTreeWidget.resizeColumnToContents(4)
        self.contactsTreeWidget.currentItemChanged.connect(lambda current, previous: self.setButtonStates(current))

        self.pickButton = QtWidgets.QPushButton(self)
        self.pickButton.setText("Assign &Position")
        self.pickButton.setToolTip("Assign current table position to selected position item")
        self.pickButton.setEnabled(False)
        self.pickButton.clicked.connect(self.pickPosition)

        self.calculateButton = QtWidgets.QPushButton(self)
        self.calculateButton.setText("&Calculate")
        self.calculateButton.setEnabled(False)
        self.calculateButton.clicked.connect(self.calculate)

        self.moveButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("&Move")
        self.moveButton.setToolTip("Move to selected position")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.moveToCurrentPosition)

        self.resetButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("&Reset")
        self.resetButton.setEnabled(False)
        self.resetButton.clicked.connect(self.resetCurrent)

        self.resetAllButton = QtWidgets.QPushButton(self)
        self.resetAllButton.setText("Reset &All")
        self.resetAllButton.clicked.connect(self.resetAll)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.contactsTreeWidget, 0, 0, 6, 1)
        layout.addWidget(self.pickButton, 0, 1)
        layout.addWidget(self.moveButton, 1, 1)
        layout.addWidget(self.calculateButton, 2, 1)
        layout.addWidget(self.resetButton, 4, 1)
        layout.addWidget(self.resetAllButton, 5, 1)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(3, 1)

    def append_sample(self, sample_item) -> None:
        item = TableSampleItem(sample_item)
        self.contactsTreeWidget.addTopLevelItem(item)
        item.setExpanded(True)

    def setButtonStates(self, item: Optional[QtWidgets.QTreeWidgetItem]) -> None:
        isContact = isinstance(item, TableContactItem)
        isMovable = item.hasPosition() if isinstance(item, TableContactItem) else False
        self.pickButton.setEnabled(isContact)
        self.moveButton.setEnabled(isMovable)
        self.calculateButton.setEnabled(not isContact)
        self.resetButton.setEnabled(isContact)

    def pickPosition(self) -> None:
        item = self.contactsTreeWidget.currentItem()
        if isinstance(item, TableContactItem):
            def callback(x, y, z):
                item.setPosition(x, y, z)
                self.contactsTreeWidget.resizeColumnToContents(0)
                self.contactsTreeWidget.resizeColumnToContents(1)
                self.contactsTreeWidget.resizeColumnToContents(2)
                self.contactsTreeWidget.resizeColumnToContents(3)
                self.contactsTreeWidget.resizeColumnToContents(4)
            self.positionPicked.emit(callback)

    def resetCurrent(self) -> None:
        item = self.contactsTreeWidget.currentItem()
        if isinstance(item, TableContactItem):
            item.reset()
            self.contactsTreeWidget.resizeColumnToContents(0)
            self.contactsTreeWidget.resizeColumnToContents(1)
            self.contactsTreeWidget.resizeColumnToContents(2)
            self.contactsTreeWidget.resizeColumnToContents(3)
            self.contactsTreeWidget.resizeColumnToContents(4)

    def resetAll(self) -> None:
        if QtWidgets.QMessageBox.question(None, "", "Do you want to reset all contact positions?") == QtWidgets.QMessageBox.Yes:
            for item in self.sampleItems():
                for contactItem in item.contactItems():
                    contactItem.reset()
            self.contactsTreeWidget.resizeColumnToContents(0)
            self.contactsTreeWidget.resizeColumnToContents(1)
            self.contactsTreeWidget.resizeColumnToContents(2)
            self.contactsTreeWidget.resizeColumnToContents(3)
            self.contactsTreeWidget.resizeColumnToContents(4)

    def moveToCurrentPosition(self) -> None:
        current_item = self.contactsTreeWidget.currentItem()
        if isinstance(current_item, TableContactItem):
            if current_item.hasPosition():
                if QtWidgets.QMessageBox.question(None, "", f"Do you want to move table to contact {current_item.name()}?") == QtWidgets.QMessageBox.Yes:
                    x, y, z = current_item.position()
                    self.absoluteMove.emit(Position(x, y, z))

    def calculate(self) -> None:
        item = self.contactsTreeWidget.currentItem()
        if isinstance(item, TableSampleItem):
            item.calculatePositions()

    def loadSamples(self, sample_items) -> None:
        self.contactsTreeWidget.clear()
        for sample_item in sample_items:
            self.append_sample(sample_item)
        self.contactsTreeWidget.resizeColumnToContents(0)
        self.contactsTreeWidget.resizeColumnToContents(1)
        self.contactsTreeWidget.resizeColumnToContents(2)
        self.contactsTreeWidget.resizeColumnToContents(3)
        self.contactsTreeWidget.resizeColumnToContents(4)

    def sampleItems(self) -> List[TableSampleItem]:
        items: list = []
        for index in range(self.contactsTreeWidget.topLevelItemCount()):
            item = self.contactsTreeWidget.topLevelItem(index)
            if isinstance(item, TableSampleItem):
                items.append(item)
        return items

    def updateSamples(self) -> None:
        for item in self.sampleItems():
            item.updateContacts()

    def setLocked(self, locked: bool) -> None:
        if locked:
            self.pickButton.setEnabled(False)
            self.moveButton.setEnabled(False)
            self.calculateButton.setEnabled(False)
            self.resetButton.setEnabled(False)
        else:
            item = self.contactsTreeWidget.currentItem()
            self.setButtonStates(item)
        self.resetAllButton.setEnabled(not locked)


class TablePositionItem(QtWidgets.QTreeWidgetItem):

    def __init__(self) -> None:
        super().__init__()
        self.setTextAlignment(1, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore[arg-type]
        self.setTextAlignment(2, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore[arg-type]
        self.setTextAlignment(3, QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)  # type: ignore[arg-type]
        self.setPosition(0, 0, 0)

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self) -> tuple:
        x = self.data(1, 0x2000)
        y = self.data(2, 0x2000)
        z = self.data(3, 0x2000)
        return x, y, z

    def setPosition(self, x: float, y: float, z: float) -> None:
        self.setData(1, 0x2000, x)
        self.setData(2, 0x2000, y)
        self.setData(3, 0x2000, z)
        self.setText(1, format(x, ".3f"))
        self.setText(2, format(y, ".3f"))
        self.setText(3, format(z, ".3f"))

    def comment(self) -> str:
        return self.text(4)

    def setComment(self, comment: str) -> None:
        self.setText(4, comment)


class PositionDialog(QtWidgets.QDialog):

    positionPicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.nameLabel = QtWidgets.QLabel(self)
        self.nameLabel.setText("Name")
        self.nameLabel.setToolTip("Position name")

        self.nameLineEdit = QtWidgets.QLineEdit(self)
        self.nameLineEdit.setText("Unnamed")

        self.xLabel = QtWidgets.QLabel(self)
        self.xLabel.setText("X")
        self.xLabel.setToolTip("Position X coordinate")

        self.xSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.xSpinBox.setRange(0, 1000)
        self.xSpinBox.setDecimals(3)
        self.xSpinBox.setSuffix(" mm")

        self.yLabel = QtWidgets.QLabel(self)
        self.yLabel.setText("X")
        self.yLabel.setToolTip("Position Y coordinate")

        self.ySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.ySpinBox.setRange(0, 1000)
        self.ySpinBox.setDecimals(3)
        self.ySpinBox.setSuffix(" mm")

        self.zLabel = QtWidgets.QLabel(self)
        self.zLabel.setText("Z")
        self.zLabel.setToolTip("Position Z coordinate")

        self.zSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zSpinBox.setRange(0, 1000)
        self.zSpinBox.setDecimals(3)
        self.zSpinBox.setSuffix(" mm")

        self.commentLabel = QtWidgets.QLabel(self)
        self.commentLabel.setText("Comment")
        self.commentLabel.setToolTip("Optional position comment")

        self.commentLineEdit = QtWidgets.QLineEdit(self)

        self.assignButton = QtWidgets.QPushButton(self)
        self.assignButton.setText("Assign Position")
        self.assignButton.setToolTip("Assign current table position.")
        self.assignButton.clicked.connect(self.positionPicked.emit)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
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

    def name(self) -> str:
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


class TablePositionsWidget(QtWidgets.QWidget):

    positionPicked = QtCore.pyqtSignal(object)
    absoluteMove = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._locked = False  # TODO

        self.positionsTreeWidget = QtWidgets.QTreeWidget(self)
        self.positionsTreeWidget.setHeaderLabels(["Name", "X", "Y", "Z", "Comment"])
        self.positionsTreeWidget.setRootIsDecorated(False)
        self.positionsTreeWidget.currentItemChanged.connect(self.on_position_selected)
        self.positionsTreeWidget.itemDoubleClicked.connect(lambda item, column: self.moveToCurrentPosition())

        self.addButton = QtWidgets.QPushButton(self)
        self.addButton.setText("&Add")
        self.addButton.setToolTip("Add new position item")
        self.addButton.clicked.connect(self.on_add_position)

        self.editButton = QtWidgets.QPushButton(self)
        self.editButton.setText("&Edit")
        self.editButton.setToolTip("Edit selected position item")
        self.editButton.setEnabled(False)
        self.editButton.clicked.connect(self.on_edit_position)

        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("&Remove")
        self.removeButton.setToolTip("Remove selected position item")
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.on_remove_position)

        self.moveButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("&Move")
        self.moveButton.setToolTip("Move to selected position")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.moveToCurrentPosition)

        self.importButton = QtWidgets.QPushButton(self)
        self.importButton.setText("Import...")
        self.importButton.setToolTip("Import from CSV")
        self.importButton.setEnabled(False)
        self.importButton.clicked.connect(self.on_import)

        self.exportButton = QtWidgets.QPushButton(self)
        self.exportButton.setText("Export...")
        self.exportButton.setToolTip("Export to CSV")
        self.exportButton.setEnabled(False)
        self.exportButton.clicked.connect(self.on_export)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.positionsTreeWidget, 0, 0, 7, 1)
        layout.addWidget(self.moveButton, 0, 1)
        layout.addWidget(self.addButton, 2, 1)
        layout.addWidget(self.editButton, 3, 1)
        layout.addWidget(self.removeButton, 4, 1)
        layout.addWidget(self.importButton, 5, 1)
        layout.addWidget(self.exportButton, 6, 1)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(1, 1)

    def readSettings(self) -> None:
        self.positionsTreeWidget.clear()
        for position in settings.table_positions:
            item = TablePositionItem()
            item.setName(position.name)
            item.setPosition(position.x, position.y, position.z)
            item.setComment(position.comment)
            self.positionsTreeWidget.addTopLevelItem(item)
        self.positionsTreeWidget.resizeColumnToContents(0)
        self.positionsTreeWidget.resizeColumnToContents(1)
        self.positionsTreeWidget.resizeColumnToContents(2)
        self.positionsTreeWidget.resizeColumnToContents(3)

    def writeSettings(self) -> None:
        positions: list = []
        for index in range(self.positionsTreeWidget.topLevelItemCount()):
            item = self.positionsTreeWidget.topLevelItem(index)
            if isinstance(item, TablePositionItem):
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
        self._locked = locked
        if locked:
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

    def on_import(self) -> None:
        filename, ok = QtWidgets.QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV (*.csv);;All files (*)")
        if ok:
            ...

    def on_export(self) -> None:
        filename, ok = QtWidgets.QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV (*.csv);;All files (*)")
        if ok:
            ...

    def on_position_selected(self, current, previous) -> None:
        enabled = current is not None
        self.editButton.setEnabled(True)
        self.removeButton.setEnabled(True)
        self.moveButton.setEnabled(True)

    def on_position_picked(self, callback) -> None:
        self.positionPicked.emit(callback)

    def on_add_position(self) -> None:
        dialog = PositionDialog()
        dialog.positionPicked.connect(lambda dialog=dialog: self.on_position_picked(dialog.setPosition))  # TODO
        if dialog.exec() == dialog.Accepted:
            x, y, z = dialog.position()
            item = TablePositionItem()
            item.setName(dialog.name())
            item.setPosition(x, y, z)  # TODO
            item.setComment(dialog.comment())
            self.positionsTreeWidget.addTopLevelItem(item)
            self.positionsTreeWidget.resizeColumnToContents(0)
            self.positionsTreeWidget.resizeColumnToContents(1)
            self.positionsTreeWidget.resizeColumnToContents(2)
            self.positionsTreeWidget.resizeColumnToContents(3)

    def on_edit_position(self) -> None:
        item = self.positionsTreeWidget.currentItem()
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
                self.positionsTreeWidget.resizeColumnToContents(0)
                self.positionsTreeWidget.resizeColumnToContents(1)
                self.positionsTreeWidget.resizeColumnToContents(2)
                self.positionsTreeWidget.resizeColumnToContents(3)

    def on_remove_position(self):
        item = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            if QtWidgets.QMessageBox.question(None, "", f"Do you want to remove position {item.name()!r}?") == QtWidgets.QMessageBox.Yes:
                index = self.positionsTreeWidget.indexOfTopLevelItem(item)
                self.positionsTreeWidget.takeTopLevelItem(index)
                if not self.positionsTreeWidget.topLevelItemCount():
                    self.editButton.setEnabled(False)
                    self.removeButton.setEnabled(False)
                self.positionsTreeWidget.resizeColumnToContents(0)
                self.positionsTreeWidget.resizeColumnToContents(1)
                self.positionsTreeWidget.resizeColumnToContents(2)
                self.positionsTreeWidget.resizeColumnToContents(3)

    def moveToCurrentPosition(self) -> None:
        if self._locked:
            return
        item = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            if QtWidgets.QMessageBox.question(None, "", f"Do you want to move table to position {item.name()!r}?") == QtWidgets.QMessageBox.Yes:
                x, y ,z = item.position()
                self.absoluteMove.emit(Position(x, y, z))


class CalibrateWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.calibrateButton = QtWidgets.QPushButton(self)
        self.calibrateButton.setText("Calibrate")

        self.calibrateLabel = QtWidgets.QLabel(self)
        self.calibrateLabel.setText(
            "Calibrate table by moving into cal/rm switches\n"
            "of every axis in a safe manner to protect the probe card."
        )

        self.calibrateGroupBox = QtWidgets.QGroupBox(self)
        self.calibrateGroupBox.setTitle("Table Calibration")

        calibrateGroupBoxLayout = QtWidgets.QHBoxLayout(self.calibrateGroupBox)
        calibrateGroupBoxLayout.addWidget(self.calibrateButton, 0)
        calibrateGroupBoxLayout.addWidget(self.calibrateLabel, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.calibrateGroupBox)
        layout.addStretch()

    def setLocked(self, locked: bool) -> None:
        self.calibrateButton.setEnabled(not locked)


class OptionsWidget(QtWidgets.QWidget):

    updateIntervalChanged = QtCore.pyqtSignal(float)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Update interval

        self.updateIntervalSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.updateIntervalSpinBox.setDecimals(2)
        self.updateIntervalSpinBox.setSingleStep(0.25)
        self.updateIntervalSpinBox.setRange(0.5, 10.0)
        self.updateIntervalSpinBox.setSuffix(" s")
        self.updateIntervalSpinBox.valueChanged.connect(self.updateIntervalChanged.emit)

        self.updateIntervalGroupBox = QtWidgets.QGroupBox(self)
        self.updateIntervalGroupBox.setTitle("Update Interval")

        updateIntervalGroupBoxLayout = QtWidgets.QHBoxLayout(self.updateIntervalGroupBox)
        updateIntervalGroupBoxLayout.addWidget(self.updateIntervalSpinBox)
        updateIntervalGroupBoxLayout.addStretch()

        # Dodge

        self.dodgeHeightSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.dodgeHeightSpinBox.setToolTip("Dodge height in microns.")
        self.dodgeHeightSpinBox.setDecimals(0)
        self.dodgeHeightSpinBox.setRange(0, 10_000)
        self.dodgeHeightSpinBox.setSingleStep(1)
        self.dodgeHeightSpinBox.setSuffix(" um")

        self.dodgeGroupBox = QtWidgets.QGroupBox(self)
        self.dodgeGroupBox.setTitle("X/Y Dodge")
        self.dodgeGroupBox.setToolTip("Enables -/+ Z dodge for XY movements.")
        self.dodgeGroupBox.setCheckable(True)

        dodgeGroupBoxLayout = QtWidgets.QHBoxLayout(self.dodgeGroupBox)
        dodgeGroupBoxLayout.addWidget(QtWidgets.QLabel("Height"))
        dodgeGroupBoxLayout.addWidget(self.dodgeHeightSpinBox)
        dodgeGroupBoxLayout.addStretch()

        # Contact quality

        self.lcrResetOnMoveCheckBox = QtWidgets.QCheckBox(self)
        self.lcrResetOnMoveCheckBox.setText("Reset graph on X/Y move")

        self.contactQualityGroupBox = QtWidgets.QGroupBox(self)
        self.contactQualityGroupBox.setTitle("Contact Quality (LCR)")

        contactQualityGroupBoxLayout = QtWidgets.QHBoxLayout(self.contactQualityGroupBox)
        contactQualityGroupBoxLayout.addWidget(self.lcrResetOnMoveCheckBox)
        contactQualityGroupBoxLayout.addStretch()

        # Step up

        self.stepUpDelaySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.stepUpDelaySpinBox.setDecimals(0)
        self.stepUpDelaySpinBox.setRange(0, 1_000)
        self.stepUpDelaySpinBox.setSingleStep(25)
        self.stepUpDelaySpinBox.setSuffix(" ms")

        self.stepUpMulitplySpinBox = QtWidgets.QSpinBox(self)
        self.stepUpMulitplySpinBox.setRange(1, 10)
        self.stepUpMulitplySpinBox.setSingleStep(1)
        self.stepUpMulitplySpinBox.setSuffix(" x")

        self.stepUpGroupBox = QtWidgets.QGroupBox(self)
        self.stepUpGroupBox.setTitle("Step Up (↑⇵)")

        stepUpGroupBoxLayout = QtWidgets.QGridLayout(self.stepUpGroupBox)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Delay"), 0, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpDelaySpinBox, 0, 1)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Multiplicator (⇵)"), 1, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpMulitplySpinBox, 1, 1)
        stepUpGroupBoxLayout.setColumnStretch(2, 1)

        # LCR options

        self.lcrUpdateIntervalSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.lcrUpdateIntervalSpinBox.setDecimals(0)
        self.lcrUpdateIntervalSpinBox.setRange(0, 1_000)
        self.lcrUpdateIntervalSpinBox.setSingleStep(25)
        self.lcrUpdateIntervalSpinBox.setSuffix(" ms")

        self.lcrMatrixChannelsLineEdit = QtWidgets.QLineEdit(self)

        self.lcrOptionsGroupBox = QtWidgets.QGroupBox(self)
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
        return (self.dodgeHeightSpinBox.value() * ureg("um")).to("mm").m

    def setDodgeHeight(self, height: float) -> None:
        """Set dodge height in millimeters."""
        self.dodgeHeightSpinBox.setValue((height * ureg("mm")).to("um").m)

    def isLcrResetOnMove(self) -> bool:
        return self.lcrResetOnMoveCheckBox.isChecked()

    def setLcrResetOnMove(self, enabled: bool) -> None:
        self.lcrResetOnMoveCheckBox.setChecked(enabled)

    def stepUpDelay(self) -> float:
        """Return step up delay in seconds."""
        return (self.stepUpDelaySpinBox.value() * ureg("ms")).to("s").m

    def setStepUpDelay(self, seconds: float) -> None:
        self.stepUpDelaySpinBox.setValue((seconds * ureg("s")).to("ms").m)

    def stepUpMultiply(self) -> int:
        """Return step up delay in seconds."""
        return self.stepUpMulitplySpinBox.value()

    def setStepUpMultiply(self, factor: int) -> None:
        self.stepUpMulitplySpinBox.setValue(factor)

    def lcrUpdateInterval(self) -> float:
        """LCR update interval in seconds."""
        return (self.lcrUpdateIntervalSpinBox.value() * ureg("ms")).to("s").m

    def setLcrUpdateInterval(self, seconds: float) -> None:
        self.lcrUpdateIntervalSpinBox.setValue((seconds * ureg("s")).to("ms").m)

    def lcrMatrixChannels(self) -> List[str]:
        """Matrix channels used for LCR readings."""
        tokens: List[str] = []
        for token in self.lcrMatrixChannelsLineEdit.text().split(","):
            token = token.strip()
            if token:
                tokens.append(token)
        return tokens

    def setLcrMatrixChannels(self, channels: List[str]) -> None:
        self.lcrMatrixChannelsLineEdit.setText(", ".join([token for token in channels]))

    def setLocked(self, locked: bool) -> None:
        self.setEnabled(not locked)


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

    moveRequested = QtCore.pyqtSignal()
    abortRequested = QtCore.pyqtSignal()
    moveFinished = QtCore.pyqtSignal()

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

        self.xAddButton = QtWidgets.QPushButton(self)
        self.xAddButton.setText("+X")
        self.xAddButton.setFixedSize(32, 32)
        self.xAddButton.clicked.connect(self.on_add_x)

        self.xSubButton = QtWidgets.QPushButton(self)
        self.xSubButton.setText("-X")
        self.xSubButton.setFixedSize(32, 32)
        self.xSubButton.clicked.connect(self.on_sub_x)

        self.yAddButton = QtWidgets.QPushButton(self)
        self.yAddButton.setText("+Y")
        self.yAddButton.setFixedSize(32, 32)
        self.yAddButton.clicked.connect(self.on_add_y)

        self.ySubButton = QtWidgets.QPushButton(self)
        self.ySubButton.setText("-Y")
        self.ySubButton.setFixedSize(32, 32)
        self.ySubButton.clicked.connect(self.on_sub_y)

        self.zAddButton = QtWidgets.QPushButton(self)
        self.zAddButton.setText("+Z")
        self.zAddButton.setFixedSize(32, 32)
        self.zAddButton.clicked.connect(self.on_add_z)

        self.zSubButton = QtWidgets.QPushButton(self)
        self.zSubButton.setText("-Z")
        self.zSubButton.setFixedSize(32, 32)
        self.zSubButton.clicked.connect(self.on_sub_z)

        self.stepUpButton = QtWidgets.QPushButton(self)
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

        self.keypadGroupBox = QtWidgets.QGroupBox(self)
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

        self.stepWidthGroupBox = QtWidgets.QGroupBox(self)
        self.stepWidthGroupBox.setTitle("Step Width")

        stepWidthGroupBoxLayout = QtWidgets.QVBoxLayout(self.stepWidthGroupBox)

        self.stepWidthButtonGroup = QtWidgets.QButtonGroup(self)
        self.stepWidthButtonGroup.buttonToggled.connect(self.toggleStepWidth)

        # Create step width radio buttons
        for item in self.load_table_step_sizes():
            step_size = item.get("step_size") * ureg("um")
            step_color = item.get("step_color")
            step_size_label = format_metric(step_size.to("m").m, "m", decimals=1)
            button = QtWidgets.QRadioButton(self)
            button.setText(step_size_label)
            button.setToolTip(f"Move in {step_size_label} steps.")
            button.setStyleSheet(f"QRadioButton:enabled{{color:{step_color};}}")
            button.setChecked(len(self.stepWidthButtonGroup.buttons()) == 0)
            button.setProperty("step", step_size.to("mm").m)
            button.setProperty("color", step_color)
            self.stepWidthButtonGroup.addButton(button)
            stepWidthGroupBoxLayout.addWidget(button)
        stepWidthGroupBoxLayout.addStretch()

        # Lights group box

        self.probecardLightButton = ToggleButton(self)
        self.probecardLightButton.setText("PC Light")
        self.probecardLightButton.setToolTip("Toggle probe card light")
        self.probecardLightButton.toggled.connect(self.probecardLightToggled.emit)

        self.microscopeLightButton = ToggleButton(self)
        self.microscopeLightButton.setText("Mic Light")
        self.microscopeLightButton.setToolTip("Toggle microscope light")
        self.microscopeLightButton.toggled.connect(self.microscopeLightToggled.emit)

        self.boxLightButton = ToggleButton(self)
        self.boxLightButton.setText("Box Light")
        self.boxLightButton.setToolTip("Toggle box light")
        self.boxLightButton.toggled.connect(self.boxLightToggled.emit)

        self.lightsGroupBox = QtWidgets.QGroupBox(self)
        self.lightsGroupBox.setTitle("Lights")

        lightsGroupBoxLayout = QtWidgets.QVBoxLayout(self.lightsGroupBox)
        lightsGroupBoxLayout.addWidget(self.probecardLightButton)
        lightsGroupBoxLayout.addWidget(self.microscopeLightButton)
        lightsGroupBoxLayout.addWidget(self.boxLightButton)
        lightsGroupBoxLayout.addStretch()

        # LCR group box

        self.lcrPrimLineEdit = QtWidgets.QLineEdit(self)
        self.lcrPrimLineEdit.setReadOnly(True)

        self.lcrSecLineEdit = QtWidgets.QLineEdit(self)
        self.lcrSecLineEdit.setReadOnly(True)

        self.lcrWidget = LCRWidget(self)

        self.lcrGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("Contact Quality (LCR)")
        self.lcrGroupBox.setCheckable(True)
        self.lcrGroupBox.setChecked(False)
        self.lcrGroupBox.toggled.connect(self.on_lcr_toggled)

        self.lcrPrimLabel = QtWidgets.QLabel(self)
        self.lcrPrimLabel.setText("Cp")

        self.lcrSecLabel = QtWidgets.QLabel(self)
        self.lcrSecLabel.setText("Rp")

        lcrGroupBoxLayout = QtWidgets.QGridLayout(self.lcrGroupBox)
        lcrGroupBoxLayout.addWidget(self.lcrPrimLabel, 0, 0)
        lcrGroupBoxLayout.addWidget(self.lcrPrimLineEdit, 0, 1)
        lcrGroupBoxLayout.addWidget(self.lcrSecLabel, 1, 0)
        lcrGroupBoxLayout.addWidget(self.lcrSecLineEdit, 1, 1)
        lcrGroupBoxLayout.addWidget(self.lcrWidget, 2, 0, 1, 2)

        # Position group box

        self.positionsWidget: TablePositionsWidget = TablePositionsWidget(self)
        self.positionsWidget.setEnabled(False)
        self.positionsWidget.positionPicked.connect(self.on_position_picked)
        self.positionsWidget.absoluteMove.connect(self.on_absolute_move)

        # Contact group box

        self.contactsWidget: TableContactsWidget = TableContactsWidget(self)
        self.contactsWidget.setEnabled(False)
        self.contactsWidget.positionPicked.connect(self.on_position_picked)
        self.contactsWidget.absoluteMove.connect(self.on_absolute_move)

        self.positionWidget = PositionWidget()

        self.calibrationWidget = CalibrationWidget()

        # Soft limits group box

        self.zSoftLimitLabel = QtWidgets.QLabel(self)
        self.zSoftLimitLabel.setText("Z")

        self.zSoftLimitValueLabel = PositionLabel(self)

        self.softLimitsGroupBox = QtWidgets.QGroupBox(self)
        self.softLimitsGroupBox.setTitle("Soft Limits")

        softLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.softLimitsGroupBox)
        softLimitsGroupBoxLayout.addWidget(self.zSoftLimitLabel, 0, 0)
        softLimitsGroupBoxLayout.addWidget(self.zSoftLimitValueLabel, 0, 1)

        # Hard limits group box

        self.xHardLimitLabel = QtWidgets.QLabel(self)
        self.xHardLimitLabel.setText("X")

        self.xHardLimitValueLabel = PositionLabel(self)

        self.yHardLimitLabel = QtWidgets.QLabel(self)
        self.yHardLimitLabel.setText("Y")

        self.yHardLimitValueLabel = PositionLabel(self)

        self.zHardLimitLabel = QtWidgets.QLabel(self)
        self.zHardLimitLabel.setText("Z")

        self.zHardLimitValueLabel = PositionLabel(self)

        self.hardLimitsGroupBox = QtWidgets.QGroupBox(self)
        self.hardLimitsGroupBox.setTitle("Hard Limits")

        hardLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.hardLimitsGroupBox)
        hardLimitsGroupBoxLayout.addWidget(self.xHardLimitLabel, 0, 0)
        hardLimitsGroupBoxLayout.addWidget(self.xHardLimitValueLabel, 0, 1)
        hardLimitsGroupBoxLayout.addWidget(self.yHardLimitLabel, 1, 0)
        hardLimitsGroupBoxLayout.addWidget(self.yHardLimitValueLabel, 1, 1)
        hardLimitsGroupBoxLayout.addWidget(self.zHardLimitLabel, 2, 0)
        hardLimitsGroupBoxLayout.addWidget(self.zHardLimitValueLabel, 2, 1)

        # Safety group box

        self.laserSensorLabel = QtWidgets.QLabel(self)
        self.laserSensorLabel.setText("Laser Sensor")

        self.laserSensorSwitch = SwitchLabel(self)

        self.safetyGroupBox = QtWidgets.QGroupBox(self)
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
        self.rightLayout.addWidget(self.positionWidget)
        self.rightLayout.addWidget(self.calibrationWidget)
        self.rightLayout.addWidget(self.softLimitsGroupBox)
        self.rightLayout.addWidget(self.hardLimitsGroupBox)
        self.rightLayout.addWidget(self.safetyGroupBox)
        self.rightLayout.addStretch()

        # Tab widget

        self.tabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.positionsWidget, "Move")
        self.tabWidget.addTab(self.contactsWidget, "Contacts")
        self.tabWidget.addTab(self.calibrateWidget, "Calibrate")
        self.tabWidget.addTab(self.optionsWidget, "Options")

        # Bottom bar

        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setVisible(False)

        self.messageLabel = QtWidgets.QLabel(self)

        self.stopButton = QtWidgets.QPushButton(self)
        self.stopButton.setText("&Stop")
        self.stopButton.setDefault(False)
        self.stopButton.setAutoDefault(False)
        self.stopButton.setEnabled(False)
        self.stopButton.clicked.connect(self.stop)

        self.closeButton = QtWidgets.QPushButton(self)
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

        # State machine

        self.idleState = QtCore.QState()
        self.idleState.entered.connect(self.enterIdle)

        self.movingState = QtCore.QState()
        self.movingState.entered.connect(self.enterMoving)

        self.abortingState = QtCore.QState()
        self.abortingState.entered.connect(self.enterAbort)

        self.idleState.addTransition(self.moveRequested, self.movingState)

        self.movingState.addTransition(self.moveFinished, self.idleState)
        self.movingState.addTransition(self.abortRequested, self.abortingState)

        self.abortingState.addTransition(self.moveFinished, self.idleState)

        self.stateMachine = QtCore.QStateMachine(self)
        self.stateMachine.addState(self.idleState)
        self.stateMachine.addState(self.movingState)
        self.stateMachine.addState(self.abortingState)
        self.stateMachine.setInitialState(self.idleState)
        self.stateMachine.start()

    def enterIdle(self) -> None:
        self.setLocked(False)
        self.progressBar.setVisible(False)
        self.stopButton.setEnabled(False)

    def enterMoving(self) -> None:
        self.setLocked(True)
        self.progressBar.setVisible(True)
        self.stopButton.setEnabled(True)

    def enterAbort(self) -> None:
        self.stopButton.setEnabled(False)

    def stepWidth(self) -> float:
        for button in self.stepWidthButtonGroup.buttons():
            if button.isChecked():
                return abs(button.property("step") or 0.0)
        return 0.0

    def load_table_step_sizes(self) -> list:
        return settings.settings.get("table_step_sizes") or self.default_steps

    def resetPosition(self) -> None:
        self.setPosition(Position())

    def setPosition(self, position: Position) -> None:
        self.current_position = position
        self.positionWidget.setPosition(position)
        self.updateLimits()
        self.updateKeypadButtons()
        if math.isfinite(position.z):
            self.lcrWidget.setLimits(position.z)
            self.lcrWidget.setLinePos(position.z)

    def resetCaldone(self) -> None:
        self.calibrationWidget.reset()

    def setCaldone(self, position: Position) -> None:
        self.current_caldone = position
        self.positionsWidget.setEnabled(caldone_valid(position))
        self.contactsWidget.setEnabled(caldone_valid(position))
        self.calibrationWidget.setCalibration(position)

    def updateLimits(self) -> None:
        x, y, z = self.current_position
        self.zSoftLimitValueLabel.setStyleSheet("")
        if not math.isnan(z):
            if z >= self.z_limit:
                self.zSoftLimitValueLabel.setStyleSheet("QLabel:enabled{color:red;}")

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
            color = button.property("color") or "inherit"
            button.setStyleSheet(f"QPushButton:enabled{{color:{color}}}")

    def update_x_buttons(self, x) -> None:
        x_enabled = True
        if not math.isnan(x):
            if (x - self.stepWidth()) < 0:
                x_enabled = False
        self.xSubButton.setEnabled(x_enabled)

    def update_y_buttons(self, y) -> None:
        y_enabled = True
        if not math.isnan(y):
            if (y - self.stepWidth()) < 0:
                y_enabled = False
        self.ySubButton.setEnabled(y_enabled)

    def update_z_buttons(self, z) -> None:
        # Disable move up button for large step sizes
        z_enabled = False
        if not math.isnan(z):
            if (z + self.stepWidth()) <= self.z_limit:
                z_enabled = True
            else:
                z_enabled = self.stepWidth() <= self.maximum_z_step_size
        self.zAddButton.setEnabled(z_enabled)
        step_up_limit = ureg("10.0 um").to("mm").m
        self.stepUpButton.setEnabled(z_enabled and (self.stepWidth() <= step_up_limit))  # TODO

    def relative_move_xy(self, x, y) -> None:
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

    def on_add_x(self) -> None:
        self.moveRequested.emit()
        self.relative_move_xy(+self.stepWidth(), 0)

    def on_sub_x(self) -> None:
        self.moveRequested.emit()
        self.relative_move_xy(-self.stepWidth(), 0)

    def on_add_y(self) -> None:
        self.moveRequested.emit()
        self.relative_move_xy(0, +self.stepWidth())

    def on_sub_y(self) -> None:
        self.moveRequested.emit()
        self.relative_move_xy(0, -self.stepWidth())

    def on_add_z(self) -> None:
        self.moveRequested.emit()
        self.process.relative_move(0, 0, +self.stepWidth())

    def on_sub_z(self) -> None:
        self.moveRequested.emit()
        self.process.relative_move(0, 0, -self.stepWidth())

    def on_step_up(self) -> None:
        self.moveRequested.emit()
        step_width = self.stepWidth()
        multiply = self.optionsWidget.stepUpMultiply()
        vector = (
            [0, 0, +step_width],
            [0, 0, -step_width * multiply],
            [0, 0, +step_width * multiply],
        )
        self.process.relative_move_vector(vector, delay=self.optionsWidget.stepUpDelay())

    def toggleStepWidth(self, button, state: bool) -> None:
        logger.info("set table step width to %.3f mm", self.stepWidth())
        self.updateKeypadButtons()

    def update_probecard_light(self, state: bool) -> None:
        self.probecardLightButton.setChecked(state)

    def update_microscope_light(self, state: bool) -> None:
        self.microscopeLightButton.setChecked(state)

    def update_box_light(self, state: bool) -> None:
        self.boxLightButton.setChecked(state)

    def update_lights_enabled(self, state: bool) -> None:
        self.probecardLightButton.setEnabled(state)
        self.microscopeLightButton.setEnabled(state)
        self.boxLightButton.setEnabled(state)

    def on_move_finished(self) -> None:
        self.moveFinished.emit()

    def setMessage(self, message: str) -> None:
        self.messageLabel.setText(message)
        logger.info(message)

    def setProgress(self, value: int, maximum: int) -> None:
        self.progressBar.setValue(value)
        self.progressBar.setMaximum(maximum)
        self.progressBar.setVisible(True)

    def on_update_interval_changed(self, seconds: float) -> None:
        self.process.update_interval = seconds

    def on_position_picked(self, callback) -> None:
        x, y, z = self.current_position
        callback(x, y, z)

    def on_absolute_move(self, position) -> None:
        self.moveRequested.emit()
        # Update to safe Z position
        position = Position(position.x, position.y, safe_z_position(position.z))
        # Clear contact quality graph on X/Y movements.
        self.lcrWidget.clear()
        self.process.safe_absolute_move(position.x, position.y, position.z)

    def on_calibrate(self) -> None:
        self.moveRequested.emit()
        self.process.calibrate_table()

    def stop(self) -> None:
        self.abortRequested.emit()
        self.process.stop_current_action()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        self.process.wait()
        event.accept()

    def loadSamples(self, sample_items) -> None:
        self.contactsWidget.loadSamples(sample_items)

    def updateSamples(self) -> None:
        self.contactsWidget.updateSamples()

    def readSettings(self) -> None:
        settings_ = QtCore.QSettings()
        settings_.beginGroup("tablecontrol")
        geometry = settings_.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)
        settings_.endGroup()

        self.positionsWidget.readSettings()
        self.z_limit = settings.table_z_limit
        self.zSoftLimitValueLabel.setValue(self.z_limit)
        x, y, z = settings.table_probecard_maximum_limits
        self.xHardLimitValueLabel.setValue(x)
        self.yHardLimitValueLabel.setValue(y)
        self.zHardLimitValueLabel.setValue(z)
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
        self.positionsWidget.writeSettings()
        settings.table_control_update_interval = self.optionsWidget.updateInterval()
        settings.table_control_dodge_enabled = self.optionsWidget.isDodgeEnabled()
        settings.table_control_dodge_height = self.optionsWidget.dodgeHeight()
        settings.settings["tablecontrol_lcr_reset_on_move"] = self.optionsWidget.isLcrResetOnMove()

    def setLocked(self, locked: bool) -> None:
        self.keypadGroupBox.setEnabled(not locked)
        self.positionsWidget.setLocked(locked)
        self.contactsWidget.setLocked(locked)
        self.closeButton.setEnabled(not locked)
        self.calibrateWidget.setLocked(locked)
        self.optionsWidget.setLocked(locked)
        self.progressBar.setVisible(locked)
        if locked:
            self.progressBar.setRange(0, 0)
            self.progressBar.setValue(0)

    def mount(self, process) -> None:
        """Mount table process."""
        self.unmount()
        self.process = process
        self.process.message_changed = self.setMessage
        self.process.progress_changed = self.setProgress
        self.process.position_changed = self.setPosition
        self.process.caldone_changed = self.setCaldone
        self.process.relative_move_finished = self.on_move_finished
        self.process.absolute_move_finished = self.on_move_finished
        self.process.calibration_finished = self.on_move_finished
        self.process.stopped = self.on_move_finished

    def unmount(self) -> None:
        """Unmount table process."""
        if self.process:
            self.process.message_changed = None
            self.process.progress_changed = None
            self.process.position_changed = None
            self.process.caldone_changed = None
            self.process.relative_move_finished = None
            self.process.absolute_move_finished = None
            self.process.calibration_finished = None
            self.process.stopped = None
            self.process = None

    def on_lcr_toggled(self, state: bool) -> None:
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
            self.lcrWidget.setLinePos(z)


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
