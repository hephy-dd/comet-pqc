from typing import Tuple

from PyQt5 import QtCore, QtWidgets

from comet import SettingsMixin

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

        QtWidgets.QMessageBox.information(
            self,
            "Restart required",
            "Application restart required for changes to take effect."
        )


class TableStepDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.stepSizeLabel = QtWidgets.QLabel(self)
        self.stepSizeLabel.setText("Size")
        self.stepSizeLabel.setToolTip("Step size in millimeters")

        self.stepSizeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.stepSizeSpinBox.setRange(0, 1000)
        self.stepSizeSpinBox.setValue(0)
        self.stepSizeSpinBox.setDecimals(3)
        self.stepSizeSpinBox.setSuffix(" mm")

        self.zLimitLabel = QtWidgets.QLabel(self)
        self.zLimitLabel.setText("Z-Limit")
        self.zLimitLabel.setToolTip("Z-Limit in millimeters")
        self.zLimitLabel.setVisible(False)

        self.zLimitSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitSpinBox.setRange(0, 1000)
        self.zLimitSpinBox.setValue(0)
        self.zLimitSpinBox.setDecimals(3)
        self.zLimitSpinBox.setSuffix(" mm")
        self.zLimitSpinBox.setVisible(False)

        self.stepColorLabel = QtWidgets.QLabel(self)
        self.stepColorLabel.setText("Color")
        self.stepColorLabel.setToolTip("Color code for step")

        self.stepColorLineEdit = QtWidgets.QLineEdit(self)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.stepSizeLabel)
        layout.addWidget(self.stepSizeSpinBox)
        layout.addWidget(self.zLimitLabel)
        layout.addWidget(self.zLimitSpinBox)
        layout.addWidget(self.stepColorLabel)
        layout.addWidget(self.stepColorLineEdit)
        layout.addWidget(self.buttonBox)

    def stepSize(self) -> float:
        return self.stepSizeSpinBox.value()

    def setStepSize(self, value: float) -> None:
        self.stepSizeSpinBox.setValue(value)

    def zLimit(self) -> float:
        return self.zLimitSpinBox.value()

    def setZLimit(self, value: float) -> None:
        self.zLimitSpinBox.setValue(value)

    def stepColor(self) -> str:
        return self.stepColorLineEdit.text()

    def setStepColor(self, value: str) -> None:
        self.stepColorLineEdit.setText(value or "")


class ItemDelegate(QtWidgets.QItemDelegate):
    """Item delegate for custom floating point number display."""

    Decimals = 3

    def drawDisplay(self, painter, option, rect, text):
        try:
            value = float(text.replace(",", "."))  # TODO issues with locale
            text = f"{value:.{self.Decimals}f} mm"
        except Exception:
            ...
        super().drawDisplay(painter, option, rect, text)


class TableStepItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, stepSize: float, zLimit: float, stepColor: str) -> None:
        super().__init__()
        self.setStepSize(stepSize)
        self.setZLimit(zLimit)
        self.setStepColor(stepColor)

    def stepSize(self):
        return self.data(0, 0x2000)

    def setStepSize(self, value: float):
        self.setData(0, 0x2000, value)
        self.setText(0, format(value))

    def zLimit(self):
        return self.data(1, 0x2000)

    def setZLimit(self, value: float):
        self.setData(1, 0x2000, value)
        self.setText(1, format(value))

    def stepColor(self) -> str:
        return self.data(2, 0x2000)

    def setStepColor(self, value: str):
        self.setData(2, 0x2000, value)
        self.setText(2, format(value))


