import copy
import logging
import math
import os
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.config import list_configs, load_sequence
from ..settings import settings as config
from ..utils import from_table_unit, to_table_unit

from .components import (
    OperatorWidget,
    PositionsComboBox,
    WorkingDirectoryWidget,
)
from .quickedit import QuickEditDialog

__all__ = [
    "StartSequenceDialog",
    "SequenceTreeWidget",
]

logger = logging.getLogger(__name__)


class StartSequenceDialog(QtWidgets.QDialog):
    """Start sequence dialog."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start Sequence")

        self.contactCheckBox = QtWidgets.QCheckBox(self)
        self.contactCheckBox.setText("Move table and contact with Probe Card")
        self.contactCheckBox.setChecked(True)

        self.positionCheckBox = QtWidgets.QCheckBox(self)
        self.positionCheckBox.setText("Move table after measurements")
        self.positionCheckBox.setChecked(False)
        self.positionCheckBox.toggled.connect(self.onpositionCheckBox_toggled)

        self.positionsComboBox = PositionsComboBox(self)
        self.positionsComboBox.setEnabled(False)

        self.operatorWidget: OperatorWidget = OperatorWidget(self)

        self.outputWidget = WorkingDirectoryWidget(self)
        self.outputWidget.setTitle("Working Directory")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Yes).setAutoDefault(False)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.No).setDefault(True)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.messageLabel = QtWidgets.QLabel(self)

        self.tableGroupBox = QtWidgets.QGroupBox(self)
        self.tableGroupBox.setTitle("Table")

        tableGroupBoxLayout = QtWidgets.QGridLayout(self.tableGroupBox)
        tableGroupBoxLayout.addWidget(self.contactCheckBox, 0, 0, 1, 2)
        tableGroupBoxLayout.addWidget(self.positionCheckBox, 1, 0)
        tableGroupBoxLayout.addWidget(self.positionsComboBox, 1, 1)
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.messageLabel, 0, 0, 1, 2)
        layout.addWidget(self.tableGroupBox, 1, 0, 1, 2)
        layout.addWidget(self.operatorWidget, 2, 0)
        layout.addWidget(self.outputWidget, 2, 1)
        layout.addWidget(self.buttonBox, 3, 0, 1, 2)
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 3)
        layout.setRowStretch(0, 1)

    def setMessage(self, message: str) -> None:
        self.messageLabel.setText(message)

    def setTableEnabled(self, enabled: bool) -> None:
        self.contactCheckBox.setEnabled(enabled)
        self.positionCheckBox.setEnabled(enabled)

    def readSettings(self) -> None:
        self.contactCheckBox.setChecked(bool(config.settings.get("move_to_contact") or False))
        self.positionCheckBox.setChecked(bool(config.settings.get("move_on_success") or False))
        self.positionsComboBox.readSettings()
        self.operatorWidget.readSettings()
        self.outputWidget.readSettings()

    def writeSettings(self) -> None:
        config.settings["move_to_contact"] = self.contactCheckBox.isChecked()
        config.settings["move_on_success"] = self.positionCheckBox.isChecked()
        self.positionsComboBox.writeSettings()
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()

    def onpositionCheckBox_toggled(self, state: bool) -> None:
        self.positionsComboBox.setEnabled(state)

    def isMoveToContact(self) -> bool:
        return self.contactCheckBox.isChecked()

    def isMoveToPosition(self) -> Optional[tuple]:
        if self.isMoveToContact() and self.positionCheckBox.isChecked():
            index = self.positionsComboBox.currentIndex()
            table_positions = config.table_positions
            if 0 <= index < len(table_positions):
                position = table_positions[index]
                return position.x, position.y, position.z
        return None


class SequenceTreeWidget(QtWidgets.QTreeWidget):
    """Sequence tree containing sample, contact and measurement items."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setExpandsOnDoubleClick(False)
        self.setHeaderLabels(["Name", "Pos", "State"])
        self.header().setMinimumSectionSize(32)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTreeWidget.InternalMove)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, position) -> None:
        item = self.itemAt(position)
        if item:
            contextMenu = QtWidgets.QMenu(self)

            # Enable Default

            def recursiveEnableDefault(item):
                for child in item.children():
                    if hasattr(child, "isEnabledDefault"):
                        child.setEnabled(child.isEnabledDefault())
                    recursiveEnableDefault(child)

            def enableDefault():
                recursiveEnableDefault(item)

            if item.childCount():
                action = contextMenu.addAction("Enable Default")
                action.triggered.connect(enableDefault)

            # Enable Failed

            def recursiveEnableFailed(item):
                for child in item.children():
                    enabled = child.state() in [
                        child.StoppedState,
                        child.ComplianceState,
                        child.TimeoutState,
                        child.ErrorState,
                        child.AnalysisErrorState,
                    ]
                    child.setEnabled(enabled)
                    recursiveEnableFailed(child)

            def enableFailed():
                recursiveEnableFailed(item)

            if item.childCount():
                action = contextMenu.addAction("Enable Only Failed")
                action.triggered.connect(enableFailed)

            # Disable All

            def recursiveDisableItem(item):
                for child in item.children():
                    child.setEnabled(False)
                    recursiveDisableItem(child)

            def disableAll():
                recursiveDisableItem(item)

            if item.childCount():
                contextMenu.addSeparator()
                action = contextMenu.addAction("Disable All")
                action.triggered.connect(disableAll)

            contextMenu.exec(self.viewport().mapToGlobal(position))

    def addSampleItem(self, item) -> None:
        self.addTopLevelItem(item)

    def addGroupItem(self, item) -> None:
        self.addTopLevelItem(item)

    def sequenceItems(self) -> list:
        """Return list of all top level sequence items."""
        items: list = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            if isinstance(item, SequenceTreeItem):
                items.append(item)
        return items

    def sampleItemsOnly(self) -> list:
        """Return a flattend list of all samples."""
        items: list = []

        def sample_items(parent):
            for index in range(parent.childCount()):
                child = parent.child(index)
                if isinstance(child, GroupTreeItem):
                    sample_items(child)
                elif isinstance(child, SampleTreeItem):
                    items.append(child)

        sample_items(self.invisibleRootItem())
        return items

    def setLocked(self, locked: bool) -> None:
        for item in self.sequenceItems():
            item.setLocked(locked)

    def reset(self) -> None:
        for item in self.sequenceItems():
            item.reset()

    def resizeColumns(self) -> None:
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)


