import copy
import logging
import math
import os
from typing import Dict, List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
import yaml

from comet.settings import SettingsMixin

from .components import (
    OperatorWidget,
    PositionsComboBox,
    WorkingDirectoryWidget,
)
from .core.config import SEQUENCE_DIR, list_configs, load_sequence
from .quickedit import QuickEditDialog, QuickEditItem
from .settings import settings
from .utils import from_table_unit, to_table_unit, show_exception

__all__ = ["StartSequenceDialog", "SequenceManager", "SequenceTree"]

logger = logging.getLogger(__name__)


def load_all_sequences(settings):
    configs = []
    for name, filename in list_configs(SEQUENCE_DIR):
        configs.append((name, filename, True))
    for filename in list(set(settings.get("custom_sequences") or [])):
        if os.path.exists(filename):
            try:
                sequence = load_sequence(filename)
            except Exception:
                ...
            else:
                configs.append((sequence.name, filename, False))
    return configs


def appendItem(item, key, value):
    """Recursively append items to tree."""
    if isinstance(value, dict):
        child = QtWidgets.QTreeWidgetItem()
        child.setData(0, QtCore.Qt.DisplayRole, key)
        if isinstance(item, QtWidgets.QTreeWidgetItem):
            item.addChild(child)
        else:
            item.addTopLevelItem(child)
        for key, value in value.items():
            appendItem(child, key, value)
    elif isinstance(value, list):
        child = QtWidgets.QTreeWidgetItem()
        child.setData(0, QtCore.Qt.DisplayRole, key)
        if isinstance(item, QtWidgets.QTreeWidgetItem):
            item.addChild(child)
        else:
            item.addTopLevelItem(child)
        for i, obj in enumerate(value):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    appendItem(child, key, value)
            else:
                appendItem(child, f"[{i}]", obj)
        child.setExpanded(True)
    else:
        child = QtWidgets.QTreeWidgetItem()
        child.setData(0, QtCore.Qt.DisplayRole, key)
        child.setData(1, QtCore.Qt.DisplayRole, value)
        if isinstance(item, QtWidgets.QTreeWidgetItem):
            item.addChild(child)
        else:
            item.addTopLevelItem(child)
        child.setExpanded(True)


class StartSequenceDialog(QtWidgets.QDialog, SettingsMixin):
    """Start sequence dialog."""

    def __init__(self, context, table_enabled, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start Sequence")

        self.messageLabel = QtWidgets.QLabel(self)
        self.messageLabel.setText(self.createMessage(context))

        self.contactCheckBox = QtWidgets.QCheckBox(self)
        self.contactCheckBox.setText("Move table and contact with Probe Card")
        self.contactCheckBox.setChecked(True)
        self.contactCheckBox.setEnabled(table_enabled)

        self.positionCheckBox = QtWidgets.QCheckBox(self)
        self.positionCheckBox.setText("Move table after measurements")
        self.positionCheckBox.setChecked(False)
        self.positionCheckBox.setEnabled(table_enabled)
        self.positionCheckBox.toggled.connect(self.setPositionsEnabled)

        self.positionsComboBox = PositionsComboBox(self)
        self.positionsComboBox.setEnabled(False)

        self.operatorComboBox = OperatorWidget(self)

        self.outputComboBox = WorkingDirectoryWidget(self)

        self.tableGroupBox = QtWidgets.QGroupBox(self)
        self.tableGroupBox.setTitle("Table")

        self.operatorGroupBox = QtWidgets.QGroupBox(self)
        self.operatorGroupBox.setTitle("Operator")

        self.outputGroupBox = QtWidgets.QGroupBox(self)
        self.outputGroupBox.setTitle("Working Directory")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Yes)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.No)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setAutoDefault(False)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.No).setDefault(True)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        tableLayout = QtWidgets.QGridLayout(self.tableGroupBox)
        tableLayout.addWidget(self.contactCheckBox, 0, 0, 1, 2)
        tableLayout.addWidget(self.positionCheckBox, 1, 0)
        tableLayout.addWidget(self.positionsComboBox, 1, 1)
        tableLayout.setRowStretch(2, 1)

        operatorLayout = QtWidgets.QVBoxLayout(self.operatorGroupBox)
        operatorLayout.addWidget(self.operatorComboBox)

        outputLayout = QtWidgets.QVBoxLayout(self.outputGroupBox)
        outputLayout.addWidget(self.outputComboBox)

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addWidget(self.operatorGroupBox, 2)
        bottomLayout.addWidget(self.outputGroupBox, 3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.messageLabel)
        layout.addWidget(self.tableGroupBox)
        layout.addLayout(bottomLayout)
        layout.addWidget(self.buttonBox)

    # Settings

    def readSettings(self) -> None:
        self.contactCheckBox.setChecked(bool(self.settings.get("move_to_contact") or False))
        self.positionCheckBox.setChecked(bool(self.settings.get("move_on_success") or False))
        self.positionsComboBox.readSettings()
        self.operatorComboBox.readSettings()
        self.outputComboBox.readSettings()

    def writeSettings(self) -> None:
        self.settings["move_to_contact"] = self.contactCheckBox.isChecked()
        self.settings["move_on_success"] = self.positionCheckBox.isChecked()
        self.positionsComboBox.writeSettings()
        self.operatorComboBox.writeSettings()
        self.outputComboBox.writeSettings()

    # Callbacks

    def setPositionsEnabled(self, state: bool) -> None:
        self.positionsComboBox.setEnabled(state)

    # Methods

    def isMoveToContact(self) -> bool:
        return self.contactCheckBox.isChecked()

    def isMoveToPosition(self):
        if self.isMoveToContact() and self.positionCheckBox.isChecked():
            current = self.positionsComboBox.currentText()
            if current:
                index = self.positionsComboBox.index(current)
                positions = settings.tablePositions()
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    # Helpers

    def createMessage(self, context) -> str:
        if isinstance(context, SamplesItem):
            return "<b>Are you sure to start all enabled sequences for all enabled samples?</b>"
        elif isinstance(context, SampleTreeItem):
            return f"<b>Are you sure to start all enabled sequences for {context.name!r}?</b>"
        elif isinstance(context, ContactTreeItem):
            return f"<b>Are you sure to start sequence {context.name!r}?</b>"
        return ""


class SequenceManagerTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, sequence, filename, builtin) -> None:
        super().__init__([sequence.name, "(built-in)" if builtin else filename])
        self.sequence = sequence
        self.builtin = builtin
        self.setToolTip(1, filename)


class SequenceManager(QtWidgets.QDialog, SettingsMixin):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sequence Manager")
        self.resize(640, 480)

        self.sequenceTreeWidget = QtWidgets.QTreeWidget(self)
        self.sequenceTreeWidget.setHeaderLabels(["Name", "Filename"])
        self.sequenceTreeWidget.setRootIsDecorated(False)
        self.sequenceTreeWidget.currentItemChanged.connect(self.loadSequencePreview)

        self.addButton = QtWidgets.QPushButton(self)
        self.addButton.setText("&Add")
        self.addButton.clicked.connect(self.addSequenceItem)

        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("&Remove")
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.removeSequenceItem)

        self.previewTreeWidget = QtWidgets.QTreeWidget(self)
        self.previewTreeWidget.setHeaderLabels(["Key", "Value"])
        self.previewTreeWidget.header().setStretchLastSection(True)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.addWidget(self.sequenceTreeWidget, 3)
        leftLayout.addWidget(self.previewTreeWidget, 4)

        rightLayout = QtWidgets.QVBoxLayout()
        rightLayout.addWidget(self.addButton, 0)
        rightLayout.addWidget(self.removeButton, 0)
        rightLayout.addStretch(1)

        layout = QtWidgets.QGridLayout(self)
        layout.addLayout(leftLayout, 0, 0)
        layout.addLayout(rightLayout, 0, 1)
        layout.addWidget(self.buttonBox, 1, 0, 1, 2)
        layout.setColumnStretch(0, 1)

    def currentSequence(self):
        """Return selected sequence object or None if nothing selected."""
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SequenceManagerTreeItem):
            return item.sequence
        return None

    def sequenceFilenames(self):
        filenames = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            if isinstance(item, SequenceManagerTreeItem):
                filenames.append(item.sequence.filename)
        return filenames

    # Settings

    def readSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManager")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreGeometry(geometry)
        settings.endGroup()

        self.readSettingsSequences()

    def readSettingsSequences(self):
        """Load all built-in and custom sequences from settings."""
        self.sequenceTreeWidget.clear()
        for name, filename, builtin in load_all_sequences(self.settings):
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                logger.exception(exc)
                logger.error("failed to load sequence: %s", filename)
            else:
                item = SequenceManagerTreeItem(sequence, filename, builtin)
                self.sequenceTreeWidget.addTopLevelItem(item)
        self.sequenceTreeWidget.resizeColumnToContents(0)
        if self.sequenceTreeWidget.topLevelItemCount():
            self.sequenceTreeWidget.setCurrentItem(self.sequenceTreeWidget.topLevelItem(0))

    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManager")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()

        self.writeSettingsSequences()

    def writeSettingsSequences(self):
        """Store custom sequences to settings."""
        sequences = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            if isinstance(item, SequenceManagerTreeItem):
                if not item.builtin:
                    sequences.append(item.sequence.filename)
        self.settings["custom_sequences"] = list(set(sequences))

    # Callbacks

    def loadSequencePreview(self, current, previous):
        """Load sequence config preview."""
        self.removeButton.setEnabled(False)
        self.previewTreeWidget.clear()
        if isinstance(current, SequenceManagerTreeItem):
            sequence = current.sequence
            self.removeButton.setEnabled(not current.builtin)
            if os.path.exists(sequence.filename):
                with open(sequence.filename) as f:
                    data = yaml.safe_load(f)
                for key, value in data.items():
                    appendItem(self.previewTreeWidget, key, value)
                self.previewTreeWidget.resizeColumnToContents(0)

    def addSequenceItem(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Sequence",
            "",
            "YAML files (*.yml, *.yaml);;All files (*)",
        )
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                show_exception(exc)
            else:
                if filename not in self.sequenceFilenames():
                    item = SequenceManagerTreeItem(sequence, filename, False)
                    self.sequenceTreeWidget.addTopLevelItem(item)
                    self.sequenceTreeWidget.setCurrentItem(item)
                    self.sequenceTreeWidget.resizeColumnToContents(0)

    def removeSequenceItem(self) -> None:
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SequenceManagerTreeItem):
            if not item.builtin:
                result = QtWidgets.QMessageBox.question(
                    self,
                    "Remove Sequence",
                    f"Do yo want to remove sequence {item.sequence.name!r}?"
                )
                if result == QtWidgets.QMessageBox.Yes:
                    index = self.sequenceTreeWidget.indexOfTopLevelItem(item)
                    self.sequenceTreeWidget.takeTopLevelItem(index)
                    count = self.sequenceTreeWidget.topLevelItemCount()
                    self.removeButton.setEnabled(count > 0)


