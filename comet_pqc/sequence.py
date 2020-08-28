import copy

from comet.ui import Tree, TreeItem
from qutie.qt import QtCore

class SequenceTree(Tree):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = ["Measurement", "State"]

    def lock(self):
        for contact in self:
            contact.lock()

    def unlock(self):
        for contact in self:
            contact.unlock()

    def reset(self):
        for contact in self:
            contact.reset()

class SequenceTreeItem(TreeItem):

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