class SequenceRootTreeItem:  #  TODO
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, iterable):
        self._children = []
        self._extend(iterable)

    def childCount(self):
        return len(self._children)

    def children(self):
        return list(self._children)

    def addChild(self, item):
        self._children.append(item)

    def _extend(self, iterable):
        for item in iterable:
            self.addChild(item)


class SequenceTreeItem(QtWidgets.QTreeWidgetItem):

    ProcessingState = "Processing..."
    ActiveState = "Active"
    SuccessState = "Success"
    ComplianceState = "Compliance"
    TimeoutState = "Timeout"
    ErrorState = "Error"
    StoppedState = "Stopped"
    AnalysisErrorState = "AnalysisError"

    def __init__(self) -> None:
        super().__init__()
        self.item_type: str = ""
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsDragEnabled)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsDropEnabled)
        self.setCheckable(True)
        self.setEnabled(False)
        self.setEnabledDefault(False)

    def children(self):
        items = []
        for index in range(self.childCount()):
            items.append(self.child(index))
        return items

    def isChecked(self, column: int) -> bool:
        return self.checkState(column) == QtCore.Qt.Checked

    def setChecked(self, column: int, state: bool) -> None:
        self.setCheckState(column, QtCore.Qt.Checked if state else QtCore.Qt.Unchecked)

    def isCheckable(self) -> bool:
        """Checkable state, `True` if item is checkable by user."""
        return (self.flags() & QtCore.Qt.ItemIsUserCheckable) != 0

    def setCheckable(self, checkable: bool) -> None:
        flags = self.flags()
        if checkable:
            flags |= QtCore.Qt.ItemIsUserCheckable
        else:
            flags &= ~QtCore.Qt.ItemIsUserCheckable
        self.setFlags(flags)

    def hasPosition(self) -> bool:
        return False

    def isSelectable(self) -> bool:
        return (self.flags() & QtCore.Qt.ItemIsSelectable) != 0

    def setSelectable(self, selectable: bool) -> None:
        flags = self.flags()
        if selectable:
            flags |= QtCore.Qt.ItemIsSelectable
        else:
            flags &= ~QtCore.Qt.ItemIsSelectable
        self.setFlags(flags)

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def isEnabled(self) -> bool:
        return self.isChecked(0)

    def setEnabled(self, enabled: bool) -> None:
        self.setChecked(0, enabled)

    def isEnabledDefault(self) -> bool:
        return self._is_enabled_default

    def setEnabledDefault(self, state: bool) -> None:
        self._is_enabled_default = state

    def state(self) -> str:
        return self.data(2, 0x2000)

    def setState(self, value) -> None:
        if value is None:
            value = ""
        self.setForeground(0, QtGui.QBrush())
        if value == self.SuccessState:
            green = QtGui.QBrush(QtGui.QColor("green"))
            self.setForeground(2, green)
        elif value in (self.ActiveState, self.ProcessingState):
            blue = QtGui.QBrush(QtGui.QColor("blue"))
            self.setForeground(0, blue)
            self.setForeground(2, blue)
        else:
            red = QtGui.QBrush(QtGui.QColor("red"))
            self.setForeground(2, red)
        self.setText(2, format(value))
        self.setData(2, 0x2000, value)

    # Methods

    def setLocked(self, locked: bool) -> None:
        self.setCheckable(not locked)
        self.setSelectable(not locked)
        for child in self.children():
            child.setLocked(locked)

    def reset(self):
        self.setState(None)
        for child in self.children():
            child.reset()


