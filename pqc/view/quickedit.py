from typing import List, Optional

from PyQt5 import QtCore, QtWidgets

__all__ = ["QuickEditDialog"]


class QuickEditItem(QtCore.QObject):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)

        self.enabledCheckBox = QtWidgets.QCheckBox()
        self.enabledCheckBox.setToolTip("Enable sample")

        self.prefixLineEdit = QtWidgets.QLineEdit()
        self.prefixLineEdit.setClearButtonEnabled(True)
        self.prefixLineEdit.setMaximumWidth(192)
        self.prefixLineEdit.setToolTip("Sample name prefix")

        self.infixLineEdit = QtWidgets.QLineEdit()
        self.infixLineEdit.setClearButtonEnabled(True)
        self.infixLineEdit.setMinimumWidth(128)
        self.infixLineEdit.setToolTip("Sample name infix")

        self.suffixLineEdit = QtWidgets.QLineEdit()
        self.suffixLineEdit.setClearButtonEnabled(True)
        self.suffixLineEdit.setMaximumWidth(128)
        self.suffixLineEdit.setToolTip("Sample name suffix")

        self.typeLineEdit = QtWidgets.QLineEdit()
        self.typeLineEdit.setClearButtonEnabled(True)
        self.typeLineEdit.setMaximumWidth(128)
        self.typeLineEdit.setToolTip("Sample type")

        self.positionLineEdit = QtWidgets.QLineEdit()
        self.positionLineEdit.setClearButtonEnabled(True)
        self.positionLineEdit.setMaximumWidth(128)
        self.positionLineEdit.setToolTip("Sample position")

        self.sequenceComboBox = QtWidgets.QComboBox()
        self.sequenceComboBox.setMinimumWidth(128)
        self.sequenceComboBox.setToolTip("Select sample sequence")

        self._widgets: List[QtWidgets.QWidget] = [
            self.enabledCheckBox,
            self.prefixLineEdit,
            self.infixLineEdit,
            self.suffixLineEdit,
            self.typeLineEdit,
            self.positionLineEdit,
            self.sequenceComboBox
        ]

    def widgets(self) -> List[QtWidgets.QWidget]:
        return list(self._widgets)

    def isEnabled(self) -> bool:
        return self.enabledCheckBox.isChecked()

    def setEnabled(self, enabled: bool) -> None:
        self.enabledCheckBox.setChecked(enabled)

    def prefix(self) -> str:
        return self.prefixLineEdit.text()

    def setPrefix(self, prefix: str) -> None:
        self.prefixLineEdit.setText(prefix)

    def infix(self) -> str:
        return self.infixLineEdit.text()

    def setInfix(self, infix: str) -> None:
        self.infixLineEdit.setText(infix)

    def suffix(self) -> str:
        return self.suffixLineEdit.text()

    def setSuffix(self, suffix: str) -> None:
        self.suffixLineEdit.setText(suffix)

    def type(self) -> str:
        return self.typeLineEdit.text()

    def setType(self, type: str) -> None:
        self.typeLineEdit.setText(type)

    def positionLabel(self) -> str:
        return self.positionLineEdit.text()

    def setPositionLabel(self, label: str) -> None:
        self.positionLineEdit.setText(label)

    def addSequence(self, sequence: str) -> None:
        self.sequenceComboBox.addItem(sequence, sequence)

    def setCurrentSequence(self, sequence: str) -> None:
        index = self.sequenceComboBox.findData(sequence)
        self.sequenceComboBox.setCurrentIndex(index)

    def currentSequence(self) -> str:
        return self.sequenceComboBox.currentData()


class QuickEditDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quick Edit Samples")
        self.setMinimumSize(640, 240)

        self._items: List[QuickEditItem] = []

        self.prefixLabel = QtWidgets.QLabel(self)
        self.prefixLabel.setText("Prefix")

        self.nameLabel = QtWidgets.QLabel()
        self.nameLabel.setText("Name")

        self.suffixLabel = QtWidgets.QLabel()
        self.suffixLabel.setText("Suffix")

        self.typeLabel = QtWidgets.QLabel()
        self.typeLabel.setText("Type")

        self.postitionLabel = QtWidgets.QLabel()
        self.postitionLabel.setText("Position")

        self.sequenceLabel = QtWidgets.QLabel()
        self.sequenceLabel.setText("Sequence")

        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.addWidget(self.prefixLabel, 0, 1)
        self.gridLayout.addWidget(self.nameLabel, 0, 2)
        self.gridLayout.addWidget(self.suffixLabel, 0, 3)
        self.gridLayout.addWidget(self.typeLabel, 0, 4)
        self.gridLayout.addWidget(self.postitionLabel, 0, 5)
        self.gridLayout.addWidget(self.sequenceLabel, 0, 6)

        self.gridLayout.setColumnStretch(0, 0)
        self.gridLayout.setColumnStretch(1, 9)
        self.gridLayout.setColumnStretch(2, 14)
        self.gridLayout.setColumnStretch(3, 7)
        self.gridLayout.setColumnStretch(4, 9)
        self.gridLayout.setColumnStretch(5, 9)

        self.scrollAreaWidget = QtWidgets.QWidget(self)

        scrollAreaWidgetLayout = QtWidgets.QVBoxLayout(self.scrollAreaWidget)
        scrollAreaWidgetLayout.addLayout(self.gridLayout)
        scrollAreaWidgetLayout.addStretch()

        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scrollAreaWidget)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.scrollArea)
        layout.addWidget(self.buttonBox)

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("quickedit")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        settings.endGroup()
        self.restoreGeometry(geometry)

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("quickedit")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()

    def addItem(self) -> QuickEditItem:
        item = QuickEditItem(self)
        row = self.gridLayout.rowCount()
        for column, widget in enumerate(item.widgets()):
            self.gridLayout.addWidget(widget, row, column)
        self._items.append(item)
        return item

    def items(self) -> List[QuickEditItem]:
        return list(self._items)
