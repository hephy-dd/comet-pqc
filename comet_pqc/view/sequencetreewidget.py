import copy
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.config import load_sequence, Sequence
from ..core.position import Position
from ..settings import settings
from ..utils import from_table_unit, to_table_unit
from .components import CheckableItemMixin, SelectableItemMixin

__all__ = ["SequenceTreeWidget"]

SEQUENCE_VERSION = 1

logger = logging.getLogger(__name__)


def load_all_sequences() -> List[Tuple[str, str]]:
    configs: List[Tuple[str, str]] = []
    custom_sequences = settings.value("custom_sequences", [], list)
    for filename in list(set(custom_sequences)):
        if os.path.exists(filename):
            try:
                sequence = load_sequence(filename)
            except Exception:
                ...
            else:
                configs.append((sequence.name, filename))
    return configs


def load_sequence_tree(fp) -> List:
    data = json.load(fp)
    version = data.get("version")
    if version is None:
        raise RuntimeError(f"Missing version information")
    if version != SEQUENCE_VERSION:
        raise RuntimeError(f"Invalid version information")
    return data.get("sequence", [])


def dump_sequence_tree(sequence: List, fp) -> None:
    data = {
        "version": SEQUENCE_VERSION,
        "sequence": sequence,
    }
    json.dump(data, fp)


class SamplesItem:
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, iterable) -> None:
        self._children: List = []
        self.extend(iterable)

    def children(self) -> List:
        return self._children

    def addChild(self, item) -> None:
        self._children.append(item)

    def extend(self, iterable) -> None:
        for item in iterable:
            self.addChild(item)