class SamplesItem:
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, iterable) -> None:
        self.children: List = []
        self.extend(iterable)

    def append(self, item) -> None:
        self.children.append(item)

    def extend(self, iterable) -> None:
        for item in iterable:
            self.append(item)


class SequenceTreeItem(QtWidgets.QTreeWidgetItem):

    IdleState = ""
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
        self.type_name: str = ""
        self.checkable = True

    # Properties

    @property
    def children(self):
        items = []
        for index in range(self.childCount()):
            item = self.child(index)
        return items

    @property
    def checkable(self) -> bool:
        return self.flags() & QtCore.Qt.ItemIsUserCheckable != 0

    @checkable.setter
    def checkable(self, value: bool) -> None:
        if value:
            flags = self.flags() | QtCore.Qt.ItemIsUserCheckable
        else:
            flags = self.flags() & ~QtCore.Qt.ItemIsUserCheckable
        self.setFlags(flags)

    @property
    def has_position(self):
        return False

    @property
    def selectable(self):
        return self.flags() & QtCore.Qt.ItemIsSelectable != 0

    @selectable.setter
    def selectable(self, value):
        flags = self.flags()
        if value:
            flags |= QtCore.Qt.ItemIsSelectable
        else:
            flags &= ~QtCore.Qt.ItemIsSelectable
        self.setFlags(flags)

    @property
    def name(self) -> str:
        return self.text(0)

    @name.setter
    def name(self, name: str) -> None:
        self.setText(0, name)

    @property
    def enabled(self):
        return self.checkState(0) == QtCore.Qt.Checked

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self.setCheckState(0, QtCore.Qt.Checked if enabled else QtCore.Qt.Unchecked)

    @property
    def state(self) -> str:
        return self.text(2)

    @state.setter
    def state(self, state: str) -> None:
        if state in (self.ActiveState, self.ProcessingState):
            self.setNameColor(QtGui.QColor("blue"))
        else:
            self.setNameColor(QtGui.QColor())

        if state == self.SuccessState:
            self.setStateColor(QtGui.QColor("green"))
        elif state in (self.ActiveState, self.ProcessingState):
            self.setStateColor(QtGui.QColor("blue"))
        else:
            self.setStateColor(QtGui.QColor("blue"))

        self.setText(2, state)

    # Methods

    def setNameColor(self, color: QtGui.QColor) -> None:
        brush = self.foreground(0)
        brush.setColor(color)
        self.setForeground(0, brush)

    def setStateColor(self, color: QtGui.QColor) -> None:
        brush = self.foreground(2)
        brush.setColor(color)
        self.setForeground(2, brush)

    def setLocked(self, state: bool) -> None:
        self.checkable = not state
        self.selectable = not state
        for child in self.children:
            child.setLocked(state)

    def reset(self) -> None:
        self.state = type(self).IdleState
        for child in self.children:
            child.reset()


