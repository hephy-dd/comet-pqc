from PyQt5 import QtCore, QtWidgets

from comet import ui
from comet.settings import SettingsMixin

from ..core import config
from ..sequence import SequenceManager
from ..utils import handle_exception, make_path
from .panel import BasicPanel

__all__ = ["SamplePanel"]


class SamplePanel(BasicPanel, SettingsMixin):

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
        self._reload_button = ui.ToolButton(
            icon=make_path("assets", "icons", "reload.svg"),
            tool_tip="Reload sequence configuration from file.",
            clicked=self.on_reload_clicked
        )
        self._sequence_manager_button = ui.ToolButton(
            icon=make_path("assets", "icons", "gear.svg"),
            tool_tip="Open sequence manager",
            clicked=self.on_sequence_manager_clicked
        )
        self._sample_groupbox = ui.GroupBox(
            title="Sample",
            layout=ui.Row(
                ui.Column(
                    ui.Label("Name"),
                    ui.Label("Type"),
                    ui.Label("Position"),
                    ui.Label("Comment"),
                    ui.Label("Sequence")
                ),
                ui.Column(
                    ui.Row(
                        self._sample_name_prefix_text,
                        self._sample_name_infix_text,
                        self._sample_name_suffix_text,
                        stretch=(3, 7, 3)
                    ),
                    self._sample_type_text,
                    self._sample_position_text,
                    self._sample_comment_text,
                    ui.Row(
                        self._sequence_text,
                        self._reload_button,
                        self._sequence_manager_button,
                        stretch=(1, 0)
                    )
                ),
                stretch=(0, 1)
            )
        )
        self.layout().insertWidget(2, self._sample_groupbox.qt)

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

    @handle_exception
    def on_reload_clicked(self):
        if not ui.show_question(
            title="Reload Configuration",
            text="Do you want to reload sequence configuration from file?"
        ): return
        if self.context.sequence:
            filename = self.context.sequence.filename
            sequence = config.load_sequence(filename)
            self.context.load_sequence(sequence)

    @handle_exception
    def on_sequence_manager_clicked(self):
        dialog = SequenceManager()
        dialog.readSettings()
        if dialog.run():
            dialog.writeSettings()
            self._sequence_text.clear()
            sequence = dialog.current_sequence
            if sequence is not None:
                self._sequence_text.value = f"{sequence.name}"
                self._sequence_text.tool_tip = f"{sequence.filename}"
                self.context.load_sequence(sequence)
                self.sampleChanged.emit(self.context)

    def mount(self, context):
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

    def unmount(self):
        self._sample_name_prefix_text.clear()
        self._sample_name_infix_text.clear()
        self._sample_name_suffix_text.clear()
        self._sample_type_text.clear()
        self._sample_position_text.clear()
        self._sample_comment_text.clear()
        self._sequence_text.clear()
        super().unmount()
