from typing import Optional

from PyQt5 import QtCore, QtWidgets, QtChart

from comet_pqc.plotwidget import VIPlotWidget

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, VSourceMixin

__all__ = ["IVRamp4WirePanel"]


class IVRamp4WirePanel(MatrixPanel, VSourceMixin, EnvironmentMixin):
    """Panel for 4 wire IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("4 Wire IV Ramp")

        self.series = {}

        self.register_vsource()
        self.register_environment()

        self.ivPlotWidget = VIPlotWidget()
        self.dataTabWidget.insertTab(0, self.ivPlotWidget, "IV Curve")

        self.vsrcSeries = QtChart.QLineSeries()
        self.vsrcSeries.setName("V Source")
        self.vsrcSeries.setPen(QtCore.Qt.blue)
        self.ivPlotWidget.addSeries(self.vsrcSeries)
        self.series["vsrc"] = self.vsrcSeries

        self.xfitSeries = QtChart.QLineSeries()
        self.xfitSeries.setName("Fit")
        self.xfitSeries.setPen(QtCore.Qt.magenta)
        self.ivPlotWidget.addSeries(self.xfitSeries)
        self.series["xfit"] = self.xfitSeries

        self.currentStartSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStartSpinBox.setDecimals(3)
        self.currentStartSpinBox.setRange(-2.1e6, +2.1e6)
        self.currentStartSpinBox.setSuffix(" uA")

        self.currentStopSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStopSpinBox.setDecimals(3)
        self.currentStopSpinBox.setRange(-2.1e6, +2.1e6)
        self.currentStopSpinBox.setSuffix(" uA")

        self.currentStepSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStepSpinBox.setDecimals(3)
        self.currentStepSpinBox.setRange(0, +2.1e6)
        self.currentStepSpinBox.setSuffix(" uA")

        self.waitingTimeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.vsrcVoltageComplianceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcVoltageComplianceSpinBox.setDecimals(3)
        self.vsrcVoltageComplianceSpinBox.setRange(0, +2200)
        self.vsrcVoltageComplianceSpinBox.setSuffix(" V")

        self.vsrcAcceptComplianceSpinBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceSpinBox.setText("Accept Compliance")

        self.bind("current_start", self.currentStartSpinBox, 0, unit="uA")
        self.bind("current_stop", self.currentStopSpinBox, 0, unit="uA")
        self.bind("current_step", self.currentStepSpinBox, 0, unit="uA")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("vsrc_voltage_compliance", self.vsrcVoltageComplianceSpinBox, 0, unit="V")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceSpinBox, False)

        rampGroupBox = QtWidgets.QGroupBox(self)
        rampGroupBox.setTitle("Ramp")

        rampGroupBoxLayout = QtWidgets.QVBoxLayout(rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start"))
        rampGroupBoxLayout.addWidget(self.currentStartSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop"))
        rampGroupBoxLayout.addWidget(self.currentStopSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step"))
        rampGroupBoxLayout.addWidget(self.currentStepSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time"))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        vsrcGroupBox = QtWidgets.QGroupBox(self)
        vsrcGroupBox.setTitle("V Source")

        vsrcGroupBoxLayout = QtWidgets.QVBoxLayout(vsrcGroupBox)
        vsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance"))
        vsrcGroupBoxLayout.addWidget(self.vsrcVoltageComplianceSpinBox)
        vsrcGroupBoxLayout.addWidget(self.vsrcAcceptComplianceSpinBox)
        vsrcGroupBoxLayout.addStretch()

        layout = self.generalWidget.layout()
        layout.addWidget(rampGroupBox, 1)
        layout.addWidget(vsrcGroupBox, 1)
        layout.addStretch(1)

    def mount(self, measurement):
        super().mount(measurement)
        self.xfitSeries.setVisible(False)
        self.ivPlotWidget.clear()
        for name, points in measurement.series.items():
            for x, y in points:
                self.series.get(name).append(x, y)
            self.series.get(name).setVisible(True)
        self.updateReadings()

    def appendReading(self, name: str, x: float, y: float) -> None:
        if self.measurement:
            if name in self.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                self.series.get(name).append(x, y)
                self.series.get(name).setVisible(True)

    def updateReadings(self) -> None:
        super().updateReadings()
        self.ivPlotWidget.resizeAxes()

    def clearReadings(self) -> None:
        super().clearReadings()
        self.xfitSeries.setVisible(False)
        self.ivPlotWidget.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.ivPlotWidget.resizeAxes()
