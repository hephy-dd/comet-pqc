"""Table control widgets and dialogs."""

import logging
import math
from typing import Dict, List, Optional, Tuple

import comet
from PyQt5 import QtChart, QtCore, QtGui, QtWidgets

from ..core.position import Position
from ..processes.table import AlternateTableProcess
from ..settings import TablePosition, settings
from ..utils import caldone_valid, format_metric, format_switch
from .components import (CalibrationWidget, PositionLabel, PositionWidget,
                         ToggleButton, handle_exception, showException,
                         showQuestion, showWarning)
from .sequencetreewidget import ContactTreeItem, SampleTreeItem
from .contactqualitywidget import ContactQualityWidget

__all__ = ["AlignmentDialog"]

DEFAULT_STEP_UP_DELAY = 0.
DEFAULT_STEP_UP_MULTIPLY = 2
DEFAULT_LCR_UPDATE_INTERVAL = .100
DEFAULT_MATRIX_CHANNELS = [
    "3H01", "2B04", "1B03", "1B12", "2B06", "2B07", "2B08", "2B09",
    "2B10", "2B11", "1H04", "1H05", "1H06", "1H07", "1H08", "1H09",
    "1H10", "1H11", "2H12", "2H05", "1A01"
]

logger = logging.getLogger(__name__)


def safe_z_position(z):
    z_limit = settings.table_z_limit()
    if z > z_limit:
        showWarning(
            title="Z Warning",
            text=f"Limiting Z movement to {z_limit:.3f} mm to protect probe card.",
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

    def __init__(self, contactItem: ContactTreeItem) -> None:
        super().__init__()
        self.setTextAlignment(2, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(3, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(4, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)  # type: ignore
        self.contactItem = contactItem  # TODO
        self.setName(contactItem.name)
        self.setPosition(contactItem.position())

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self) -> Position:
        return self._position

    def setPosition(self, position: Position) -> None:
        x, y, z = position
        self._position = Position(x, y, z)
        self.setText(2, format(x, ".3f") if x is not None else "")
        self.setText(3, format(y, ".3f") if y is not None else "")
        self.setText(4, format(z, ".3f") if z is not None else "")

    def hasPosition(self) -> bool:
        return self._position.is_valid

    def updateContact(self) -> None:
        self.contactItem.setPosition(self.position())


class TableSampleItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, sampleItem: SampleTreeItem) -> None:
        super().__init__()
        self.setName("/".join([item for item in (sampleItem.name, sampleItem.sample_type) if item]))
        self.setPositionName(sampleItem.sample_position)
        for contactItem in sampleItem.children():
            child = TableContactItem(contactItem)
            self.addChild(child)

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def positionName(self) -> str:
        return self.text(1)

    def setPositionName(self, name: str) -> None:
        self.setText(1, name)

    def contactItems(self) -> List[TableContactItem]:
        items = []
        for index in range(self.childCount()):
            item = self.child(index)
            if isinstance(item, TableContactItem):
                items.append(item)
        return items

    def updateContacts(self) -> None:
        for contactItem in self.contactItems():
            contactItem.updateContact()
            logger.info("Updated contact position: %s %s %s", self.name(), contactItem.name(), contactItem.position())

    def calculatePositions(self) -> None:
        tr = LinearTransform()
        contactItem = self.contactItems()
        count = len(contactItem)
        if count > 2:
            first = list(contactItem[0].position())
            last = list(contactItem[-1].position())
            for index, position in enumerate(tr.calculate(first, last, count - 1)):
                contactItem[index].setPosition(position)


class TableContactsTreeWidget(QtWidgets.QTreeWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Contact", "Pos", "X", "Y", "Z", ""])

    def addSample(self, sample) -> None:
        item = TableSampleItem(sample)
        self.addTopLevelItem(item)
        item.setExpanded(True)

    def sampleItems(self) -> List[TableSampleItem]:
        items: List[TableSampleItem] = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            if isinstance(item, TableSampleItem):
                items.append(item)
        return items

    def resizeColumns(self) -> None:
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)


class TableContactsWidget(QtWidgets.QWidget):

    position_picked = QtCore.pyqtSignal(object)
    absolute_move = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.contacts_tree: TableContactsTreeWidget = TableContactsTreeWidget(self)
        self.contacts_tree.currentItemChanged.connect(self.currentItemChanged)

        self.assignButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.assignButton.setText("Assign &Position")
        self.assignButton.setToolTip("Assign current table position to selected position item")
        self.assignButton.setEnabled(False)
        self.assignButton.clicked.connect(self.on_pick_position)

        self.calculateButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.calculateButton.setText("&Calculate")
        self.calculateButton.setToolTip("Calculate positions between first and last contact")
        self.calculateButton.setEnabled(False)
        self.calculateButton.clicked.connect(self.on_calculate)

        self.moveButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("&Move")
        self.moveButton.setToolTip("Move to selected position")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.moveToPosition)

        self.resetButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.resetButton.setText("&Reset")
        self.resetButton.setToolTip("&Reset selected position")
        self.resetButton.setEnabled(False)
        self.resetButton.clicked.connect(self.on_reset)

        self.resetAllButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.resetAllButton.setText("Reset &All",)
        self.resetAllButton.setToolTip("Reset all contact positions")
        self.resetAllButton.clicked.connect(self.on_reset_all)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.contacts_tree, 0, 0, 6, 1)
        layout.addWidget(self.assignButton, 0, 1)
        layout.addWidget(self.moveButton, 1, 1)
        layout.addWidget(self.calculateButton, 2, 1)
        layout.addWidget(self.resetButton, 4, 1)
        layout.addWidget(self.resetAllButton, 5, 1)
        layout.setRowStretch(3, 1)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def currentItemChanged(self, current, previous) -> None:
        self.update_button_states(current)

    def update_button_states(self, item: Optional[QtWidgets.QTreeWidgetItem] = None) -> None:
        if item is None:
            item = self.contacts_tree.currentItem()
        isSample: bool = False
        isContact: bool = False
        hasPosition: bool = False
        if isinstance(item, TableContactItem):
            isContact = True
            hasPosition = item.hasPosition()
        if isinstance(item, TableSampleItem):
            isSample = True
        self.assignButton.setEnabled(isContact)
        self.moveButton.setEnabled(hasPosition)
        self.calculateButton.setEnabled(isSample)
        self.resetButton.setEnabled(isContact)

    @QtCore.pyqtSlot()
    def on_pick_position(self) -> None:
        item = self.contacts_tree.currentItem()
        if isinstance(item, TableContactItem):
            def callback(x, y, z):
                item.setPosition(Position(x, y, z))
                self.contacts_tree.resizeColumns()
            self.position_picked.emit(callback)

    @QtCore.pyqtSlot()
    def on_reset(self) -> None:
        item = self.contacts_tree.currentItem()
        if isinstance(item, TableContactItem):
            item.setPosition(Position())
            self.contacts_tree.resizeColumns()

    @QtCore.pyqtSlot()
    def on_reset_all(self) -> None:
        if showQuestion("Do you want to reset all contact positions?"):
            for sampleItem in self.contacts_tree.sampleItems():
                for contactItem in sampleItem.contactItems():
                    contactItem.setPosition(Position())
            self.contacts_tree.resizeColumns()

    @QtCore.pyqtSlot()
    def moveToPosition(self) -> None:
        item = self.contacts_tree.currentItem()
        if isinstance(item, TableContactItem):
            if item.hasPosition():
                if showQuestion(f"Do you want to move table to contact {item.name()}?"):
                    self.absolute_move.emit(item.position())

    @QtCore.pyqtSlot()
    def on_calculate(self) -> None:
        item = self.contacts_tree.currentItem()
        if isinstance(item, TableSampleItem):
            item.calculatePositions()

    def load_samples(self, sample_items) -> None:
        self.contacts_tree.clear()
        for sample in sample_items:
            self.contacts_tree.addSample(sample)
        self.contacts_tree.resizeColumns()

    def update_samples(self) -> None:
        for sampleItem in self.contacts_tree.sampleItems():
            sampleItem.updateContacts()

    def isLocked(self) -> bool:
        return self.property("locked") == True

    def setLocked(self, locked: bool) -> None:
        self.setProperty("locked", locked)
        if locked:
            self.assignButton.setEnabled(False)
            self.moveButton.setEnabled(False)
            self.calculateButton.setEnabled(False)
            self.resetButton.setEnabled(False)
            self.resetAllButton.setEnabled(False)
        else:
            self.update_button_states()
            self.resetAllButton.setEnabled(True)


