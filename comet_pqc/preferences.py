from PyQt5 import QtCore, QtWidgets

from comet import SettingsMixin
from comet import ui

from .settings import settings
from .utils import from_table_unit, to_table_unit

__all__ = ["PreferencesDialog"]


class PreferencesDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")

        self.tableWidget = TableWidget(self)
        self.webapiWidget = WebAPIWidget(self)
        self.optionsWidget = OptionsWidget(self)

        self.tabWidget = QtWidgets.QTabWidget(self)
        self.tabWidget.addTab(self.tableWidget, "Table")
        self.tabWidget.addTab(self.webapiWidget, "Webserver")
        self.tabWidget.addTab(self.optionsWidget, "Options")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget, 1)
        layout.addWidget(self.buttonBox, 0)

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("PreferencesDialog")

        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreGeometry(geometry)

        settings.endGroup()

        self.tableWidget.readSettings()
        self.webapiWidget.readSettings()
        self.optionsWidget.readSettings()

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("PreferencesDialog")

        settings.setValue("geometry", self.saveGeometry())

        settings.endGroup()

        self.tableWidget.writeSettings()
        self.webapiWidget.writeSettings()
        self.optionsWidget.writeSettings()

        QtWidgets.QMessageBox.information(self, "Restart required", "Application restart required for changes to take effect.")


