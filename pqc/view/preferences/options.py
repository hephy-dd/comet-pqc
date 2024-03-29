from typing import Optional

from PyQt5 import QtWidgets

from pqc.settings import settings

__all__ = ["OptionsWidget"]


class OptionsWidget(QtWidgets.QWidget):
    """Options tab for preferences dialog."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.pngPlotsCheckBox = QtWidgets.QCheckBox(self)
        self.pngPlotsCheckBox.setText("Save plots as PNG")

        self.pointsInPlotsCheckBox = QtWidgets.QCheckBox(self)
        self.pointsInPlotsCheckBox.setText("Show points in plots")

        self.pngAnalysisCheckBox = QtWidgets.QCheckBox(self)
        self.pngAnalysisCheckBox.setText("Add analysis preview to PNG")

        self.exportJsonCheckBox = QtWidgets.QCheckBox(self)
        self.exportJsonCheckBox.setText("Write JSON data (*.json)")

        self.exportTxtCheckBox = QtWidgets.QCheckBox(self)
        self.exportTxtCheckBox.setText("Write plain text data (*.txt)")

        self.writeLogfilesCheckBox = QtWidgets.QCheckBox(self)
        self.writeLogfilesCheckBox.setText("Write measurement log files (*.log)")

        self.vsrcComboBox = QtWidgets.QComboBox(self)
        self.vsrcComboBox.addItems(["K2410", "K2470", "K2657A"])

        self.hvsrcComboBox = QtWidgets.QComboBox(self)
        self.hvsrcComboBox.addItems(["K2410", "K2470", "K2657A"])

        self.retryMeasurementSpinBox = QtWidgets.QSpinBox(self)
        self.retryMeasurementSpinBox.setRange(0, 1000)
        self.retryMeasurementSpinBox.setSuffix("x")
        self.retryMeasurementSpinBox.setToolTip("Number of retries for measurements with failed analysis.")

        self.retryContactSpinBox = QtWidgets.QSpinBox(self)
        self.retryContactSpinBox.setRange(0, 1000)
        self.retryContactSpinBox.setSuffix("x")
        self.retryContactSpinBox.setToolTip("Number of re-contact retries for measurements with failed analysis.")

        # Plots

        self.plotsGroupBox = QtWidgets.QGroupBox(self)
        self.plotsGroupBox.setTitle("Plots")

        plotsGroupBoxLayout = QtWidgets.QGridLayout(self.plotsGroupBox)
        plotsGroupBoxLayout.addWidget(self.pngPlotsCheckBox, 0, 0)
        plotsGroupBoxLayout.addWidget(self.pointsInPlotsCheckBox, 1, 0)

        # Analysis

        self.analysisGroupBox = QtWidgets.QGroupBox(self)
        self.analysisGroupBox.setTitle("Analysis")

        analysisGroupBoxLayout = QtWidgets.QGridLayout(self.analysisGroupBox)
        analysisGroupBoxLayout.addWidget(self.pngAnalysisCheckBox, 0, 0)
        analysisGroupBoxLayout.setColumnStretch(1, 1)
        analysisGroupBoxLayout.setRowStretch(1, 1)

        # Formats

        self.formatsGroupBox = QtWidgets.QGroupBox(self)
        self.formatsGroupBox.setTitle("Formats")

        formatsGroupBoxLayout = QtWidgets.QGridLayout(self.formatsGroupBox)
        formatsGroupBoxLayout.addWidget(self.exportJsonCheckBox, 0, 0)
        formatsGroupBoxLayout.addWidget(self.exportTxtCheckBox, 1, 0)

        # Logfiles

        self.logfileGroupBox = QtWidgets.QGroupBox(self)
        self.logfileGroupBox.setTitle("Log files")

        logfileGroupBoxLayout = QtWidgets.QGridLayout(self.logfileGroupBox)
        logfileGroupBoxLayout.addWidget(self.writeLogfilesCheckBox, 0, 0)
        logfileGroupBoxLayout.setColumnStretch(1, 1)
        logfileGroupBoxLayout.setRowStretch(1, 1)

        # Instruments

        self.instrumentsGroupBox = QtWidgets.QGroupBox(self)
        self.instrumentsGroupBox.setTitle("Instruments")

        instrumentsGroupBoxLayout = QtWidgets.QGridLayout(self.instrumentsGroupBox)
        instrumentsGroupBoxLayout.addWidget(QtWidgets.QLabel("V Source"), 0, 0)
        instrumentsGroupBoxLayout.addWidget(self.vsrcComboBox, 0, 1)
        instrumentsGroupBoxLayout.addWidget(QtWidgets.QLabel("HV Source"), 1, 0)
        instrumentsGroupBoxLayout.addWidget(self.hvsrcComboBox, 1, 1)
        instrumentsGroupBoxLayout.setColumnStretch(2, 1)

        # Auto Retry

        self.autoRetryGroupBox = QtWidgets.QGroupBox(self)
        self.autoRetryGroupBox.setTitle("Auto Retry")

        autoRetryGroupBoxLayout = QtWidgets.QGridLayout(self.autoRetryGroupBox)
        autoRetryGroupBoxLayout.addWidget(QtWidgets.QLabel("Retry Measurements"), 0, 0)
        autoRetryGroupBoxLayout.addWidget(self.retryMeasurementSpinBox, 0, 1)
        autoRetryGroupBoxLayout.addWidget(QtWidgets.QLabel("Retry Contact"), 1, 0)
        autoRetryGroupBoxLayout.addWidget(self.retryContactSpinBox, 1, 1)
        autoRetryGroupBoxLayout.setColumnStretch(2, 1)

        # Layout

        firstRowLayout = QtWidgets.QHBoxLayout()
        firstRowLayout.addWidget(self.plotsGroupBox, 0)
        firstRowLayout.addWidget(self.analysisGroupBox, 1)

        secondRowLayout = QtWidgets.QHBoxLayout()
        secondRowLayout.addWidget(self.formatsGroupBox, 0)
        secondRowLayout.addWidget(self.logfileGroupBox, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(firstRowLayout)
        layout.addLayout(secondRowLayout)
        layout.addWidget(self.instrumentsGroupBox)
        layout.addWidget(self.autoRetryGroupBox)
        layout.addStretch(1)

    def readSettings(self) -> None:
        png_plots = bool(settings.settings.get("png_plots", False))
        self.pngPlotsCheckBox.setChecked(png_plots)
        points_in_plots = bool(settings.settings.get("points_in_plots", False))
        self.pointsInPlotsCheckBox.setChecked(points_in_plots)
        self.pngAnalysisCheckBox.setChecked(settings.png_analysis)
        self.exportJsonCheckBox.setChecked(settings.export_json)
        self.exportTxtCheckBox.setChecked(settings.export_txt)
        write_logfiles = bool(settings.settings.get("write_logfiles", True))
        self.writeLogfilesCheckBox.setChecked(write_logfiles)
        vsrc_instrument = str(settings.settings.get("vsrc_instrument", "K2657A"))
        index = self.vsrcComboBox.findText(vsrc_instrument)
        self.vsrcComboBox.setCurrentIndex(index)
        hvsrc_instrument = str(settings.settings.get("hvsrc_instrument", "K2410"))
        index = self.hvsrcComboBox.findText(hvsrc_instrument)
        self.hvsrcComboBox.setCurrentIndex(index)
        self.retryMeasurementSpinBox.setValue(int(settings.retry_measurement_count))
        self.retryContactSpinBox.setValue(int(settings.retry_contact_count))

    def writeSettings(self) -> None:
        settings.settings["png_plots"] = self.pngPlotsCheckBox.isChecked()
        settings.settings["points_in_plots"] = self.pointsInPlotsCheckBox.isChecked()
        settings.png_analysis = self.pngAnalysisCheckBox.isChecked()
        settings.export_json = self.exportJsonCheckBox.isChecked()
        settings.export_txt = self.exportTxtCheckBox.isChecked()
        settings.settings["write_logfiles"] = self.writeLogfilesCheckBox.isChecked()
        settings.settings["vsrc_instrument"] = self.vsrcComboBox.currentText()
        settings.settings["hvsrc_instrument"] = self.hvsrcComboBox.currentText()
        settings.retry_measurement_count = self.retryMeasurementSpinBox.value()
        settings.retry_contact_count = self.retryContactSpinBox.value()
