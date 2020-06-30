import logging

import comet

# fixes
import qutie
comet.RadioButton = qutie.RadioButton

from .processes import ControlProcess

__all__ = ['TableControl']

class SquareSpacer(comet.Spacer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32

class SquareButton(comet.Button):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32

class SquareLabel(comet.Label):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 32
        self.height = 32
        self.qt.setAlignment(qutie.qt.QtCore.Qt.AlignCenter)

class TableControl(comet.Widget):

    fine_step_width = 1.0
    wide_step_width = 10.0

    def __init__(self, *args, move=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Event
        self.move = move
        # Control buttons
        self.back_button = SquareButton(
            text="∆",
            tool_tip="Move table to back.",
            clicked=self.on_back
        )
        self.front_button = SquareButton(
            text="∇",
            tool_tip="Move table to front.",
            clicked=self.on_front
        )
        self.left_button = SquareButton(
            "⊲",
            tool_tip="Move table left.",
            clicked=self.on_left
        )
        self.right_button = SquareButton(
            "⊳",
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
        # Movement buttons
        self.wide_button = comet.RadioButton(
            text=f"Wide ({self.wide_step_width} μm)",
            tool_tip="Move in wide steps.",
            stylesheet="QRadioButton{color:red;}",
            toggled=self.on_wide
        )
        self.fine_button = comet.RadioButton(
            text=f"Fine ({self.fine_step_width} μm)",
            tool_tip="Move in fine steps.",
            stylesheet="QRadioButton{color:green;}",
            toggled=self.on_fine
        )
        self.pos_x_label = comet.Label()
        self.pos_y_label = comet.Label()
        self.pos_z_label = comet.Label()
        self.cal_x_label = comet.Label()
        self.cal_y_label = comet.Label()
        self.cal_z_label = comet.Label()
        self.rm_x_label = comet.Label()
        self.rm_y_label = comet.Label()
        self.rm_z_label = comet.Label()
        # Layout
        self.controls_tab = comet.Tab(
            title="Controls",
            layout=comet.Column(
                comet.Spacer(),
                comet.Row(
                    comet.Spacer(),
                    comet.Row(
                        comet.Column(SquareSpacer(), self.left_button, SquareSpacer()),
                        comet.Column(self.back_button, SquareLabel("X/Y"), self.front_button),
                        comet.Column(SquareSpacer(), self.right_button, SquareSpacer())
                    ),
                    SquareSpacer(),
                    comet.Column(
                        self.up_button,
                        SquareLabel("Z"),
                        self.down_button
                    ),
                    SquareSpacer(),
                    comet.Column(
                        comet.GroupBox(
                            title="Movement",
                            layout=comet.Column(
                                self.fine_button,
                                self.wide_button
                            )
                        ),
                        comet.Spacer(horizontal=False)
                    ),
                    comet.Spacer(),
                    stretch=(1, 0, 0, 0, 0, 0, 1)
                ),
                comet.Spacer(),
                stretch=(1, 0, 1)
            )
        )
        self.command_tab = comet.Tab(
            title="Commands",
            layout=comet.Row(
                comet.Column(
                    comet.GroupBox(
                        title="Load Chuck",
                        layout=comet.Row(
                            comet.Label("Move chuck to loading/unloading position."),
                            comet.Button("Move", width=80),
                        )

                    ),
                    comet.GroupBox(
                        title="Move to Probe Card",
                        layout=comet.Row(
                            comet.Label("Move chuck to safe position below probe card."),
                            comet.Button("Move", width=80),
                        )
                    ),
                    comet.Spacer()
                ),
                comet.Spacer(),
                stretch=(0, 1)
            )
        )
        self.layout = comet.Column(
            comet.Row(
                comet.Tabs(
                    self.controls_tab,
                    self.command_tab
                ),
                comet.Column(
                    comet.GroupBox(
                        width=160,
                        title="Position",
                        layout=comet.Row(
                            comet.Column(
                                comet.Label("X"),
                                comet.Label("Y"),
                                comet.Label("Z"),
                            ),
                            comet.Column(
                                self.pos_x_label,
                                self.pos_y_label,
                                self.pos_z_label
                            ),
                        )
                    ),
                    comet.GroupBox(
                        title="State",
                        layout=comet.Row(
                            comet.Column(
                                comet.Label("X"),
                                comet.Label("Y"),
                                comet.Label("Z"),
                            ),
                            comet.Column(
                                self.cal_x_label,
                                self.cal_y_label,
                                self.cal_z_label
                            ),
                            comet.Column(
                                self.rm_x_label,
                                self.rm_y_label,
                                self.rm_z_label
                            )
                        )
                    )
                ),
                comet.Spacer(),
                stretch=(0, 0, 0, 0, 0, 0, 0, 0, 1)
            ),
            comet.Spacer(),
            stretch=(0, 1)
        )
        # Init buttons
        self.fine_button.checked = True
        self.position = 0, 0, 0

    @property
    def step_width(self):
        if self.fine_button.checked:
            return abs(self.fine_step_width)
        elif self.wide_button.checked:
            return abs(self.wide_step_width)
        return 0

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        self.__position = value[0], value[1], value[2]
        self.pos_x_label.text = f"{1000.0 * value[0]:.3f} mm"
        self.pos_y_label.text = f"{1000.0 * value[1]:.3f} mm"
        self.pos_z_label.text = f"{1000.0 * value[2]:.3f} mm"

    @property
    def caldone(self):
        return self.__caldone

    @caldone.setter
    def caldone(self, value):
        def getcal(value):
            return value & 0x1
        def getrm(value):
            return (value[0] >> 1) & 0x1
        self.__caldone = value[0], value[1], value[2]
        self.cal_x_label.text = format(getcal(value[0]))
        self.cal_y_label.text = format(getcal(value[1]))
        self.cal_z_label.text = format(getcal(value[2]))
        self.rm_x_label.text = format(getrm(value[0]))
        self.rm_y_label.text = format(getrm(value[1]))
        self.rm_z_label.text = format(getrm(value[2]))

    def on_back(self):
        self.emit("move", 0, self.step_width, 0)

    def on_front(self):
        self.emit("move", 0, -self.step_width, 0)

    def on_left(self):
        self.emit("move", -self.step_width, 0, 0)

    def on_right(self):
        self.emit("move", self.step_width, 0, 0)

    def on_up(self):
        self.emit("move", 0, 0, self.step_width)

    def on_down(self):
        self.emit("move", 0, 0, -self.step_width)

    def on_fine(self, state):
        for button in self.control_buttons:
            button.stylesheet = "QPushButton{color:green;font-size:22px;}"

    def on_wide(self, state):
        for button in self.control_buttons:
            button.stylesheet = "QPushButton{color:red;font-size:22px;}"

class TableControlDialog(comet.Dialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title="Table Control"
        self.control = TableControl()
        self.layout=comet.Column(
            self.control,
            comet.Row(
                comet.Button("&Close", clicked=self.close),
                comet.Spacer(vertical=False)
            ),
        )
        self.process = ControlProcess()
        def on_failed(*args):
            comet.show_exception(*args)
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
        self.control.move = on_move

    def run(self):
        self.process.start()
        super().run()
        self.process.stop()
        self.process.join()
