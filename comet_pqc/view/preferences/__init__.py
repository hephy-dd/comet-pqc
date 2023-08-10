from typing import Optional

from PyQt5 import QtCore, QtWidgets

from comet import ResourceMixin
from comet.utils import escape_string, unescape_string

from comet_pqc.settings import settings
from .options import OptionsWidget
from .table import TableWidget

__all__ = ["PreferencesDialog"]


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
            item = QtWidgets.QTreeWidgetItem([key])
            self.treeWidget.addTopLevelItem(item)
            item.setExpanded(True)
            d = resources.get(key) or {}
            resource_name = d.get("resource_name") or resource.resource_name
            read_termination = d.get("read_termination") or resource.options.get("read_termination") or self.default_read_termination
            write_termination = d.get("write_termination") or resource.options.get("write_termination") or self.default_write_termination
            timeout = d.get("timeout") or resource.options.get("timeout") or self.default_timeout
            visa_library = d.get("visa_library") or resource.visa_library
            item.addChild(QtWidgets.QTreeWidgetItem(["resource_name", resource_name]))
            item.addChild(QtWidgets.QTreeWidgetItem(["read_termination", escape_string(read_termination)]))
            item.addChild(QtWidgets.QTreeWidgetItem(["write_termination", escape_string(write_termination)]))
            item.addChild(QtWidgets.QTreeWidgetItem(["timeout", format(timeout)]))
            item.addChild(QtWidgets.QTreeWidgetItem(["visa_library", visa_library]))
        self.treeWidget.resizeColumnToContents(0)

    def writeSettings(self) -> None:
        resources = {}
        for index in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(index)
            try:
                timeout = int(item.child(3).text(1))
            except ValueError:
                timeout = self.default_timeout
            resources[item.text(0)] = {
                "resource_name": item.child(0).text(1),
                "read_termination": unescape_string(item.child(1).text(1)),
                "write_termination": unescape_string(item.child(2).text(1)),
                "timeout": timeout,
                "visa_library": item.child(4).text(1),
            }
        settings.settings["resources"] = resources

    def editItem(self) -> None:
        item = self.treeWidget.currentItem()
        if item is not None and not item.childCount():
            text, success = QtWidgets.QInputDialog.getText(self, "", "", QtWidgets.QLineEdit.Normal, item.text(1))
            if success:
                item.setText(1, text)

    def itemSelected(self, current, previous):
        self.editButton.setEnabled(current is not None and not current.childCount())

    def itemDoubleClicked(self, item, index):
        self.editItem()


class PreferencesDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")

        self.tabWidget = QtWidgets.QTabWidget(self)

        self.resources_tab = ResourcesWidget(self)
        self.tabWidget.addTab(self.resources_tab, "Resources")

        self.tableWidget = TableWidget(self)
        self.tabWidget.addTab(self.tableWidget, "Table")

        self.optionsWidget = OptionsWidget(self)
        self.tabWidget.addTab(self.optionsWidget, "Options")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

    def writeSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            widget.writeSettings()
        QtWidgets.QMessageBox.information(self, "Restart Required", "Application restart required for changes to take effect.")

    def readSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            widget.readSettings()
