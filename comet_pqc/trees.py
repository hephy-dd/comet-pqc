import copy

from comet.ui.tree import Tree, TreeItem

class SequenceTree(Tree):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = ["Measurement", "State"]

class ConnectionTreeItem(TreeItem):

    def __init__(self, connection):
        super().__init__([connection.name, None])
        self.name = connection.name
        self.connection = connection.connection
        self.description = connection.description
        self[0].checkable = True
        self[0].checked = connection.enabled
        for measurement in connection.measurements:
            self.append(MeasurementTreeItem(measurement))

class MeasurementTreeItem(TreeItem):

    def __init__(self, measurement):
        super().__init__([measurement.name, None])
        self.name = measurement.name
        self.type = measurement.type
        self.parameters = copy.deepcopy(measurement.parameters)
        self.default_parameters = copy.deepcopy(measurement.default_parameters)
        self.description = measurement.description
        self.series = {}
        self[0].checkable = True
        self[0].checked = measurement.enabled
