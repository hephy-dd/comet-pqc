from typing import Optional

import comet
from PyQt5 import QtWidgets

from ..plotwidget import PlotWidget
from ..metricwidget import MetricWidget
from .mixins import EnvironmentMixin, HVSourceMixin, MatrixMixin
from .panel import MeasurementPanel

__all__ = ["IVRampPanel"]


class IVRampPanel(MeasurementPanel):
    """Panel for IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "IV Ramp"

        self.plot = PlotWidget(self)
        self.plot.addAxis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.addAxis("y", align="right", text="Current [uA]")
        self.plot.addSeries("hvsrc", "x", "y", text="HV Source", color="red")
        self.plot.addSeries("xfit", "x", "y", text="Fit", color="magenta")
        self.dataTabWidget.insertTab(0, self.plot, "IV Curve")

        self.voltageStartSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStartSpinBox.setRange(-2200, +2200)
        self.voltageStartSpinBox.setDecimals(3)
        self.voltageStartSpinBox.setSuffix(" V")

        self.voltageStopSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStopSpinBox.setRange(-2200, +2200)
        self.voltageStopSpinBox.setDecimals(3)
        self.voltageStopSpinBox.setSuffix(" V")

        self.voltageStepSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltageStepSpinBox.setRange(0, 200)
        self.voltageStepSpinBox.setDecimals(3)
        self.voltageStepSpinBox.setSuffix(" V")

        self.waitingTimeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waitingTimeSpinBox.setRange(0, 60)
        self.waitingTimeSpinBox.setDecimals(2)
        self.waitingTimeSpinBox.setSuffix(" s")

        self.hvsrcComplianceMetric: MetricWidget = MetricWidget("A", self)
        self.hvsrcComplianceMetric.setMinimum(0)
        self.hvsrcComplianceMetric.setDecimals(3)
        self.hvsrcComplianceMetric.setPrefixes("mun")

        self.hvsrcAcceptComplianceCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.rampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.rampGroupBox.setTitle("Ramp")

        rampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.rampGroupBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        rampGroupBoxLayout.addWidget(self.voltageStartSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        rampGroupBoxLayout.addWidget(self.voltageStopSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        rampGroupBoxLayout.addWidget(self.voltageStepSpinBox)
        rampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        rampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        rampGroupBoxLayout.addStretch()

        self.hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hvsrcGroupBox.setTitle("HV Source")

        hvSourceGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.hvsrcGroupBox)
        hvSourceGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        hvSourceGroupBoxLayout.addWidget(self.hvsrcComplianceMetric)
        hvSourceGroupBoxLayout.addWidget(self.hvsrcAcceptComplianceCheckBox)
        hvSourceGroupBoxLayout.addStretch()

        self.generalWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        generalWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.generalWidget)
        generalWidgetLayout.addWidget(self.rampGroupBox)
        generalWidgetLayout.addWidget(self.hvsrcGroupBox)
        generalWidgetLayout.addStretch()
        generalWidgetLayout.setStretch(0, 1)
        generalWidgetLayout.setStretch(1, 1)
        generalWidgetLayout.setStretch(2, 1)

        self.controlTabWidget.addTab(self.generalWidget, "General")

        MatrixMixin(self)
        HVSourceMixin(self)
        EnvironmentMixin(self)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["hvsrc"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform["hvsrc"]

        # Bindings

        self.bind("voltage_start", self.voltageStartSpinBox, 0, unit="V")
        self.bind("voltage_stop", self.voltageStopSpinBox, 100, unit="V")
        self.bind("voltage_step", self.voltageStepSpinBox, 1, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")

        self.bind("hvsrc_current_compliance", self.hvsrcComplianceMetric, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series():
                self.plot.series().clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series().get(name).append(*tr(x, y))
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
        if self.measurement:
            if self.plot.isZoomed():
                self.plot.update("x")
            else:
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
