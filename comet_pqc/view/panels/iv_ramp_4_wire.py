from typing import Optional

import comet
from PyQt5 import QtWidgets

from ..plotwidget import PlotWidget
from .mixins import EnvironmentMixin, MatrixMixin, VSourceMixin
from .panel import MeasurementPanel

__all__ = ["IVRamp4WirePanel"]


class IVRamp4WirePanel(MeasurementPanel):
    """Panel for 4 wire IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "4 Wire IV Ramp"

        self.plot = PlotWidget(self)
        self.plot.addAxis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.addAxis("y", align="right", text="Voltage [V]")
        self.plot.addSeries("vsrc", "x", "y", text="V Source", color="blue")
        self.plot.addSeries("xfit", "x", "y", text="Fit", color="magenta")
        self.dataTabWidget.insertTab(0, self.plot, "IV Curve")

        self.currentStartSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStartSpinBox.setRange(-2e6, +2e6)
        self.currentStartSpinBox.setDecimals(3)
        self.currentStartSpinBox.setSuffix(" uA")

        self.currentStopSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStopSpinBox.setRange(-2e6, +2e6)
        self.currentStopSpinBox.setDecimals(3)
        self.currentStopSpinBox.setSuffix(" uA")

        self.currentStepSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.currentStepSpinBox.setRange(0, +2e6)
        self.currentStepSpinBox.setDecimals(3)
        self.currentStepSpinBox.setSuffix(" uA")

        self.waitingTimeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.vsrcComplianceSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcComplianceSpinBox.setRange(0, +2200)
        self.vsrcComplianceSpinBox.setDecimals(3)
        self.vsrcComplianceSpinBox.setSuffix(" V")

        self.vsrcAcceptComplianceCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.rampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.rampGroupBox.setTitle("Ramp")

        rampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        rampGroupBoxLayout.addWidget(self.currentStartSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        rampGroupBoxLayout.addWidget(self.currentStopSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        rampGroupBoxLayout.addWidget(self.currentStepSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        self.vsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.vsrcGroupBox.setTitle("V Source")

        vsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.vsrcGroupBox)
        vsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        vsrcGroupBoxLayout.addWidget(self.vsrcComplianceSpinBox)
        vsrcGroupBoxLayout.addWidget(self.vsrcAcceptComplianceCheckBox)
        vsrcGroupBoxLayout.addStretch()

        self.generalWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        generalWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.generalWidget)
        generalWidgetLayout.addWidget(self.rampGroupBox)
        generalWidgetLayout.addWidget(self.vsrcGroupBox)
        generalWidgetLayout.addStretch()
        generalWidgetLayout.setStretch(0, 1)
        generalWidgetLayout.setStretch(1, 1)
        generalWidgetLayout.setStretch(2, 1)

        self.controlTabWidget.addTab(self.generalWidget, "General")

        MatrixMixin(self)
        VSourceMixin(self)
        EnvironmentMixin(self)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["vsrc"] = lambda x, y: ((x * ampere).to("uA").m, (y * volt).to("V").m)
        self.series_transform["xfit"] = self.series_transform["vsrc"]

        # Bindings

        self.bind("current_start", self.currentStartSpinBox, 0, unit="uA")
        self.bind("current_stop", self.currentStopSpinBox, 0, unit="uA")
        self.bind("current_step", self.currentStepSpinBox, 0, unit="uA")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("vsrc_voltage_compliance", self.vsrcComplianceSpinBox, 0, unit="V")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)

    def mount(self, measurement):
        super().mount(measurement)
        self.plot.series().get("xfit").qt.setVisible(False)
        for name, points in measurement.series.items():
            if name in self.plot.series():
                self.plot.series().clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series().get(name).append(*tr(x, y))
            self.plot.series().get(name).qt.setVisible(True)
        self.update_readings()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name in self.plot.series():
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                tr = self.series_transform.get(name, self.series_transform_default)
                self.plot.series().get(name).append(*tr(x, y))
                self.plot.series().get(name).qt.setVisible(True)

    def update_readings(self):
        super().update_readings()
        if self.measurement:
            if self.plot.isZoomed():
                self.plot.update("x")
            else:
                self.plot.chart.zoomOut() # HACK
                self.plot.fit()

    def clearReadings(self):
        super().clearReadings()
        self.plot.series().get("xfit").qt.setVisible(False)
        for series in self.plot.series().values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()
