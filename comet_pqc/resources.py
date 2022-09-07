import logging
from typing import List

from PyQt5 import QtCore, QtWidgets

__all__ = ["ResourcesDialog"]

logger = logging.getLogger(__name__)


class ResourceItem(QtWidgets.QTreeWidgetItem):

    DefaultModel: str = ""
    DefaultAddress: str = ""
    DefaultTermination: str = "\r\n"
    DefaultTimeout: float = 4.0

    NameColumn: int = 0

    def __init__(self) -> None:
        super().__init__()
        self._models: List[str] = []
        self._model: str = type(self).DefaultModel
        self._address: str = type(self).DefaultAddress
        self._termination: str = type(self).DefaultTermination
        self._timeout: float = type(self).DefaultTimeout

    def name(self) -> str:
        return self.text(type(self).NameColumn)

    def setName(self, name: str) -> None:
        self.setText(type(self).NameColumn, name)

    def models(self) -> List[str]:
        return self._models

    def setModels(self, models: List[str]) -> None:
        self._models.clear()
        self._models.extend(models)

    def model(self) -> str:
        return self._model

    def setModel(self, model: str) -> None:
        self._model = model

    def address(self) -> str:
        return self._address

    def setAddress(self, address: str) -> None:
        self._address = address

    def termination(self) -> str:
        return self._termination

    def setTermination(self, termination: str) -> None:
        self._termination = termination

    def timeout(self) -> float:
        return self._timeout

    def setTimeout(self, timeout: float) -> None:
        self._timeout = timeout


class ResourcesDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Resources")

        self._resourceTreeWidget = QtWidgets.QTreeWidget()
        self._resourceTreeWidget.setHeaderLabels(["Resources"])
        self._resourceTreeWidget.setRootIsDecorated(False)
        self._resourceTreeWidget.currentItemChanged.connect(self.itemChanged)

        self._modelLabel = QtWidgets.QLabel("Model")

        self._modelComboBox = QtWidgets.QComboBox()

        self._addressLabel = QtWidgets.QLabel("Address")

        self._addressLineEdit = QtWidgets.QLineEdit()

        self._terminationNameLabel = QtWidgets.QLabel("Termination")

        self._terminationComboBox = QtWidgets.QComboBox()
        self._terminationComboBox.addItem("CR+LF", "\r\n")
        self._terminationComboBox.addItem("LF", "\n")
        self._terminationComboBox.addItem("CR", "\r")

        self._timeoutNameLabel = QtWidgets.QLabel("Timeout")

        self._timeoutSpinBox = QtWidgets.QDoubleSpinBox()
        self._timeoutSpinBox.setDecimals(1)
        self._timeoutSpinBox.setRange(0, 60)
        self._timeoutSpinBox.setSuffix(" s")

        vBoxLayout = QtWidgets.QGridLayout()
        vBoxLayout.addWidget(self._addressLabel, 0, 0, 1, 3)
        vBoxLayout.addWidget(self._addressLineEdit, 1, 0, 1, 3)
        vBoxLayout.addWidget(self._modelLabel, 2, 0, 1, 1)
        vBoxLayout.addWidget(self._modelComboBox, 3, 0, 1, 1)
        vBoxLayout.addWidget(self._terminationNameLabel, 2, 1, 1, 1)
        vBoxLayout.addWidget(self._terminationComboBox, 3, 1, 1, 1)
        vBoxLayout.addWidget(self._timeoutNameLabel, 2, 2, 1, 1)
        vBoxLayout.addWidget(self._timeoutSpinBox, 3, 2, 1, 1)
        vBoxLayout.setColumnStretch(0, 5)
        vBoxLayout.setColumnStretch(1, 4)
        vBoxLayout.setColumnStretch(2, 4)
        vBoxLayout.setRowStretch(0, 0)
        vBoxLayout.setRowStretch(1, 0)
        vBoxLayout.setRowStretch(2, 0)
        vBoxLayout.setRowStretch(3, 0)
        vBoxLayout.setRowStretch(4, 1)

        hBoxLayout = QtWidgets.QHBoxLayout()
        hBoxLayout.addWidget(self._resourceTreeWidget)
        hBoxLayout.addLayout(vBoxLayout)
        hBoxLayout.setStretch(0, 3)
        hBoxLayout.setStretch(1, 5)

        self._buttonBox = QtWidgets.QDialogButtonBox()
        self._buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self._buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self._buttonBox.accepted.connect(self.accept)
        self._buttonBox.accepted.connect(self.updateCurrentItem)
        self._buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(hBoxLayout)
        layout.addWidget(self._buttonBox)

    def readSettings(self) -> None:
        """Load dialog specific settings."""
        settings = QtCore.QSettings()
        settings.beginGroup("ResourcesDialog")
        size = settings.value("size", QtCore.QSize(640, 480), QtCore.QSize)
        self.resize(size)
        settings.endGroup()

    def syncSettings(self) -> None:
        """Syncronize dialog specific settings."""
        settings = QtCore.QSettings()
        settings.beginGroup("ResourcesDialog")
        settings.setValue("size", self.size())
        settings.endGroup()

    def models(self) -> List[str]:
        models: List[str] = []
        for index in range(self._modelComboBox.count()):
            models.append(self._modelComboBox.itemText(index))
        return models

    def setModels(self, models: List[str]) -> None:
        self._modelComboBox.clear()
        self._modelComboBox.addItems(models)

    def model(self) -> str:
        return self._modelComboBox.currentText()

    def setModel(self, model: str) -> None:
        index: int = self._modelComboBox.findText(model)
        self._modelComboBox.setCurrentIndex(index)

    def address(self) -> str:
        return self._addressLineEdit.text().strip()

    def setAddress(self, address: str) -> None:
        self._addressLineEdit.setText(address)

    def termination(self) -> str:
        return self._terminationComboBox.currentData()

    def setTermination(self, termination: str) -> None:
        index: int = self._terminationComboBox.findData(termination)
        self._terminationComboBox.setCurrentIndex(index)

    def timeout(self) -> float:
        return float(self._timeoutSpinBox.value())

    def setTimeout(self, seconds: float) -> None:
        self._timeoutSpinBox.setValue(seconds)

    def loadItem(self, item) -> None:
        """Load inputs with item values."""
        self.setModels(item.models())
        self.setModel(item.model())
        self.setAddress(item.address())
        self.setTermination(item.termination())
        self.setTimeout(item.timeout())

    def updateItem(self, item) -> None:
        """Update item with values from inputs."""
        item.setModel(self.model())
        item.setAddress(self.address())
        item.setTermination(self.termination())
        item.setTimeout(self.timeout())

    def updateCurrentItem(self) -> None:
        """Update current item with values from inputs."""
        item = self._resourceTreeWidget.currentItem()
        if item:
            self.updateItem(item)

    def itemChanged(self, current, previous) -> None:
        """Called when selected item changed."""
        if previous:
            self.updateItem(previous)
        if current:
            self.loadItem(current)

    def addResourceItem(self, item) -> None:
        self._resourceTreeWidget.addTopLevelItem(item)
        # Select first item in tree to initialize inputs
        if not self._resourceTreeWidget.currentItem():
            self._resourceTreeWidget.setCurrentItem(item)

    def addResource(self, name: str, values: dict) -> None:
        """Add resource item to tree view."""
        models = values.get("models", [])
        model = values.get("model", ResourceItem.DefaultModel)
        address = values.get("address", ResourceItem.DefaultAddress)
        termination = values.get("termination", ResourceItem.DefaultTermination)
        timeout = values.get("timeout", ResourceItem.DefaultTimeout)
        item = ResourceItem()
        item.setName(name)
        item.setModels(models)
        item.setModel(model)
        item.setAddress(address)
        item.setTermination(termination)
        item.setTimeout(timeout)
        self.addResourceItem(item)

    def setResources(self, resources: dict) -> None:
        """Set resources from dictionary."""
        self._resourceTreeWidget.clear()
        for name, values in resources.items():
            self.addResource(name, values)

    def resources(self) -> dict:
        """Return resources dictionary."""
        resources: dict = {}
        for index in range(self._resourceTreeWidget.topLevelItemCount()):
            item = self._resourceTreeWidget.topLevelItem(index)
            if isinstance(item, ResourceItem):
                resource = resources.setdefault(item.name(), {})
                resource["model"] = item.model()
                resource["address"] = item.address()
                resource["termination"] = item.termination()
                resource["timeout"] = item.timeout()
        return resources