class TablePositionItem(QtWidgets.QTreeWidgetItem):

    def __init__(self) -> None:
        super().__init__()
        self.setTextAlignment(1, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(2, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setTextAlignment(3, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)  # type: ignore
        self.setPosition(Position())

    def __lt__(self, other):
        if isinstance(other, self(type)):
            return self.name() < other.name()
        return super().__lt__(other)

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def position(self) -> Position:
        return self._position

    def setPosition(self, position: Position) -> None:
        x, y, z = position
        self._position = Position(x, y, z)
        self.setText(1, format(x, ".3f"))
        self.setText(2, format(y, ".3f"))
        self.setText(3, format(z, ".3f"))

    def comment(self) -> str:
        return self.text(4)

    def setComment(self, comment: str) -> None:
        self.setText(4, comment)


class PositionDialog(QtWidgets.QDialog):

    position_picked = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.nameLabel: QtWidgets.QLabel = QtWidgets.QLabel("Name", self)

        self.nameLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("Unnamed", self)
        self.nameLineEdit.setToolTip("Position name")

        self.xLabel: QtWidgets.QLabel = QtWidgets.QLabel("X", self)

        self.xSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.xSpinBox.setToolTip("Position X coordinate")
        self.xSpinBox.setRange(0, 1000)
        self.xSpinBox.setDecimals(3)
        self.xSpinBox.setSuffix(" mm")

        self.yLabel: QtWidgets.QLabel = QtWidgets.QLabel("Y", self)

        self.ySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.ySpinBox.setToolTip("Position Y coordinate")
        self.ySpinBox.setRange(0, 1000)
        self.ySpinBox.setDecimals(3)
        self.ySpinBox.setSuffix(" mm")

        self.zLabel: QtWidgets.QLabel = QtWidgets.QLabel("Z", self)

        self.zSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zSpinBox.setToolTip("Position Z coordinate")
        self.zSpinBox.setRange(0, 1000)
        self.zSpinBox.setDecimals(3)
        self.zSpinBox.setSuffix(" mm")

        self.commentLabel: QtWidgets.QLabel = QtWidgets.QLabel("Comment", self)

        self.commentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.commentLineEdit.setToolTip("Optional position comment")

        self.assignPositionButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.assignPositionButton.setText("Assign Position")
        self.assignPositionButton.setToolTip("Assign current table position.")
        self.assignPositionButton.clicked.connect(self.assignPosition)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.nameLabel, 0, 0, 1, 5)
        layout.addWidget(self.nameLineEdit, 1, 0, 1, 5)
        layout.addWidget(self.xLabel, 2, 0)
        layout.addWidget(self.xSpinBox, 3, 0)
        layout.addWidget(self.yLabel, 2, 1)
        layout.addWidget(self.ySpinBox, 3, 1)
        layout.addWidget(self.zLabel, 2, 2)
        layout.addWidget(self.zSpinBox, 3, 2)
        layout.addWidget(self.assignPositionButton, 3, 4)
        layout.addWidget(self.commentLabel, 4, 0, 1, 5)
        layout.addWidget(self.commentLineEdit, 5, 0, 1, 5)
        layout.addWidget(self.buttonBox, 7, 0, 1, 5)
        layout.setColumnStretch(3, 1)
        layout.setRowStretch(6, 1)

    def name(self) -> str:
        return self.nameLineEdit.text()

    def setName(self, name: str) -> None:
        self.nameLineEdit.setText(name)

    def position(self) -> Position:
        x: float = self.xSpinBox.value()
        y: float = self.ySpinBox.value()
        z: float = self.zSpinBox.value()
        return Position(x, y, z)

    def setPosition(self, position: Position) -> None:
        self.xSpinBox.setValue(position.x)
        self.ySpinBox.setValue(position.y)
        self.zSpinBox.setValue(position.z)

    def comment(self) -> str:
        return self.commentLineEdit.text()

    def setComment(self, comment: str) -> None:
        self.commentLineEdit.setText(comment)

    @QtCore.pyqtSlot()
    def assignPosition(self) -> None:
        def callback(x, y, z):
            self.setPosition(Position(x, y, z))
        self.position_picked.emit(callback)


class TablePositionsWidget(QtWidgets.QWidget):

    position_picked = QtCore.pyqtSignal(object)
    absolute_move = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.positionsTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.positionsTreeWidget.setHeaderLabels(["Name", "X", "Y", "Z", "Comment"])
        self.positionsTreeWidget.setRootIsDecorated(False)
        self.positionsTreeWidget.currentItemChanged.connect(self.currentItemChanged)
        self.positionsTreeWidget.doubleClicked.connect(self.itemDoubleClicked)

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

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.positionsTreeWidget, 0, 0, 5, 1)
        layout.addWidget(self.moveButton, 0, 1)
        layout.addWidget(self.addButton, 2, 1)
        layout.addWidget(self.editButton, 3, 1)
        layout.addWidget(self.removeButton, 4, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)

    def positionItems(self) -> List[TablePositionItem]:
        items: List[TablePositionItem] = []
        for index in range(self.positionsTreeWidget.topLevelItemCount()):
            item = self.positionsTreeWidget.topLevelItem(index)
            if isinstance(item, TablePositionItem):
                items.append(item)
        return items

    def resizeColumns(self) -> None:
        self.positionsTreeWidget.resizeColumnToContents(0)
        self.positionsTreeWidget.resizeColumnToContents(1)
        self.positionsTreeWidget.resizeColumnToContents(2)
        self.positionsTreeWidget.resizeColumnToContents(3)

    def readSettings(self):
        self.positionsTreeWidget.clear()
        for position in settings.table_positions():
            item = TablePositionItem()
            item.setName(position.name)
            item.setPosition(Position(position.x, position.y, position.z))
            item.setComment(position.comment)
            self.positionsTreeWidget.addTopLevelItem(item)
        self.resizeColumns()

    def writeSettings(self):
        positions = []
        for item in self.positionItems():
            name = item.name()
            x, y, z = item.position()
            comment = item.comment()
            positions.append(TablePosition(
                name=name,
                x=x,
                y=y,
                z=z,
                comment=comment,
            ))
        settings.set_table_positions(positions)

    def isLocked(self) -> bool:
        return self.property("locked") == True

    def setLocked(self, locked: bool) -> None:
        self.setProperty("locked", locked)
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

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def currentItemChanged(self, current, previous) -> None:
        enabled = current is not None
        self.editButton.setEnabled(True)
        self.removeButton.setEnabled(True)
        self.moveButton.setEnabled(True)

    @QtCore.pyqtSlot()
    def itemDoubleClicked(self):
        if not self.isLocked():
            self.moveToPosition()

    @QtCore.pyqtSlot(object)
    def assignPosition(self, callback):
        self.position_picked.emit(callback)

    @QtCore.pyqtSlot()
    def addPosition(self):
        dialog = PositionDialog(self)
        dialog.position_picked.connect(self.assignPosition)
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            name = dialog.name()
            position = dialog.position()
            comment = dialog.comment()
            item = TablePositionItem()
            item.setName(name)
            item.setPosition(position)
            item.setComment(comment)
            self.positionsTreeWidget.addTopLevelItem(item)
            self.resizeColumns()

    @QtCore.pyqtSlot()
    def editPosition(self):
        item = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            dialog = PositionDialog(self)
            dialog.position_picked.connect(self.assignPosition)
            dialog.setName(item.name())
            dialog.setPosition(item.position())
            dialog.setComment(item.comment())
            dialog.exec()
            if dialog.result() == dialog.Accepted:
                item.setName(dialog.name())
                item.setPosition(dialog.position())
                item.setComment(dialog.comment())
                self.resizeColumns()

    @QtCore.pyqtSlot()
    def removePosition(self):
        item = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            if showQuestion(f"Do you want to remove position {item.name()!r}?"):
                index = self.positionsTreeWidget.indexOfTopLevelItem(item)
                self.positionsTreeWidget.takeTopLevelItem(index)
                if not self.positionsTreeWidget.topLevelItemCount():
                    self.editButton.setEnabled(False)
                    self.removeButton.setEnabled(False)
                self.resizeColumns()

    @QtCore.pyqtSlot()
    def moveToPosition(self):
        item = self.positionsTreeWidget.currentItem()
        if isinstance(item, TablePositionItem):
            if showQuestion(f"Do you want to move table to position {item.name()!r}?"):
                self.absolute_move.emit(item.position())


