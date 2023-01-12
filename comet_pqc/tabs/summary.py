import datetime
from typing import Optional

from PyQt5 import QtGui, QtWidgets

__all__ = ["SummaryWidget"]


class SummaryWidget(QtWidgets.QWidget):

    Header = ["Time", "Sample", "Type", "Contact", "Measurement", "Result"]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.treeWidget = QtWidgets.QTreeWidget(self)
        self.treeWidget.setRootIsDecorated(False)
        self.treeWidget.setHeaderLabels(type(self).Header)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.treeWidget)

    def appendResult(self, *args):
        item = SummaryTreeItem(*args)
        self.treeWidget.addTopLevelItem(item)
        for index in range(self.treeWidget.columnCount()):
            self.treeWidget.resizeColumnToContents(index)
        self.treeWidget.scrollToItem(item)
        header = type(self).Header
        row = {}
        for index in range(self.treeWidget.columnCount()):
            row.update({header[index]: item.text(index)})
        return row


class SummaryTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, timestamp, sample_name, sample_type, contact_name,
                 measurement_name, measurement_state):
        super().__init__([
            datetime.datetime.fromtimestamp(timestamp).isoformat(),
            sample_name,
            sample_type,
            contact_name,
            measurement_name,
            measurement_state
        ])
        # TODO
        if "Success" in self.text(5):
            self.setForeground(5, QtGui.QColor("green"))
        else:
            self.setForeground(5, QtGui.QColor("red"))
