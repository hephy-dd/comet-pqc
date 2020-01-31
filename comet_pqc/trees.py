from PyQt5 import QtCore, QtGui, QtWidgets

import comet

class SlotItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, slot, wafer, sequence):
        super().__init__()
        self.setData(0, 0x2000, slot)
        self.setText(0, slot.name)
        self.setData(1, 0x2000, wafer)
        self.setText(1, wafer.name)
        self.setData(2, 0x2000, sequence)
        self.setText(2, sequence.name)

class WaferTree(comet.Widget):
    """Wafer/Slot selection widget."""

    QtBaseClass = QtWidgets.QTreeWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qt.setRootIsDecorated(False)
        self.qt.setHeaderLabels(["Slot", "Wafer", "Sequence"])
        self.qt.resizeColumnToContents(2)
        self.qt.resizeColumnToContents(1)
        self.qt.resizeColumnToContents(0)

    def load(self, config, wafer, sequence):
        self.qt.clear()
        for slot in config.slots:
            item = SlotItem(slot, wafer, sequence)
            self.qt.addTopLevelItem(item)
        self.qt.resizeColumnToContents(2)
        self.qt.resizeColumnToContents(1)
        self.qt.resizeColumnToContents(0)

class MeasurementItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, measurement):
        super().__init__(parent)
        self.setData(0, 0x2000, measurement)
        self.setCheckState(0, [QtCore.Qt.Unchecked, QtCore.Qt.Checked][measurement.enabled])
        self.setText(0, measurement.name)
        self.setText(1, "-")

class SequenceItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, sequence):
        super().__init__(parent)
        self.setData(0, 0x2000, sequence)
        self.setCheckState(0, [QtCore.Qt.Unchecked, QtCore.Qt.Checked][sequence.enabled])
        self.setText(0, sequence.name)
        self.setText(1, "-")
        for measurement in sequence.measurements:
            item = MeasurementItem(self, measurement)
            self.addChild(item)

class SequenceTree(comet.Widget):
    """Mesurement sequence selection widget."""

    QtBaseClass = QtWidgets.QTreeWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qt.setHeaderLabels(["Measurement"])
        self.qt.resizeColumnToContents(0)

    def load(self, config):
        self.qt.clear()
        for sequence in config.items:
            item = SequenceItem(self.qt, sequence)
            self.qt.addTopLevelItem(item)
            item.setExpanded(True)
        self.qt.resizeColumnToContents(0)
