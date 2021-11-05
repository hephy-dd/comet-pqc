from typing import List

from PyQt5 import QtCore
from PyQt5 import QtWidgets

__all__ = ['QuickEditDialog']


class QuickEditItem(QtCore.QObject):

    def __init__(self, parent: QtCore.QObject = None) -> None:
        super().__init__(parent)

        self._enabledCheckBox = QtWidgets.QCheckBox()

        self._prefixLineEdit = QtWidgets.QLineEdit()
        self._prefixLineEdit.setClearButtonEnabled(True)
        self._prefixLineEdit.setToolTip("Sample name prefix")

        self._infixLineEdit = QtWidgets.QLineEdit()
        self._infixLineEdit.setClearButtonEnabled(True)
        self._infixLineEdit.setToolTip("Sample name infix")

        self._suffixLineEdit = QtWidgets.QLineEdit()
        self._suffixLineEdit.setClearButtonEnabled(True)
        self._suffixLineEdit.setToolTip("Sample name suffix")

        self._typeLineEdit = QtWidgets.QLineEdit()
        self._typeLineEdit.setClearButtonEnabled(True)
        self._typeLineEdit.setToolTip("Sample type")

        self._positionLineEdit = QtWidgets.QLineEdit()
        self._positionLineEdit.setClearButtonEnabled(True)
        self._positionLineEdit.setToolTip("Sample position")

        self._sequenceComboBox = QtWidgets.QComboBox()
        self._sequenceComboBox.setToolTip("Select sample sequence")

        self._widgets: List[QtWidgets.QWidget] = [
            self._enabledCheckBox,
            self._prefixLineEdit,
            self._infixLineEdit,
            self._suffixLineEdit,
            self._typeLineEdit,
            self._positionLineEdit,
            self._sequenceComboBox
        ]

    def widgets(self) -> List[QtWidgets.QWidget]:
        return list(self._widgets)

    def isEnabled(self) -> bool:
        return self._enabledCheckBox.isChecked()

    def setEnabled(self, enabled: bool) -> None:
        self._enabledCheckBox.setChecked(enabled)

    def prefix(self) -> str:
        return self._prefixLineEdit.text()

    def setPrefix(self, prefix: str) -> None:
        self._prefixLineEdit.setText(prefix)

    def infix(self) -> str:
        return self._infixLineEdit.text()

    def setInfix(self, infix: str) -> None:
        self._infixLineEdit.setText(infix)

    def suffix(self) -> str:
        return self._suffixLineEdit.text()

    def setSuffix(self, suffix: str) -> None:
        self._suffixLineEdit.setText(suffix)

    def type(self) -> str:
        return self._typeLineEdit.text()

    def setType(self, type: str) -> None:
        self._typeLineEdit.setText(type)

    def position(self) -> str:
        return self._positionLineEdit.text()

    def setPosition(self, position: str) -> None:
        self._positionLineEdit.setText(position)

    def addSequence(self, sequence: str) -> None:
        self._sequenceComboBox.addItem(sequence, sequence)

    def setCurrentSequence(self, sequence: str) -> None:
        index = self._sequenceComboBox.findData(sequence)
        self._sequenceComboBox.setCurrentIndex(index)

    def currentSequence(self) -> str:
        return self._sequenceComboBox.currentData()


class QuickEditDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Edit Samples")
        self.resize(320, 240)

        self._items: List[QuickEditItem] = []

        self._scrollAreaLayout = QtWidgets.QGridLayout()
        self._scrollAreaLayout.addWidget(QtWidgets.QLabel("Name"), 0, 2)
        self._scrollAreaLayout.addWidget(QtWidgets.QLabel("Type"), 0, 4)
        self._scrollAreaLayout.addWidget(QtWidgets.QLabel("Position"), 0, 5)
        self._scrollAreaLayout.addWidget(QtWidgets.QLabel("Sequence"), 0, 6)
        self._scrollAreaLayout.setColumnStretch(0, 0)
        self._scrollAreaLayout.setColumnStretch(1, 2)
        self._scrollAreaLayout.setColumnStretch(2, 3)
        self._scrollAreaLayout.setColumnStretch(3, 2)
        self._scrollAreaLayout.setColumnStretch(4, 1)
        self._scrollAreaLayout.setColumnStretch(5, 1)
        self._scrollAreaLayout.setColumnStretch(6, 1)

        self._scrollAreaWidget = QtWidgets.QWidget()

        layout2 = QtWidgets.QVBoxLayout(self._scrollAreaWidget)
        layout2.addLayout(self._scrollAreaLayout)
        layout2.addStretch()

        self._scrollArea = QtWidgets.QScrollArea()
        self._scrollArea.setWidgetResizable(True)
        self._scrollArea.setWidget(self._scrollAreaWidget)

        self._buttonBox = QtWidgets.QDialogButtonBox()
        self._buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self._buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self._buttonBox.accepted.connect(self.accept)
        self._buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._scrollArea)
        layout.addWidget(self._buttonBox)

    def addItem(self) -> QuickEditItem:
        item = QuickEditItem(self)
        row = self._scrollAreaLayout.rowCount()
        for column, widget in enumerate(item.widgets()):
            self._scrollAreaLayout.addWidget(widget, row, column)
        self._items.append(item)
        return item

    def items(self) -> List[QuickEditItem]:
        return list(self._items)
