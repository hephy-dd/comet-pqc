from PyQt5 import QtCore, QtGui, QtWidgets

import comet

class SlotItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, slot, wafer, sequence):
        super().__init__()
        self.setCheckState(0, QtCore.Qt.Checked)
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
        self.qt.itemActivated.connect(self.edit_item)

    def edit_item(self, item, column):
        if column == 1:
            comet.show_info(title="1", text=item.data(1, 0x2000).id)
        if column == 2:
            comet.show_info(title="2", text=item.data(2, 0x2000).id)

    def load(self, config, wafer, sequence):
        self.qt.clear()
        for slot in config.slots:
            item = SlotItem(slot, wafer, sequence)
            self.qt.addTopLevelItem(item)
        self.qt.resizeColumnToContents(2)
        self.qt.resizeColumnToContents(1)
        self.qt.resizeColumnToContents(0)
        if self.qt.topLevelItemCount():
            self.qt.setCurrentItem(self.qt.topLevelItem(0))

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

    def items(self):
        items = []
        for index in range(self.childCount()):
            items.append(self.child(index))
        return items

class SequenceTree(comet.Widget):
    """Mesurement sequence selection widget."""

    QtBaseClass = QtWidgets.QTreeWidget

    def __init__(self, slot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slot = slot
        self.qt.setHeaderLabels([f"{slot.name} Measurement", "Status"])
        self.qt.resizeColumnToContents(0)
        self.qt.setColumnWidth(1, 64)
        self.qt.itemChanged.connect(self.update_item)

    def update_item(self, item, column):
        item.data(0, 0x2000).enabled = item.checkState(0) == QtCore.Qt.Checked
        print(item.data(0, 0x2000))

    def items(self):
        items = []
        for index in range(self.qt.topLevelItemCount()):
            items.append(self.qt.topLevelItem(index))
        return items

    def sync(self):
        for item in self.items():
            flags = item.flags()
            if not item.data(0, 0x2000).locked:
                flags |= QtCore.Qt.ItemIsUserCheckable
                color = "black"
            else:
                flags &= ~QtCore.Qt.ItemIsUserCheckable
                color = "green"
            item.setFlags(flags)
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(color)))
            item.setForeground(1, QtGui.QBrush(QtGui.QColor(color)))
            item.setText(1, item.data(0, 0x2000).state)
            for measurement in item.items():
                flags = measurement.flags()
                if not measurement.data(0, 0x2000).locked:
                    flags |= QtCore.Qt.ItemIsUserCheckable
                    color = "black"
                else:
                    flags &= ~QtCore.Qt.ItemIsUserCheckable
                    color = "green"
                measurement.setFlags(flags)
                measurement.setForeground(0, QtGui.QBrush(QtGui.QColor(color)))
                measurement.setForeground(1, QtGui.QBrush(QtGui.QColor(color)))
                measurement.setText(1, measurement.data(0, 0x2000).state)

    def load(self, config):
        self.qt.itemChanged.disconnect()
        self.qt.clear()
        for sequence in config.items:
            item = SequenceItem(self.qt, sequence)
            self.qt.addTopLevelItem(item)
            item.setExpanded(True)
        self.qt.resizeColumnToContents(0)
        self.qt.itemChanged.connect(self.update_item)
