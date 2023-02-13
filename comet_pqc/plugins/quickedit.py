from typing import List, Optional

from PyQt5 import QtCore, QtWidgets

from ..view.components import showException
from ..view.sequencetreewidget import load_all_sequences, load_sequence
from . import Plugin

__all__ = ["QuickEditPlugin"]


class QuickEditPlugin(Plugin):

    def install(self, window):
        self.editButton: QtWidgets.QPushButton = QtWidgets.QPushButton()
        self.editButton.setText("Edit")
        self.editButton.setStatusTip("Quick edit properties of sequence items.")
        self.editButton.clicked.connect(self.editSequence)
        self.window = window
        widget = window.dashboard.sequence_widget
        widget.bottomLayout.insertWidget(3, self.editButton)
        window.dashboard.lockedStateChanged.connect(self.setLocked)

    def uninstall(self, window):
        widget = window.dashboard.sequence_widget
        window.dashboard.lockedStateChanged.disconnect(self.setLocked)
        index = widget.bottomLayout.indexOf(self.editButton)
        widget.bottomLayout.takeAt(index)

    def setLocked(self, state):
        self.editButton.setEnabled(not state)

    def editSequence(self):
        dashboard = self.window.dashboard
        try:
            sequences = load_all_sequences()
            dialog = EditSamplesDialog(dashboard.sampleItems(), sequences)
            dialog.exec()
        except Exception as exc:
            showException(exc)


class QuickEditItem(QtCore.QObject):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)

        self.enabledCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.enabledCheckBox.setToolTip(self.tr("Enable sample"))

        self.prefixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.prefixLineEdit.setClearButtonEnabled(True)
        self.prefixLineEdit.setMaximumWidth(192)
        self.prefixLineEdit.setToolTip(self.tr("Sample name prefix"))

        self.infixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.infixLineEdit.setClearButtonEnabled(True)
        self.infixLineEdit.setMinimumWidth(128)
        self.infixLineEdit.setToolTip(self.tr("Sample name infix"))

        self.suffixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.suffixLineEdit.setClearButtonEnabled(True)
        self.suffixLineEdit.setMaximumWidth(128)
        self.suffixLineEdit.setToolTip(self.tr("Sample name suffix"))

        self.typeLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.typeLineEdit.setClearButtonEnabled(True)
        self.typeLineEdit.setMaximumWidth(128)
        self.typeLineEdit.setToolTip(self.tr("Sample type"))

        self.positionLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.positionLineEdit.setClearButtonEnabled(True)
        self.positionLineEdit.setMaximumWidth(128)
        self.positionLineEdit.setToolTip(self.tr("Sample position"))

        self.sequenceComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.sequenceComboBox.setMinimumWidth(128)
        self.sequenceComboBox.setToolTip(self.tr("Select sample sequence"))
        self.sequenceComboBox.addItem("", None)

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

    def positionName(self) -> str:
        return self.positionLineEdit.text()

    def setPositionName(self, name: str) -> None:
        self.positionLineEdit.setText(name)

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
        self.setWindowTitle(self.tr("Quick Edit Samples"))
        self.setMinimumSize(640, 240)

        self._items: List[QuickEditItem] = []

        self.prefixLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.prefixLabel.setText(self.tr("Prefix"))

        self.nameLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.nameLabel.setText(self.tr("Name"))

        self.suffixLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.suffixLabel.setText(self.tr("Suffix"))

        self.typeLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.typeLabel.setText(self.tr("Type"))

        self.postitionLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.postitionLabel.setText(self.tr("Position"))

        self.sequenceLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.sequenceLabel.setText(self.tr("Sequence"))

        self.gridLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
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

        self.scrollAreaWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        self.gridWrapperLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.scrollAreaWidget)
        self.gridWrapperLayout.addLayout(self.gridLayout)
        self.gridWrapperLayout.addStretch()

        self.scrollArea: QtWidgets.QScrollArea = QtWidgets.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scrollAreaWidget)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.scrollArea)
        layout.addWidget(self.buttonBox)

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("QuickEditDialog")

        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreGeometry(geometry)

        settings.endGroup()

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("QuickEditDialog")

        settings.setValue("geometry", self.saveGeometry())

        settings.endGroup()

    def addItem(self, item: QuickEditItem) -> None:
        self._items.append(item)
        item.setParent(self)
        row = self.gridLayout.rowCount()
        for column, widget in enumerate(item.widgets()):
            self.gridLayout.addWidget(widget, row, column)

    def items(self) -> List[QuickEditItem]:
        return list(self._items)


class EditSamplesDialog:  # TODO
    """Quick edit all samples at once dialog."""

    def __init__(self, samples: List, sequences: List) -> None:
        self.samples: List = samples
        self.sequences: List = sequences

    def populateDialog(self, dialog):
        for sample_item in self.samples:
            item = QuickEditItem()
            item.setEnabled(sample_item.isEnabled())
            item.setPrefix(sample_item.name_prefix)
            item.setInfix(sample_item.name_infix)
            item.setSuffix(sample_item.name_suffix)
            item.setType(sample_item.sample_type)
            item.setPositionName(sample_item.sample_position)
            for name, filename in self.sequences:
                item.addSequence(name)
            if sample_item.sequence is not None:
                item.setCurrentSequence(sample_item.sequence.name)
            item.setProperty("sample_item", sample_item)
            dialog.addItem(item)

    def updateSamplesFromDialog(self, dialog):
        for item in dialog.items():
            sample_item = item.property("sample_item")
            sample_item.setEnabled(item.isEnabled())
            sample_item.name_prefix = item.prefix()
            sample_item.name_infix = item.infix()
            sample_item.name_suffix = item.suffix()
            sample_item.sample_type = item.type()
            sample_item.sample_position = item.positionName()
            for name, filename in self.sequences:
                if item.currentSequence() == name:
                    sequence = load_sequence(filename)
                    sample_item.load_sequence(sequence)

    def exec(self):  # TODO
        dialog = QuickEditDialog()
        dialog.readSettings()
        self.populateDialog(dialog)
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            self.updateSamplesFromDialog(dialog)
        dialog.writeSettings()
