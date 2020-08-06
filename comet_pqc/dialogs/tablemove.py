import logging

import comet
from comet.settings import SettingsMixin

# Fix
comet.SettingsMixin = SettingsMixin

__all__ = ['TableMoveDialog']

class TableMoveDialog(comet.Dialog, comet.ProcessMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title="Move Table"
        self.content = TableMove()
        self.start_button = comet.Button(
            text="Start",
            enabled=False,
            clicked=self.on_start
        )
        self.stop_button = comet.Button(
            text="Stop",
            enabled=False,
            clicked=self.on_stop
        )
        self.close_button = comet.Button("&Close", clicked=self.close)
        self.layout=comet.Column(
            self.content,
            comet.Row(
                self.start_button,
                self.stop_button,
                self.close_button,
                comet.Spacer(vertical=False)
            ),
        )
        self.process = self.processes.get('move')
        self.process.failed = self.on_failed
        self.process.position = self.on_position
        self.process.caldone = self.on_caldone
        self.content.load_positions()
        self.content.assign_position = self.on_assign_position
        self.content.move_selected = self.on_move_selected
        self.close_event = self.on_close
        self.minimum_size = 800, 480

    def on_close(self):
        """Prevent close dialog if process is still running."""
        if self.process.alive:
            if not comet.show_question(
                title="Stop movement",
                text="Do you want to stop the current movement?"
            ): return False
            self.process.stop()
            self.process.join()
            comet.show_info(
                title="Movement stopped",
                text="Movement stopped."
            )
        self.content.store_positions()
        return True

    def on_failed(self, *args):
        comet.show_exception(*args)
        self.close()

    def on_position(self, x, y, z):
        self.content.position = x, y, z

    def on_caldone(self, x, y, z):
        self.content.caldone = x, y, z

    def on_start(self):
        item = self.content.positions_tree.current
        if item:
            if comet.show_question(f"Do you want to move table to position '{item[0].value}'?"):
                self.start_button.enabled = False
                self.stop_button.enabled = True
                self.close_button.enabled = False
                self.content.enabled = False
                self.process.set('name', item.name)
                self.process.set('x', item.x)
                self.process.set('y', item.y)
                self.process.set('z', item.z)
                self.process.set('z_limit', int(self.content.z_limit * 1e3)) # to micron
                self.process.start()

    def on_stop(self):
        self.process.stop()

    def on_finished(self):
        name = self.process.get('name')
        if self.process.get("z_warning"):
            z_limit = self.process.get("z_limit")
            comet.show_warning(
                title="Safe Z Position",
                text=f"Limited Z movement to {z_limit/1e3:.3f} mm to protect probe card."
            )
        if self.process.get("success", False):
            comet.show_info(title="Success", text=f"Moved table successfully to {name}.")
        self.process.set('name', None)
        self.process.set('x', 0)
        self.process.set('y', 0)
        self.process.set('z', 0)
        self.start_button.enabled = True
        self.stop_button.enabled = False
        self.close_button.enabled = True
        self.content.enabled = True

    def on_move_selected(self):
        item = self.content.positions_tree.current
        if item:
            self.start_button.enabled = True
        else:
            self.start_button.enabled = False

    def on_assign_position(self):
        item = self.content.positions_tree.current
        if item:
            x, y, z = self.content.position
            item.x = x
            item.y = y
            item.z = z

    def run(self):
        self.process.peek()
        self.process.finished = self.on_finished
        super().run()
        self.process.finished = None

class TablePositionItem(comet.TreeItem):

    def __init__(self, name, x, y, z):
        super().__init__()
        self.name = name
        self.x = x
        self.y = y
        self.z = z

    @property
    def name(self):
        return self[0].value

    @name.setter
    def name(self, value):
        self[0].value = value

    @property
    def x(self):
        return self[1].value

    @x.setter
    def x(self, value):
        self[1].value = float(value)

    @property
    def y(self):
        return self[2].value

    @y.setter
    def y(self, value):
        self[2].value = float(value)

    @property
    def z(self):
        return self[3].value

    @z.setter
    def z(self, value):
        self[3].value = float(value)

class TableMove(comet.Column, comet.SettingsMixin):

    maximum_z_limit = 23.800

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos_x_label = comet.Label()
        self.pos_y_label = comet.Label()
        self.pos_z_label = comet.Label()
        self.cal_x_label = comet.Label()
        self.cal_y_label = comet.Label()
        self.cal_z_label = comet.Label()
        self.rm_x_label = comet.Label()
        self.rm_y_label = comet.Label()
        self.rm_z_label = comet.Label()
        self.positions_tree = comet.Tree()
        self.positions_tree.header = "Name", "X", "Y", "Z"
        self.positions_tree.indentation = 0
        self.positions_tree.minimum_width = 400
        self.positions_tree.selected = self.on_position_selected
        self.positions_tree.fit()
        # Layout
        self.assign_button = comet.Button(
            text="Assign Position",
            enabled=False,
            clicked=self.on_assign_position
        )
        self.add_button = comet.Button(
            text="&Add",
            clicked=self.on_add_position
        )
        self.edit_button = comet.Button(
            text="&Edit Name",
            enabled=False,
            clicked=self.on_edit_position
        )
        self.remove_button = comet.Button(
            text="&Remove",
            enabled=False,
            clicked=self.on_remove_position
        )
        self.z_limit_label = comet.Label()
        self.positions_layout = comet.Column(
            comet.Row(
                self.positions_tree,
                comet.Column(
                    self.assign_button,
                    comet.Spacer(),
                    self.add_button,
                    self.edit_button,
                    self.remove_button
                ),
                stretch=(1, 0)
            ),
            comet.Row(
                self.z_limit_label,
                comet.Button("...", width=32, clicked=self.edit_z_limit),
                comet.Spacer(),
                stretch=(0, 0, 1)
            ),
            stretch=(1, 0)
        )
        self.append(comet.Column(
            comet.Row(
                comet.GroupBox(
                    title="Table positions",
                    layout=self.positions_layout
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
                    ),
                    comet.Spacer(),
                    stretch=(0, 0, 1)
                ),
                stretch=(1, 0)
            ),
            stretch=(10, 1)
        ))
        self.position = 0, 0, 0
        self.z_limit = 20.000

    def set_z_limit(self, limit):
        self.z_limit = min(self.maximum_z_limit, limit)
        self.z_limit_label.text = f"Z Soft Limit: {self.z_limit:.3f} mm"

    def edit_z_limit(self):
        value = comet.get_number(
            title="Z Soft Limit",
            label="Z Soft Limit",
            value=self.z_limit,
            minimum=0,
            maximum=self.maximum_z_limit,
            decimals=3
        )
        if value is not None:
            self.set_z_limit(value)

    def load_positions(self):
        self.positions_tree.clear()
        for position in self.settings.get('table_positions', []):
            self.positions_tree.append(TablePositionItem(
                name=position.get('name'),
                x=position.get('x'),
                y=position.get('y'),
                z=position.get('z')
            ))
        self.positions_tree.fit()
        self.set_z_limit(self.settings.get('table_z_limit', self.maximum_z_limit))

    def store_positions(self):
        positions = []
        for position in self.positions_tree:
            positions.append(dict(
                name=position.name,
                x=position.x,
                y=position.y,
                z=position.z
            ))
        self.settings['table_positions'] = positions
        self.settings['table_z_limit'] = self.z_limit

    @property
    def z_limit(self):
        return self.__z_limit

    @z_limit.setter
    def z_limit(self, value):
        self.__z_limit = min(self.maximum_z_limit, value)
        self.z_limit_label.text = f"Z Soft Limit: {self.__z_limit:.3f} mm"

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        self.__position = value[0], value[1], value[2]
        # TODO
        self.pos_x_label.text = f"{value[0] / 1000.:.3f} mm"
        self.pos_y_label.text = f"{value[1] / 1000.:.3f} mm"
        self.pos_z_label.text = f"{value[2] / 1000.:.3f} mm"

    @property
    def caldone(self):
        return self.__caldone

    @caldone.setter
    def caldone(self, value):
        def getcal(value):
            return value & 0x1
        def getrm(value):
            return (value >> 1) & 0x1
        self.__caldone = value[0], value[1], value[2]
        self.cal_x_label.text = "cal {}".format(getcal(value[0]))
        self.cal_x_label.stylesheet = "color: green" if getcal(value[0]) else "color: red"
        self.cal_y_label.text = "cal {}".format(getcal(value[1]))
        self.cal_y_label.stylesheet = "color: green" if getcal(value[1]) else "color: red"
        self.cal_z_label.text = "cal {}".format(getcal(value[2]))
        self.cal_z_label.stylesheet = "color: green" if getcal(value[2]) else "color: red"
        self.rm_x_label.text = "rm {}".format(getrm(value[0]))
        self.rm_x_label.stylesheet = "color: green" if getrm(value[0]) else "color: red"
        self.rm_y_label.text = "rm {}".format(getrm(value[1]))
        self.rm_y_label.stylesheet = "color: green" if getrm(value[1]) else "color: red"
        self.rm_z_label.text = "rm {}".format(getrm(value[2]))
        self.rm_z_label.stylesheet = "color: green" if getrm(value[2]) else "color: red"
        state = value == (3, 3, 3)
        self.positions_layout.enabled = state

    def on_position_selected(self, item):
        self.assign_button.enabled = True
        self.edit_button.enabled = True
        self.remove_button.enabled = True
        self.emit('move_selected')

    def on_assign_position(self):
        item = self.positions_tree.current
        if item:
            if comet.show_question(f"Do you want to assign current position to '{item[0].value}'?"):
                self.emit('assign_position')

    def on_add_position(self):
        name = comet.get_text(title="Add Position", label="Name", text="")
        if name:
            self.positions_tree.append(TablePositionItem(name, 0, 0, 0))
            self.positions_tree.fit()

    def on_edit_position(self):
        item = self.positions_tree.current
        if item:
            text = comet.get_text(title="Edit Position Name", label="Name", text=item[0].value)
            if text:
                item[0].value = text
                self.positions_tree.fit()

    def on_remove_position(self):
        item = self.positions_tree.current
        if item:
            if comet.show_question(f"Do you want to remove position '{item[0].value}'?"):
                self.positions_tree.remove(item)
                if not len(self.positions_tree):
                    self.assign_button.enabled = False
                    self.edit_button.enabled = False
                    self.remove_button.enabled = False
                self.positions_tree.fit()
