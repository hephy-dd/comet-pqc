import datetime
import logging
import os
from typing import Optional

from PyQt5 import QtGui, QtWidgets

from ..core.formatter import CSVFormatter
from ..settings import settings
from ..view.components import showException
from . import Plugin

__all__ = ["SummaryPlugin"]

logger = logging.getLogger(__name__)


def append_summary(data: dict, filename: str) -> None:
    has_header = os.path.exists(filename)
    with open(filename, "a") as fp:
        fmt = CSVFormatter(fp)
        for key in data.keys():
            fmt.add_column(key)
        if not has_header:
            fmt.write_header()
        fmt.write_row(data)


class SummaryPlugin(Plugin):

    def install(self, window):
        self.window = window
        self.summaryWidget = SummaryWidget()
        window.dashboard.addTabWidget(self.summaryWidget, "Summary")
        window.dashboard.summary.connect(self.appendSummary)

    def uninstall(self, window):
        window.dashboard.summary.disconnect(self.appendSummary)
        window.dashboard.removeTabWidget(self.summaryWidget)
        del self.window

    def appendSummary(self, data):
        """Push result to summary and write to summary file (experimantal)."""
        try:
            data = self.summaryWidget.appendResult(data)  # TODO
            output_path = self.window.dashboard.outputDir()
            if os.path.exists(output_path):
                filename = os.path.join(output_path, settings.value("summary_filename", "summary.csv", str))
                append_summary(data, filename)
        except Exception as exc:
            showException(exc)


class SummaryWidget(QtWidgets.QWidget):

    Header = ["Time", "Sample", "Type", "Contact", "Measurement", "Result"]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.treeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.treeWidget.setRootIsDecorated(False)
        self.treeWidget.setHeaderLabels(type(self).Header)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.treeWidget)

    def appendResult(self, data):
        item = SummaryTreeItem(**data)
        self.treeWidget.addTopLevelItem(item)
        for index in range(self.treeWidget.columnCount()):
            self.treeWidget.resizeColumnToContents(index)
        self.treeWidget.scrollToItem(item)
        # TODO clean up!
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
