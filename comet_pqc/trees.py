import copy

from comet.ui.tree import Tree, TreeItem

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self[0].checkable = True

    def lock(self):
        self[0].checkable = False
        for child in self.children:
            child.lock()

    def unlock(self):
        self[0].checkable = True
        for child in self.children:
            child.unlock()

    def reset(self):
        self.state = None
        for child in self.children:
            child.reset()

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
        self[0].bold = (value == "Active")
        if value == "Success":
            self[1].color = "green"
        elif value == "Active":
            self[1].color = "blue"
        else:
            self[1].color = "red"
        self[1].value = value

class ContactTreeItem(SequenceTreeItem):

    def __init__(self, contact):
        super().__init__([contact.name, None])
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
        self.name = measurement.name
        self.type = measurement.type
        self.enabled = measurement.enabled
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.description = measurement.description
        self.series = {}
