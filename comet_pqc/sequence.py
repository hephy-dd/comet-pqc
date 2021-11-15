import copy
import math
import os
import logging

from comet import ui
from comet.settings import SettingsMixin
from qutie.qutie import QtCore
import yaml

from analysis_pqc import STATUS_PASSED

from .config import load_sequence, list_configs, SEQUENCE_DIR

from .components import PositionsComboBox
from .components import OperatorWidget
from .components import WorkingDirectoryWidget

from .quickedit import QuickEditDialog

from .settings import settings
from .utils import from_table_unit
from .utils import to_table_unit

__all__ = ['StartSequenceDialog', 'SequenceManager', 'SequenceTree']

logger = logging.getLogger(__name__)

def load_all_sequences(settings):
    configs = []
    for name, filename in list_configs(SEQUENCE_DIR):
        configs.append((name, filename, True))
    for filename in list(set(settings.get('custom_sequences') or [])):
        if os.path.exists(filename):
            try:
                sequence = load_sequence(filename)
            except:
                pass
            else:
                configs.append((sequence.name, filename, False))
    return configs

class StartSequenceDialog(ui.Dialog, SettingsMixin):
    """Start sequence dialog."""

    def __init__(self, context, table_enabled):
        super().__init__()
        self.title = "Start Sequence"
        self._contact_checkbox = ui.CheckBox(
            text="Move table and contact with Probe Card",
            checked=True,
            enabled=table_enabled
        )
        self._position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            enabled=table_enabled,
            changed=self.on_position_checkbox_toggled
        )
        self._positions_combobox = PositionsComboBox(
            enabled=False
        )
        self._operator_combobox = OperatorWidget()
        self._output_combobox = WorkingDirectoryWidget()
        self._button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self._button_box.qt.button(self._button_box.QtClass.Yes).setAutoDefault(False)
        self._button_box.qt.button(self._button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=self._create_message(context)
            ),
            ui.GroupBox(
                title="Table",
                layout=ui.Column(
                    self._contact_checkbox,
                    ui.Row(
                        self._position_checkbox,
                        self._positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self._operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self._output_combobox
                ),
                stretch=(2, 3)
            ),
            self._button_box,
            stretch=(1, 0, 0, 0)
        )

    # Settings

    def load_settings(self):
        self._contact_checkbox.checked = bool(self.settings.get('move_to_contact') or False)
        self._position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self._positions_combobox.load_settings()
        self._operator_combobox.load_settings()
        self._output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_to_contact'] = self._contact_checkbox.checked
        self.settings['move_on_success'] = self._position_checkbox.checked
        self._positions_combobox.store_settings()
        self._operator_combobox.store_settings()
        self._output_combobox.store_settings()

    # Callbacks

    def on_position_checkbox_toggled(self, state):
        self._positions_combobox.enabled = state

    # Methods

    def move_to_contact(self):
        return self._contact_checkbox.checked

    def move_to_position(self):
        if self.move_to_contact() and self._position_checkbox.checked:
            current = self._positions_combobox.current
            if current:
                index = self._positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    # Helpers

    def _create_message(self, context):
        if isinstance(context, SamplesItem):
            return "<b>Are you sure to start all enabled sequences for all enabled samples?</b>"
        elif isinstance(context, SampleTreeItem):
            return f"<b>Are you sure to start all enabled sequences for '{context.name}'?</b>"
        elif isinstance(context, ContactTreeItem):
            return f"<b>Are you sure to start sequence '{context.name}'?</b>"

