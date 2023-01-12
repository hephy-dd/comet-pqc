import logging
from typing import Optional

from comet.settings import SettingsMixin
from PyQt5 import QtCore, QtGui, QtWidgets

from ..core import config
from ..sequence import SequenceManager
from ..utils import make_path, show_exception
from .panel import Panel

__all__ = ["SamplePanel"]


class SamplePanel(Panel, SettingsMixin):

    type_name = "sample"

    sampleChanged: QtCore.pyqtSignal = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Sample")

        self.namePrefixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.namePrefixLineEdit.setStatusTip("Sample name prefix")
        self.namePrefixLineEdit.setClearButtonEnabled(True)
        self.namePrefixLineEdit.editingFinished.connect(self.updateSampleName)

        self.nameInfixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.nameInfixLineEdit.setStatusTip("Sample name")
        self.nameInfixLineEdit.setClearButtonEnabled(True)
        self.nameInfixLineEdit.editingFinished.connect(self.updateSampleName)

        self.nameSuffixLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.nameSuffixLineEdit.setStatusTip("Sample name suffix")
        self.nameSuffixLineEdit.setClearButtonEnabled(True)
        self.nameSuffixLineEdit.editingFinished.connect(self.updateSampleName)

        self.typeLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.typeLineEdit.setStatusTip("Sample type")
        self.typeLineEdit.setClearButtonEnabled(True)
        self.typeLineEdit.editingFinished.connect(self.updateSampleName)

        self.positionLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.positionLineEdit.setStatusTip("Sample position on the chuck")
        self.positionLineEdit.setClearButtonEnabled(True)
        self.positionLineEdit.editingFinished.connect(self.on_sample_position_edited)

        self.sequenceLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.sequenceLineEdit.setReadOnly(True)

        self.commentLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.commentLineEdit.setStatusTip("Sample comment (optional)")
        self.commentLineEdit.setClearButtonEnabled(True)
        self.commentLineEdit.editingFinished.connect(self.updateComment)

        self.reloadSequenceButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.reloadSequenceButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "reload.svg")))
        self.reloadSequenceButton.setStatusTip("Reload sequence configuration from file.")
        self.reloadSequenceButton.clicked.connect(self.reloadSequenceFromFile)

        self.sequenceManagerButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.sequenceManagerButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "gear.svg")))
        self.sequenceManagerButton.setStatusTip("Open sequence manager")
        self.sequenceManagerButton.clicked.connect(self.showSequenceManager)

        self.sampleGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.sampleGroupBox.setTitle("Sample")

        sampleNameLayout = QtWidgets.QHBoxLayout()
        sampleNameLayout.addWidget(self.namePrefixLineEdit, 3)
        sampleNameLayout.addWidget(self.nameInfixLineEdit, 7)
        sampleNameLayout.addWidget(self.nameSuffixLineEdit, 3)

        sequenceLayout = QtWidgets.QHBoxLayout()
        sequenceLayout.addWidget(self.sequenceLineEdit, 1)
        sequenceLayout.addWidget(self.reloadSequenceButton, 0)
        sequenceLayout.addWidget(self.sequenceManagerButton, 0)

        sampleGroupBoxLayout = QtWidgets.QGridLayout(self.sampleGroupBox)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        sampleGroupBoxLayout.addLayout(sampleNameLayout, 0, 1)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Type"), 1, 0)
        sampleGroupBoxLayout.addWidget(self.typeLineEdit, 1, 1)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Position"), 2, 0)
        sampleGroupBoxLayout.addWidget(self.positionLineEdit, 2, 1)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Comment"), 3, 0)
        sampleGroupBoxLayout.addWidget(self.commentLineEdit, 3, 1)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Sequence"), 4, 0)
        sampleGroupBoxLayout.addLayout(sequenceLayout, 4, 1)

        self.rootLayout.addWidget(self.sampleGroupBox, 0)
        self.rootLayout.addStretch()

    @QtCore.pyqtSlot()
    def updateSampleName(self) -> None:
        if self.context:
            self.context.name_infix = self.nameInfixLineEdit.text()
            self.context.name_prefix = self.namePrefixLineEdit.text()
            self.context.name_suffix = self.nameSuffixLineEdit.text()
            self.context.sample_type = self.typeLineEdit.text()
            self.titleLabel.setText(f"{self.title()} &rarr; {self.context.name}")
            self.sampleChanged.emit(self.context)

    @QtCore.pyqtSlot()
    def on_sample_position_edited(self) -> None:
        if self.context:
            self.context.sample_position = self.positionLineEdit.text()
            self.sampleChanged.emit(self.context)

    @QtCore.pyqtSlot()
    def updateComment(self) -> None:
        if self.context:
            self.context.comment = self.commentLineEdit.text()
            self.sampleChanged.emit(self.context)

    @QtCore.pyqtSlot()
    def reloadSequenceFromFile(self) -> None:
        try:
            if self.context and self.context.sequence:
                result = QtWidgets.QMessageBox.question(
                    self,
                    "Reload Configuration",
                    "Do you want to reload sequence configuration from file?"
                )
                if result == QtWidgets.QMessageBox.Yes:
                    filename = self.context.sequence.filename
                    sequence = config.load_sequence(filename)
                    self.context.load_sequence(sequence)
        except Exception as exc:
            logging.exception(exc)
            show_exception(exc)

    @QtCore.pyqtSlot()
    def showSequenceManager(self) -> None:
        try:
            dialog = SequenceManager()
            dialog.readSettings()
            dialog.exec()
            if dialog.result() == QtWidgets.QDialog.Accepted:
                dialog.writeSettings()
                self.sequenceLineEdit.clear()
                sequence = dialog.currentSequence()
                if sequence is not None:
                    self.sequenceLineEdit.setText(f"{sequence.name}")
                    self.sequenceLineEdit.setToolTip(f"{sequence.filename}")
                    self.context.load_sequence(sequence)
                    self.sampleChanged.emit(self.context)
        except Exception as exc:
            logging.exception(exc)
            show_exception(exc)

    def mount(self, context) -> None:
        """Mount measurement to panel."""
        super().mount(context)
        self.titleLabel.setText(f"{self.title()} &rarr; {context.name}")
        self.descriptionLabel.setText("Current halfmoon sample")
        self.namePrefixLineEdit.setText(context.name_prefix)
        self.nameInfixLineEdit.setText(context.name_infix)
        self.nameSuffixLineEdit.setText(context.name_suffix)
        self.typeLineEdit.setText(context.sample_type)
        self.positionLineEdit.setText(context.sample_position)
        self.commentLineEdit.setText(context.comment)
        if context.sequence:
            self.sequenceLineEdit.setText(context.sequence.name)
        else:
            self.sequenceLineEdit.clear()

    def unmount(self) -> None:
        self.namePrefixLineEdit.clear()
        self.nameInfixLineEdit.clear()
        self.nameSuffixLineEdit.clear()
        self.typeLineEdit.clear()
        self.positionLineEdit.clear()
        self.commentLineEdit.clear()
        self.sequenceLineEdit.clear()
        super().unmount()
