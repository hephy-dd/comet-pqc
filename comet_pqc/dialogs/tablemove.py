import logging

from qutie.qutie import QtWidgets

import comet
from comet import ui
from comet.settings import SettingsMixin

from ..components import PositionGroupBox
from ..components import CalibrationGroupBox
from ..utils import format_table_unit
from ..utils import from_table_unit
from ..utils import to_table_unit

# Fix
comet.SettingsMixin = SettingsMixin

__all__ = ['TableMoveDialog']

class PositionDialog(ui.Dialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_text = ui.Text(value="Unnamed")
        self.x_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.y_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.z_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.comment_text = ui.Text()
        self.button_box = ui.DialogButtonBox(buttons=("ok", "cancel"), accepted=self.accept, rejected=self.reject)
        self.layout = ui.Column(
            ui.Label("Name", tool_tip="Position name"),
            self.name_text,
            ui.Label("X", tool_tip="Position X coordinate"),
            self.x_number,
            ui.Label("Y", tool_tip="Position Y coordinate"),
            self.y_number,
            ui.Label("Z", tool_tip="Position Z coordinate"),
            self.z_number,
            ui.Label("Comment", tool_tip="Optional position comment"),
            self.comment_text,
            self.button_box
        )

    @property
    def name(self):
        return self.name_text.value

    @name.setter
    def name(self, value):
        self.name_text.value = value

    @property
    def position(self):
        x = self.x_number.value
        y = self.y_number.value
        z = self.z_number.value
        return x, y, z

    @position.setter
    def position(self, value):
        x, y, z = value[:3]
        self.x_number.value = x
        self.y_number.value = y
        self.z_number.value = z

    @property
    def comment(self):
        return self.comment_text.value

    @comment.setter
    def comment(self, value):
        self.comment_text.value = value

class TableMoveDialog(ui.Dialog, comet.ProcessMixin, comet.SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title="Move Table"
        self.content = TableMove()
        self.start_button = ui.Button(
            text="Start",
            tool_tip="Move to selected position",
            enabled=False,
            clicked=self.on_start
        )
        self.stop_button = ui.Button(
            text="Stop",
            tool_tip="Stop running move operation",
            enabled=False,
            clicked=self.on_stop
        )
        self.close_button = ui.Button("&Close", clicked=self.close)
        self.layout=ui.Column(
            self.content,
            ui.Row(
                self.start_button,
                self.stop_button,
                self.close_button,
                ui.Spacer(vertical=False)
            ),
        )
        self.process = self.processes.get('move')
        self.process.failed = self.on_failed
        self.process.position = self.on_position
        self.process.caldone = self.on_caldone
        self.content.load_positions()
        self.content.assign_position = self.on_assign_position
        self.content.move_selected = self.on_move_selected
        self.content.positions_tree.double_clicked = self.on_position_double_clicked

        self.close_event = self.on_close
        self.minimum_size = 800, 480

    def on_close(self):
        """Prevent close dialog if process is still running."""
        if self.process.alive:
            if not ui.show_question(
                title="Stop movement",
                text="Do you want to stop the current movement?"
            ): return False
            self.process.stop()
            self.process.join()
            ui.show_info(
                title="Movement stopped",
                text="Movement stopped."
            )
        self.content.store_positions()
        return True

    def on_failed(self, *args):
        ui.show_exception(*args)
        self.close()

    def on_position(self, x, y, z):
        self.content.position = x, y, z

    def on_caldone(self, x, y, z):
        self.content.caldone = x, y, z

    def on_position_double_clicked(self, index, item):
        self.on_start(item)

    def on_start(self, item=None):
        if item is None:
            item = self.content.positions_tree.current
        if item:
            if ui.show_question(f"Do you want to move table to position '{item[0].value}'?"):
                self.start_button.enabled = False
                self.stop_button.enabled = True
                self.close_button.enabled = False
                self.content.enabled = False
                mm = comet.ureg("mm")
                self.process.set('name', item.name)
                self.process.set('x', to_table_unit(item.x))
                self.process.set('y', to_table_unit(item.y))
                self.process.set('z', to_table_unit(item.z))
                self.process.set('z_limit', int(self.content.z_limit_movement))
                self.process.start()

    def on_stop(self):
        self.stop_button.enabled = False
        self.process.stop()

    def on_finished(self):
        name = self.process.get('name')
        if self.process.get("z_warning"):
            z_limit = self.process.get("z_limit")
            ui.show_warning(
                title="Safe Z Position",
                text=f"Limited Z movement to {format_table_unit(z_limit)} to protect probe card."
            )
        if self.process.get("success", False):
            ui.show_info(title="Success", text=f"Moved table successfully to {name}.")
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
            item.x = from_table_unit(x)
            item.y = from_table_unit(y)
            item.z = from_table_unit(z)

    def load_settings(self):
        dialog_size = self.settings.get('tablemove_dialog_size', (640, 480))
        self.resize(*dialog_size)

    def store_settings(self):
        self.settings['tablemove_dialog_size'] = self.size

    def run(self):
        self.process.peek()
        self.process.finished = self.on_finished
        self.load_settings()
        super().run()
        self.store_settings()
        self.process.finished = None

class ItemDelegate(QtWidgets.QItemDelegate):
    """Item delegate for custom floating point number display."""

    decimals = 3

    def drawDisplay(self, painter, option, rect, text):
        text = format(float(text), f".{self.decimals}f")
        super().drawDisplay(painter, option, rect, text)

class TablePositionItem(ui.TreeItem):

    def __init__(self, name, x, y, z, comment=None):
        super().__init__()
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.comment = comment or ""

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

    @property
    def comment(self):
        return self[4].value

    @comment.setter
    def comment(self, value):
        self[4].value = value

class TableMove(ui.Column, comet.SettingsMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.positions_tree = ui.Tree()
        self.positions_tree.header = "Name", "X", "Y", "Z", "Comment"
        self.positions_tree.indentation = 0
        self.positions_tree.minimum_width = 400
        self.positions_tree.selected = self.on_position_selected
        self.positions_tree.qt.setColumnWidth(1, 64)
        self.positions_tree.qt.setColumnWidth(2, 64)
        self.positions_tree.qt.setColumnWidth(3, 64)
        self.positions_tree.qt.setItemDelegateForColumn(1, ItemDelegate(self.positions_tree.qt))
        self.positions_tree.qt.setItemDelegateForColumn(2, ItemDelegate(self.positions_tree.qt))
        self.positions_tree.qt.setItemDelegateForColumn(3, ItemDelegate(self.positions_tree.qt))
        # Layout
        self.assign_button = ui.Button(
            text="Assign Position",
            tool_tip="Assign current table position to selected position item",
            enabled=False,
            clicked=self.on_assign_position
        )
        self.add_button = ui.Button(
            text="&Add",
            tool_tip="Add new position item",
            clicked=self.on_add_position
        )
        self.edit_button = ui.Button(
            text="&Edit",
            tool_tip="Edit selected position item",
            enabled=False,
            clicked=self.on_edit_position
        )
        self.remove_button = ui.Button(
            text="&Remove",
            tool_tip="Remove selected position item",
            enabled=False,
            clicked=self.on_remove_position
        )
        self.z_limit_movement_label = ui.Label("Z Limit: n/a")
        self.positions_layout = ui.Column(
            ui.Row(
                self.positions_tree,
                ui.Column(
                    self.assign_button,
                    ui.Spacer(),
                    self.add_button,
                    self.edit_button,
                    self.remove_button
                ),
                stretch=(1, 0)
            )
        )
        self.position_groupbox = PositionGroupBox()
        self.calibration_groupbox = CalibrationGroupBox()
        self.append(ui.Column(
            ui.Row(
                ui.GroupBox(
                    title="Table positions (mm)",
                    layout=self.positions_layout
                ),
                ui.Column(
                    self.position_groupbox,
                    self.calibration_groupbox,
                    ui.GroupBox(
                        title="Limits",
                        layout=ui.Column(
                            self.z_limit_movement_label,
                        )
                    ),
                    ui.Spacer(),
                    stretch=(0, 0, 0, 1)
                ),
                stretch=(1, 0)
            ),
            stretch=(10, 1)
        ))
        self.position = 0, 0, 0
        self.z_limit_movement = 0.0

    def load_positions(self):
        self.positions_tree.clear()
        for position in self.settings.get('table_positions', []):
            self.positions_tree.append(TablePositionItem(
                name=position.get('name'),
                x=from_table_unit(position.get('x')),
                y=from_table_unit(position.get('y')),
                z=from_table_unit(position.get('z')),
                comment=position.get('comment') or "",
            ))
        self.positions_tree.fit(0)
        self.z_limit_movement = self.settings.get('z_limit_movement') or 0.0

    def store_positions(self):
        positions = []
        mm = comet.ureg("mm")
        for position in self.positions_tree:
            positions.append(dict(
                name=position.name,
                x=to_table_unit(position.x),
                y=to_table_unit(position.y),
                z=to_table_unit(position.z),
                comment=position.comment
            ))
        self.settings['table_positions'] = positions

    @property
    def z_limit_movement(self):
        return self.__z_limit

    @z_limit_movement.setter
    def z_limit_movement(self, value):
        self.__z_limit = value
        self.z_limit_movement_label.text = f"Z Limit: {format_table_unit(self.__z_limit)}"

    @property
    def position(self):
        return self.position_groupbox.value

    @position.setter
    def position(self, value):
        self.position_groupbox.value = value[:3]

    @property
    def caldone(self):
        return self.calibration_groupbox.value

    @caldone.setter
    def caldone(self, value):
        self.calibration_groupbox.value = value[:3]
        self.positions_layout.enabled = self.calibration_groupbox.valid

    def on_position_selected(self, item):
        self.assign_button.enabled = True
        self.edit_button.enabled = True
        self.remove_button.enabled = True
        self.emit('move_selected')

    def on_assign_position(self):
        item = self.positions_tree.current
        if item:
            if ui.show_question(f"Do you want to assign current position to '{item[0].value}'?"):
                self.emit('assign_position')

    def on_add_position(self):
        dialog = PositionDialog()
        if dialog.run():
            name = dialog.name
            x, y, z = dialog.position
            comment = dialog.comment
            self.positions_tree.append(TablePositionItem(name, x, y, z, comment))
            self.positions_tree.fit(0)

    def on_edit_position(self):
        item = self.positions_tree.current
        if item:
            dialog = PositionDialog()
            dialog.name = item.name
            dialog.position = item.x, item.y, item.z
            dialog.comment = item.comment
            if dialog.run():
                item.name = dialog.name
                item.x, item.y, item.z = dialog.position
                item.comment = dialog.comment
                self.positions_tree.fit(0)

    def on_remove_position(self):
        item = self.positions_tree.current
        if item:
            if ui.show_question(f"Do you want to remove position '{item[0].value}'?"):
                self.positions_tree.remove(item)
                if not len(self.positions_tree):
                    self.assign_button.enabled = False
                    self.edit_button.enabled = False
                    self.remove_button.enabled = False
                self.positions_tree.fit(0)
