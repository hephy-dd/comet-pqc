import copy

from comet.ui.tree import Tree, TreeItem

class SequenceTree(Tree):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = ["Measurement", "State"]

    def lock(self):
        for connection in self:
            connection.lock()

    def unlock(self):
        for connection in self:
            connection.unlock()

    def reset(self):
        for connection in self:
            connection.reset()

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
        self[1].color = "red" if value != "Success" else "green"
        self[1].value = value

class ConnectionTreeItem(SequenceTreeItem):

    def __init__(self, connection):
        super().__init__([connection.name, None])
        self.name = connection.name
        self.enabled = connection.enabled
        self.connection = connection.connection
        self.description = connection.description
        for measurement in connection.measurements:
            self.append(MeasurementTreeItem(self, measurement))

class MeasurementTreeItem(SequenceTreeItem):

    def __init__(self, connection, measurement):
        super().__init__([measurement.name, None])
        self.connection = connection
        self.name = measurement.name
        self.type = measurement.type
        self.enabled = measurement.enabled
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.description = measurement.description
        self.series = {}