class SampleTreeItem(SequenceTreeItem):
    """Sample (halfmoon) item of sequence tree."""

    def __init__(self, name_prefix=None, name_infix=None, name_suffix=None,
                 sample_type=None, sample_position=None, enabled=False, comment=None) -> None:
        super().__init__()
        self.type_name = "sample"
        self._name_prefix = name_prefix or ""
        self._name_infix = name_infix or ""
        self._name_suffix = name_suffix or ""
        self._sample_type = sample_type or ""
        self.sample_position = sample_position or ""
        self.update_name()
        self.comment = comment or ""
        self.enabled = enabled
        self.sequence = None

    # Properties

    @property
    def sequence_filename(self):
        return self.sequence.filename if self.sequence else None

    @property
    def name(self):
        return "".join((self.name_prefix, self.name_infix, self.name_suffix)).strip()

    @name.setter
    def name(self, _):
        raise AttributeError()

    @property
    def name_prefix(self):
        return self._name_prefix

    @name_prefix.setter
    def name_prefix(self, value):
        self._name_prefix = value
        self.update_name()

    @property
    def name_infix(self):
        return self._name_infix

    @name_infix.setter
    def name_infix(self, value):
        self._name_infix = value
        self.update_name()

    @property
    def name_suffix(self):
        return self._name_suffix

    @name_suffix.setter
    def name_suffix(self, value):
        self._name_suffix = value
        self.update_name()

    @property
    def sample_type(self):
        return self._sample_type.strip()

    @sample_type.setter
    def sample_type(self, value):
        self._sample_type = value
        self.update_name()

    @property
    def sample_position(self) -> str:
        return self._sample_position

    @sample_position.setter
    def sample_position(self, value: str) -> None:
        self._sample_position = value.strip()
        self.setText(1, value.strip())

    @property
    def comment(self):
        return self._sample_comment

    @comment.setter
    def comment(self, value):
        self._sample_comment = value.strip()

    # Settings

    def from_settings(self, **kwargs):
        self._name_prefix = kwargs.get("sample_name_prefix") or ""
        self._name_infix = kwargs.get("sample_name_infix") or kwargs.get("sample_name") or "Unnamed"
        self._name_suffix = kwargs.get("sample_name_suffix") or ""
        self.update_name()
        self.sample_type = kwargs.get("sample_type") or ""
        self.sample_position = kwargs.get("sample_position") or ""
        self.comment = kwargs.get("sample_comment") or ""
        self.enabled = kwargs.get("sample_enabled") or False
        filename = kwargs.get("sample_sequence_filename")
        if filename and os.path.exists(filename):
            sequence = load_sequence(filename)
            self.load_sequence(sequence)
        default_position = float("nan"), float("nan"), float("nan")
        for contact_position in kwargs.get("sample_contacts") or []:
            for contact in self.children:
                if contact.id == contact_position.get("id"):
                    try:
                        x, y, z = tuple(map(from_table_unit, contact_position.get("position")))
                    except Exception:
                        ...
                    else:
                        contact.position = x, y, z
                    finally:
                        break

    def to_settings(self):
        sample_contacts = []
        for contact in self.children:
            if contact.has_position:
                sample_contacts.append({
                    "id": contact.id,
                    "position": tuple(map(to_table_unit, contact.position))
                })
        return {
            "sample_name_prefix": self.name_prefix,
            "sample_name_infix": self.name_infix,
            "sample_name_suffix": self.name_suffix,
            "sample_type": self.sample_type,
            "sample_position": self.sample_position,
            "sample_comment": self.comment,
            "sample_enabled": self.enabled,
            "sample_sequence_filename": self.sequence_filename,
            "sample_contacts": sample_contacts
        }

    # Methods

    def update_name(self):
        tokens = self.name, self.sample_type
        self.setText(0, "/".join((token for token in tokens if token)))

    def reset_positions(self):
        for contact_item in self.children:
            contact_item.reset_position()

    def load_sequence(self, sequence):
        # Store contact positions
        contact_positions = {}
        for contact_item in self.children:
            if contact_item.has_position:
                contact_positions[contact_item.id] = contact_item.position
        while self.children:
            self.takeChild(0)
        self.sequence = sequence
        for contact in sequence.contacts:
            item = ContactTreeItem(self, contact)
            self.addChild(item)
        # Restore contact positions
        for contact_item in self.children:
            if contact_item.id in contact_positions:
                contact_item.position = contact_positions.get(contact_item.id)