class GroupTreeItem(SequenceTreeItem):

    def __init__(self) -> None:
        super().__init__()
        self.item_type = "group"
        self.setFlags(self.flags() | QtCore.Qt.ItemIsDragEnabled)
        self.setFlags(self.flags() | QtCore.Qt.ItemIsDropEnabled)

    def from_settings(self, **kwargs) -> None:
        self.setName(kwargs.get("group_name", ""))
        self.setEnabled(kwargs.get("group_enabled", False))
        for sample_kwargs in kwargs.get("group_samples", []):
            sample_item = SampleTreeItem()
            sample_item.from_settings(**sample_kwargs)
            self.addChild(sample_item)
            self.setExpanded(True)

    def to_settings(self) -> dict:
        group_samples = []
        for sample in self.children():
            group_samples.append(sample.to_settings())
        return {
            "group_name": self.name(),
            "group_enabled": self.isEnabled(),
            "group_samples": group_samples,
        }


class SampleTreeItem(SequenceTreeItem):
    """Sample (halfmoon) item of sequence tree."""

    def __init__(self) -> None:
        super().__init__()
        self.item_type = "sample"
        self.setFlags(self.flags() | QtCore.Qt.ItemIsDragEnabled)
        self._namePrefix: str = ""
        self._nameInfix: str = ""
        self._nameSuffix: str = ""
        self._sampleType: str = ""
        self._sampleComment: str = ""
        self.update_name()
        self.setEnabled(False)
        self.setEnabledDefault(False)
        self.sequence = None

    # Properties

    @property
    def sequence_filename(self):
        return self.sequence.filename if self.sequence else None

    def name(self) -> str:
        return "".join((self._namePrefix, self._nameInfix, self._nameSuffix)).strip()

    def namePrefix(self) -> str:
        return self._namePrefix

    def setNamePrefix(self, prefix: str) -> None:
        self._namePrefix = prefix
        self.update_name()

    def nameInfix(self) -> str:
        return self._nameInfix

    def setNameInfix(self, infix: str) -> None:
        self._nameInfix = infix
        self.update_name()

    def nameSuffix(self) -> str:
        return self._nameSuffix

    def setNameSuffix(self, suffix: str) -> None:
        self._nameSuffix = suffix
        self.update_name()

    def sampleType(self) -> str:
        return self._sampleType

    def setSampleType(self, type: str) -> None:
        self._sampleType = type
        self.update_name()

    def samplePositionLabel(self) -> str:
        return self.text(1)

    def setSamplePositionLabel(self, label: str) -> None:
        self.setText(1, label)

    def comment(self) -> str:
        return self._sampleComment

    def setComment(self, comment: str):
        self._sampleComment = comment

    # Settings

    def from_settings(self, **kwargs):
        self.setNamePrefix(kwargs.get("sample_name_prefix") or "")
        self.setNameInfix(kwargs.get("sample_name_infix") or kwargs.get("sample_name") or "Unnamed")
        self.setNameSuffix(kwargs.get("sample_name_suffix") or "")
        self.update_name()
        self.setSampleType(kwargs.get("sample_type") or "")
        self.setSamplePositionLabel(kwargs.get("sample_position") or "")
        self.setComment(kwargs.get("sample_comment") or "")
        self.setEnabled(kwargs.get("sample_enabled") or False)
        filename = kwargs.get("sample_sequence_filename")
        if filename and os.path.exists(filename):
            sequence = load_sequence(filename)
            self.load_sequence(sequence)
        default_position = float("nan"), float("nan"), float("nan")
        for contact_position in kwargs.get("sample_contacts") or []:
            for contact in self.children():
                if contact.id == contact_position.get("id"):
                    try:
                        x, y, z = tuple(map(from_table_unit, contact_position.get("position")))
                    except Exception:
                        ...
                    else:
                        contact.position = x, y, z
                    finally:
                        break

    def to_settings(self) -> dict:
        sample_contacts = []
        for contact in self.children():
            if contact.hasPosition():
                sample_contacts.append({
                    "id": contact.id,
                    "position": tuple(map(to_table_unit, contact.position))
                })
        return {
            "sample_name_prefix": self.namePrefix(),
            "sample_name_infix": self.nameInfix(),
            "sample_name_suffix": self.nameSuffix(),
            "sample_type": self.sampleType(),
            "sample_position": self.samplePositionLabel(),
            "sample_comment": self.comment(),
            "sample_enabled": self.isEnabled(),
            "sample_sequence_filename": self.sequence_filename,
            "sample_contacts": sample_contacts
        }

    # Methods

    def update_name(self):
        tokens = [self.name(), self.sampleType()]
        self.setText(0, "/".join((token for token in tokens if token)))

    def reset_positions(self):
        for contact_item in self.children():
            contact_item.reset_position()

    def load_sequence(self, sequence):
        # Store contact positions
        contact_positions = {}
        for contact_item in self.children():
            if contact_item.hasPosition():
                contact_positions[contact_item.id] = contact_item.position
        while len(self.children()):
            self.takeChild(0)
        self.sequence = sequence
        for contact in sequence.contacts:
            item = self.addChild(ContactTreeItem(self, contact))
        # Restore contact positions
        for contact_item in self.children():
            if contact_item.id in contact_positions:
                contact_item.position = contact_positions.get(contact_item.id)


