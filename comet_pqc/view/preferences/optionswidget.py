from typing import Optional

from PyQt5 import QtCore, QtWidgets

from comet_pqc.settings import settings

from .preferencesdialog import PreferencesWidget

__all__ = ["OptionsWidget"]


class OptionsWidget(PreferencesWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.pngPlotsCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.pngPlotsCheckBox.setText("Save plots as PNG")

        self.pointsInPlotsCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.pointsInPlotsCheckBox.setText("Show points in plots")

        self.pngAnalysisCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.pngAnalysisCheckBox.setText("Add analysis preview to PNG")

        self.exportJsonCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.exportJsonCheckBox.setText("Write JSON data (*.json)")

        self.exportTxtCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.exportTxtCheckBox.setText("Write plain text data (*.txt)")

        self.writeLogfilesCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.writeLogfilesCheckBox.setText("Write measurement log files (*.log)")

        self.vsrcInstrumentComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        self.vsrcInstrumentComboBox.addItems(["K2410", "K2470", "K2657A"])

        self.hvsrcInstrumentComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        self.hvsrcInstrumentComboBox.addItems(["K2410", "K2470", "K2657A"])

        self.retryMeasurementSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.retryMeasurementSpinBox.setToolTip("Number of retries for measurements with failed analysis.")
        self.retryMeasurementSpinBox.setRange(0, 10)
        self.retryMeasurementSpinBox.setSuffix("x")

        self.retryContactSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.retryContactSpinBox.setToolTip("Number of re-contact retries for measurements with failed analysis.")
        self.retryContactSpinBox.setRange(0, 10)
        self.retryContactSpinBox.setSuffix("x")

        self.plotsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.plotsGroupBox.setTitle("Plots")

        plotsGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.plotsGroupBox)
        plotsGroupBoxLayout.addWidget(self.pngPlotsCheckBox)
        plotsGroupBoxLayout.addWidget(self.pointsInPlotsCheckBox)

        self.analysisGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.analysisGroupBox.setTitle("Analysis")

        analysisGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.analysisGroupBox)
        analysisGroupBoxLayout.addWidget(self.pngAnalysisCheckBox)
        analysisGroupBoxLayout.addStretch()

        self.formatsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.formatsGroupBox.setTitle("Formats")

        formatsGroupBoxlayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.formatsGroupBox)
        formatsGroupBoxlayout.addWidget(self.exportJsonCheckBox)
        formatsGroupBoxlayout.addWidget(self.exportTxtCheckBox)

        self.logfilesGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.logfilesGroupBox.setTitle("Log Files")

        logfilesGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.logfilesGroupBox)
        logfilesGroupBoxLayout.addWidget(self.writeLogfilesCheckBox)
        logfilesGroupBoxLayout.addStretch()

        self.instrumentsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.instrumentsGroupBox.setTitle("Instruments")

        instrumentsGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.instrumentsGroupBox)
        instrumentsGroupBoxLayout.addRow("V Source", self.vsrcInstrumentComboBox)
        instrumentsGroupBoxLayout.addRow("HV Source", self.hvsrcInstrumentComboBox)

        self.autoRetryGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.autoRetryGroupBox.setTitle("Auto Retry")

        autoRetryGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.autoRetryGroupBox)
        autoRetryGroupBoxLayout.addRow("Retry Measurements", self.retryMeasurementSpinBox)
        autoRetryGroupBoxLayout.addRow("Retry Contact", self.retryContactSpinBox)

        row1Layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        row1Layout.addWidget(self.plotsGroupBox)
        row1Layout.addWidget(self.analysisGroupBox)
        row1Layout.addStretch()

        row2Layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        row2Layout.addWidget(self.formatsGroupBox)
        row2Layout.addWidget(self.logfilesGroupBox)
        row2Layout.addStretch()

        row3Layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        row3Layout.addWidget(self.instrumentsGroupBox)
        row3Layout.addWidget(self.autoRetryGroupBox)
        row3Layout.addStretch()

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(row1Layout)
        layout.addLayout(row2Layout)
        layout.addLayout(row3Layout)
        layout.addStretch(10)

    def readSettings(self):
        self.pngPlotsCheckBox.setChecked(settings.value("png_plots", False, bool))
        self.pointsInPlotsCheckBox.setChecked(settings.value("points_in_plots", False, bool))
        self.pngAnalysisCheckBox.setChecked(settings.value("png_analysis", False, bool))
        self.exportJsonCheckBox.setChecked(settings.value("export_json", False, bool))
        self.exportTxtCheckBox.setChecked(settings.value("export_txt", True, bool))
        self.writeLogfilesCheckBox.setChecked(settings.value("write_logfiles", True, bool))
        index = self.vsrcInstrumentComboBox.findText(settings.value("vsrc_instrument", "K2657A", str))
        self.vsrcInstrumentComboBox.setCurrentIndex(index)
        index = self.hvsrcInstrumentComboBox.findText(settings.value("hvsrc_instrument", "K2410", str))
        self.hvsrcInstrumentComboBox.setCurrentIndex(index)
        self.retryMeasurementSpinBox.setValue(settings.retry_measurement_count())
        self.retryContactSpinBox.setValue(settings.retry_contact_count())

    def writeSettings(self):
        settings.setValue("png_plots", self.pngPlotsCheckBox.isChecked())
        settings.setValue("points_in_plots", self.pointsInPlotsCheckBox.isChecked())
        settings.setValue("png_analysis", self.pngAnalysisCheckBox.isChecked())
        settings.setValue("export_json", self.exportJsonCheckBox.isChecked())
        settings.setValue("export_txt", self.exportTxtCheckBox.isChecked())
        settings.setValue("write_logfiles", self.writeLogfilesCheckBox.isChecked())
        settings.setValue("vsrc_instrument", self.vsrcInstrumentComboBox.currentText())
        settings.setValue("hvsrc_instrument", self.hvsrcInstrumentComboBox.currentText())
        settings.set_retry_measurement_count(self.retryMeasurementSpinBox.value())
        settings.set_retry_contact_count(self.retryContactSpinBox.value())