class ContactTreeItem(SequenceTreeItem):
    """Contact (flute) item of sequence tree."""

    def __init__(self, sample, contact) -> None:
        super().__init__()
        self.type_name = "contact"
        self.sample = sample
        self.id = contact.id
        self.name = contact.name
        self.enabled = contact.enabled
        self.contact_id = contact.contact_id
        self.description = contact.description
        self.reset_position()
        for measurement in contact.measurements:
            self.addChild(MeasurementTreeItem(self, measurement))

    # Properties

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, position):
        x, y, z = position
        self.__position = x, y, z
        text = value = {False: "", True: "OK"}.get(self.has_position)
        self.setText(1, text)

    @property
    def has_position(self) -> bool:
        return any((not math.isnan(value) for value in self.__position))

    # Methods

    def reset_position(self) -> None:
        self.position = float("nan"), float("nan"), float("nan")


class MeasurementTreeItem(SequenceTreeItem):
    """Measurement item of sequence tree."""

    def __init__(self, contact, measurement) -> None:
        super().__init__()
        self.contact = contact
        self.id = measurement.id
        self.name = measurement.name
        self.type_name = measurement.type
        self.enabled = measurement.enabled
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.tags = measurement.tags
        self.description = measurement.description
        self.series: Dict = {}
        self.analysis: Dict = {}

    def reset(self) -> None:
        super().reset()
        self.series.clear()
        self.analysis.clear()


class SequenceTree(QtWidgets.QTreeWidget):
    """Sequence tree containing sample, contact and measurement items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Name", "Pos", "State"])
        self.header().setMinimumSectionSize(32)
        self.header().resizeSection(1, 32)
        self.setExpandsOnDoubleClick(False)

    # Methods

    def sampleItems(self) -> List[SampleTreeItem]:
        items = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            if isinstance(item, SampleTreeItem):
                items.append(item)
        return items

    def setLocked(self, state: bool) -> None:
        for item in self.sampleItems():
            item.setLocked(state)

    def reset(self) -> None:
        for item in self.sampleItems():
            item.reset()

    def resizeColumnsToContent(self) -> None:
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)


class EditSamplesDialog(SettingsMixin):
    """Quick edit all samples at once dialog."""

    def __init__(self, samples, sequences):
        self.samples = samples
        self.sequences = sequences

    def populateDialog(self, dialog):
        for sample_item in self.samples:
            item = QuickEditItem()
            item.setEnabled(sample_item.enabled)
            item.setPrefix(sample_item.name_prefix)
            item.setInfix(sample_item.name_infix)
            item.setSuffix(sample_item.name_suffix)
            item.setType(sample_item.sample_type)
            item.setPosition(sample_item.sample_position)
            for name, filename, builtin in self.sequences:
                item.addSequence(name)
            if sample_item.sequence is not None:
                item.setCurrentSequence(sample_item.sequence.name)
            item.setProperty("sample_item", sample_item)
            dialog.addItem(item)

    def updateSamplesFromDialog(self, dialog):
        for item in dialog.items():
            sample_item = item.property("sample_item")
            sample_item.enabled = item.isEnabled()
            sample_item.name_prefix = item.prefix()
            sample_item.name_infix = item.infix()
            sample_item.name_suffix = item.suffix()
            sample_item.sample_type = item.type()
            sample_item.sample_position = item.position()
            for name, filename, builtin in self.sequences:
                if item.currentSequence() == name:
                    sequence = load_sequence(filename)
                    sample_item.load_sequence(sequence)

    def readSettings(self, dialog):
        width, height = self.settings.get("quick_edit_dialog_size", (800, 480))
        dialog.resize(width, height)

    def writeSettings(self, dialog):
        width, height = dialog.width(), dialog.height()
        self.settings["quick_edit_dialog_size"] = width, height

    def run(self):
        dialog = QuickEditDialog()
        self.readSettings(dialog)
        self.populateDialog(dialog)
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            self.updateSamplesFromDialog(dialog)
        self.writeSettings(dialog)