class TableWidget(QtWidgets.QWidget, SettingsMixin):
    """Table limits tab for preferences dialog."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.stepsTreeWidget = QtWidgets.QTreeWidget(self)
        self.stepsTreeWidget.setHeaderLabels(["Size", "Z-Limit", "Color"])
        self.stepsTreeWidget.setRootIsDecorated(False)

        # Hide Z-Limit column
        self.stepsTreeWidget.setColumnHidden(1, True)
        self.stepsTreeWidget.setItemDelegateForColumn(0, ItemDelegate(self.stepsTreeWidget))
        self.stepsTreeWidget.setItemDelegateForColumn(1, ItemDelegate(self.stepsTreeWidget))
        self.stepsTreeWidget.currentItemChanged.connect(self.updateStepButtons)
        self.stepsTreeWidget.itemDoubleClicked.connect(self.stepDoubleClicked)

        self.addStepButton = QtWidgets.QPushButton(self)
        self.addStepButton.setText("&Add")
        self.addStepButton.setToolTip("Add table step")
        self.addStepButton.clicked.connect(self.addNewStep)

        self.editStepButton = QtWidgets.QPushButton(self)
        self.editStepButton.setText("&Edit")
        self.editStepButton.setToolTip("Edit selected table step")
        self.editStepButton.setEnabled(False)
        self.editStepButton.clicked.connect(self.editCurrentStep)

        self.removeStepButton = QtWidgets.QPushButton(self)
        self.removeStepButton.setText("&Remove")
        self.removeStepButton.setToolTip("Remove selected table step")
        self.removeStepButton.setEnabled(False)
        self.removeStepButton.clicked.connect(self.removeCurrentStep)

        self.zLimitMovementSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitMovementSpinBox.setRange(0, 128)
        self.zLimitMovementSpinBox.setDecimals(3)
        self.zLimitMovementSpinBox.setSuffix(" mm")

        def createSpinBox(parent):
            spinBox = QtWidgets.QDoubleSpinBox(parent)
            spinBox.setRange(0, 1000)
            spinBox.setDecimals(3)
            spinBox.setSuffix(" mm")
            return spinBox

        self.probecardLimitXSpinBox = createSpinBox(self)
        self.probecardLimitYSpinBox = createSpinBox(self)
        self.probecardLimitZSpinBox = createSpinBox(self)
        self.probecardLimitZCheckBox = QtWidgets.QCheckBox(self)
        self.probecardLimitZCheckBox.setText("Temporary Z-Limit")
        self.probecardLimitZCheckBox.setToolTip("Select to show temporary Z-Limit notice.")

        self.joystickLimitXSpinBox = createSpinBox(self)
        self.joystickLimitYSpinBox = createSpinBox(self)
        self.joystickLimitZSpinBox = createSpinBox(self)

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

        self.stepsGroupBox = QtWidgets.QGroupBox(self)
        self.stepsGroupBox.setTitle("Control Steps (mm)")

        stepsLayout = QtWidgets.QGridLayout(self.stepsGroupBox)
        stepsLayout.addWidget(self.stepsTreeWidget, 0, 0, 4, 1)
        stepsLayout.addWidget(self.addStepButton, 0, 1)
        stepsLayout.addWidget(self.editStepButton, 1, 1)
        stepsLayout.addWidget(self.removeStepButton, 2, 1)
        stepsLayout.setRowStretch(3, 1)

        self.zLimitGroupBox = QtWidgets.QGroupBox(self)
        self.zLimitGroupBox.setTitle("Movement Z-Limit")

        zLimitLayout = QtWidgets.QHBoxLayout(self.zLimitGroupBox)
        zLimitLayout.addWidget(self.zLimitMovementSpinBox)
        zLimitLayout.addStretch()

        self.probecardGroupBox = QtWidgets.QGroupBox(self)
        self.probecardGroupBox.setTitle("Probe Card Limts")

        probecardLayout = QtWidgets.QGridLayout(self.probecardGroupBox)
        probecardLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        probecardLayout.addWidget(self.probecardLimitXSpinBox, 1, 0)
        probecardLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        probecardLayout.addWidget(self.probecardLimitYSpinBox, 1, 1)
        probecardLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        probecardLayout.addWidget(self.probecardLimitZSpinBox, 1, 2)
        probecardLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        probecardLayout.setColumnStretch(3, 1)
        probecardLayout.addWidget(self.probecardLimitZCheckBox, 1, 4)

        self.joystickGroupBox = QtWidgets.QGroupBox(self)
        self.joystickGroupBox.setTitle("Joystick Limits")

        joystickLayout = QtWidgets.QGridLayout(self.joystickGroupBox)
        joystickLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        joystickLayout.addWidget(self.joystickLimitXSpinBox, 1, 0)
        joystickLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        joystickLayout.addWidget(self.joystickLimitYSpinBox, 1, 1)
        joystickLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        joystickLayout.addWidget(self.joystickLimitZSpinBox, 1, 2)
        joystickLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        joystickLayout.setColumnStretch(3, 1)

        self.delayGroupBox = QtWidgets.QGroupBox(self)
        self.delayGroupBox.setTitle("Probecard Contact Delay")

        delayLayout = QtWidgets.QHBoxLayout(self.delayGroupBox)
        delayLayout.addWidget(self.probecardContactDelaySpinBox)
        delayLayout.addStretch()

        self.overdriveGroupBox = QtWidgets.QGroupBox(self)
        self.overdriveGroupBox.setTitle("Re-Contact Z-Overdrive (1x)")

        overdriveLayout = QtWidgets.QHBoxLayout(self.overdriveGroupBox)
        overdriveLayout.addWidget(self.recontactOverdriveNumberSpinBox)
        overdriveLayout.addStretch()

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.stepsGroupBox, 0, 0, 1, 2)
        layout.addWidget(self.zLimitGroupBox, 1, 0, 1, 2)
        layout.addWidget(self.probecardGroupBox, 2, 0, 1, 2)
        layout.addWidget(self.joystickGroupBox, 3, 0, 1, 2)
        layout.addWidget(self.delayGroupBox, 4, 0, 1, 1)
        layout.addWidget(self.overdriveGroupBox, 4, 1, 1, 1)
        layout.setRowStretch(0, 1)

    def probecardLimits(self) -> Tuple[float, float, float]:
        x = self.probecardLimitXSpinBox.value()
        y = self.probecardLimitYSpinBox.value()
        z = self.probecardLimitZSpinBox.value()
        return x, y, z

    def setProbecardLimits(self, x: float, y: float, z: float) -> None:
        self.probecardLimitXSpinBox.setValue(x)
        self.probecardLimitYSpinBox.setValue(y)
        self.probecardLimitZSpinBox.setValue(z)

    def joystickLimits(self) -> Tuple[float, float, float]:
        x = self.joystickLimitXSpinBox.value()
        y = self.joystickLimitYSpinBox.value()
        z = self.joystickLimitZSpinBox.value()
        return x, y, z

    def setJoystickLimits(self, x: float, y: float, z: float) -> None:
        self.joystickLimitXSpinBox.setValue(x)
        self.joystickLimitYSpinBox.setValue(y)
        self.joystickLimitZSpinBox.setValue(z)

    def updateStepButtons(self, current, previous) -> None:
        enabled = current is not None
        self.editStepButton.setEnabled(enabled)
        self.removeStepButton.setEnabled(enabled)

    def stepDoubleClicked(self, item, column) -> None:
        self.editCurrentStep()

    def addNewStep(self) -> None:
        dialog = TableStepDialog()
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            self.stepsTreeWidget.addTopLevelItem(TableStepItem(
                dialog.stepSize(),
                dialog.zLimit(),
                dialog.stepColor()
            ))
            self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def editCurrentStep(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if isinstance(item, TableStepItem):
            dialog = TableStepDialog()
            dialog.setStepSize(item.stepSize())
            dialog.setZLimit(item.zLimit())
            dialog.setStepColor(item.stepColor())
            dialog.exec()
            if dialog.result() == dialog.Accepted:
                item.setStepSize(dialog.stepSize())
                item.setZLimit(dialog.zLimit())
                item.setStepColor(dialog.stepColor())
                self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def removeCurrentStep(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if isinstance(item, TableStepItem):
            result = QtWidgets.QMessageBox.question(
                self,
                "Remove Item",
                f"Do you want to remove step size {item.stepSize()!r}?"
            )
            if result == QtWidgets.QMessageBox.Yes:
                index = self.stepsTreeWidget.indexOfTopLevelItem(item)
                self.stepsTreeWidget.takeTopLevelItem(index)
                if not self.stepsTreeWidget.topLevelItemCount():
                    self.editStepButton.setEnabled(False)
                    self.removeStepButton.setEnabled(False)
                self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def readSettings(self) -> None:
        table_step_sizes = self.settings.get("table_step_sizes") or []
        self.stepsTreeWidget.clear()
        for item in table_step_sizes:
            self.stepsTreeWidget.addTopLevelItem(TableStepItem(
                from_table_unit(item.get("step_size")),
                from_table_unit(item.get("z_limit")),
                format(item.get("step_color"))
            ))
        self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.zLimitMovementSpinBox.setValue(settings.table_z_limit)
        # Probecard limits
        x, y, z = settings.table_probecard_maximum_limits
        self.setProbecardLimits(x, y, z)
        temporary_z_limit = settings.table_temporary_z_limit
        self.probecardLimitZCheckBox.setChecked(temporary_z_limit)
        # Joystick limits
        x, y, z = settings.table_joystick_maximum_limits
        self.setJoystickLimits(x, y, z)
        table_contact_delay = self.settings.get("table_contact_delay") or 0
        self.probecardContactDelaySpinBox.setValue(table_contact_delay)
        self.recontactOverdriveNumberSpinBox.setValue(settings.retry_contact_overdrive)

    def writeSettings(self) -> None:
        table_step_sizes = []
        for index in range(self.stepsTreeWidget.topLevelItemCount()):
            item = self.stepsTreeWidget.topLevelItem(index)
            if isinstance(item, TableStepItem):
                table_step_sizes.append({
                    "step_size": to_table_unit(item.stepSize()),
                    "z_limit": to_table_unit(item.zLimit()),
                    "step_color": format(item.stepColor()),
                })
        self.settings["table_step_sizes"] = table_step_sizes
        settings.table_z_limit = self.zLimitMovementSpinBox.value()
        # Probecard limits
        settings.table_probecard_maximum_limits = self.probecardLimits()
        temporary_z_limit = self.probecardLimitZCheckBox.isChecked()
        settings.table_temporary_z_limit = temporary_z_limit
        # Joystick limits
        settings.table_joystick_maximum_limits = self.joystickLimits()
        table_contact_delay = self.probecardContactDelaySpinBox.value()
        self.settings["table_contact_delay"] = table_contact_delay
        settings.retry_contact_overdrive = self.recontactOverdriveNumberSpinBox.value()


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

    def writeSettings(self) -> None:
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
        self.retryMeasurementSpinBox.setSuffix(" x")
        self.retryMeasurementSpinBox.setToolTip("Number of retries for measurements with failed analysis.")

        self.retryContactSpinBox = QtWidgets.QSpinBox(self)
        self.retryContactSpinBox.setRange(0, 10)
        self.retryContactSpinBox.setSuffix(" x")
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

    def readSettings(self) -> None:
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

    def writeSettings(self) -> None:
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