class SequenceManager(ui.Dialog, SettingsMixin):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self):
        super().__init__()
        # Properties
        self.title = "Sequence Manager"
        # Layout
        self.resize(640, 480)
        self._sequence_tree = ui.Tree(
            header=("Name", "Filename"),
            indentation=0,
            selected=self.on_sequence_tree_selected
        )
        self._add_button = ui.Button(
            text="&Add",
            clicked=self.on_add_sequence
        )
        self._remove_button = ui.Button(
            text="&Remove",
            enabled=False,
            clicked=self.on_remove_sequence
        )
        self._preview_tree = ui.Tree(header=["Key", "Value"])
        self.layout = ui.Column(
            ui.Row(
                ui.Column(
                    self._sequence_tree,
                    self._preview_tree,
                    stretch=(4, 3)
                ),
                ui.Column(
                    self._add_button,
                    self._remove_button,
                    ui.Spacer()
                ),
                stretch=(1, 0)
            ),
            ui.DialogButtonBox(
                buttons=("ok", "cancel"),
                accepted=self.accept,
                rejected=self.reject
            ),
            stretch=(1, 0)
        )

    # Properties

    @property
    def current_sequence(self):
        """Return selected sequence object or None if nothing selected."""
        item = self._sequence_tree.current
        if item is not None:
            return item.sequence
        return None

    @property
    def sequence_filenames(self):
        filenames = []
        for sequence_item in self._sequence_tree:
            filenames.append(sequence_item.sequence.filename)
        return filenames

    # Settings

    def load_settings(self):
        self.load_settings_dialog_size()
        self.load_settings_sequences()

    def load_settings_dialog_size(self):
        """Load dialog size from settings."""
        width, height = self.settings.get('sequence_manager_dialog_size') or (640, 480)
        self.resize(width, height)

    def load_settings_sequences(self):
        """Load all built-in and custom sequences from settings."""
        self._sequence_tree.clear()
        for name, filename, builtin in load_all_sequences(self.settings):
            try:
                sequence = load_sequence(filename)
                item = self._sequence_tree.append([sequence.name, '(built-in)' if builtin else filename])
                item.sequence = sequence
                item.sequence.builtin = builtin
                item.qt.setToolTip(1, filename)
            except Exception as exc:
                logger.error("failed to load sequence: %s", filename)
                pass
        self._sequence_tree.fit()
        if len(self._sequence_tree):
            self._sequence_tree.current = self._sequence_tree[0]

    def store_settings(self):
        self.store_settings_dialog_size()
        self.store_settings_sequences()

    def store_settings_dialog_size(self):
        """Store dialog size to settings."""
        self.settings['sequence_manager_dialog_size'] = self.width, self.height

    def store_settings_sequences(self):
        """Store custom sequences to settings."""
        sequences = []
        for item in self._sequence_tree:
            if not item.sequence.builtin:
                sequences.append(item.sequence.filename)
        self.settings['custom_sequences'] = list(set(sequences))

    # Callbacks

    def on_sequence_tree_selected(self, item):
        """Load sequence config preview."""
        self._remove_button.enabled = False
        self._preview_tree.clear()
        if item is not None:
            self._remove_button.enabled = not item.sequence.builtin
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

    def on_add_sequence(self):
        filename = ui.filename_open(filter="YAML files (*.yml, *.yaml);;All files (*)")
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                ui.show_exception(exc)
            else:
                if filename not in self.sequence_filenames:
                    item = self._sequence_tree.append([sequence.name, filename])
                    item.qt.setToolTip(1, filename)
                    item.sequence = sequence
                    item.sequence.builtin = False
                    self._sequence_tree.current = item

    def on_remove_sequence(self):
        item = self._sequence_tree.current
        if item and not item.sequence.builtin:
            if ui.show_question(
                title="Remove Sequence",
                text=f"Do yo want to remove sequence '{item.sequence.name}'?"
            ):
                self._sequence_tree.remove(item)
                self._remove_button.enabled = len(self._sequence_tree)

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

    def lock(self):
        for contact in self:
            contact.lock()

    def unlock(self):
        for contact in self:
            contact.unlock()

    def reset(self):
        for contact in self:
            contact.reset()

class SamplesItem:
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, iterable):
        self.children = []
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

    def lock(self):
        self.checkable = False
        self.selectable = False
        for child in self.children:
            child.lock()

    def unlock(self):
        self.checkable = True
        self.selectable = True
        for child in self.children:
            child.unlock()

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
        return ''.join((self.name_prefix, self.name_infix, self.name_suffix)).strip()

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
        default_position = float('nan'), float('nan'), float('nan')
        for contact_position in kwargs.get("sample_contacts") or []:
            for contact in self.children:
                if contact.id == contact_position.get("id"):
                    try:
                        x, y, z = tuple(map(from_table_unit, contact_position.get("position")))
                    except:
                        pass
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
        self[0].value = '/'.join((token for token in tokens if token))

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
        self[1].value = {False: '', True: 'OK'}.get(self.has_position)

    @property
    def has_position(self):
        return any((not math.isnan(value) for value in self.__position))

    # Methods

    def reset_position(self):
        self.position = float('nan'), float('nan'), float('nan')

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

    def reset(self):
        super().reset()
        self.series.clear()
        self.analysis.clear()


class EditSamplesDialog(SettingsMixin):
    """Quick edit all samples at once dialog."""

    def __init__(self, sequence_tree, sequences):
        self.sequence_tree = sequence_tree
        self.sequences = sequences

    def _populate_dialog(self, dialog):
        for sample_item in self.sequence_tree:
            item = dialog.addItem()
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
            item.setProperty('sample_item', sample_item)

    def _update_samples(self, dialog):
        for item in dialog.items():
            sample_item = item.property('sample_item')
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

    def load_settings(self, dialog):
        width, height = self.settings.get('quick_edit_dialog_size', (800, 480))
        dialog.resize(width, height)

    def store_settings(self, dialog):
        width, height = dialog.width(), dialog.height()
        self.settings['quick_edit_dialog_size'] = width, height

    def run(self):
        dialog = QuickEditDialog()
        self.load_settings(dialog)
        self._populate_dialog(dialog)
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            self._update_samples(dialog)
        self.store_settings(dialog)
