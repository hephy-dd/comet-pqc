from comet import ui

from comet.ui.preferences import PreferencesTab

__all__ = ['OptionsTab']

class OptionsTab(PreferencesTab):
    """Options tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Options")
        self.png_plots_checkbox = ui.CheckBox("Save plots as PNG")
        self.layout = ui.Column(
            ui.GroupBox(
                title="Plots",
                layout=ui.Row(
                    self.png_plots_checkbox
                )
            ),
            ui.Spacer()
        )

    def load(self):
        png_plots = self.settings.get("png_plots") or False
        self.png_plots_checkbox.checked = png_plots

    def store(self):
        png_plots = self.png_plots_checkbox.checked
        self.settings["png_plots"] = png_plots
