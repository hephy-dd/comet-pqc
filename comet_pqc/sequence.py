import copy
import logging
import math
import os
from typing import List

from PyQt5 import QtCore, QtWidgets
import qutie as ui
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


class StartSequenceDialog(QtWidgets.QDialog, SettingsMixin):
    """Start sequence dialog."""

    def __init__(self, context, table_enabled, parent: QtWidgets.QWidget = None) -> None:
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

        self.positionsComboBox = PositionsComboBox()
        self.positionsComboBox.qt.setEnabled(False)

        self.operatorComboBox = OperatorWidget()

        self.outputComboBox = WorkingDirectoryWidget()

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
        tableLayout.addWidget(self.positionsComboBox.qt, 1, 1)
        tableLayout.setRowStretch(2, 1)

        operatorLayout = QtWidgets.QVBoxLayout(self.operatorGroupBox)
        operatorLayout.addWidget(self.operatorComboBox.qt)

        outputLayout = QtWidgets.QVBoxLayout(self.outputGroupBox)
        outputLayout.addWidget(self.outputComboBox.qt)

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
        self.positionsComboBox.qt.setEnabled(state)

    # Methods

    def isMoveToContact(self) -> bool:
        return self.contactCheckBox.isChecked()

    def isMoveToPosition(self):
        if self.isMoveToContact() and self.positionCheckBox.isChecked():
            current = self.positionsComboBox.current
            if current:
                index = self.positionsComboBox.index(current)
                positions = settings.table_positions
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


class SequenceManagerTreeItem(ui.TreeItem):

    def __init__(self, sequence, filename, builtin) -> None:
        super().__init__([sequence.name, "(built-in)" if builtin else filename])
        self.sequence = sequence
        self.sequence.builtin = builtin
        self.qt.setToolTip(1, filename)


class SequenceManager(QtWidgets.QDialog, SettingsMixin):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sequence Manager")
        self.resize(640, 480)

        self._sequence_tree = ui.Tree(
            header=("Name", "Filename"),
            indentation=0,
            selected=self.loadSequencePreview
        )

        self.addButton = QtWidgets.QPushButton(self)
        self.addButton.setText("&Add")
        self.addButton.clicked.connect(self.addSequenceItem)

        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("&Remove")
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.removeSequenceItem)

        self._preview_tree = ui.Tree(header=["Key", "Value"])

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.addWidget(self._sequence_tree.qt, 3)
        leftLayout.addWidget(self._preview_tree.qt, 4)

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
        item = self._sequence_tree.current
        if item is not None:
            return item.sequence
        return None

    def sequenceFilenames(self):
        filenames = []
        for sequence_item in self._sequence_tree:
            filenames.append(sequence_item.sequence.filename)
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
        self._sequence_tree.clear()
        for name, filename, builtin in load_all_sequences(self.settings):
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                logger.exception(exc)
                logger.error("failed to load sequence: %s", filename)
            else:
                item = SequenceManagerTreeItem(sequence, filename, builtin)
                self._sequence_tree.append(item)
        self._sequence_tree.fit()
        if len(self._sequence_tree):
            self._sequence_tree.current = self._sequence_tree[0]

    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManager")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()

        self.writeSettingsSequences()

    def writeSettingsSequences(self):
        """Store custom sequences to settings."""
        sequences = []
        for item in self._sequence_tree:
            if isinstance(item, SequenceManagerTreeItem):
                if not item.sequence.builtin:
                    sequences.append(item.sequence.filename)
        self.settings["custom_sequences"] = list(set(sequences))

    # Callbacks

    def loadSequencePreview(self, item):
        """Load sequence config preview."""
        self.removeButton.setEnabled(False)
        self._preview_tree.clear()
        if isinstance(item, SequenceManagerTreeItem):
            self.removeButton.setEnabled(not item.sequence.builtin)
            if os.path.exists(item.sequence.filename):
                with open(item.sequence.filename) as f:
                    data = yaml.safe_load(f)
                    def append(item, key, value):
                        """Recursively append items."""
                        if isinstance(value, dict):
                            child = item.append([key])
                            for key, value in value.items():
                                append(child, key, value)
                        elif isinstance(value, list):
                            child = item.append([key])
                            for i, obj in enumerate(value):
                                if isinstance(obj, dict):
                                    for key, value in obj.items():
                                        append(child, key, value)
                                else:
                                    append(child, f"[{i}]", obj)
                            child.expanded = True
                        else:
                            item.append([key, value])
                            item.expanded = True
                    for key, value in data.items():
                        append(self._preview_tree, key, value)
                    self._preview_tree.fit()

    def addSequenceItem(self) -> None:
        filename = ui.filename_open(filter="YAML files (*.yml, *.yaml);;All files (*)")
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                show_exception(exc)
            else:
                if filename not in self.sequenceFilenames():
                    item = SequenceManagerTreeItem(sequence, filename, False)
                    self._sequence_tree.append(item)
                    self._sequence_tree.current = item

    def removeSequenceItem(self) -> None:
        item = self._sequence_tree.current
        if isinstance(item, SequenceManagerTreeItem):
            if not item.sequence.builtin:
                result = QtWidgets.QMessageBox.question(
                    self,
                    "Remove Sequence",
                    f"Do yo want to remove sequence {item.sequence.name!r}?"
                )
                if result == QtWidgets.QMessageBox.Yes:
                    self._sequence_tree.remove(item)
                    self.removeButton.setEnabled(len(self._sequence_tree) > 0)


