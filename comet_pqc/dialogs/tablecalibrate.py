import comet
from comet import ui

__all__ = ['TableCalibrateDialog']

class TableCalibrateDialog(ui.Dialog, comet.ProcessMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Calibrate Table"
        self.pos_x_label = ui.Label()
        self.pos_y_label = ui.Label()
        self.pos_z_label = ui.Label()
        self.cal_x_label = ui.Label()
        self.cal_y_label = ui.Label()
        self.cal_z_label = ui.Label()
        self.rm_x_label = ui.Label()
        self.rm_y_label = ui.Label()
        self.rm_z_label = ui.Label()
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
                ui.GroupBox(
                    width=160,
                    title="Position",
                    layout=ui.Row(
                        ui.Column(
                            ui.Label("X"),
                            ui.Label("Y"),
                            ui.Label("Z"),
                        ),
                        ui.Column(
                            self.pos_x_label,
                            self.pos_y_label,
                            self.pos_z_label
                        ),
                    )
                ),
                ui.GroupBox(
                    title="State",
                    layout=ui.Row(
                        ui.Column(
                            ui.Label("X"),
                            ui.Label("Y"),
                            ui.Label("Z"),
                        ),
                        ui.Column(
                            self.cal_x_label,
                            self.cal_y_label,
                            self.cal_z_label
                        ),
                        ui.Column(
                            self.rm_x_label,
                            self.rm_y_label,
                            self.rm_z_label
                        )
                    )
                )
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
        self.pos_x_label.text = f"{x / 1000.:.3f} mm"
        self.pos_y_label.text = f"{y / 1000.:.3f} mm"
        self.pos_z_label.text = f"{z / 1000.:.3f} mm"

    def on_caldone(self, x, y, z):
        def getcal(value):
            return value & 0x1
        def getrm(value):
            return (value >> 1) & 0x1
        self.cal_x_label.text = "cal {}".format(getcal(x))
        self.cal_x_label.stylesheet = "color: green" if getcal(x) else "color: red"
        self.cal_y_label.text = "cal {}".format(getcal(y))
        self.cal_y_label.stylesheet = "color: green" if getcal(y) else "color: red"
        self.cal_z_label.text = "cal {}".format(getcal(z))
        self.cal_z_label.stylesheet = "color: green" if getcal(z) else "color: red"
        self.rm_x_label.text = "rm {}".format(getrm(x))
        self.rm_x_label.stylesheet = "color: green" if getrm(x) else "color: red"
        self.rm_y_label.text = "rm {}".format(getrm(y))
        self.rm_y_label.stylesheet = "color: green" if getrm(y) else "color: red"
        self.rm_z_label.text = "rm {}".format(getrm(z))
        self.rm_z_label.stylesheet = "color: green" if getrm(z) else "color: red"

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