class WebAPIWidget(QtWidgets.QWidget, SettingsMixin):
    """Web API settings tab for preferences dialog."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.enabledCheckBox = QtWidgets.QCheckBox(self)
        self.enabledCheckBox.setText("Enable Server")

        self.hostnameLineEdit = QtWidgets.QLineEdit(self)

        self.portSpinBox = QtWidgets.QSpinBox(self)
        self.portSpinBox.setRange(0, 99999)
        self.portSpinBox.setSingleStep(1)

        self.jsonGroupBox = QtWidgets.QGroupBox(self)
        self.jsonGroupBox.setTitle("JSON API")

        jsonFormLayout = QtWidgets.QFormLayout()
        jsonFormLayout.addWidget(self.enabledCheckBox)
        jsonFormLayout.addRow("Host", self.hostnameLineEdit)
        jsonFormLayout.addRow("Port", self.portSpinBox)

        jsonLayout = QtWidgets.QHBoxLayout(self.jsonGroupBox)
        jsonLayout.addLayout(jsonFormLayout, 0)
        jsonLayout.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.jsonGroupBox)
        layout.addStretch()

    def isServerEnabled(self) -> bool:
        return self.enabledCheckBox.isChecked()

    def setServerEnabled(self, enabled: bool) -> None:
        self.enabledCheckBox.setChecked(enabled)

    def hostname(self) -> str:
        return self.hostnameLineEdit.text().strip()

    def setHostname(self, hostname: str) -> None:
        self.hostnameLineEdit.setText(hostname)

    def port(self) -> int:
        return int(self.portSpinBox.value())

    def setPort(self, port: int) -> None:
        self.portSpinBox.setValue(port)

    def readSettings(self) -> None:
        enabled = self.settings.get("webapi_enabled") or False
        self.setServerEnabled(enabled)
        hostname = self.settings.get("webapi_host") or "0.0.0.0"
        self.setHostname(hostname)
        port = int(self.settings.get("webapi_port") or 9000)
        self.setPort(port)

    def writeSettings(self):
        self.settings["webapi_enabled"] = self.isServerEnabled()
        self.settings["webapi_host"] = self.hostname()
        self.settings["webapi_port"] = self.port()


class OptionsWidget(QtWidgets.QWidget, SettingsMixin):
    """Options tab for preferences dialog."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        # Plots

        self.pngPlotsCheckBox = QtWidgets.QCheckBox(self)
        self.pngPlotsCheckBox.setText("Save plots as PNG")

        self.pointsInPlotsCheckBox = QtWidgets.QCheckBox(self)
        self.pointsInPlotsCheckBox.setText("Show points in plots")

        self.plotsGroupBox = QtWidgets.QGroupBox(self)
        self.plotsGroupBox.setTitle("Plots")

        plotsLayout = QtWidgets.QFormLayout(self.plotsGroupBox)
        plotsLayout.addWidget(self.pngPlotsCheckBox)
        plotsLayout.addWidget(self.pointsInPlotsCheckBox)

        # Analysis

        self.pngAnalysisCheckBox = QtWidgets.QCheckBox(self)
        self.pngAnalysisCheckBox.setText("Add analysis preview to PNG")

        self.analysisGroupBox = QtWidgets.QGroupBox(self)
        self.analysisGroupBox.setTitle("Analysis")

        analysisLayout = QtWidgets.QFormLayout(self.analysisGroupBox)
        analysisLayout.addWidget(self.pngAnalysisCheckBox)

        # Formats

        self.exportJsonCheckBox = QtWidgets.QCheckBox(self)
        self.exportJsonCheckBox.setText("Write JSON data (*.json)")

        self.exportTxtCheckBox = QtWidgets.QCheckBox(self)
        self.exportTxtCheckBox.setText("Write plain text data (*.txt)")

        self.formatsGroupBox = QtWidgets.QGroupBox(self)
        self.formatsGroupBox.setTitle("Formats")

        formatsLayout = QtWidgets.QFormLayout(self.formatsGroupBox)
        formatsLayout.addWidget(self.exportJsonCheckBox)
        formatsLayout.addWidget(self.exportTxtCheckBox)

        # Logfiles

        self.writeLogfilesCheckBox = QtWidgets.QCheckBox(self)
        self.writeLogfilesCheckBox.setText("Write measurement log files (*.log)")

        self.logfilesGroupBox = QtWidgets.QGroupBox(self)
        self.logfilesGroupBox.setTitle("Log files")

        logfilesLayout = QtWidgets.QFormLayout(self.logfilesGroupBox)
        logfilesLayout.addWidget(self.writeLogfilesCheckBox)

        # Auto retry

        self.retryMeasurementSpinBox = QtWidgets.QSpinBox(self)
        self.retryMeasurementSpinBox.setRange(0, 100)
        self.retryMeasurementSpinBox.setSuffix("x")
        self.retryMeasurementSpinBox.setToolTip("Number of retries for measurements with failed analysis.")

        self.retryContactSpinBox = QtWidgets.QSpinBox(self)
        self.retryContactSpinBox.setRange(0, 10)
        self.retryContactSpinBox.setSuffix("x")
        self.retryContactSpinBox.setToolTip("Number of re-contact retries for measurements with failed analysis.")

        self.autoRetryGroupBox = QtWidgets.QGroupBox(self)
        self.autoRetryGroupBox.setTitle("Auto Retry")

        autoRetryFormLayout = QtWidgets.QFormLayout()
        autoRetryFormLayout.addRow("Retry Measurements", self.retryMeasurementSpinBox)
        autoRetryFormLayout.addRow("Retry Contact", self.retryContactSpinBox)

        autoRetryLayout = QtWidgets.QHBoxLayout(self.autoRetryGroupBox)
        autoRetryLayout.addLayout(autoRetryFormLayout)
        autoRetryLayout.addStretch()

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.plotsGroupBox, 0, 0, 1, 1)
        layout.addWidget(self.analysisGroupBox, 0, 1, 1, 1)
        layout.addWidget(self.formatsGroupBox, 1, 0, 1, 1)
        layout.addWidget(self.logfilesGroupBox, 1, 1, 1, 1)
        layout.addWidget(self.autoRetryGroupBox, 2, 0, 1, 2)
        layout.setRowStretch(3, 1)

    def readSettings(self):
        png_plots = self.settings.get("png_plots", False)
        self.pngPlotsCheckBox.setChecked(png_plots)
        points_in_plots = self.settings.get("points_in_plots", False)
        self.pointsInPlotsCheckBox.setChecked(points_in_plots)
        png_analysis = self.settings.get("png_analysis", False)
        self.pngAnalysisCheckBox.setChecked(png_analysis)
        export_json = self.settings.get("export_json", False)
        self.exportJsonCheckBox.setChecked(export_json)
        export_txt = self.settings.get("export_txt", True)
        self.exportTxtCheckBox.setChecked(export_txt)
        write_logfiles = self.settings.get("write_logfiles", True)
        self.writeLogfilesCheckBox.setChecked(write_logfiles)
        self.retryMeasurementSpinBox.setValue(settings.retry_measurement_count)
        self.retryContactSpinBox.setValue(settings.retry_contact_count)

    def writeSettings(self):
        png_plots = self.pngPlotsCheckBox.isChecked()
        self.settings["png_plots"] = png_plots
        points_in_plots = self.pointsInPlotsCheckBox.isChecked()
        self.settings["points_in_plots"] = points_in_plots
        png_analysis = self.pngAnalysisCheckBox.isChecked()
        self.settings["png_analysis"] = png_analysis
        export_json = self.exportJsonCheckBox.isChecked()
        self.settings["export_json"] = export_json
        export_txt = self.exportTxtCheckBox.isChecked()
        self.settings["export_txt"] = export_txt
        write_logfiles = self.writeLogfilesCheckBox.isChecked()
        self.settings["write_logfiles"] = write_logfiles
        settings.retry_measurement_count = self.retryMeasurementSpinBox.value()
        settings.retry_contact_count = self.retryContactSpinBox.value()


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
        self._step_color_text.value = value or ""


class ItemDelegate(QtWidgets.QItemDelegate):
    """Item delegate for custom floating point number display."""

    Decimals = 3

    def drawDisplay(self, painter, option, rect, text):
        text = format(float(text), f".{self.Decimals}f")
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