class ContactTreeItem(SequenceTreeItem):
    """Contact (flute) item of sequence tree."""

    def __init__(self, sample, contact):
        super().__init__()
        self.item_type = "contact"
        self.sample = sample
        self.id = contact.id
        self.setName(contact.name)
        self.setEnabled(contact.enabled)
        self.setEnabledDefault(contact.enabled)
        self._is_enabled_default = contact.enabled
        self.contact_id = contact.contact_id
        self.setDescription(contact.description)
        self.reset_position()
        for measurement in contact.measurements:
            self.addChild(MeasurementTreeItem(self, measurement))

    def description(self) -> str:
        return self._description

    def setDescription(self, description: str) -> None:
        self._description = description

    # Properties

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, position):
        x, y, z = position
        self.__position = x, y, z
        self.setText(1, {False: "", True: "OK"}.get(self.hasPosition()))

    def hasPosition(self) -> bool:
        return any((not math.isnan(value) for value in self.__position))

    # Methods

    def reset_position(self):
        self.position = float("nan"), float("nan"), float("nan")


class MeasurementTreeItem(SequenceTreeItem):
    """Measurement item of sequence tree."""

    def __init__(self, contact, measurement):
        super().__init__()
        self.item_type = measurement.type
        self.contact = contact
        self.id = measurement.id
        self.setName(measurement.name)
        self.setEnabled(measurement.enabled)
        self.setEnabledDefault(measurement.enabled)
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.setTags(measurement.tags)
        self.setDescription(measurement.description)
        self.series = {}
        self.analysis = {}

    def tags(self) -> list:
        return list(self._tags)

    def setTags(self, tags: list) -> None:
        self._tags = [format(tag) for tag in tags]

    def description(self) -> str:
        return self._description

    def setDescription(self, description: str) -> None:
        self._description = description

    def reset(self):
        super().reset()
        self.series.clear()
        self.analysis.clear()


class EditSamplesDialog:
    """Quick edit all samples at once dialog."""

    def __init__(self, items, sequences):
        self.items = items
        self.sequences = sequences

    def populate_dialog(self, dialog):
        for sample_item in self.items:
            item = dialog.addItem()
            item.setEnabled(sample_item.isEnabled())
            item.setPrefix(sample_item.namePrefix())
            item.setInfix(sample_item.nameInfix())
            item.setSuffix(sample_item.nameSuffix())
            item.setType(sample_item.sampleType())
            item.setPositionLabel(sample_item.samplePositionLabel())
            for name, filename in self.sequences:
                item.addSequence(name)
            if sample_item.sequence is not None:
                item.setCurrentSequence(sample_item.sequence.name)
            item.setProperty("sample_item", sample_item)

    def update_samples(self, dialog):
        progress = QtWidgets.QProgressDialog()
        progress.setLabelText("Updating sequence...")
        progress.setMaximum(len(dialog.items()))
        progress.setCancelButton(None)

        def callback():
            sequence_cache: dict = {}
            for item in dialog.items():
                progress.setValue(progress.value() + 1)
                sample_item = item.property("sample_item")
                sample_item.setEnabled(item.isEnabled())
                sample_item.setNamePrefix(item.prefix())
                sample_item.setNameInfix(item.infix())
                sample_item.setNameSuffix(item.suffix())
                sample_item.setSampleType(item.type())
                sample_item.setSamplePositionLabel(item.positionLabel())
                for name, filename in self.sequences:
                    if item.currentSequence() == name:
                        if filename not in sequence_cache:
                            sequence = load_sequence(filename)
                            sequence_cache[filename] = sequence
                        sequence = sequence_cache[filename]
                        sample_item.load_sequence(sequence)
            progress.close()

        QtCore.QTimer.singleShot(200, callback)
        progress.exec()

    def run(self):
        dialog = QuickEditDialog()
        dialog.readSettings()
        self.populate_dialog(dialog)
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            self.update_samples(dialog)
        dialog.writeSettings()