class SequenceTreeItem(QtWidgets.QTreeWidgetItem, CheckableItemMixin, SelectableItemMixin):

    ProcessingState: str = "Processing..."
    ActiveState: str = "Active"
    SuccessState: str = "Success"
    ComplianceState: str = "Compliance"
    TimeoutState: str = "Timeout"
    ErrorState: str = "Error"
    StoppedState: str = "Stopped"
    AnalysisErrorState: str = "AnalysisError"

    def __init__(self, type: str) -> None:
        super().__init__()
        self.type: str = type  # type: ignore
        self.setCheckable(True)

    # Properties

    def hasPosition(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return self.text(0)

    @name.setter
    def name(self, value) -> None:
        self.setText(0, value)

    def isEnabled(self) -> bool:
        return self.checkState(0) == QtCore.Qt.Checked

    def setEnabled(self, enabled: bool) -> None:
        self.setCheckState(0, QtCore.Qt.Checked if enabled else QtCore.Qt.Unchecked)

    @property
    def state(self):
        return self.text(2)

    @state.setter
    def state(self, value) -> None:
        self.setForeground(0, QtGui.QColor())
        if value == self.SuccessState:
            self.setForeground(2, QtGui.QColor("green"))
        elif value in (self.ActiveState, self.ProcessingState):
            self.setForeground(0, QtGui.QColor("blue"))
            self.setForeground(2, QtGui.QColor("blue"))
        else:
            self.setForeground(2, QtGui.QColor("red"))
        self.setText(2, value)

    # Methods

    def children(self):
        items = []
        for index in range(self.childCount()):
            item = self.child(index)
            items.append(item)
        return items

    def setLocked(self, locked: bool) -> None:
        self.setCheckable(not locked)
        self.setSelectable(not locked)
        for child in self.children():
            child.setLocked(locked)

    def reset(self):
        self.state = None
        for child in self.children():
            child.reset()


class SampleTreeItem(SequenceTreeItem):
    """Sample (halfmoon) item of sequence tree."""

    def __init__(self, name_prefix=None, name_infix=None, name_suffix=None,
                 sample_type=None, sample_position=None, enabled: bool = False, comment: Optional[str] = None) -> None:
        super().__init__("sample")
        self._name_prefix: str = name_prefix or ""
        self._name_infix: str = name_infix or ""
        self._name_suffix: str = name_suffix or ""
        self._sample_type: str = sample_type or ""
        self.sample_position = sample_position or ""
        self.update_name()
        self.setComment(comment or "")
        self.setEnabled(enabled)
        self.sequence: Optional[Sequence] = None

    # Properties

    def sequenceFilename(self) -> str:
        if self.sequence is None:
            return ""
        return self.sequence.filename

    @property  # type: ignore
    def name(self):
        return "".join((self.name_prefix, self.name_infix, self.name_suffix)).strip()

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
        self.setText(1, value.strip())

    def comment(self) -> str:
        return self._sample_comment

    def setComment(self, comment: str) -> None:
        self._sample_comment = comment

    # Settings

    def from_settings(self, **kwargs):
        self._name_prefix = kwargs.get("sample_name_prefix") or ""
        self._name_infix = kwargs.get("sample_name_infix") or kwargs.get("sample_name") or "Unnamed"
        self._name_suffix = kwargs.get("sample_name_suffix") or ""
        self.update_name()
        self.sample_type = kwargs.get("sample_type") or ""
        self.sample_position = kwargs.get("sample_position") or ""
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
                        contact.setPosition(Position(x, y, z))
                    finally:
                        break

    def to_settings(self) -> Dict[str, Any]:
        sample_contacts = []
        for contact in self.children():
            if contact.hasPosition():
                sample_contacts.append({
                    "id": contact.id,
                    "position": tuple(map(to_table_unit, contact.position()))
                })
        return {
            "sample_name_prefix": self.name_prefix,
            "sample_name_infix": self.name_infix,
            "sample_name_suffix": self.name_suffix,
            "sample_type": self.sample_type,
            "sample_position": self.sample_position,
            "sample_comment": self.comment(),
            "sample_enabled": self.isEnabled(),
            "sample_sequence_filename": self.sequenceFilename(),
            "sample_contacts": sample_contacts
        }

    # Methods

    def update_name(self):
        tokens = self.name, self.sample_type
        self.setText(0, "/".join((token for token in tokens if token)))

    def load_sequence(self, sequence):
        # Store contact positions
        contact_positions = {}
        for contact_item in self.children():
            if contact_item.hasPosition():
                contact_positions[contact_item.id] = contact_item.position()
        while len(self.children()):
            self.takeChild(0)
        self.sequence = sequence
        for contact in sequence.contacts:
            item = self.addChild(ContactTreeItem(self, contact))
        # Restore contact positions
        for contact_item in self.children():
            if contact_item.id in contact_positions:
                contact_item.setPosition(contact_positions.get(contact_item.id))

    def clear_sequence(self) -> None:
        while len(self.children()):
            self.takeChild(0)
        self.sequence = None



class ContactTreeItem(SequenceTreeItem):
    """Contact (flute) item of sequence tree."""

    def __init__(self, sample, contact) -> None:
        super().__init__("contact")
        self._position: Position = Position()
        self.sample = sample
        self.id: str = contact.id
        self.name: str = contact.name
        self.setEnabled(contact.enabled)
        self.contact_id: str = contact.contact_id
        self.setDescription(contact.description)
        for measurement in contact.measurements:
            self.addChild(MeasurementTreeItem(self, measurement))

    # Properties

    def position(self) -> Position:
        return self._position

    def setPosition(self, position: Position) -> None:
        x, y, z = position
        self._position = Position(x, y, z)
        text: str = "OK" if self.hasPosition() else ""
        self.setText(1, text)

    def hasPosition(self) -> bool:
        return self._position.is_valid

    def description(self) -> str:
        return self._description

    def setDescription(self, description: str) -> None:
        self._description = description


class MeasurementTreeItem(SequenceTreeItem):
    """Measurement item of sequence tree."""

    def __init__(self, contact, measurement) -> None:
        super().__init__(measurement.type)
        self.contact = contact
        self.id: str = measurement.id
        self.name: str = measurement.name
        self.setEnabled(measurement.enabled)
        self.parameters: Dict = copy.deepcopy(measurement.parameters)
        self.default_parameters: Dict = copy.deepcopy(measurement.default_parameters)
        self.tags: List[str] = measurement.tags
        self.setDescription(measurement.description)
        self.setRemeasureCount(0)
        self.setRecontactCount(0)
        self.series: Dict = {}
        self.analysis: Dict = {}

    def description(self) -> str:
        return self._description

    def setDescription(self, description: str) -> None:
        self._description = description

    def remeasureCount(self) -> int:
        return self._remeasureCount

    def setRemeasureCount(self, count: int) -> None:
        self._remeasureCount = count
        self.setText(3, format(count, "d") if count else "")

    def incrementRemeasureCount(self) -> None:
        count = self.remeasureCount()
        self.setRemeasureCount(count + 1)

    def recontactCount(self) -> int:
        return self._recontactCount

    def setRecontactCount(self, count: int) -> None:
        self._recontactCount = count
        self.setText(4, format(count, "d") if count else "")

    def incrementRecontactCount(self) -> None:
        count = self.recontactCount()
        self.setRecontactCount(count + 1)

    def reset(self) -> None:
        super().reset()
        self.series.clear()
        self.analysis.clear()


class SequenceTreeWidget(QtWidgets.QTreeWidget):
    """Sequence tree containing sample, contact and measurement items."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setExpandsOnDoubleClick(False)
        self.setHeaderLabels(["Name", "Pos", "State", "RM", "RC"])
        self.header().setMinimumSectionSize(32)
        self.header().resizeSection(1, 32)

    def sampleItems(self) -> List[SampleTreeItem]:
        items = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            if isinstance(item, SampleTreeItem):
                items.append(item)
        return items

    def setLocked(self, locked: bool) -> None:
        self.blockSignals(locked)
        for item in self.sampleItems():
            item.setLocked(locked)

    def reset(self) -> None:
        for item in self.sampleItems():
            item.reset()

    def resizeColumns(self) -> None:
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.setColumnWidth(3, 32)
        self.setColumnWidth(24, 32)
        if self.columnWidth(0) < 200:
            self.setColumnWidth(0, 200)
