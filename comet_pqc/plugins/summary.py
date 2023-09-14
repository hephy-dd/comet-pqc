import os
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.formatter import CSVFormatter

__all__ = ["SummaryPlugin"]


SUMMARY_FILENAME = "summary.csv"


def get_color(text):
    if "success" in text.lower():
        return "green"
    return "red"


class SummaryWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tree_widget = QtWidgets.QTreeWidget(self)
        self.tree_widget.setHeaderLabels(["Time", "Sample", "Type", "Contact", "Measurement", "Result"])
        self.tree_widget.setRootIsDecorated(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tree_widget)

    def appendResult(self, data: dict):
        item = QtWidgets.QTreeWidgetItem()
        item.setText(0, datetime.fromtimestamp(data.get("timestamp", 0)).isoformat())
        item.setText(1, data.get("sample_name", ""))
        item.setText(2, data.get("sample_type", ""))
        item.setText(3, data.get("contact_name", ""))
        item.setText(4, data.get("measurement_name", ""))
        item.setText(5, data.get("measurement_state", ""))
        brush = QtGui.QBrush(QtGui.QColor(get_color(item.text(5))))
        item.setForeground(5, brush)
        self.tree_widget.addTopLevelItem(item)
        # Resize columns
        for column in range(self.tree_widget.columnCount()):
            self.tree_widget.resizeColumnToContents(column)
        # Scroll to last row
        self.tree_widget.scrollToItem(item)
        return item


class SummaryPlugin:

    def __init__(self, window) -> None:
        self.window = window

    def on_install(self) -> None:
        self.summaryWidget = SummaryWidget()
        self.window.addPage(self.summaryWidget, "Summary")

    def on_uninstall(self) -> None:
        self.window.removePage(self.summaryWidget)
        self.summaryWidget.deleteLater()

    def on_measurement_finished(self, data: dict) -> None:
        """Push result to summary and write to summary file (experimantal)."""
        item = self.summaryWidget.appendResult(data)  # TODO
        output_path = self.window.dashboard.outputDir()
        if output_path and os.path.exists(output_path):
            filename = os.path.join(output_path, SUMMARY_FILENAME)
            has_header = os.path.exists(filename)
            header = ["Time", "Sample", "Type", "Contact", "Measurement", "Result"]
            with open(filename, "a") as fp:
                fmt = CSVFormatter(fp)
                for key in header:
                    fmt.add_column(key)
                if not has_header:
                    fmt.write_header()
                fmt.write_row({name: item.text(i) for i, name in enumerate(header)})
