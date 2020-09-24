import copy
import os

from comet import ui
from comet.settings import SettingsMixin
from qutie.qt import QtCore

from analysis_pqc import STATUS_PASSED

from .config import load_sequence

class SequenceManager(ui.Dialog, SettingsMixin):

    def __init__(self):
        super().__init__()
        self.title = "Sequence Manager"
        self.resize(640, 480)
        self.sequence_tree = ui.Tree(
            header=("Name", "Filename"),
            indentation=0
        )
        self.layout = ui.Column(
            ui.Row(
                self.sequence_tree,
                ui.Column(
                    ui.Button("Add", clicked=self.on_add_sequence),
                    ui.Button("Remove", clicked=self.on_remove_sequence),
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

    def on_add_sequence(self):
        filename = ui.filename_open()
        if filename:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                ui.show_exception(exc)
            else:
                if filename not in self.sequence_filenames:
                    self.sequence_tree.append([sequence.name, filename])

    def on_remove_sequence(self):
        item = self.sequence_tree.current
        if item:
            self.sequence_tree.remove(item)

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
                    self.sequence_tree.append([sequence.name, filename])

    def store_settings(self):
        sequences = []
        for sequence_item in self.sequence_tree:
            sequences.append(sequence_item[1].value)
        self.settings['custom_sequences'] = list(set(sequences))

class SequenceTree(ui.Tree):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = ["Measurement", "State", 'Quality']

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
    def state(self):
        return self[1].value

    @state.setter
    def state(self, value):
        self[0].bold = (value in (self.ActiveState, self.ProcessingState))
        self[0].color = None
        if value == self.SuccessState:
            self[1].color = "green"
        elif value in (self.ActiveState, self.ProcessingState):
            self[0].color = "blue"
            self[1].color = "blue"
        else:
            self[1].color = "red"
        self[1].value = value

    @property
    def quality(self):
        return self[2].value

    @quality.setter
    def quality(self, value):
        # Oh dear...
        value = value or ""
        if value.lower() == STATUS_PASSED.lower():
            self[2].color = "green"
        else:
            self[2].color = "red"
        self[2].value = value.capitalize()

class ContactTreeItem(SequenceTreeItem):

    def __init__(self, contact):
        super().__init__([contact.name, None])
        self.id = contact.id
        self.name = contact.name
        self.enabled = contact.enabled
        self.contact_id = contact.contact_id
        self.description = contact.description
        for measurement in contact.measurements:
            self.append(MeasurementTreeItem(self, measurement))

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
