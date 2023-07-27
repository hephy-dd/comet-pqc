from PyQt5 import QtCore, QtGui, QtWidgets

from comet import ui

from ..core import config
from ..sequence import SequenceManagerDialog
from ..utils import handle_exception, make_path
from .panel import BasicPanel

__all__ = ["SamplePanel"]


class SamplePanel(BasicPanel):

    type = "sample"

    sampleChanged = QtCore.pyqtSignal(object)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Layout
        self._sample_name_prefix_text = ui.Text(
            tool_tip="Sample name prefix",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_name_infix_text = ui.Text(
            tool_tip="Sample name",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_name_suffix_text = ui.Text(
            tool_tip="Sample name suffix",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_type_text = ui.Text(
            tool_tip="Sample type",
            clearable=True,
            editing_finished=self.on_sample_name_edited
        )
        self._sample_position_text = ui.Text(
            tool_tip="Sample position on the chuck",
            clearable=True,
            editing_finished=self.on_sample_position_edited
        )
        self._sequence_text = ui.Text(
            readonly=True
        )
        self._sample_comment_text = ui.Text(
            tool_tip="Sample comment (optional)",
            clearable=True,
            editing_finished=self.on_sample_comment_edited
        )

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
        sampleNameLayout.addWidget(self._sample_name_prefix_text.qt, 3)
        sampleNameLayout.addWidget(self._sample_name_infix_text.qt, 7)
        sampleNameLayout.addWidget(self._sample_name_suffix_text.qt, 3)

        sampleSequenceLayout = QtWidgets.QHBoxLayout()
        sampleSequenceLayout.addWidget(self._sequence_text.qt, 1)
        sampleSequenceLayout.addWidget(self.reloadSequenceButton, 0)
        sampleSequenceLayout.addWidget(self.editSequenceButton, 0)

        sampleGroupBoxLayout = QtWidgets.QGridLayout(self.sampleGroupBox)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Type"), 1, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Position"), 2, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Comment"), 3, 0)
        sampleGroupBoxLayout.addWidget(QtWidgets.QLabel("Sequence"), 4, 0)
        sampleGroupBoxLayout.addLayout(sampleNameLayout, 0, 1)
        sampleGroupBoxLayout.addWidget(self._sample_type_text.qt, 1, 1)
        sampleGroupBoxLayout.addWidget(self._sample_position_text.qt ,2, 1)
        sampleGroupBoxLayout.addWidget(self._sample_comment_text.qt, 3, 1)
        sampleGroupBoxLayout.addLayout(sampleSequenceLayout, 4, 1)
        sampleGroupBoxLayout.setColumnStretch(0, 0)
        sampleGroupBoxLayout.setColumnStretch(1, 1)

        self.layout().insertWidget(2, self.sampleGroupBox)

    def on_sample_name_edited(self):
        if self.context:
            self.context.name_infix = self._sample_name_infix_text.value
            self.context.name_prefix = self._sample_name_prefix_text.value
            self.context.name_suffix = self._sample_name_suffix_text.value
            self.context.sample_type = self._sample_type_text.value
            self.setTitle(f"Sample &rarr; {self.context.name}")
            self.sampleChanged.emit(self.context)

    def on_sample_position_edited(self):
        if self.context:
            self.context.sample_position = self._sample_position_text.value
            self.sampleChanged.emit(self.context)

    def on_sample_comment_edited(self):
        if self.context:
            self.context.comment = self._sample_comment_text.value
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
            self._sequence_text.clear()
            sequence = dialog.currentSequence()
            if sequence is not None:
                self._sequence_text.value = f"{sequence.name}"
                self._sequence_text.tool_tip = f"{sequence.filename}"
                self.context.load_sequence(sequence)
                self.sampleChanged.emit(self.context)

    def mount(self, context) -> None:
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"Sample &rarr; {context.name}")
        self.setDescription("Current halfmoon sample")
        self._sample_name_prefix_text.value = context.name_prefix
        self._sample_name_infix_text.value = context.name_infix
        self._sample_name_suffix_text.value = context.name_suffix
        self._sample_type_text.value = context.sample_type
        self._sample_position_text.value = context.sample_position
        self._sample_comment_text.value = context.comment
        if context.sequence:
            self._sequence_text.value = context.sequence.name
        else:
            self._sequence_text.value = ""

    def unmount(self) -> None:
        self._sample_name_prefix_text.clear()
        self._sample_name_infix_text.clear()
        self._sample_name_suffix_text.clear()
        self._sample_type_text.clear()
        self._sample_position_text.clear()
        self._sample_comment_text.clear()
        self._sequence_text.clear()
        super().unmount()
