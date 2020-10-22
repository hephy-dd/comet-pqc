import comet
from comet import ui

from ..components import PositionGroupBox
from ..components import CalibrationGroupBox

__all__ = ['TableCalibrateDialog']

class TableCalibrateDialog(ui.Dialog, comet.ProcessMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Calibrate Table"
        self.position_groupbox = PositionGroupBox()
        self.calibration_groupbox = CalibrationGroupBox()
        self.start_button = ui.Button(
            text="Start",
            clicked=self.on_start
        )
        self.stop_button = ui.Button(
            text="Stop",
            enabled=False,
            clicked=self.on_stop
        )
        self.close_button = ui.Button(
            text="Close",
            clicked=self.close
        )
        self.layout = ui.Column(
            ui.Row(
                self.position_groupbox,
                self.calibration_groupbox
            ),
            ui.Row(
                self.start_button,
                self.stop_button,
                ui.Spacer(vertical=False),
                self.close_button,
            )
        )
        self.process = self.processes.get("calibrate")
        self.process.position = self.on_position
        self.process.caldone = self.on_caldone
        self.close_event = self.on_close

    def on_position(self, x, y, z):
        self.position_groupbox.value = x, y, z

    def on_caldone(self, x, y, z):
        self.calibration_groupbox.value = x, y, z

    def on_start(self):
        if not ui.show_question(
            title="Calibrate table",
            text="Are you sure you want to calibrate the table?",
            informative="Make sure to remove any needle positioners from inside the box."
        ): return
        self.process.set("success", False)
        self.start_button.enabled = False
        self.stop_button.enabled = True
        self.close_button.enabled = False
        self.process.start()

    def on_stop(self):
        self.process.stop()

    def on_finished(self):
        self.start_button.enabled = True
        self.stop_button.enabled = False
        self.close_button.enabled = True
        if self.process.get("success", False):
            ui.show_info(title="Success", text="Table calibrated successfully.")

    def on_close(self):
        """Prevent close dialog if process is still running."""
        if self.process.alive:
            if not ui.show_question(
                title="Stop calibration",
                text="Do you want to stop the calibration?"
            ): return False
            self.process.stop()
            self.process.join()
            ui.show_info(
                title="Calibration stopped",
                text="Calibration stopped."
            )
        return True

    def run(self):
        self.process.peek()
        self.process.finished = self.on_finished
        super().run()
        self.process.finished = None
