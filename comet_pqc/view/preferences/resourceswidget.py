from PyQt5 import QtCore, QtWidgets

from comet.resource import ResourceMixin
from comet.utils import escape_string, unescape_string

from .preferencesdialog import PreferencesWidget

from ...settings import settings
from ..components import showInfo

__all__ = ["ResourcesWidget"]


class ResourcesWidget(PreferencesWidget, ResourceMixin):

    default_write_termination = "\n"
    default_read_termination = "\n"
    default_timeout = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.treeWidget = QtWidgets.QTreeWidget(self)
        self.treeWidget.setHeaderLabels(["Resource", "Value"])
        self.treeWidget.currentItemChanged.connect(self.itemChanged)
        self.treeWidget.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.editButton = QtWidgets.QPushButton(self)
        self.editButton.setText("&Edit")
        self.editButton.setEnabled(False)
        self.editButton.clicked.connect(self.editItem)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.treeWidget, 0, 0, 2, 1)
        layout.addWidget(self.editButton, 0, 1)
        layout.setRowStretch(1, 1)

    def readSettings(self):
        self.treeWidget.clear()
        resources = settings.value("resources", {}, dict)
        for key, resource in self.resources.items():
            item = QtWidgets.QTreeWidgetItem([key])
            self.treeWidget.addTopLevelItem(item)
            item.setExpanded(True)
            d = resources.get(key, {})
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
        self.treeWidget.resizeColumnToContents(1)

    def writeSettings(self):
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
        settings.setValue("resources", resources)

    def editItem(self):
        item = self.treeWidget.currentItem()
        if item and item.parent():
            text, success = QtWidgets.QInputDialog.getText(
                self,
                item.parent().text(0),
                item.text(0),
                QtWidgets.QLineEdit.Normal,
                item.text(1),
            )
            if success:
                item.setText(1, text)

    def itemChanged(self, current, previous):
        self.editButton.setEnabled(current is not None and current.parent() is not None)

    def itemDoubleClicked(self, item, column):
        self.editItem()
