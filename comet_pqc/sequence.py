import copy
import math
import os

from comet import ui
from comet.settings import SettingsMixin
from qutie.qutie import QtCore

from analysis_pqc import STATUS_PASSED

from .config import load_sequence

class SequenceManager(ui.Dialog, SettingsMixin):

    def __init__(self):
        super().__init__()
        self.title = "Sequence Manager"
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
        self.layout = ui.Column(
            ui.Row(
                self.sequence_tree,
                ui.Column(
                    self.add_button,
                    self.remove_button,
                    ui.Spacer()
                ),
                stretch=(1, 0)
            ),
            ui.Row(
                ui.Spacer(),
                ui.Button("Close", clicked=self.close)
            ),
            stretch=(1, 0)
        )

    def on_sequence_tree_selected(self, item):
        self.remove_button.enabled = len(self.sequence_tree)

    def on_add_sequence(self):
        filename = ui.filename_open()
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                ui.show_exception(exc)
            else:
                if filename not in self.sequence_filenames:
                    item = self.sequence_tree.append([sequence.name, filename])
                    item.qt.setToolTip(1, filename)
                    self.sequence_tree.current = item

    def on_remove_sequence(self):
        item = self.sequence_tree.current
        if item:
            if ui.show_question(
                title="Remove Sequence",
                text=f"Do yo want to remove sequence '{item[0].value}'?"
            ):
                self.sequence_tree.remove(item)
                self.remove_button.enabled = len(self.sequence_tree)

    @property
    def sequence_filenames(self):
        filenames = []
        for sequence_item in self.sequence_tree:
            filenames.append(sequence_item[1].value)
        return filenames

    def load_settings(self):
        self.sequence_tree.clear()
        for filename in list(set(self.settings.get('custom_sequences') or [])):
            if os.path.exists(filename):
                try:
                    sequence = load_sequence(filename)
                except Exception as exc:
                    ui.show_exception(exc)
                else:
                    item = self.sequence_tree.append([sequence.name, filename])
                    item.qt.setToolTip(1, filename)

    def store_settings(self):
        sequences = []
        for sequence_item in self.sequence_tree:
            sequences.append(sequence_item[1].value)
        self.settings['custom_sequences'] = list(set(sequences))

class SequenceTree(ui.Tree):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = ["Measurement", "Pos", "State"]
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
        self[0].checkable = True

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
    def enabled(self):
        return self[0].checked

    @enabled.setter
    def enabled(self, enabled):
        self[0].checked = enabled

    @property
    def pos(self):
        return self[1].value

    @enabled.setter
    def pos(self, enabled):
        self[1].value = {False: '', True: 'OK'}.get(enabled)

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

class ContactTreeItem(SequenceTreeItem):

    def __init__(self, contact):
        super().__init__([contact.name, None])
        self.id = contact.id
        self.name = contact.name
        self.enabled = contact.enabled
        self.contact_id = contact.contact_id
        self.description = contact.description
        self.reset_position()
        for measurement in contact.measurements:
            self.append(MeasurementTreeItem(self, measurement))

    @property
    def has_position(self):
        return any((not math.isnan(value) for value in self.position))

    def reset_position(self):
        self.pos = False
        self.position = float('nan'), float('nan'), float('nan')

class MeasurementTreeItem(SequenceTreeItem):

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
