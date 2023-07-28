from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core import config
from ..sequence import SequenceManagerDialog
from ..utils import handle_exception, make_path
from .panel import BasicPanel

__all__ = ["SamplePanel"]


class SamplePanel(BasicPanel):

    sampleChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.sampleNamePrefixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sampleNamePrefixLineEdit.setToolTip("Sample name prefix")
        self.sampleNamePrefixLineEdit.setClearButtonEnabled(True)
        self.sampleNamePrefixLineEdit.editingFinished.connect(self.updateSampleName)

        self.sampleNameInfixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sampleNameInfixLineEdit.setToolTip("Sample name")
        self.sampleNameInfixLineEdit.setClearButtonEnabled(True)
        self.sampleNameInfixLineEdit.editingFinished.connect(self.updateSampleName)

        self.sampleNameSuffixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sampleNameSuffixLineEdit.setToolTip("Sample name suffix")
        self.sampleNameSuffixLineEdit.setClearButtonEnabled(True)
        self.sampleNameSuffixLineEdit.editingFinished.connect(self.updateSampleName)

        self.sampleTypeLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sampleTypeLineEdit.setToolTip("Sample type")
        self.sampleTypeLineEdit.setClearButtonEnabled(True)
        self.sampleTypeLineEdit.editingFinished.connect(self.updateSampleType)

        self.samplePositionLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.samplePositionLineEdit.setToolTip("Sample position on the chuck")
        self.samplePositionLineEdit.setClearButtonEnabled(True)
        self.samplePositionLineEdit.editingFinished.connect(self.updateSamplePosition)

        self.sequenceLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sequenceLineEdit.setReadOnly(True)

        self.sampleCommentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sampleCommentLineEdit.setToolTip("Sample comment (optional)")
        self.sampleCommentLineEdit.setClearButtonEnabled(True)
        self.sampleCommentLineEdit.editingFinished.connect(self.updateSampleComment)

        self.reloadSequenceButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.reloadSequenceButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadSequenceButton.setToolTip("Reload sequence configuration from file.")
        self.reloadSequenceButton.clicked.connect(self.reloadSequence)

        self.editSequenceButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.editSequenceButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "gear.svg")))
        self.editSequenceButton.setToolTip("Open sequence manager")
        self.editSequenceButton.clicked.connect(self.showSequenceManager)

        self.sampleGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.sampleGroupBox.setTitle("Sample")

        sampleNameLayout = QtWidgets.QHBoxLayout()
        sampleNameLayout.addWidget(self.sampleNamePrefixLineEdit, 3)
        sampleNameLayout.addWidget(self.sampleNameInfixLineEdit, 7)
        sampleNameLayout.addWidget(self.sampleNameSuffixLineEdit, 3)

        sampleSequenceLayout = QtWidgets.QHBoxLayout()
        sampleSequenceLayout.addWidget(self.sequenceLineEdit, 1)
        sampleSequenceLayout.addWidget(self.reloadSequenceButton, 0)
        sampleSequenceLayout.addWidget(self.editSequenceButton, 0)

        sampleGroupBoxLayout = QtWidgets.QGridLayout(self.sampleGroupBox)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Type"), 1, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Position"), 2, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Comment"), 3, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Sequence"), 4, 0)
        sampleGroupBoxLayout.addLayout(sampleNameLayout, 0, 1)
        sampleGroupBoxLayout.addWidget(self.sampleTypeLineEdit, 1, 1)
        sampleGroupBoxLayout.addWidget(self.samplePositionLineEdit ,2, 1)
        sampleGroupBoxLayout.addWidget(self.sampleCommentLineEdit, 3, 1)
        sampleGroupBoxLayout.addLayout(sampleSequenceLayout, 4, 1)
        sampleGroupBoxLayout.setColumnStretch(0, 0)
        sampleGroupBoxLayout.setColumnStretch(1, 1)

        self.layout().insertWidget(2, self.sampleGroupBox)

    def updateSampleName(self) -> None:
        if self.context:
            self.context.name_infix = self.sampleNameInfixLineEdit.text()
            self.context.name_prefix = self.sampleNamePrefixLineEdit.text()
            self.context.name_suffix = self.sampleNameSuffixLineEdit.text()
            self.context.sample_type = self.sampleTypeLineEdit.text()
            self.setTitle(f"Sample &rarr; {self.context.name}")
            self.sampleChanged.emit(self.context)

    def updateSampleType(self) -> None:
        if self.context:
            self.context.sample_type = self.sampleTypeLineEdit.text()
            self.sampleChanged.emit(self.context)

    def updateSamplePosition(self) -> None:
        if self.context:
            self.context.sample_position = self.samplePositionLineEdit.text()
            self.sampleChanged.emit(self.context)

    def updateSampleComment(self) -> None:
        if self.context:
            self.context.comment = self.sampleCommentLineEdit.text()
            self.sampleChanged.emit(self.context)

    def reloadSequence(self) -> None:
        result = QtWidgets.QMessageBox.question(self, "Reload Configuration", "Do you want to reload sequence configuration from file?")
        if result != QtWidgets.QMessageBox.Yes:
            return
        if self.context.sequence:
            filename = self.context.sequence.filename
            sequence = config.load_sequence(filename)
            self.context.load_sequence(sequence)

    def showSequenceManager(self) -> None:
        dialog = SequenceManagerDialog()
        dialog.readSettings()
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            dialog.writeSettings()
            self.sequenceLineEdit.clear()
            sequence = dialog.currentSequence()
            if sequence is not None:
                self.sequenceLineEdit.setValue(str(sequence.name))
                self.sequenceLineEdit.setToolTip(str(sequence.filename))
                self.context.load_sequence(sequence)
                self.sampleChanged.emit(self.context)

    def mount(self, context) -> None:
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"Sample &rarr; {context.name}")
        self.setDescription("Current halfmoon sample")
        self.sampleNamePrefixLineEdit.setText(context.name_prefix)
        self.sampleNameInfixLineEdit.setText(context.name_infix)
        self.sampleNameSuffixLineEdit.setText(context.name_suffix)
        self.sampleTypeLineEdit.setText(context.sample_type)
        self.samplePositionLineEdit.setText(context.sample_position)
        self.sampleCommentLineEdit.setText(context.comment)
        if context.sequence:
            self.sequenceLineEdit.setText(context.sequence.name)
        else:
            self.sequenceLineEdit.clear()

    def unmount(self) -> None:
        self.sampleNamePrefixLineEdit.clear()
        self.sampleNameInfixLineEdit.clear()
        self.sampleNameSuffixLineEdit.clear()
        self.sampleTypeLineEdit.clear()
        self.samplePositionLineEdit.clear()
        self.sampleCommentLineEdit.clear()
        self.sequenceLineEdit.clear()
        super().unmount()
