from qutie.qutie import QtCore
from qutie.qutie import QtWidgets

from comet import ui
from comet.ui.preferences import PreferencesTab

from ..settings import settings

__all__ = ['OptionsTab']


class OptionsTab(PreferencesTab):
    """Options tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Options")
        self._png_plots_checkbox = ui.CheckBox("Save plots as PNG")
        self._points_in_plots_checkbox = ui.CheckBox("Show points in plots")
        self._png_analysis_checkbox = ui.CheckBox("Add analysis preview to PNG")
        self._export_json_checkbox = ui.CheckBox("Write JSON data (*.json)")
        self._export_txt_checkbox = ui.CheckBox("Write plain text data (*.txt)")
        self._write_logfiles_checkbox = ui.CheckBox("Write measurement log files (*.log)")
        self._vsrc_instrument_combobox = ui.ComboBox(["K2410", "K2657A"])
        self._hvsrc_instrument_combobox = ui.ComboBox(["K2410", "K2657A"])
        self._retry_measurement_number = ui.Number(
            minimum=0,
            suffix="x",
            tool_tip="Number of retries for measurements with failed analysis."
        )
        self._retry_contact_number = ui.Number(
            minimum=0,
            suffix="x",
            tool_tip="Number of re-contact retries for measurements with failed analysis."
        )
        self.layout = ui.Column(
            ui.Row(
                ui.GroupBox(
                    title="Plots",
                    layout=ui.Column(
                        self._png_plots_checkbox,
                        self._points_in_plots_checkbox,
                    )
                ),
                ui.GroupBox(
                    title="Analysis",
                    layout=ui.Column(
                        self._png_analysis_checkbox,
                        ui.Spacer()
                    )
                ),
                stretch=(0, 1)
            ),
            ui.Row(
                ui.GroupBox(
                    title="Formats",
                    layout=ui.Column(
                        self._export_json_checkbox,
                        self._export_txt_checkbox
                    )
                ),
                ui.GroupBox(
                    title="Log files",
                    layout=ui.Column(
                        self._write_logfiles_checkbox,
                            ui.Spacer()
                    )
                ),
                stretch=(0, 1)
            ),
            ui.GroupBox(
                title="Instruments",
                layout=ui.Row(
                    ui.Column(
                        ui.Label("V Source"),
                        ui.Label("HV Source")
                    ),
                    ui.Column(
                        self._vsrc_instrument_combobox,
                        self._hvsrc_instrument_combobox
                    ),
                    ui.Spacer(vertical=False),
                    stretch=(0, 0, 1)
                )
            ),
            ui.GroupBox(
                title="Auto Retry",
                layout=ui.Row(
                    ui.Column(
                        ui.Label("Retry Measurements"),
                        ui.Label("Retry Contact")
                    ),
                    ui.Column(
                        self._retry_measurement_number,
                        self._retry_contact_number
                    ),
                    ui.Spacer()
                )
            ),
            ui.Spacer(),
            stretch=(0, 0, 0, 0, 1)
        )

    def load(self):
        png_plots = self.settings.get("png_plots") or False
        self._png_plots_checkbox.checked = png_plots
        points_in_plots = self.settings.get("points_in_plots") or False
        self._points_in_plots_checkbox.checked = points_in_plots
        png_analysis = self.settings.get("png_analysis") or False
        self._png_analysis_checkbox.checked = png_analysis
        export_json = self.settings.get("export_json") or False
        self._export_json_checkbox.checked = export_json
        export_txt = self.settings.get("export_txt") or True
        self._export_txt_checkbox.checked = export_txt
        write_logfiles = self.settings.get("write_logfiles") or True
        self._write_logfiles_checkbox.checked = write_logfiles
        vsrc_instrument = self.settings.get("vsrc_instrument") or "K2657A"
        if vsrc_instrument in self._vsrc_instrument_combobox:
            self._vsrc_instrument_combobox.current = vsrc_instrument
        hvsrc_instrument = self.settings.get("hvsrc_instrument") or "K2410"
        if hvsrc_instrument in self._hvsrc_instrument_combobox:
            self._hvsrc_instrument_combobox.current = hvsrc_instrument
        self._retry_measurement_number.value = settings.retry_measurement_count
        self._retry_contact_number.value = settings.retry_contact_count

    def store(self):
        png_plots = self._png_plots_checkbox.checked
        self.settings["png_plots"] = png_plots
        points_in_plots = self._points_in_plots_checkbox.checked
        self.settings["points_in_plots"] = points_in_plots
        png_analysis = self._png_analysis_checkbox.checked
        self.settings["png_analysis"] = png_analysis
        export_json = self._export_json_checkbox.checked
        self.settings["export_json"] = export_json
        export_txt = self._export_txt_checkbox.checked
        self.settings["export_txt"] = export_txt
        write_logfiles = self._write_logfiles_checkbox.checked
        self.settings["write_logfiles"] = write_logfiles
        vsrc_instrument = self._vsrc_instrument_combobox.current or "K2657A"
        self.settings["vsrc_instrument"] = vsrc_instrument
        hvsrc_instrument = self._hvsrc_instrument_combobox.current or "K2410"
        self.settings["hvsrc_instrument"] = hvsrc_instrument
        settings.retry_measurement_count = self._retry_measurement_number.value
        settings.retry_contact_count = self._retry_contact_number.value
