from typing import List

from PyQt5 import QtCore
from PyQt5 import QtWidgets

__all__ = ['QuickEditDialog']


class QuickEditItem(QtCore.QObject):

    def __init__(self, parent: QtCore.QObject = None) -> None:
        super().__init__(parent)

        self._enabledCheckBox = QtWidgets.QCheckBox()
        self._enabledCheckBox.setToolTip(self.tr("Enable sample"))

        self._prefixLineEdit = QtWidgets.QLineEdit()
        self._prefixLineEdit.setClearButtonEnabled(True)
        self._prefixLineEdit.setMaximumWidth(192)
        self._prefixLineEdit.setToolTip(self.tr("Sample name prefix"))

        self._infixLineEdit = QtWidgets.QLineEdit()
        self._infixLineEdit.setClearButtonEnabled(True)
        self._infixLineEdit.setMinimumWidth(128)
        self._infixLineEdit.setToolTip(self.tr("Sample name infix"))

        self._suffixLineEdit = QtWidgets.QLineEdit()
        self._suffixLineEdit.setClearButtonEnabled(True)
        self._suffixLineEdit.setMaximumWidth(128)
        self._suffixLineEdit.setToolTip(self.tr("Sample name suffix"))

        self._typeLineEdit = QtWidgets.QLineEdit()
        self._typeLineEdit.setClearButtonEnabled(True)
        self._typeLineEdit.setMaximumWidth(128)
        self._typeLineEdit.setToolTip(self.tr("Sample type"))

        self._positionLineEdit = QtWidgets.QLineEdit()
        self._positionLineEdit.setClearButtonEnabled(True)
        self._positionLineEdit.setMaximumWidth(128)
        self._positionLineEdit.setToolTip(self.tr("Sample position"))

        self._sequenceComboBox = QtWidgets.QComboBox()
        self._sequenceComboBox.setMinimumWidth(128)
        self._sequenceComboBox.setToolTip(self.tr("Select sample sequence"))

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

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Quick Edit Samples"))
        self.setMinimumSize(640, 240)

        self._items: List[QuickEditItem] = []

        self._prefixLabel = QtWidgets.QLabel()
        self._prefixLabel.setText(self.tr("Prefix"))

        self._nameLabel = QtWidgets.QLabel()
        self._nameLabel.setText(self.tr("Name"))

        self._suffixLabel = QtWidgets.QLabel()
        self._suffixLabel.setText(self.tr("Suffix"))

        self._typeLabel = QtWidgets.QLabel()
        self._typeLabel.setText(self.tr("Type"))

        self._postitionLabel = QtWidgets.QLabel()
        self._postitionLabel.setText(self.tr("Position"))

        self._sequenceLabel = QtWidgets.QLabel()
        self._sequenceLabel.setText(self.tr("Sequence"))

        self._gridLayout = QtWidgets.QGridLayout()
        self._gridLayout.addWidget(self._prefixLabel, 0, 1)
        self._gridLayout.addWidget(self._nameLabel, 0, 2)
        self._gridLayout.addWidget(self._suffixLabel, 0, 3)
        self._gridLayout.addWidget(self._typeLabel, 0, 4)
        self._gridLayout.addWidget(self._postitionLabel, 0, 5)
        self._gridLayout.addWidget(self._sequenceLabel, 0, 6)

        self._gridLayout.setColumnStretch(0, 0)
        self._gridLayout.setColumnStretch(1, 9)
        self._gridLayout.setColumnStretch(2, 14)
        self._gridLayout.setColumnStretch(3, 7)
        self._gridLayout.setColumnStretch(4, 9)
        self._gridLayout.setColumnStretch(5, 9)

        self._scrollAreaWidget = QtWidgets.QWidget()

        self._gridWrapperLayout = QtWidgets.QVBoxLayout(self._scrollAreaWidget)
        self._gridWrapperLayout.addLayout(self._gridLayout)
        self._gridWrapperLayout.addStretch()

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
        row = self._gridLayout.rowCount()
        for column, widget in enumerate(item.widgets()):
            self._gridLayout.addWidget(widget, row, column)
        self._items.append(item)
        return item

    def items(self) -> List[QuickEditItem]:
        return list(self._items)
