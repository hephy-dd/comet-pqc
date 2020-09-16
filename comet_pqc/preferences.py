from comet import ui

from comet.ui.preferences import PreferencesTab

__all__ = ['OptionsTab']

class OptionsTab(PreferencesTab):
    """Options tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Options")
        self.png_plots_checkbox = ui.CheckBox("Save plots as PNG")
        self.export_json_checkbox = ui.CheckBox("Write JSON data (*.json)")
        self.export_txt_checkbox = ui.CheckBox("Write plain text data (*.txt)")
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
            ui.Spacer()
        )

    def load(self):
        png_plots = self.settings.get("png_plots", False)
        self.png_plots_checkbox.checked = png_plots
        export_json = self.settings.get("export_json", False)
        self.export_json_checkbox.checked = export_json
        export_txt = self.settings.get("export_txt", True)
        self.export_txt_checkbox.checked = export_txt

    def store(self):
        png_plots = self.png_plots_checkbox.checked
        self.settings["png_plots"] = png_plots
        export_json = self.export_json_checkbox.checked
        self.settings["export_json"] = export_json
        export_txt = self.export_txt_checkbox.checked
        self.settings["export_txt"] = export_txt