class TableWidget(QtWidgets.QWidget, SettingsMixin):
    """Table limits tab for preferences dialog."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

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
        self.zLimitMovementSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitMovementSpinBox.setRange(0, 128)
        self.zLimitMovementSpinBox.setDecimals(3)
        self.zLimitMovementSpinBox.setSuffix(" mm")

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

        self.probecardContactDelaySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.probecardContactDelaySpinBox.setRange(0, 3600)
        self.probecardContactDelaySpinBox.setDecimals(2)
        self.probecardContactDelaySpinBox.setSingleStep(0.1)
        self.probecardContactDelaySpinBox.setSuffix(" s")

        self.recontactOverdriveNumberSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.recontactOverdriveNumberSpinBox.setRange(0, 0.025)
        self.recontactOverdriveNumberSpinBox.setDecimals(3)
        self.recontactOverdriveNumberSpinBox.setSingleStep(0.001)
        self.recontactOverdriveNumberSpinBox.setSuffix(" mm")

        self.stepsGroupBox = ui.GroupBox(
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
        )

        self.zLimitGroupBox = QtWidgets.QGroupBox(self)
        self.zLimitGroupBox.setTitle("Movement Z-Limit")

        zLimitLayout = QtWidgets.QVBoxLayout(self.zLimitGroupBox)
        zLimitLayout.addWidget(self.zLimitMovementSpinBox)

        self.probecardGroupBox = ui.GroupBox(
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
        )

        self.joystickGropBox = ui.GroupBox(
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
        )

        self.delayGroupBox = QtWidgets.QGroupBox(self)
        self.delayGroupBox.setTitle("Probecard Contact Delay")

        delayLayout = QtWidgets.QHBoxLayout(self.delayGroupBox)
        delayLayout.addWidget(self.probecardContactDelaySpinBox)

        self.overdriveGroupBox = QtWidgets.QGroupBox(self)
        self.overdriveGroupBox.setTitle("Re-Contact Z-Overdrive (1x)")

        overdriveLayout = QtWidgets.QHBoxLayout(self.overdriveGroupBox)
        overdriveLayout.addWidget(self.recontactOverdriveNumberSpinBox)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.stepsGroupBox.qt, 0, 0, 1, 2)
        layout.addWidget(self.zLimitGroupBox, 1, 0, 1, 2)
        layout.addWidget(self.probecardGroupBox.qt, 2, 0, 1, 2)
        layout.addWidget(self.joystickGropBox.qt, 3, 0, 1, 2)
        layout.addWidget(self.delayGroupBox, 4, 0, 1, 1)
        layout.addWidget(self.overdriveGroupBox, 4, 1, 1, 1)
        layout.setRowStretch(0, 1)

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
            if ui.show_question(f"Do you want to remove step size {item[0].value!r}?"):
                self._steps_tree.remove(item)
                if not len(self._steps_tree):
                    self._edit_step_button.enabled = False
                    self._remove_step_button.enabled = False
                self._steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def readSettings(self):
        table_step_sizes = self.settings.get("table_step_sizes") or []
        self._steps_tree.clear()
        for item in table_step_sizes:
            self._steps_tree.append(TableStepItem(
                step_size=from_table_unit(item.get("step_size")),
                z_limit=from_table_unit(item.get("z_limit")),
                step_color=format(item.get("step_color"))
            ))
        self._steps_tree.qt.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.zLimitMovementSpinBox.setValue(settings.table_z_limit)
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
        table_contact_delay = self.settings.get("table_contact_delay") or 0
        self.probecardContactDelaySpinBox.setValue(table_contact_delay)
        self.recontactOverdriveNumberSpinBox.setValue(settings.retry_contact_overdrive)

    def writeSettings(self):
        table_step_sizes = []
        for item in self._steps_tree:
            table_step_sizes.append({
                "step_size": to_table_unit(item.step_size),
                "z_limit": to_table_unit(item.z_limit),
                "step_color": format(item.step_color),
            })
        self.settings["table_step_sizes"] = table_step_sizes
        settings.table_z_limit = self.zLimitMovementSpinBox.value()
        # Probecard limits
        settings.table_probecard_maximum_limits = [
            self._probecard_limit_x_maximum_number.value,
            self._probecard_limit_y_maximum_number.value,
            self._probecard_limit_z_maximum_number.value
        ]
        temporary_z_limit = self._probecard_limit_z_maximum_checkbox.checked
        settings.table_temporary_z_limit = temporary_z_limit
        # Joystick limits
        settings.table_joystick_maximum_limits = [
            self._joystick_limit_x_maximum_number.value,
            self._joystick_limit_y_maximum_number.value,
            self._joystick_limit_z_maximum_number.value
        ]
        table_contact_delay = self.probecardContactDelaySpinBox.value()
        self.settings["table_contact_delay"] = table_contact_delay
        settings.retry_contact_overdrive = self.recontactOverdriveNumberSpinBox.value()
