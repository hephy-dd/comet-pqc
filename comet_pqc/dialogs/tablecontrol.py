import logging

import comet
from comet import ui
from comet.settings import SettingsMixin
from qutie.qt import QtCore

from ..components import PositionGroupBox
from ..components import CalibrationGroupBox
from ..utils import format_table_unit

__all__ = ['TableControlDialog']

def format_width(width):
    """Retrun foramtted step width."""
    if width >= 1000.0:
        return f'{width / 1000.} mm'
    return f'{width} μm'

class TableControlDialog(ui.Dialog, comet.ProcessMixin, SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title="Table Control"
        self.control = TableControl()
        self.layout=ui.Column(
            self.control,
            ui.Row(
                ui.Button("&Close", clicked=self.close),
                ui.Spacer(vertical=False)
            ),
        )
        self.process = self.processes.get('control')
        def on_failed(*args):
            ui.show_exception(*args)
            self.close()
        self.process.failed = on_failed
        def on_close():
             self.close()
        self.process.finished = on_close
        def on_move(x, y, z):
            logging.info(f"Move table: {x} {y} {z}")
            self.process.push(x, y, z)
        def on_position(x, y, z):
            self.control.position = x, y, z
        def on_caldone(x, y, z):
            self.control.caldone = x, y, z
        self.process.position = on_position
        self.process.caldone = on_caldone
        self.process.set('z_limit_movement', self.control.z_limit_movement)
        self.process.set('z_limit_overdrive', self.control.z_limit_overdrive)
        self.control.move = on_move

    def run(self):
        self.process.start()
        super().run()
        self.process.stop()
        self.process.join()

class SquareSpacer(ui.Spacer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32

class SquareButton(ui.Button):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32

class SquareLabel(ui.Label):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32
        self.qt.setAlignment(QtCore.Qt.AlignCenter)

class TableControl(ui.Column, SettingsMixin):

    step_widths = (
        (1.0, "fine", "green"),
        (10.0, "wide", "orange"),
        (100.0, "large", "red"),
        (1000.0, "ridiculous", "darkred"),
        (10000.0, "ludicrous", "darkmagenta")
    )

    def __init__(self, *args, move=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Event
        self.move = move
        # Control buttons
        self.back_button = SquareButton(
            text="⊳",
            tool_tip="Move table to back.",
            clicked=self.on_back
        )
        self.front_button = SquareButton(
            text="⊲",
            tool_tip="Move table to front.",
            clicked=self.on_front
        )
        self.left_button = SquareButton(
            "∆",
            tool_tip="Move table left.",
            clicked=self.on_left
        )
        self.right_button = SquareButton(
            "∇",
            tool_tip="Move table right.",
            clicked=self.on_right
        )
        self.up_button = SquareButton(
            "∆",
            tool_tip="Move table up.",
            clicked=self.on_up
        )
        self.down_button = SquareButton(
            "∇",
            tool_tip="Move table down.",
            clicked=self.on_down
        )
        self.control_buttons = (
            self.front_button,
            self.back_button,
            self.left_button,
            self.right_button,
            self.up_button,
            self.down_button
        )
        # Create movement radio buttons
        self.step_buttons = ui.Column()
        for width, name, color in self.step_widths:
            button = ui.RadioButton(
                text=format_width(width),
                tool_tip=f"Move in {name} steps.",
                stylesheet=f"QRadioButton{{color:{color};}}",
                toggled=self.on_colorcode
            )
            button.step_width = width
            button.step_name = name
            button.step_color = color
            self.step_buttons.append(button)
        self.laser_state_label = ui.Label("n/a")
        self.z_limit_movement_label = ui.Label("n/a")
        self.z_limit_overdrive_label = ui.Label("n/a")
        # Layout
        self.controls_layout = ui.Column(
            ui.Spacer(),
            ui.Row(
                ui.Spacer(),
                ui.Row(
                    ui.Column(
                        SquareSpacer(),
                        self.front_button,
                        SquareSpacer()
                    ),
                    ui.Column(
                        self.left_button,
                        SquareLabel("X/Y"),
                        self.right_button
                    ),
                    ui.Column(
                        SquareSpacer(),
                        self.back_button,
                        SquareSpacer()
                    )
                ),
                SquareSpacer(),
                ui.Column(
                    self.up_button,
                    SquareLabel("Z"),
                    self.down_button
                ),
                SquareSpacer(),
                ui.Column(
                    ui.GroupBox(
                        title="Movement",
                        layout=self.step_buttons
                    ),
                    ui.Spacer(horizontal=False)
                ),
                ui.Spacer(),
                stretch=(1, 0, 0, 0, 0, 0, 1)
            ),
            ui.Spacer(),
            stretch=(1, 0, 1)
        )
        self.position_groupbox = PositionGroupBox()
        self.calibration_groupbox = CalibrationGroupBox()
        self.limits_groupbox = ui.GroupBox(
            title="Z Limits",
            layout=ui.Row(
                ui.Column(
                    ui.Label("Movement"),
                    ui.Label("Overdrive")
                ),
                ui.Column(
                    self.z_limit_movement_label,
                    self.z_limit_overdrive_label
                )
            )
        )
        self.safety_groupbox = ui.GroupBox(
            title="Safety",
            layout=ui.Row(
                ui.Column(
                    ui.Label("Laser Sensor"),
                ),
                ui.Column(
                    self.laser_state_label,
                )
            )
        )
        self.append(ui.Column(
            ui.Row(
                ui.Column(
                    ui.GroupBox(
                        title="Control",
                        layout=self.controls_layout
                    ),
                    ui.Label("All controls relative to Probe-Card camera image.", enabled=False)
                ),
                ui.Column(
                    self.position_groupbox,
                    self.calibration_groupbox,
                    self.limits_groupbox,
                    self.safety_groupbox
                ),
                ui.Spacer(),
                stretch=(0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
            ),
            ui.Spacer(),
            stretch=(0, 1)
        ))
        # Init buttons
        if self.step_buttons:
            self.step_buttons[0].checked = True
        # Initialize
        self.lock_controls()
        self.position = 0, 0, 0
        self.caldone = 0, 0, 0
        self.on_update_laser_state(None)
        self.update_limits()

    @property
    def z_limit_movement(self):
        return self.settings.get('z_limit_movement') or 0.0

    @property
    def z_limit_overdrive(self):
        return self.settings.get('z_limit_overdrive') or 0.0

    def update_limits(self):
        x, y, z = self.position
        # Movement
        z_limit_movement = self.z_limit_movement
        color_movement = "green" if z < z_limit_movement else "red"
        self.z_limit_movement_label.text = f"{format_table_unit(z_limit_movement)}"
        self.z_limit_movement_label.stylesheet = f"QLabel:enabled{{color:{color_movement}}}"
        # Overdrive
        z_limit_overdrive = self.z_limit_overdrive
        color_overdrive = ("green" if z < z_limit_movement else "orange") if z < z_limit_overdrive else "red"
        self.z_limit_overdrive_label.text = f"{format_table_unit(z_limit_overdrive)}"
        self.z_limit_overdrive_label.stylesheet = f"QLabel:enabled{{color:{color_overdrive}}}"

    def lock_controls(self):
        self.front_button.enabled = False
        self.back_button.enabled = False
        self.left_button.enabled = False
        self.right_button.enabled = False
        self.up_button.enabled = False
        self.down_button.enabled = False

    def update_controls(self):
        x, y, z = self.position
        movement_enabled = z < self.z_limit_movement
        self.front_button.enabled = movement_enabled and y > 0.0
        self.back_button.enabled = movement_enabled
        self.left_button.enabled = movement_enabled and x > 0.0
        self.right_button.enabled = movement_enabled
        z_enabled = True if z <= self.z_limit_movement else self.step_width < 1000.
        z_enabled = z_enabled and (z + self.step_width) <= self.z_limit_overdrive
        self.up_button.enabled = z_enabled
        self.down_button.enabled = z >= 0.0

    @property
    def step_width(self):
        for button in self.step_buttons:
            if button.checked:
                return abs(button.step_width)
        return 0

    @property
    def step_color(self):
        for button in self.step_buttons:
            if button.checked:
                return button.step_color
        return "black"

    @property
    def position(self):
        return self.position_groupbox.value

    @position.setter
    def position(self, value):
        self.position_groupbox.value = value[:3]
        self.update_controls()
        self.update_limits()

    @property
    def caldone(self):
        return self.calibration_groupbox.value

    @caldone.setter
    def caldone(self, value):
        self.calibration_groupbox.value = value[:3]
        self.controls_layout.enabled = self.calibration_groupbox.valid

    def on_back(self):
        self.lock_controls()
        self.emit("move", 0, self.step_width, 0)

    def on_front(self):
        self.lock_controls()
        self.emit("move", 0, -self.step_width, 0)

    def on_left(self):
        self.lock_controls()
        self.emit("move", -self.step_width, 0, 0)

    def on_right(self):
        self.lock_controls()
        self.emit("move", self.step_width, 0, 0)

    def on_up(self):
        self.lock_controls()
        self.emit("move", 0, 0, self.step_width)

    def on_down(self):
        self.lock_controls()
        self.emit("move", 0, 0, -self.step_width)

    def on_colorcode(self, state):
        for button in self.control_buttons:
            button.enabled = False
            button.stylesheet = f"QPushButton:enabled{{color:{self.step_color};font-size:22px;}}"

    def on_update_laser_state(self, enabled):
        laser_state = {False: "OFF", True: "ON"}.get(enabled, "n/a")
        laser_style = {False: "QLabel{color:red}", True: "QLabel{color:green}"}.get(enabled, "")
        self.laser_state_label.text = laser_state
        self.laser_state_label.stylesheet = laser_style
