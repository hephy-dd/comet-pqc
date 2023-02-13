import logging
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from comet_pqc.core import config
from comet_pqc.utils import make_path

from ..components import showException, showQuestion
from ..sequencemanager import SequenceManagerDialog
from .panel import Panel

__all__ = ["SamplePanel"]


class SamplePanel(Panel):

    sampleChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "Sample"

        self.namePrefixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.namePrefixLineEdit.setStatusTip("Sample name prefix")
        self.namePrefixLineEdit.setClearButtonEnabled(True)
        self.namePrefixLineEdit.editingFinished.connect(self.applySampleName)

        self.nameInfixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.nameInfixLineEdit.setStatusTip("Sample name")
        self.nameInfixLineEdit.setClearButtonEnabled(True)
        self.nameInfixLineEdit.editingFinished.connect(self.applySampleName)

        self.nameSuffixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.nameSuffixLineEdit.setStatusTip("Sample name suffix")
        self.nameSuffixLineEdit.setClearButtonEnabled(True)
        self.nameSuffixLineEdit.editingFinished.connect(self.applySampleName)

        self.typeLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.typeLineEdit.setStatusTip("Sample type")
        self.typeLineEdit.setClearButtonEnabled(True)
        self.typeLineEdit.editingFinished.connect(self.applySampleName)

        self.positionLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.positionLineEdit.setStatusTip("Sample position on the chuck")
        self.positionLineEdit.setClearButtonEnabled(True)
        self.positionLineEdit.editingFinished.connect(self.applyPosition)

        self.sequenceNameLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sequenceNameLineEdit.setReadOnly(True)

        self.commentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.commentLineEdit.setStatusTip("Sample comment (optional)")
        self.commentLineEdit.setClearButtonEnabled(True)
        self.commentLineEdit.editingFinished.connect(self.applyComment)

        self.reloadButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.reloadButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadButton.setStatusTip("Reload sequence configuration from file")
        self.reloadButton.clicked.connect(self.reloadConfig)

        self.sequenceManagerButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.sequenceManagerButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "gear.svg")))
        self.sequenceManagerButton.setStatusTip("Open sequence manager")
        self.sequenceManagerButton.clicked.connect(self.selectSequence)

        self.sampleGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.sampleGroupBox.setTitle("Sample")

        sequenceLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        sequenceLayout.addWidget(self.sequenceNameLineEdit)
        sequenceLayout.addWidget(self.reloadButton)
        sequenceLayout.addWidget(self.sequenceManagerButton)

        sampleGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.sampleGroupBox)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Type"), 1, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Position"), 2, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Comment"), 3, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Sequence"), 4, 0)
        sampleGroupBoxLayout.addWidget(self.namePrefixLineEdit, 0, 1)
        sampleGroupBoxLayout.addWidget(self.nameInfixLineEdit, 0, 2)
        sampleGroupBoxLayout.addWidget(self.nameSuffixLineEdit, 0, 3)
        sampleGroupBoxLayout.addWidget(self.typeLineEdit, 1, 1, 1, 3)
        sampleGroupBoxLayout.addWidget(self.positionLineEdit, 2, 1, 1, 3)
        sampleGroupBoxLayout.addWidget(self.commentLineEdit, 3, 1, 1, 3)
        sampleGroupBoxLayout.addLayout(sequenceLayout, 4, 1, 1, 3)
        sampleGroupBoxLayout.setColumnStretch(1, 3)
        sampleGroupBoxLayout.setColumnStretch(2, 7)
        sampleGroupBoxLayout.setColumnStretch(3, 3)

        self.panelLayout.insertWidget(2, self.sampleGroupBox)

    @QtCore.pyqtSlot()
    def applySampleName(self):
        if self.context:
            self.context.name_infix = self.nameInfixLineEdit.text()
            self.context.name_prefix = self.namePrefixLineEdit.text()
            self.context.name_suffix = self.nameSuffixLineEdit.text()
            self.context.sample_type = self.typeLineEdit.text()
            self.setTitle(f"{self.title} &rarr; {self.context.name}")
            self.sampleChanged.emit(self.context)

    @QtCore.pyqtSlot()
    def applyPosition(self):
        if self.context:
            self.context.sample_position = self.positionLineEdit.text()
            self.sampleChanged.emit(self.context)

    @QtCore.pyqtSlot()
    def applyComment(self):
        if self.context:
            self.context.setComment(self.commentLineEdit.text())
            self.sampleChanged.emit(self.context)

    @QtCore.pyqtSlot()
    def reloadConfig(self):
        if showQuestion(
            title="Reload Configuration",
            text="Do you want to reload sequence configuration from file?"
        ):
            try:
                if self.context.sequence:
                    filename = self.context.sequence.filename
                    sequence = config.load_sequence(filename)
                    self.context.load_sequence(sequence)
            except Exception as exc:
                logging.exception(exc)
                showException(exc)

    @QtCore.pyqtSlot()
    def selectSequence(self):
        try:
            dialog = SequenceManagerDialog(self)
            dialog.readSettings()
            dialog.readSequences()
            if dialog.exec() == dialog.Accepted:
                dialog.writeSequences()
                self.sequenceNameLineEdit.clear()
                sequence = dialog.currentSequence()
                if sequence is not None:
                    self.sequenceNameLineEdit.setText(f"{sequence.name}")
                    self.sequenceNameLineEdit.setToolTip(f"{sequence.filename}")
                    self.context.load_sequence(sequence)
                    self.sampleChanged.emit(self.context)
            dialog.writeSettings()
        except Exception as exc:
            logging.exception(exc)
            showException(exc)

    def mount(self, context) -> None:
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"{self.title} &rarr; {context.name}")
        self.setDescription("Current halfmoon sample")
        self.namePrefixLineEdit.setText(context.name_prefix)
        self.nameInfixLineEdit.setText(context.name_infix)
        self.nameSuffixLineEdit.setText(context.name_suffix)
        self.typeLineEdit.setText(context.sample_type)
        self.positionLineEdit.setText(context.sample_position)
        self.commentLineEdit.setText(context.comment())
        if context.sequence:
            self.sequenceNameLineEdit.setText(context.sequence.name)
        else:
            self.sequenceNameLineEdit.setText("")
        self.sampleGroupBox.show()

    def unmount(self) -> None:
        self.namePrefixLineEdit.clear()
        self.nameInfixLineEdit.clear()
        self.nameSuffixLineEdit.clear()
        self.typeLineEdit.clear()
        self.positionLineEdit.clear()
        self.commentLineEdit.clear()
        self.sequenceNameLineEdit.clear()
        self.sampleGroupBox.hide()
        super().unmount()

    def setLocked(self, state: bool) -> None:
        super().setLocked(state)
        self.sampleGroupBox.setEnabled(not state)