class StepSizeButton(QtWidgets.QRadioButton):

    def stepSize(self) -> float:
        return self.property("stepSize") or 0.

    def setStepSize(self, size: float) -> None:
        self.setProperty("stepSize", size)
        label = format_metric((size * comet.ureg("mm")).to("m").m, "m", decimals=1)
        self.setText(label)
        self.setToolTip(f"Move in {label} steps.")

    def stepColor(self) -> str:
        return self.property("stepColor") or "black"

    def setStepColor(self, color: str) -> None:
        self.setProperty("stepColor", color)
        self.setStyleSheet(f"QRadioButton:enabled{{color:{color};}}")


class AlignmentDialog(QtWidgets.QDialog):

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

    def __init__(self, process: AlternateTableProcess, lcr_process, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Alignment")
        self.process: AlternateTableProcess = process
        self.current_position = Position()

        # Control

        self.xUpButton: QtWidgets.QPushButton = QtWidgets.QPushButton("+X", self)
        self.xUpButton.setFixedSize(32, 32)
        self.xUpButton.clicked.connect(self.on_add_x)

        self.xDownButton: QtWidgets.QPushButton = QtWidgets.QPushButton("-X", self)
        self.xDownButton.setFixedSize(32, 32)
        self.xDownButton.clicked.connect(self.on_sub_x)

        self.yUpButton: QtWidgets.QPushButton = QtWidgets.QPushButton("+Y", self)
        self.yUpButton.setFixedSize(32, 32)
        self.yUpButton.clicked.connect(self.on_add_y)

        self.yDownButton: QtWidgets.QPushButton = QtWidgets.QPushButton("-Y", self)
        self.yDownButton.setFixedSize(32, 32)
        self.yDownButton.clicked.connect(self.on_sub_y)

        self.zUpButton: QtWidgets.QPushButton = QtWidgets.QPushButton("+Z", self)
        self.zUpButton.setFixedSize(32, 32)
        self.zUpButton.clicked.connect(self.on_add_z)

        self.zDownButton: QtWidgets.QPushButton = QtWidgets.QPushButton("-Z", self)
        self.zDownButton.setFixedSize(32, 32)
        self.zDownButton.clicked.connect(self.on_sub_z)

        self.stepUpButton: QtWidgets.QPushButton = QtWidgets.QPushButton("↑⇵", self)
        self.stepUpButton.setFixedSize(32, 32)
        self.stepUpButton.setToolTip("Step up, move single step up then double step down and double step up (experimental).")
        self.stepUpButton.clicked.connect(self.on_step_up)

        self.controlButtons: List = [
            self.xUpButton,
            self.xDownButton,
            self.yUpButton,
            self.yDownButton,
            self.zUpButton,
            self.zDownButton,
            self.stepUpButton
        ]

        self.controlGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.controlGroupBox.setTitle("Control")

        controlGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.controlGroupBox)
        controlGroupBoxLayout.addWidget(self.yDownButton, 2, 1)
        controlGroupBoxLayout.addWidget(self.xDownButton, 1, 2)
        controlGroupBoxLayout.addWidget(self.xUpButton, 3, 2)
        controlGroupBoxLayout.addWidget(self.yUpButton, 2, 3)
        controlGroupBoxLayout.addWidget(self.zUpButton, 1, 5)
        controlGroupBoxLayout.addWidget(self.stepUpButton, 1, 6)
        controlGroupBoxLayout.addWidget(self.zDownButton, 3, 5)
        controlGroupBoxLayout.setRowStretch(0, 1)
        controlGroupBoxLayout.setRowStretch(4, 1)
        controlGroupBoxLayout.setColumnStretch(0, 1)
        controlGroupBoxLayout.setColumnStretch(7, 1)

        # Step size

        self.stepSizeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepSizeGroupBox.setTitle("Step Size")

        self.stepSizeGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.stepSizeGroupBox)

        # Create movement radio buttons
        self.stepSizeButtons: List[StepSizeButton] = []
        for item in self.load_table_step_sizes():
            step_size = (item.get("step_size") * comet.ureg("um")).to("mm").m
            step_color = item.get("step_color", "black")
            button = StepSizeButton(self)
            button.setStepSize(step_size)
            button.setStepColor(step_color)
            button.setChecked(len(self.stepSizeButtons) == 0)
            button.toggled.connect(self.onStepToggled)
            self.stepSizeButtons.append(button)
            self.stepSizeGroupBoxLayout.addWidget(button)
        self.stepSizeGroupBoxLayout.addStretch()

        # LCR readings

        self.lcrPrimLabel: QtWidgets.QLabel = QtWidgets.QLabel("Cp", self)

        self.lcrPrimLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrPrimLineEdit.setReadOnly(True)

        self.lcrSecLabel: QtWidgets.QLabel = QtWidgets.QLabel("Rp", self)

        self.lcrSecLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrSecLineEdit.setReadOnly(True)

        self.lcrWidget = ContactQualityWidget(self)
        self.lcrWidget.setMinimumSize(320, 100)

        self.lcrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("Contact Quality (LCR)")
        self.lcrGroupBox.setCheckable(True)
        self.lcrGroupBox.setChecked(False)
        self.lcrGroupBox.toggled.connect(self.setLCREnabled)

        lcrGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.lcrGroupBox)
        lcrGroupBoxLayout.addWidget(self.lcrPrimLabel)
        lcrGroupBoxLayout.addWidget(self.lcrPrimLineEdit, 0, 1)
        lcrGroupBoxLayout.addWidget(self.lcrSecLabel)
        lcrGroupBoxLayout.addWidget(self.lcrSecLineEdit, 1, 1)
        lcrGroupBoxLayout.addWidget(self.lcrWidget, 2, 0, 1, 2)

        # Lights

        self.probecardLightButton = ToggleButton(self)
        self.probecardLightButton.setText("PC Light")
        self.probecardLightButton.setToolTip("Toggle probe card light")
        self.probecardLightButton.setEnabled(False)
        self.probecardLightButton.toggled.connect(self.probecardLightToggled.emit)

        self.microscopeLightButton = ToggleButton(self)
        self.microscopeLightButton.setText("Mic Light")
        self.microscopeLightButton.setToolTip("Toggle microscope light")
        self.microscopeLightButton.setEnabled(False)
        self.microscopeLightButton.toggled.connect(self.microscopeLightToggled.emit)

        self.boxLightButton = ToggleButton(self)
        self.boxLightButton.setText("Box Light")
        self.boxLightButton.setToolTip("Toggle box light")
        self.boxLightButton.setEnabled(False)
        self.boxLightButton.toggled.connect(self.boxLightToggled.emit)

        self.lightsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lightsGroupBox.setTitle("Lights")

        lightsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.lightsGroupBox)
        lightsGroupBoxLayout.addWidget(self.probecardLightButton)
        lightsGroupBoxLayout.addWidget(self.microscopeLightButton)
        lightsGroupBoxLayout.addWidget(self.boxLightButton)
        lightsGroupBoxLayout.addStretch()

        # Positions

        self.positionWidget = PositionWidget(self)

        self.calibrationWidget = CalibrationWidget(self)

        self.zLimitLabel = PositionLabel(self)

        self.xHardLimitLabel = PositionLabel(self)

        self.yHardLimitLabel = PositionLabel(self)

        self.zHardLimitLabel = PositionLabel(self)

        self.laserLabel = SwitchLabel(self)

        topLayout = QtWidgets.QHBoxLayout()
        topLayout.addWidget(self.controlGroupBox)
        topLayout.addWidget(self.stepSizeGroupBox)
        topLayout.addWidget(self.lcrGroupBox)
        topLayout.addWidget(self.lightsGroupBox)
        topLayout.addStretch()

        self.softLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.softLimitsGroupBox.setTitle("Soft Limits")

        softLimitsGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.softLimitsGroupBox)
        softLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 0)
        softLimitsGroupBoxLayout.addWidget(self.zLimitLabel, 0, 1)

        self.hardLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hardLimitsGroupBox.setTitle("Hard Limits")

        hardLimitsGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.hardLimitsGroupBox)
        hardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        hardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 1, 0)
        hardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 2, 0)
        hardLimitsGroupBoxLayout.addWidget(self.xHardLimitLabel, 0, 1)
        hardLimitsGroupBoxLayout.addWidget(self.yHardLimitLabel, 1, 1)
        hardLimitsGroupBoxLayout.addWidget(self.zHardLimitLabel, 2, 1)

        self.safetyGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.safetyGroupBox.setTitle("Safety")

        safetyGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.safetyGroupBox)
        safetyGroupBoxLayout.addWidget(QtWidgets.QLabel("Laser Sensor"), 0, 0)
        safetyGroupBoxLayout.addWidget(self.laserLabel, 0, 1)

        rightLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        rightLayout.addWidget(self.positionWidget)
        rightLayout.addWidget(self.calibrationWidget)
        rightLayout.addWidget(self.softLimitsGroupBox)
        rightLayout.addWidget(self.hardLimitsGroupBox)
        rightLayout.addWidget(self.safetyGroupBox)
        rightLayout.addStretch()

        # Move tab

        self.positionsWidget: TablePositionsWidget = TablePositionsWidget(self)
        self.positionsWidget.setEnabled(False)
        self.positionsWidget.position_picked.connect(self.assignPosition)
        self.positionsWidget.absolute_move.connect(self.moveToPosition)

        # Contacts tab

        self.contactsWidget: TableContactsWidget = TableContactsWidget(self)
        self.contactsWidget.setEnabled(False)
        self.contactsWidget.position_picked.connect(self.assignPosition)
        self.contactsWidget.absolute_move.connect(self.moveToPosition)

        # Calibrate tab

        self.calibrateButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.calibrateButton.setText("Calibrate")
        self.calibrateButton.clicked.connect(self.startCalibration)

        self.calibrateLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.calibrateLabel.setText(
            "Calibrate table by moving into cal/rm switches\nof every axis in"
            " a safe manner to protect the probe card."
        )

        self.calibrateGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.calibrateGroupBox.setTitle("Table Calibration")

        calibrateGroupBoxLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.calibrateGroupBox)
        calibrateGroupBoxLayout.addWidget(self.calibrateButton)
        calibrateGroupBoxLayout.addWidget(self.calibrateLabel)
        calibrateGroupBoxLayout.addStretch()

        self.calibrateWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        calibrateWidgetLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.calibrateWidget)
        calibrateWidgetLayout.addWidget(self.calibrateGroupBox)
        calibrateWidgetLayout.addStretch()

        # Options tab

        self.updateIntervalSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.updateIntervalSpinBox.setRange(0.5, 10.0)
        self.updateIntervalSpinBox.setDecimals(2)
        self.updateIntervalSpinBox.setSingleStep(0.25)
        self.updateIntervalSpinBox.setSuffix(" s")

        self.intervalGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.intervalGroupBox.setTitle("Update Interval")

        intervalGroupBoxLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.intervalGroupBox)
        intervalGroupBoxLayout.addWidget(self.updateIntervalSpinBox)
        intervalGroupBoxLayout.addStretch()

        self.dodgeHeightSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.dodgeHeightSpinBox.setToolTip("Doge height in microns.")
        self.dodgeHeightSpinBox.setRange(0, 10_000)
        self.dodgeHeightSpinBox.setSuffix(" um")

        self.dodgeGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.dodgeGroupBox.setTitle("X/Y Dodge")
        self.dodgeGroupBox.setToolTip("Enables -/+ Z dodge for XY movements.")
        self.dodgeGroupBox.setCheckable(True)

        dodgeGroupBoxLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.dodgeGroupBox)
        dodgeGroupBoxLayout.addWidget(QtWidgets.QLabel("Height"))
        dodgeGroupBoxLayout.addWidget(self.dodgeHeightSpinBox)
        dodgeGroupBoxLayout.addStretch()

        self.lcrResetOnMoveCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.lcrResetOnMoveCheckBox.setText("Reset graph on X/Y move")

        self.contactQualityGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.contactQualityGroupBox.setTitle("Contact Quality (LCR)")

        contactQualityGroupBoxlayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.contactQualityGroupBox)
        contactQualityGroupBoxlayout.addWidget(self.lcrResetOnMoveCheckBox)
        contactQualityGroupBoxlayout.addStretch()

        self.lcrUpdateIntervalSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.lcrUpdateIntervalSpinBox.setRange(0, 1000)
        self.lcrUpdateIntervalSpinBox.setSingleStep(25)
        self.lcrUpdateIntervalSpinBox.setSuffix(" ms")

        self.lcrMatrixChannelsLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.stepUpDelaySpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.stepUpDelaySpinBox.setRange(0, 1_000)
        self.stepUpDelaySpinBox.setSingleStep(25)
        self.stepUpDelaySpinBox.setSuffix(" ms")

        self.stepUpMultiplySpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.stepUpMultiplySpinBox.setRange(1, 10)
        self.stepUpMultiplySpinBox.setSingleStep(1)
        self.stepUpMultiplySpinBox.setSuffix(" x")

        self.stepUpGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepUpGroupBox.setTitle("Step Up (↑⇵)")

        stepUpGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.stepUpGroupBox)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Delay"), 0, 0)
        stepUpGroupBoxLayout.addWidget(QtWidgets.QLabel("Multiplicator (⇵)"), 1, 0)
        stepUpGroupBoxLayout.addWidget(self.stepUpDelaySpinBox, 0, 1)
        stepUpGroupBoxLayout.addWidget(self.stepUpMultiplySpinBox, 1, 1)
        stepUpGroupBoxLayout.setColumnStretch(2, 1)

        self.lcrOptionsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrOptionsGroupBox.setTitle("Contact Quality (LCR)")

        lcrOptionsGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.lcrOptionsGroupBox)
        lcrOptionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Reading Interval"), 0, 0)
        lcrOptionsGroupBoxLayout.addWidget(QtWidgets.QLabel("Matrix Channels"), 1, 0)
        lcrOptionsGroupBoxLayout.addWidget(self.lcrUpdateIntervalSpinBox, 0, 1)
        lcrOptionsGroupBoxLayout.addWidget(self.lcrMatrixChannelsLineEdit, 1, 1, 1, 2)
        lcrOptionsGroupBoxLayout.setColumnStretch(2, 1)

        self.optionsWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        optionsWidgetLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.optionsWidget)
        optionsWidgetLayout.addWidget(self.intervalGroupBox, 0, 0)
        optionsWidgetLayout.addWidget(self.dodgeGroupBox, 0, 1)
        optionsWidgetLayout.addWidget(self.contactQualityGroupBox, 0, 2)
        optionsWidgetLayout.addWidget(self.stepUpGroupBox, 1, 0, 1, 3)
        optionsWidgetLayout.addWidget(self.lcrOptionsGroupBox, 2, 0, 1, 3)
        optionsWidgetLayout.setRowStretch(3, 1)
        optionsWidgetLayout.setColumnStretch(2, 1)

        # Tabs

        self.tabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.positionsWidget, "Move")
        self.tabWidget.addTab(self.contactsWidget, "Contacts")
        self.tabWidget.addTab(self.calibrateWidget, "Calibrate")
        self.tabWidget.addTab(self.optionsWidget, "Options")

        # Button box

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
        self.closeButton.clicked.connect(self.reject)

        self.buttonBoxLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self.buttonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonBoxLayout.addWidget(self.progressBar)
        self.buttonBoxLayout.addWidget(self.messageLabel)
        self.buttonBoxLayout.addStretch()
        self.buttonBoxLayout.addWidget(self.stopButton)
        self.buttonBoxLayout.addWidget(self.closeButton)

        # Layout

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addLayout(topLayout, 0, 0)
        layout.addWidget(self.tabWidget, 1, 0)
        layout.addLayout(rightLayout, 0, 1, 2, 1)
        layout.addLayout(self.buttonBoxLayout, 2, 0, 1, 2)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)

        # Initialize

        self.setPosition(Position())
        self.reset_caldone()
        self.update_limits()
        self.reset_safety()
        self.update_control_buttons()

        self.lcr_process = lcr_process
        self.lcr_process.finished = self.on_lcr_finished
        self.lcr_process.failed = self.on_lcr_failed
        self.lcr_process.reading = self.on_lcr_reading

        self.process.message_changed.connect(self.setMessage)
        self.process.progress_changed.connect(self.setProgress)
        self.process.position_changed.connect(self.setPosition)
        self.process.caldone_changed.connect(self.update_caldone)
        self.process.relative_move_finished.connect(self.setMoveFinished)
        self.process.absolute_move_finished.connect(self.setMoveFinished)
        self.process.calibration_finished.connect(self.on_calibration_finished)
        self.process.stopped.connect(self.on_calibration_finished)

        self.updateIntervalSpinBox.valueChanged.connect(self.onUpdateIntervalChange)  # TODO

    def step_width(self) -> float:
        """Current selected step size in mm."""
        for button in self.stepSizeButtons:
            if button.isChecked():
                return abs(button.stepSize())
        return 0.

    def step_color(self) -> str:
        """Color for current selected step size."""
        for button in self.stepSizeButtons:
            if button.isChecked():
                return button.stepColor()
        return "black"

    def updateInterval(self) -> float:
        return self.updateIntervalSpinBox.value()

    def setUpdateInterval(self, interval: float) -> None:
        self.updateIntervalSpinBox.setValue(interval)

    def isDodgeEnabled(self) -> bool:
        return self.dodgeGroupBox.isChecked()

    def setDodgeEnabled(self, enabled: bool) -> None:
        self.dodgeGroupBox.setChecked(enabled)

    def dodgeHeight(self) -> float:
        return (self.dodgeHeightSpinBox.value() * comet.ureg("um")).to("mm").m

    def setDodgeHeight(self, height: float) -> None:
        self.dodgeHeightSpinBox.setValue((height * comet.ureg("mm")).to("um").m)

    def isLcrResetOnMove(self) -> bool:
        return self.lcrResetOnMoveCheckBox.isChecked()

    def setLcrResetOnMove(self, enabled: bool) -> None:
        self.lcrResetOnMoveCheckBox.setChecked(enabled)

    def stepUpDelay(self) -> float:
        """Return step up delay in seconds."""
        return (self.stepUpDelaySpinBox.value() * comet.ureg("ms")).to("s").m

    def setStepUpDelay(self, delay: float) -> None:
        self.stepUpDelaySpinBox.setValue((delay * comet.ureg("s")).to("ms").m)

    def stepUpMultiply(self) -> int:
        """Return step up delay in seconds."""
        return int(self.stepUpMultiplySpinBox.value())

    def setStepUpMultiply(self, count: int) -> None:
        self.stepUpMultiplySpinBox.setValue(count)

    def lcrUpdateInterval(self) -> float:
        """LCR update interval in seconds."""
        return (self.lcrUpdateIntervalSpinBox.value() * comet.ureg("ms")).to("s").m

    def setLcrUpdateInterval(self, interval: float) -> None:
        self.lcrUpdateIntervalSpinBox.setValue((interval * comet.ureg("s")).to("ms").m)

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

    def load_table_step_sizes(self):
        return settings.value("table_step_sizes", self.default_steps, list)

    def setPosition(self, position: Position) -> None:
        self.current_position = position
        self.positionWidget.setPosition(position)
        self.update_limits()
        self.update_control_buttons()
        if math.isfinite(position.z):
            self.lcrWidget.setLimits(position.z)
            self.lcrWidget.setLine(position.z)

    def reset_caldone(self):
        self.calibrationWidget.reset()

    def update_caldone(self, position):
        self.current_caldone = position
        self.positionsWidget.setEnabled(caldone_valid(position))
        self.contactsWidget.setEnabled(caldone_valid(position))
        self.controlGroupBox.setEnabled(caldone_valid(position))
        self.calibrationWidget.setCalibration(position)

    def update_limits(self):
        x, y, z = self.current_position
        self.zLimitLabel.setStyleSheet("")
        if not math.isnan(z):
            if z >= self.z_limit:
                self.zLimitLabel.setStyleSheet("QLabel:enabled{color:red}")

    def reset_safety(self):
        self.laserLabel.setValue(None)

    def update_safety(self, laser_sensor):
        self.laserLabel.setValue(laser_sensor)

    def update_control_buttons(self):
        x, y, z = self.current_position
        self.update_x_buttons(x)
        self.update_y_buttons(y)
        self.update_z_buttons(z)
        for button in self.controlButtons:
            color = self.step_color()
            button.setStyleSheet(f"QPushButton:enabled{{color:{color}}}")

    def update_x_buttons(self, x):
        x_enabled = True
        if not math.isnan(x):
            if (x - self.step_width()) < 0:
                x_enabled = False
        self.xDownButton.setEnabled(x_enabled)

    def update_y_buttons(self, y):
        y_enabled = True
        if not math.isnan(y):
            if (y - self.step_width()) < 0:
                y_enabled = False
        self.yDownButton.setEnabled(y_enabled)

    def update_z_buttons(self, z):
        # Disable move up button for large step sizes
        z_enabled = False
        if not math.isnan(z):
            if (z + self.step_width()) <= self.z_limit:
                z_enabled = True
            else:
                z_enabled = self.step_width() <= self.maximum_z_step_size
        self.zUpButton.setEnabled(z_enabled)
        step_up_limit = comet.ureg("10.0 um").to("mm").m
        self.stepUpButton.setEnabled(z_enabled and (self.step_width() <= step_up_limit))  # TODO

    def relative_move_xy(self, x, y):
        # Dodge on X/Y movements.
        if self.dodge_enabled:
            dodge_height = self.dodgeHeight()
            current_position = self.current_position
            if current_position.z < dodge_height:
                dodge_height = max(0, current_position.z)
            vector = [(0, 0, -dodge_height), (x, y, 0), (0, 0, +dodge_height)]
        else:
            vector = [(x, y, 0)]
        # Clear contact quality graph on X/Y movements.
        if self.isLcrResetOnMove():
            self.lcrWidget.clear()
        self.process.relative_move_vector(vector)
        # Clear contact quality graph on X/Y movements.
        if self.isLcrResetOnMove():
            self.lcrWidget.clear()

    def on_add_x(self):
        self.setLocked(True)
        self.relative_move_xy(+self.step_width(), 0)

    def on_sub_x(self):
        self.setLocked(True)
        self.relative_move_xy(-self.step_width(), 0)

    def on_add_y(self):
        self.setLocked(True)
        self.relative_move_xy(0, +self.step_width())

    def on_sub_y(self):
        self.setLocked(True)
        self.relative_move_xy(0, -self.step_width())

    def on_add_z(self):
        self.setLocked(True)
        self.process.relative_move(0, 0, +self.step_width())

    def on_sub_z(self):
        self.setLocked(True)
        self.process.relative_move(0, 0, -self.step_width())

    def on_step_up(self):
        self.setLocked(True)
        step_width = self.step_width()
        multiply = self.stepUpMultiply()
        vector = (
            [0, 0, +step_width],
            [0, 0, -step_width * multiply],
            [0, 0, +step_width * multiply],
        )
        self.process.relative_move_vector(vector, delay=self.stepUpDelay())

    @QtCore.pyqtSlot()
    def onStepToggled(self) -> None:
        logger.info("set table step width to %.3f mm", self.step_width())
        self.update_control_buttons()

    def setProbecardLightEnabled(self, enabled: bool) -> None:
        self.probecardLightButton.setChecked(enabled)

    def setMicroscopeLightEnabled(self, enabled: bool) -> None:
        self.microscopeLightButton.setChecked(enabled)

    def setBoxLightEnabled(self, enabled: bool) -> None:
        self.boxLightButton.setChecked(enabled)

    def setLightsEnabled(self, enabled: bool) -> None:
        self.probecardLightButton.setEnabled(enabled)
        self.microscopeLightButton.setEnabled(enabled)
        self.boxLightButton.setEnabled(enabled)

    @QtCore.pyqtSlot()
    def setMoveFinished(self) -> None:
        self.progressBar.setVisible(False)
        self.stopButton.setEnabled(False)
        self.setLocked(False)

    def on_calibration_finished(self) -> None:
        self.progressBar.setVisible(False)
        self.stopButton.setEnabled(False)
        self.setLocked(False)

    @QtCore.pyqtSlot(str)
    def setMessage(self, message: str) -> None:
        self.messageLabel.setText(message)

    @QtCore.pyqtSlot(int, int)
    def setProgress(self, value: int, maximum: int) -> None:
        self.progressBar.setMaximum(maximum)
        self.progressBar.setValue(value)
        self.progressBar.setVisible(True)

    @QtCore.pyqtSlot(float)
    def onUpdateIntervalChange(self, interval: float) -> None:
        self.process.update_interval = interval

    @QtCore.pyqtSlot(object)
    def assignPosition(self, callback) -> None:
        x, y, z = self.current_position
        callback(x, y, z)

    @QtCore.pyqtSlot(Position)
    def moveToPosition(self, position) -> None:
        # Update to safe Z position
        position = Position(position.x, position.y, safe_z_position(position.z))
        self.setLocked(True)
        # Clear contact quality graph on X/Y movements.
        self.lcrWidget.clear()
        self.stopButton.setEnabled(True)
        x, y, z = position
        self.process.safe_absolute_move(x, y, z)

    @QtCore.pyqtSlot()
    def startCalibration(self) -> None:
        self.setLocked(True)
        self.stopButton.setEnabled(True)
        self.process.calibrate_table()

    @QtCore.pyqtSlot()
    def requestStop(self) -> None:
        self.stopButton.setEnabled(False)
        self.process.stop_current_action()

    def load_samples(self, sample_items):
        self.contactsWidget.load_samples(sample_items)

    def update_samples(self):
        self.contactsWidget.update_samples()

    def readSettings(self) -> None:
        self.positionsWidget.readSettings()
        self.z_limit = settings.table_z_limit()
        self.zLimitLabel.setValue(self.z_limit)
        x, y, z = settings.table_probecard_maximum_limits()
        self.xHardLimitLabel.setValue(x)
        self.yHardLimitLabel.setValue(y)
        self.zHardLimitLabel.setValue(z)
        self.setStepUpDelay(settings.value("tablecontrol_step_up_delay", DEFAULT_STEP_UP_DELAY, float))
        self.setStepUpMultiply(settings.value("tablecontrol_step_up_multiply", DEFAULT_STEP_UP_MULTIPLY, int))
        self.setLcrUpdateInterval(settings.value("tablecontrol_lcr_update_delay", DEFAULT_LCR_UPDATE_INTERVAL, float))
        matrix_channels = settings.value("tablecontrol_lcr_matrix_channels", DEFAULT_MATRIX_CHANNELS, list)
        self.setLcrMatrixChannels(matrix_channels)
        self.lcr_process.update_interval = self.lcrUpdateInterval()
        self.lcr_process.matrix_channels = self.lcrMatrixChannels()
        self.setUpdateInterval(settings.value("table_control_update_interval", 1.0, float))
        self.setDodgeEnabled(settings.value("table_control_dodge_enabled", False, bool))
        self.setDodgeHeight(settings.tableControlDodgeHeight())
        self.setLcrResetOnMove(settings.value("tablecontrol_lcr_reset_on_move", True, bool))

        _settings = QtCore.QSettings()
        _settings.beginGroup("AlignmentDialog")
        geometry = _settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        _settings.endGroup()

        if not self.restoreGeometry(geometry):
            self.resize(800, 600)

    def writeSettings(self) -> None:
        settings.setValue("tablecontrol_step_up_delay", self.stepUpDelay())
        settings.setValue("tablecontrol_step_up_multiply", self.stepUpMultiply())
        settings.setValue("tablecontrol_lcr_update_delay", self.lcrUpdateInterval())
        settings.setValue("tablecontrol_lcr_matrix_channels", self.lcrMatrixChannels())
        self.positionsWidget.writeSettings()
        settings.setValue("table_control_update_interval", self.updateInterval())
        settings.setValue("table_control_dodge_enabled", self.isDodgeEnabled())
        settings.setTableControlDodgeHeight(self.dodgeHeight())
        settings.setValue("tablecontrol_lcr_reset_on_move", self.isLcrResetOnMove())

        geometry = self.saveGeometry()
        _settings = QtCore.QSettings()
        _settings.beginGroup("AlignmentDialog")
        _settings.setValue("geometry", geometry)
        _settings.endGroup()

    def setLocked(self, locked: bool) -> None:
        self.positionsWidget.setLocked(locked)
        self.contactsWidget.setLocked(locked)
        self.controlGroupBox.setEnabled(not locked)
        self.closeButton.setEnabled(not locked)
        self.progressBar.setVisible(locked)
        self.progressBar.setRange(0, 0)
        self.progressBar.setValue(0)

    @QtCore.pyqtSlot(bool)
    def setLCREnabled(self, enabled: bool) -> None:
        self.lcrPrimLineEdit.setEnabled(enabled)
        self.lcrSecLineEdit.setEnabled(enabled)
        self.lcrWidget.setEnabled(enabled)
        try:
            if enabled:
                self.lcrWidget.clear()
                self.lcr_process.set("matrix_instrument", settings.matrix_instrument)
                self.lcr_process.update_interval = self.lcrUpdateInterval()
                self.lcr_process.matrix_channels = self.lcrMatrixChannels()
                self.lcr_process.start()
            else:
                self.lcr_process.stop()
        except Exception as exc:
            logger.exception(exc)
            showException(exc)

    def on_lcr_finished(self):
        ...

    def on_lcr_failed(self, exc, tb=None) -> None:
        self.lcrPrimLineEdit.setText("ERROR")
        self.lcrSecLineEdit.setText("ERROR")

    def on_lcr_reading(self, prim, sec) -> None:
        self.lcrPrimLineEdit.setText(format_metric(prim, unit="F"))
        self.lcrSecLineEdit.setText(format_metric(sec, unit="Ohm"))
        _, _, z = self.current_position
        if math.isfinite(z) and math.isfinite(sec):
            # Append only absolute Rp readings
            self.lcrWidget.append(z, abs(sec))
            self.lcrWidget.setLine(z)


class SwitchLabel(QtWidgets.QLabel):

    def value(self) -> Optional[bool]:
        return self.property("value")

    def setValue(self, value: Optional[bool]) -> None:
        self.setProperty("value", value)
        if value is None:
            self.setText(format(float("nan")))
            self.setStyleSheet("")
        else:
            self.setText(format_switch(value))
            self.setStyleSheet("QLabel:enabled{color:green}" if value else "QLabel:enabled{color:red}")
