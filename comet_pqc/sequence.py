import copy
import math
import os

from comet import ui, app
from comet.settings import SettingsMixin
from qutie.qutie import QtCore, QtGui

from analysis_pqc import STATUS_PASSED

from .config import load_sequence, list_configs, SEQUENCE_DIR

from .components import PositionsComboBox
from .components import OperatorWidget
from .components import WorkingDirectoryWidget

from .settings import settings
from .utils import from_table_unit

__all__ = ['StartSequenceDialog', 'StartSampleDialog']

def load_all_sequences():
    configs = []
    for name, filename in list_configs(SEQUENCE_DIR):
        configs.append((name, filename, True))
    for filename in list(set(app().settings.get('custom_sequences') or [])):
        if os.path.exists(filename):
            try:
                sequence = load_sequence(filename)
            except:
                pass
            else:
                configs.append((sequence.name, filename, False))
    return configs

class StartSequenceDialog(ui.Dialog, SettingsMixin):

    def __init__(self, contact_item, table_enabled=False):
        super().__init__()
        self.title = "Start Sequence"
        self.contact_checkbox = ui.CheckBox(
            text="Move table and contact with Probe Card",
            checked=contact_item.has_position,
            enabled=contact_item.has_position
        )
        self.position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            changed=self.on_position_checkbox_toggled
        )
        self.positions_combobox = PositionsComboBox(
            enabled=False
        )
        self.operator_combobox = OperatorWidget()
        self.output_combobox = WorkingDirectoryWidget()
        self.button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self.button_box.qt.button(self.button_box.QtClass.Yes).setAutoDefault(False)
        self.button_box.qt.button(self.button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=f"<b>Are you sure to start sequence '{contact_item.name}'?</b>"
            ),
            ui.GroupBox(
                title="Table",
                enabled=table_enabled,
                layout=ui.Column(
                    self.contact_checkbox,
                    ui.Row(
                        self.position_checkbox,
                        self.positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self.operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self.output_combobox
                )
            ),
            self.button_box,
            stretch=(1, 0, 0, 0)
        )

    def load_settings(self):
        self.position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self.positions_combobox.load_settings()
        self.operator_combobox.load_settings()
        self.output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_on_success'] = self.position_checkbox.checked
        self.positions_combobox.store_settings()
        self.operator_combobox.store_settings()
        self.output_combobox.store_settings()

    def move_to_position(self):
        if self.position_checkbox.checked:
            current = self.positions_combobox.current
            if current:
                index = self.positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    def on_position_checkbox_toggled(self, state):
        self.positions_combobox.enabled = state

class StartSampleDialog(ui.Dialog, SettingsMixin):

    def __init__(self, sample_item, table_enabled=False):
        super().__init__()
        self.title = "Start Sequences"
        self.position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            changed=self.on_position_checkbox_toggled
        )
        self.positions_combobox = PositionsComboBox(
            enabled=False
        )
        self.operator_combobox = OperatorWidget()
        self.output_combobox = WorkingDirectoryWidget()
        self.button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self.button_box.qt.button(self.button_box.QtClass.Yes).setAutoDefault(False)
        self.button_box.qt.button(self.button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=f"<b>Are you sure to start all enabled sequences for '{sample_item.name}'?</b>"
            ),
            ui.GroupBox(
                title="Table",
                enabled=table_enabled,
                layout=ui.Column(
                    ui.Row(
                        self.position_checkbox,
                        self.positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self.operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self.output_combobox
                )
            ),
            self.button_box,
            stretch=(1, 0, 0, 0)
        )

    def load_settings(self):
        self.position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self.positions_combobox.load_settings()
        self.operator_combobox.load_settings()
        self.output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_on_success'] = self.position_checkbox.checked
        self.positions_combobox.store_settings()
        self.operator_combobox.store_settings()
        self.output_combobox.store_settings()

    def move_to_position(self):
        if self.position_checkbox.checked:
            current = self.positions_combobox.current
            if current:
                index = self.positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    def on_position_checkbox_toggled(self, state):
        self.positions_combobox.enabled = state

