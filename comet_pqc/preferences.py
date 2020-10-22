import comet
from comet import ui

from comet.ui.preferences import PreferencesTab

__all__ = ['TabelTab', 'OptionsTab']

class TableTab(PreferencesTab):
    """Table limits tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Table")
        self.z_limit_movement_number = ui.Number(
            minimum=0,
            maximum=128.0,
            decimals=3,
            suffix="mm",
            changed=self.on_z_limit_movement_changed
        )
        self.z_limit_overdrive_number = ui.Number(
            minimum=0,
            maximum=128.0,
            decimals=3,
            suffix="mm",
            changed=self.on_z_limit_overdrive_changed
        )
        self.layout = ui.Column(
            ui.GroupBox(
                title="Table Z-Limits",
                layout=ui.Column(
                    ui.Label("X/Y Movement"),
                    self.z_limit_movement_number,
                    ui.Label("Overdrive"),
                    self.z_limit_overdrive_number
                )
            ),
            ui.Spacer()
        )

    def on_z_limit_movement_changed(self, value):
        pass

    def on_z_limit_overdrive_changed(self, value):
        pass

    def load(self):
        z_limit_movement = self.settings.get('z_limit_movement', 0.0) / 1000. # from micron
        self.z_limit_movement_number.value = z_limit_movement
        z_limit_overdrive = self.settings.get('z_limit_overdrive', 0.0) / 1000. # from micron
        self.z_limit_overdrive_number.value = z_limit_overdrive

    def store(self):
        z_limit_movement = self.z_limit_movement_number.value * 1000. # to micron
        self.settings['z_limit_movement'] = z_limit_movement
        z_limit_overdrive = self.z_limit_overdrive_number.value * 1000. # to micron
        self.settings['z_limit_overdrive'] = z_limit_overdrive

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
