from qutie.qutie import QtCore
from qutie.qutie import QtWidgets

from comet import ui
from comet.ui.preferences import PreferencesTab

from ..settings import settings
from ..utils import from_table_unit
from ..utils import to_table_unit

__all__ = ['TableTab']


class TableStepDialog(ui.Dialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._step_size_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self._z_limit_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm", visible=False)
        self._step_color_text = ui.Text()
        self._button_box = ui.DialogButtonBox(buttons=("ok", "cancel"), accepted=self.accept, rejected=self.reject)
        self.layout = ui.Column(
            ui.Label("Size", tool_tip="Step size in millimeters"),
            self._step_size_number,
            ui.Label("Z-Limit", tool_tip="Z-Limit in millimeters", visible=False),
            self._z_limit_number,
            ui.Label("Color", tool_tip="Color code for step"),
            self._step_color_text,
            self._button_box
        )

    @property
    def step_size(self):
        return self._step_size_number.value

    @step_size.setter
    def step_size(self, value):
        self._step_size_number.value = value

    @property
    def z_limit(self):
        return self._z_limit_number.value

    @z_limit.setter
    def z_limit(self, value):
        self._z_limit_number.value = value

    @property
    def step_color(self):
        return self._step_color_text.value

    @step_color.setter
    def step_color(self, value):
        self._step_color_text.value = value or ''


class ItemDelegate(QtWidgets.QItemDelegate):
    """Item delegate for custom floating point number display."""

    decimals = 3

    def drawDisplay(self, painter, option, rect, text):
        text = format(float(text), f".{self.decimals}f")
        super().drawDisplay(painter, option, rect, text)


class TableStepItem(ui.TreeItem):

    def __init__(self, step_size, z_limit, step_color=None):
        super().__init__()
        self.step_size = step_size
        self.z_limit = z_limit
        self.step_color = step_color

    @property
    def step_size(self):
        return self[0].value

    @step_size.setter
    def step_size(self, value):
        self[0].value = float(value)

    @property
    def z_limit(self):
        return self[1].value

    @z_limit.setter
    def z_limit(self, value):
        self[1].value = float(value)

    @property
    def step_color(self):
        return self[2].value

    @step_color.setter
    def step_color(self, value):
        self[2].value = value


class TableTab(PreferencesTab):
    """Table limits tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Table")
        self.temporary_z_limit_changed = None
        self._steps_tree = ui.Tree(
            header=("Size", "Z-Limit", "Color"),
            root_is_decorated=False
        )
        # Hide Z-Limit column
        self._steps_tree.qt.setColumnHidden(1, True)
        self._steps_tree.selected = self.on_position_selected
        self._steps_tree.double_clicked = self.on_steps_tree_double_clicked
        self._steps_tree.qt.setItemDelegateForColumn(0, ItemDelegate(self._steps_tree.qt))
        self._steps_tree.qt.setItemDelegateForColumn(1, ItemDelegate(self._steps_tree.qt))
        self._add_step_button = ui.Button(
            text="&Add",
            tool_tip="Add table step",
            clicked=self.on_add_step_clicked
        )
        self._edit_step_button = ui.Button(
            text="&Edit",
            tool_tip="Edit selected table step",
            enabled=False,
            clicked=self.on_edit_step_clicked
        )
        self._remove_step_button = ui.Button(
            text="&Remove",
            tool_tip="Remove selected table step",
            enabled=False,
            clicked=self.on_remove_step_clicked
        )
        self._z_limit_movement_number = ui.Number(
            minimum=0,
            maximum=128.0,
            decimals=3,
            suffix="mm",
            changed=self.on_z_limit_movement_changed
        )
        def create_number():
            return ui.Number(
                minimum=0,
                maximum=1000.0,
                decimals=3,
                suffix="mm"
            )
        self._probecard_limit_x_maximum_number = create_number()
        self._probecard_limit_y_maximum_number = create_number()
        self._probecard_limit_z_maximum_number = create_number()
        self._probecard_limit_z_maximum_checkbox = ui.CheckBox(
            text="Temporary Z-Limit",
            tool_tip="Select to show temporary Z-Limit notice."
        )
        self._joystick_limit_x_maximum_number = create_number()
        self._joystick_limit_y_maximum_number = create_number()
        self._joystick_limit_z_maximum_number = create_number()
        self._probecard_contact_delay_number = ui.Number(
            minimum=0,
            maximum=3600,
            decimals=2,
            step=.1,
            suffix="s"
        )
        self._recontact_overdrive_number = ui.Number(
            minimum=0,
            maximum=0.025,
            decimals=3,
            step=.001,
            suffix="mm"
        )
        self.layout = ui.Column(
            ui.GroupBox(
                title="Control Steps (mm)",
                layout=ui.Row(
                    self._steps_tree,
                    ui.Column(
                        self._add_step_button,
                        self._edit_step_button,
                        self._remove_step_button,
                        ui.Spacer()
                    ),
                    stretch=(1, 0)
                )
            ),
            ui.GroupBox(
            title="Movement Z-Limit",
                layout=ui.Column(
                    self._z_limit_movement_number
                )
            ),
            ui.GroupBox(
                title="Probe Card Limts",
                layout=ui.Row(
                    ui.Column(
                        ui.Label("X"),
                        self._probecard_limit_x_maximum_number
                    ),
                    ui.Column(
                        ui.Label("Y"),
                        self._probecard_limit_y_maximum_number
                    ),
                    ui.Column(
                        ui.Label("Z"),
                        self._probecard_limit_z_maximum_number
                    ),
                    ui.Column(
                        ui.Label(),
                        ui.Label("Maximum"),
                    ),
                    ui.Spacer(),
                    ui.Column(
                        ui.Label(),
                        self._probecard_limit_z_maximum_checkbox,
                    )
                )
            ),
            ui.GroupBox(
                title="Joystick Limits",
                layout=ui.Row(
                    ui.Column(
                        ui.Label("X"),
                        self._joystick_limit_x_maximum_number
                    ),
                    ui.Column(
                        ui.Label("Y"),
                        self._joystick_limit_y_maximum_number
                    ),
                    ui.Column(
                        ui.Label("Z"),
                        self._joystick_limit_z_maximum_number
                    ),
                    ui.Column(
                        ui.Label(),
                        ui.Label("Maximum"),
                    ),
                    ui.Spacer()
                )
            ),
            ui.Row(
                ui.GroupBox(
                    title="Probecard Contact Delay",
                    layout=ui.Row(
                        self._probecard_contact_delay_number
                    )
                ),
                ui.GroupBox(
                    title="Re-Contact Z-Overdrive (1x)",
                    layout=ui.Row(
                        self._recontact_overdrive_number
                    )
                ),
                stretch=(0, 1)
            ),
            stretch=(1, 0, 0, 0, 0)
        )

    def on_position_selected(self, item):
        enabled = item is not None
        self._edit_step_button.enabled = enabled
        self._remove_step_button.enabled = enabled

    def on_steps_tree_double_clicked(self, index, item):
        self.on_edit_step_clicked()

    def on_add_step_clicked(self):
        dialog = TableStepDialog()
        if dialog.run():
            step_size = dialog.step_size
            z_limit = dialog.z_limit
            step_color = dialog.step_color
            self._steps_tree.append(TableStepItem(step_size, z_limit, step_color))
            self._steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def on_edit_step_clicked(self):
        item = self._steps_tree.current
        if item:
            dialog = TableStepDialog()
            dialog.step_size = item.step_size
            dialog.z_limit = item.z_limit
            dialog.step_color = item.step_color
            if dialog.run():
                item.step_size = dialog.step_size
                item.z_limit = dialog.z_limit
                item.step_color = dialog.step_color
                self._steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def on_remove_step_clicked(self):
        item = self._steps_tree.current
        if item:
            if ui.show_question(f"Do you want to remove step size '{item[0].value}'?"):
                self._steps_tree.remove(item)
                if not len(self._steps_tree):
                    self._edit_step_button.enabled = False
                    self._remove_step_button.enabled = False
                self._steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def on_z_limit_movement_changed(self, value):
        pass

    def load(self):
        table_step_sizes = self.settings.get('table_step_sizes') or []
        self._steps_tree.clear()
        for item in table_step_sizes:
            self._steps_tree.append(TableStepItem(
                step_size=from_table_unit(item.get('step_size')),
                z_limit=from_table_unit(item.get('z_limit')),
                step_color=format(item.get('step_color'))
            ))
        self._steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self._z_limit_movement_number.value = settings.table_z_limit
        # Probecard limits
        x, y, z = settings.table_probecard_maximum_limits
        self._probecard_limit_x_maximum_number.value = x
        self._probecard_limit_y_maximum_number.value = y
        self._probecard_limit_z_maximum_number.value = z
        temporary_z_limit = settings.table_temporary_z_limit
        self._probecard_limit_z_maximum_checkbox.checked = temporary_z_limit
        # Joystick limits
        x, y, z = settings.table_joystick_maximum_limits
        self._joystick_limit_x_maximum_number.value = x
        self._joystick_limit_y_maximum_number.value = y
        self._joystick_limit_z_maximum_number.value = z
        table_contact_delay = self.settings.get('table_contact_delay') or 0
        self._probecard_contact_delay_number.value = table_contact_delay
        self._recontact_overdrive_number.value = settings.retry_contact_overdrive

    def store(self):
        table_step_sizes = []
        for item in self._steps_tree:
            table_step_sizes.append(dict(
                step_size=to_table_unit(item.step_size),
                z_limit=to_table_unit(item.z_limit),
                step_color=format(item.step_color)
            ))
        self.settings['table_step_sizes'] = table_step_sizes
        settings.table_z_limit = self._z_limit_movement_number.value
        # Probecard limits
        settings.table_probecard_maximum_limits = [
            self._probecard_limit_x_maximum_number.value,
            self._probecard_limit_y_maximum_number.value,
            self._probecard_limit_z_maximum_number.value
        ]
        temporary_z_limit = self._probecard_limit_z_maximum_checkbox.checked
        settings.table_temporary_z_limit = temporary_z_limit
        self.emit('temporary_z_limit_changed', temporary_z_limit)
        # Joystick limits
        settings.table_joystick_maximum_limits = [
            self._joystick_limit_x_maximum_number.value,
            self._joystick_limit_y_maximum_number.value,
            self._joystick_limit_z_maximum_number.value
        ]
        table_contact_delay = self._probecard_contact_delay_number.value
        self.settings['table_contact_delay'] = table_contact_delay
        settings.retry_contact_overdrive = self._recontact_overdrive_number.value
