from qutie.qutie import QtCore, QtWidgets

import comet
from comet import ui
from comet.ui.preferences import PreferencesTab

from .utils import from_table_unit
from .utils import to_table_unit

__all__ = ['TableTab', 'OptionsTab']

class TableStepDialog(ui.Dialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step_size_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.z_limit_number = ui.Number(value=0., minimum=0., maximum=1000., decimals=3, suffix="mm")
        self.button_box = ui.DialogButtonBox(buttons=("ok", "cancel"), accepted=self.accept, rejected=self.reject)
        self.layout = ui.Column(
            ui.Label("Size", tool_tip="Step size in millimeters"),
            self.step_size_number,
            ui.Label("Z-Limit", tool_tip="Z-Limit in millimeters"),
            self.z_limit_number,
            self.button_box
        )

    @property
    def step_size(self):
        return self.step_size_number.value

    @step_size.setter
    def step_size(self, value):
        self.step_size_number.value = value

    @property
    def z_limit(self):
        return self.z_limit_number.value

    @z_limit.setter
    def z_limit(self, value):
        self.z_limit_number.value = value

class ItemDelegate(QtWidgets.QItemDelegate):
    """Item delegate for custom floating point number display."""

    decimals = 3

    def drawDisplay(self, painter, option, rect, text):
        text = format(float(text), f".{self.decimals}f")
        super().drawDisplay(painter, option, rect, text)

class TableStepItem(ui.TreeItem):

    def __init__(self, step_size, z_limit):
        super().__init__()
        self.step_size = step_size
        self.z_limit = z_limit

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

class TableTab(PreferencesTab):
    """Table limits tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Table")
        self.steps_tree = ui.Tree(
            header=("Size", "Z-Limit")
        )
        self.steps_tree.selected = self.on_position_selected
        self.steps_tree.qt.setItemDelegateForColumn(0, ItemDelegate(self.steps_tree.qt))
        self.steps_tree.qt.setItemDelegateForColumn(1, ItemDelegate(self.steps_tree.qt))
        self.add_step_button = ui.Button(
            text="&Add",
            tool_tip="Add table step",
            clicked=self.on_add_step_clicked
        )
        self.edit_step_button = ui.Button(
            text="&Edit",
            tool_tip="Edit selected table step",
            enabled=False,
            clicked=self.on_edit_step_clicked
        )
        self.remove_step_button = ui.Button(
            text="&Remove",
            tool_tip="Remove selected table step",
            enabled=False,
            clicked=self.on_remove_step_clicked
        )
        self.z_limit_movement_number = ui.Number(
            minimum=0,
            maximum=128.0,
            decimals=3,
            suffix="mm",
            changed=self.on_z_limit_movement_changed
        )
        self.layout = ui.Column(
            ui.GroupBox(
                title="Control Steps (mm)",
                layout=ui.Row(
                    self.steps_tree,
                    ui.Column(
                        self.add_step_button,
                        self.edit_step_button,
                        self.remove_step_button,
                        ui.Spacer()
                    ),
                    stretch=(1, 0)
                )
            ),
            ui.GroupBox(
                title="Movement Z-Limit",
                layout=ui.Column(
                    self.z_limit_movement_number
                )
            )
        )

    def on_position_selected(self, item):
        enabled = item is not None
        self.edit_step_button.enabled = enabled
        self.remove_step_button.enabled = enabled

    def on_add_step_clicked(self):
        dialog = TableStepDialog()
        if dialog.run():
            step_size = dialog.step_size
            z_limit = dialog.z_limit
            self.steps_tree.append(TableStepItem(step_size, z_limit))
            self.steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def on_edit_step_clicked(self):
        item = self.steps_tree.current
        if item:
            dialog = TableStepDialog()
            dialog.step_size = item.step_size
            dialog.z_limit = item.z_limit
            if dialog.run():
                item.step_size = dialog.step_size
                item.z_limit = dialog.z_limit
                self.steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def on_remove_step_clicked(self):
        item = self.steps_tree.current
        if item:
            if ui.show_question(f"Do you want to remove step size '{item[0].value}'?"):
                self.steps_tree.remove(item)
                if not len(self.steps_tree):
                    self.edit_step_button.enabled = False
                    self.remove_step_button.enabled = False
                self.steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def on_z_limit_movement_changed(self, value):
        pass

    def load(self):
        table_step_sizes = self.settings.get('table_step_sizes') or []
        self.steps_tree.clear()
        for item in table_step_sizes:
            self.steps_tree.append(TableStepItem(
                step_size=from_table_unit(item.get('step_size')),
                z_limit=from_table_unit(item.get('z_limit'))
            ))
        self.steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)
        z_limit_movement = from_table_unit(self.settings.get('z_limit_movement', 0.0))
        self.z_limit_movement_number.value = z_limit_movement

    def store(self):
        table_step_sizes = []
        for item in self.steps_tree:
            table_step_sizes.append(dict(
                step_size=to_table_unit(item.step_size),
                z_limit=to_table_unit(item.z_limit)
            ))
        self.settings['table_step_sizes'] = table_step_sizes
        z_limit_movement = to_table_unit(self.z_limit_movement_number.value)
        self.settings['z_limit_movement'] = z_limit_movement

class OptionsTab(PreferencesTab):
    """Options tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Options")
        self.png_plots_checkbox = ui.CheckBox("Save plots as PNG")
        self.export_json_checkbox = ui.CheckBox("Write JSON data (*.json)")
        self.export_txt_checkbox = ui.CheckBox("Write plain text data (*.txt)")
        self.write_logfiles_checkbox = ui.CheckBox("Write measurement log files (*.log)")
        self.layout = ui.Column(
            ui.GroupBox(
                title="Plots",
                layout=ui.Row(
                    self.png_plots_checkbox
                )
            ),
            ui.GroupBox(
                title="Formats",
                layout=ui.Column(
                    self.export_json_checkbox,
                    self.export_txt_checkbox
                )
            ),
            ui.GroupBox(
                title="Log files",
                layout=ui.Column(
                    self.write_logfiles_checkbox
                )
            ),
            ui.Spacer()
        )

    def load(self):
        png_plots = self.settings.get("png_plots", False)
        self.png_plots_checkbox.checked = png_plots
        export_json = self.settings.get("export_json", False)
        self.export_json_checkbox.checked = export_json
        export_txt = self.settings.get("export_txt", True)
        self.export_txt_checkbox.checked = export_txt
        write_logfiles = self.settings.get("write_logfiles", True)
        self.write_logfiles_checkbox.checked = write_logfiles

    def store(self):
        png_plots = self.png_plots_checkbox.checked
        self.settings["png_plots"] = png_plots
        export_json = self.export_json_checkbox.checked
        self.settings["export_json"] = export_json
        export_txt = self.export_txt_checkbox.checked
        self.settings["export_txt"] = export_txt
        write_logfiles = self.write_logfiles_checkbox.checked
        self.settings["write_logfiles"] = write_logfiles