class StartSamplesDialog(ui.Dialog, SettingsMixin):

    def __init__(self, sample_items):
        super().__init__()
        self.title = "Start Sequences"
        self.position_checkbox = ui.CheckBox(
            text="Move table after measurements",
            checked=False,
            changed=self.on_position_checkbox_toggled
        )
        self.positions_combobox = PositionsComboBox(
            enabled=False
        )
        self.operator_combobox = OperatorWidget()
        self.output_combobox = WorkingDirectoryWidget()
        self.button_box = ui.DialogButtonBox(
            buttons=("yes", "no"),
            accepted=self.accept,
            rejected=self.reject
        )
        self.button_box.qt.button(self.button_box.QtClass.Yes).setAutoDefault(False)
        self.button_box.qt.button(self.button_box.QtClass.No).setDefault(True)
        self.layout = ui.Column(
            ui.Label(
                text=f"<b>Are you sure to start all enabled sequences for all enabled samples?</b>"
            ),
            ui.GroupBox(
                title="Table",
                layout=ui.Column(
                    ui.Row(
                        self.position_checkbox,
                        self.positions_combobox
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Operator",
                    layout=self.operator_combobox
                ),
                ui.GroupBox(
                    title="Working Directory",
                    layout=self.output_combobox
                )
            ),
            self.button_box,
            stretch=(1, 0, 0, 0)
        )

    def load_settings(self):
        self.position_checkbox.checked = bool(self.settings.get('move_on_success') or False)
        self.positions_combobox.load_settings()
        self.operator_combobox.load_settings()
        self.output_combobox.load_settings()

    def store_settings(self):
        self.settings['move_on_success'] = self.position_checkbox.checked
        self.positions_combobox.store_settings()
        self.operator_combobox.store_settings()
        self.output_combobox.store_settings()

    def move_to_position(self):
        if self.position_checkbox.checked:
            current = self.positions_combobox.current
            if current:
                index = self.positions_combobox.index(current)
                positions = settings.table_positions
                if 0 <= index < len(positions):
                    position = positions[index]
                    return position.x, position.y, position.z
        return None

    def on_position_checkbox_toggled(self, state):
        self.positions_combobox.enabled = state

class SequenceManager(ui.Dialog, SettingsMixin):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self):
        super().__init__()
        # Properties
        self.title = "Sequence Manager"
        # Layout
        self.resize(640, 480)
        self.sequence_tree = ui.Tree(
            header=("Name", "Filename"),
            indentation=0,
            selected=self.on_sequence_tree_selected
        )
        self.add_button = ui.Button(
            text="&Add",
            clicked=self.on_add_sequence
        )
        self.remove_button = ui.Button(
            text="&Remove",
            enabled=False,
            clicked=self.on_remove_sequence
        )
        self.preview_textarea = ui.TextArea(
            readonly=True
        )
        font = self.preview_textarea.qt.font()
        font.setFamily("Monospace")
        self.preview_textarea.qt.setFont(font)
        self.layout = ui.Column(
            ui.Row(
                ui.Column(
                    self.sequence_tree,
                    self.preview_textarea,
                    stretch=(4, 3)
                ),
                ui.Column(
                    self.add_button,
                    self.remove_button,
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

    def on_sequence_tree_selected(self, item):
        """Load sequence config preview."""
        self.remove_button.enabled = False
        self.preview_textarea.clear()
        if item is not None:
            self.remove_button.enabled = not item.sequence.builtin
            if os.path.exists(item.sequence.filename):
                with open(item.sequence.filename) as f:
                    self.preview_textarea.qt.setText(f.read())
                    self.preview_textarea.qt.textCursor().setPosition(0)
                    self.preview_textarea.qt.ensureCursorVisible()

    def on_add_sequence(self):
        filename = ui.filename_open(filter="YAML files (*.yml, *.yaml);;All files (*)")
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                ui.show_exception(exc)
            else:
                if filename not in self.sequence_filenames:
                    item = self.sequence_tree.append([sequence.name, filename])
                    item.qt.setToolTip(1, filename)
                    item.sequence = sequence
                    item.sequence.builtin = False
                    self.sequence_tree.current = item

    def on_remove_sequence(self):
        item = self.sequence_tree.current
        if item and not item.sequence.builtin:
            if ui.show_question(
                title="Remove Sequence",
                text=f"Do yo want to remove sequence '{item.sequence.name}'?"
            ):
                self.sequence_tree.remove(item)
                self.remove_button.enabled = len(self.sequence_tree)

    @property
    def sequence_filenames(self):
        filenames = []
        for sequence_item in self.sequence_tree:
            filenames.append(sequence_item.sequence.filename)
        return filenames

    def load_settings(self):
        width, height = self.settings.get('sequence_manager_dialog_size') or (640, 480)
        self.resize(width, height)
        self.sequence_tree.clear()
        for name, filename, builtin in load_all_sequences():
            try:
                sequence = load_sequence(filename)
                item = self.sequence_tree.append([sequence.name, '(built-in)' if builtin else filename])
                item.sequence = sequence
                item.sequence.builtin = builtin
                item.qt.setToolTip(1, filename)
            except Exception as exc:
                logging.error("failed to load sequence: %s", filename)
                pass
        self.sequence_tree.fit()
        if len(self.sequence_tree):
            self.sequence_tree.current = self.sequence_tree[0]

    def store_settings(self):
        self.settings['sequence_manager_dialog_size'] = self.width, self.height
        sequences = []
        for sequence_item in self.sequence_tree:
            if not sequence_item.sequence.builtin:
                sequences.append(sequence_item.sequence.filename)
        self.settings['custom_sequences'] = list(set(sequences))

class SequenceTree(ui.Tree):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.expands_on_double_click = False
        self.header = ["Name", "Pos", "State"]
        self.qt.header().setMinimumSectionSize(32)
        self.qt.header().resizeSection(1, 32)

    def lock(self):
        for contact in self:
            contact.lock()

    def unlock(self):
        for contact in self:
            contact.unlock()

    def reset(self):
        for contact in self:
            contact.reset()

class SampleSequence:
    """Virtual item holding multiple samples to be executed."""

    def __init__(self, samples):
        self.samples = samples

class SequenceTreeItem(ui.TreeItem):

    ProcessingState = "Processing..."
    ActiveState = "Active"
    SuccessState = "Success"
    ComplianceState = "Compliance"
    TimeoutState = "Timeout"
    ErrorState = "Error"
    StoppedState = "Stopped"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkable = True

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
        self.quality = None
        for child in self.children:
            child.reset()

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

    @property
    def quality(self):
        return self[3].value

    @quality.setter
    def quality(self, value):
        # Oh dear...
        value = value or ""
        if value.lower() == STATUS_PASSED.lower():
            self[3].color = "green"
        else:
            self[3].color = "red"
        self[3].value = value.capitalize()

class SampleTreeItem(SequenceTreeItem):
    """Sample (halfmoon) item of sequence tree."""

    def __init__(self, name, sample_type, enabled=False, comment=None):
        super().__init__([name, None])
        self.name = name
        self.sample_type = sample_type
        self.comment = comment or ""
        self.enabled = enabled
        self.sequence = None

    def load_sequence(self, sequence):
        while len(self.children):
            self.qt.takeChild(0)
        self.sequence = sequence
        for contact in sequence.contacts:
            item = self.append(ContactTreeItem(self, contact))
            item.expanded = True

class ContactTreeItem(SequenceTreeItem):
    """Contact (flute) item of sequence tree."""

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
        self.description = measurement.description
        self.series = {}
        self.analysis = {}
