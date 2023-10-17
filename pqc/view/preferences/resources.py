from typing import Optional

from PyQt5 import QtWidgets

from comet import ResourceMixin
from comet.utils import escape_string, unescape_string

from pqc.settings import settings

__all__ = ["ResourcesWidget"]


class TextItem(QtWidgets.QTreeWidgetItem): ...


class TerminationItem(QtWidgets.QTreeWidgetItem): ...


class TimeoutItem(QtWidgets.QTreeWidgetItem): ...


class ResourceItem(QtWidgets.QTreeWidgetItem):

    def __init__(self) -> None:
        super().__init__()
        self.resourceNameItem = TextItem(self, ["Resource Name"])
        self.readTerminationItem = TerminationItem(self, ["Read Termination"])
        self.writeTerminationItem = TerminationItem(self, ["Write Termination"])
        self.timeoutItem = TimeoutItem(self, ["Timeout"])
        self.visaLibraryItem = TextItem(self, ["Visa Library"])

    def name(self) -> str:
        return self.text(0)

    def setName(self, name: str) -> None:
        self.setText(0, name)

    def resourceName(self) -> str:
        return self.resourceNameItem.text(1)

    def setResourceName(self, name: str) -> None:
        self.resourceNameItem.setText(1, name)

    def readTermination(self) -> str:
        return self.readTerminationItem.text(1)

    def setReadTermination(self, termination: str) -> None:
        self.readTerminationItem.setText(1, termination)

    def writeTermination(self) -> str:
        return self.writeTerminationItem.text(1)

    def setWriteTermination(self, termination: str) -> None:
        self.writeTerminationItem.setText(1, termination)

    def timeout(self) -> str:
        return self.timeoutItem.text(1)

    def setTimeout(self, timeout: str) -> None:
        self.timeoutItem.setText(1, timeout)

    def visaLibrary(self) -> str:
        return self.visaLibraryItem.text(1)

    def setVisaLibrary(self, library: str) -> None:
        self.visaLibraryItem.setText(1, library)


class ResourcesWidget(ResourceMixin, QtWidgets.QWidget):

    default_write_termination = "\n"
    default_read_termination = "\n"
    default_timeout = 2000

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.treeWidget = QtWidgets.QTreeWidget(self)
        self.treeWidget.setHeaderLabels(["Resource", "Value"])
        self.treeWidget.currentItemChanged.connect(self.itemSelected)
        self.treeWidget.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.editButton = QtWidgets.QPushButton(self)
        self.editButton.setText("&Edit")
        self.editButton.setEnabled(False)
        self.editButton.clicked.connect(self.editItem)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.treeWidget, 0, 0, 2, 1)
        layout.addWidget(self.editButton, 0, 1)
        layout.setRowStretch(1, 1)

    def readSettings(self) -> None:
        self.treeWidget.clear()
        resources = settings.settings.get("resources") or {}
        for key, resource in self.resources.items():
            item = ResourceItem()
            item.setName(key)
            self.treeWidget.addTopLevelItem(item)
            item.setExpanded(True)
            d = resources.get(key) or {}
            resource_name = d.get("resource_name") or resource.resource_name
            read_termination = d.get("read_termination") or resource.options.get("read_termination") or self.default_read_termination
            write_termination = d.get("write_termination") or resource.options.get("write_termination") or self.default_write_termination
            timeout = d.get("timeout") or resource.options.get("timeout") or self.default_timeout
            visa_library = d.get("visa_library") or resource.visa_library
            item.setResourceName(resource_name)
            item.setReadTermination(escape_string(read_termination))
            item.setWriteTermination(escape_string(write_termination))
            item.setTimeout(format(timeout))
            item.setVisaLibrary(visa_library)
        self.treeWidget.resizeColumnToContents(0)

    def writeSettings(self) -> None:
        resources = {}
        for index in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(index)
            if isinstance(item, ResourceItem):
                try:
                    timeout = int(item.timeout())
                except ValueError:
                    timeout = self.default_timeout
                resources[item.name()] = {
                    "resource_name": item.resourceName(),
                    "read_termination": unescape_string(item.readTermination()),
                    "write_termination": unescape_string(item.writeTermination()),
                    "timeout": timeout,
                    "visa_library": item.visaLibrary(),
                }
        settings.settings["resources"] = resources

    def editItem(self) -> None:
        item = self.treeWidget.currentItem()
        if isinstance(item, TextItem):
            text, success = QtWidgets.QInputDialog.getText(self, "", "", QtWidgets.QLineEdit.Normal, item.text(1))
            if success:
                item.setText(1, text)
        elif isinstance(item, TerminationItem):
            items = ["\\r\\n", "\\n", "\\r"]
            index = items.index(item.text(1)) if item.text(1) in items else 0
            text, success = QtWidgets.QInputDialog.getItem(self, "Termination", "Set termination character(s).", items, index, False)
            if success:
                item.setText(1, text)
        elif isinstance(item, TimeoutItem):
            try:
                value = int(item.text(1))
            except:
                value = 4000
            value, success = QtWidgets.QInputDialog.getInt(self, "Timeout", "Set timeout in milliseconds.", value, 0, 60000)
            if success:
                item.setText(1, format(value))

    def itemSelected(self, current, previous):
        self.editButton.setEnabled(current is not None and not current.childCount())

    def itemDoubleClicked(self, item, index):
        self.editItem()