class SequenceTree(ui.Tree):
    """Sequence tree containing sample, contact and measurement items."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.expands_on_double_click = False
        self.header = ["Name", "Pos", "State"]
        # Qt5 Tweaks
        self.qt.header().setMinimumSectionSize(32)
        self.qt.header().resizeSection(1, 32)

    # Methods

    def setLocked(self, state: bool) -> None:
        for contact in self:
            contact.setLocked(state)

    def reset(self):
        for contact in self:
            contact.reset()


class SamplesItem:
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, iterable):
        self.children: List = []
        self.extend(iterable)

    def append(self, item):
        self.children.append(item)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)


class SequenceTreeItem(ui.TreeItem):

    ProcessingState = "Processing..."
    ActiveState = "Active"
    SuccessState = "Success"
    ComplianceState = "Compliance"
    TimeoutState = "Timeout"
    ErrorState = "Error"
    StoppedState = "Stopped"
    AnalysisErrorState = "AnalysisError"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkable = True

    # Properties

    @property
    def has_position(self):
        return False

    @property
    def selectable(self):
        return self.qt.flags() & QtCore.Qt.ItemIsSelectable != 0

    @selectable.setter
    def selectable(self, value):
        flags = self.qt.flags()
        if value:
            flags |= QtCore.Qt.ItemIsSelectable
        else:
            flags &= ~QtCore.Qt.ItemIsSelectable
        self.qt.setFlags(flags)

    @property
    def name(self):
        return self[0].value

    @name.setter
    def name(self, value):
        self[0].value = value

    @property
    def enabled(self):
        return self[0].checked

    @enabled.setter
    def enabled(self, enabled):
        self[0].checked = enabled

    @property
    def state(self):
        return self[2].value

    @state.setter
    def state(self, value):
        self[0].bold = (value in (self.ActiveState, self.ProcessingState))
        self[0].color = None
        if value == self.SuccessState:
            self[2].color = "green"
        elif value in (self.ActiveState, self.ProcessingState):
            self[0].color = "blue"
            self[2].color = "blue"
        else:
            self[2].color = "red"
        self[2].value = value

    # Methods

    def setLocked(self, state: bool) -> None:
        self.checkable = not state
        self.selectable = not state
        for child in self.children:
            child.setLocked(state)

    def reset(self):
        self.state = None
        for child in self.children:
            child.reset()


class SampleTreeItem(SequenceTreeItem):
    """Sample (halfmoon) item of sequence tree."""

    type = "sample"

    def __init__(self, name_prefix=None, name_infix=None, name_suffix=None,
                 sample_type=None, sample_position=None, enabled=False, comment=None):
        super().__init__()
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
    def sample_position(self):
        return self._sample_position

    @sample_position.setter
    def sample_position(self, value):
        self._sample_position = value.strip()
        self[1].value = value.strip()

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
        self[0].value = "/".join((token for token in tokens if token))

    def reset_positions(self):
        for contact_item in self.children:
            contact_item.reset_position()

    def load_sequence(self, sequence):
        # Store contact positions
        contact_positions = {}
        for contact_item in self.children:
            if contact_item.has_position:
                contact_positions[contact_item.id] = contact_item.position
        while len(self.children):
            self.qt.takeChild(0)
        self.sequence = sequence
        for contact in sequence.contacts:
            item = self.append(ContactTreeItem(self, contact))
        # Restore contact positions
        for contact_item in self.children:
            if contact_item.id in contact_positions:
                contact_item.position = contact_positions.get(contact_item.id)


class ContactTreeItem(SequenceTreeItem):
    """Contact (flute) item of sequence tree."""

    type = "contact"

    def __init__(self, sample, contact):
        super().__init__([contact.name, None])
        self.sample = sample
        self.id = contact.id
        self.name = contact.name
        self.enabled = contact.enabled
        self.contact_id = contact.contact_id
        self.description = contact.description
        self.reset_position()
        for measurement in contact.measurements:
            self.append(MeasurementTreeItem(self, measurement))

    # Properties

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, position):
        x, y, z = position
        self.__position = x, y, z
        self[1].value = {False: "", True: "OK"}.get(self.has_position)

    @property
    def has_position(self):
        return any((not math.isnan(value) for value in self.__position))

    # Methods

    def reset_position(self):
        self.position = float("nan"), float("nan"), float("nan")


class MeasurementTreeItem(SequenceTreeItem):
    """Measurement item of sequence tree."""

    def __init__(self, contact, measurement):
        super().__init__([measurement.name, None])
        self.contact = contact
        self.id = measurement.id
        self.name = measurement.name
        self.type = measurement.type
        self.enabled = measurement.enabled
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.tags = measurement.tags
        self.description = measurement.description
        self.series = {}
        self.analysis = {}

    def reset(self) -> None:
        super().reset()
        self.series.clear()
        self.analysis.clear()


class EditSamplesDialog(SettingsMixin):
    """Quick edit all samples at once dialog."""

    def __init__(self, sequence_tree, sequences):
        self.sequence_tree = sequence_tree
        self.sequences = sequences

    def populateDialog(self, dialog):
        for sample_item in self.sequence_tree:
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
