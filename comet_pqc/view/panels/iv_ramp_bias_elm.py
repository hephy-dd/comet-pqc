from typing import Optional

import comet
from PyQt5 import QtWidgets

from ..plotwidget import PlotWidget
from .mixins import (ElectrometerMixin, EnvironmentMixin, HVSourceMixin,
                     MatrixMixin, VSourceMixin)
from .panel import MeasurementPanel

__all__ = ["IVRampBiasElmPanel"]


class IVRampBiasElmPanel(MeasurementPanel):
    """Panel for bias IV ramp measurements."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "IV Ramp Bias Elm"

        self.plot = PlotWidget(self)
        self.plot.addAxis("x", align="bottom", text="Voltage [V]")
        self.plot.addAxis("y", align="right", text="Current [uA]")
        self.plot.addSeries("elm", "x", "y", text="Electrometer", color="blue")
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

        self.biasVoltageSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.biasVoltageSpinBox.setRange(-2200, +2200)
        self.biasVoltageSpinBox.setDecimals(3)
        self.biasVoltageSpinBox.setSuffix(" V")

        self.biasModeComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        self.biasModeComboBox.addItem("constant", "constant")
        self.biasModeComboBox.addItem("offset", "offset")

        self.hvsrcCurrentComplianceSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrcCurrentComplianceSpinBox.setRange(0, 2e6)
        self.hvsrcCurrentComplianceSpinBox.setDecimals(3)
        self.hvsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.hvsrcAcceptComplianceCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.vsrcCurrentComplianceSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrcCurrentComplianceSpinBox.setRange(0, 2e6)
        self.vsrcCurrentComplianceSpinBox.setDecimals(3)
        self.vsrcCurrentComplianceSpinBox.setSuffix(" uA")

        self.vsrcAcceptComplianceCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.vsrcAcceptComplianceCheckBox.setText("Accept Compliance")

        self.hvsrcRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hvsrcRampGroupBox.setTitle("HV Source Ramp")

        hvsrcRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.hvsrcRampGroupBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltageStartSpinBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltageStopSpinBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltageStepSpinBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        hvsrcRampGroupBoxLayout.addWidget(self.waitingTimeSpinBox)
        hvsrcRampGroupBoxLayout.addStretch()

        self.vsrcBiasGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.vsrcBiasGroupBox.setTitle("V Source Bias")

        vsrcBiasGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.vsrcBiasGroupBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage", self))
        vsrcBiasGroupBoxLayout.addWidget(self.biasVoltageSpinBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Compliance", self))
        vsrcBiasGroupBoxLayout.addWidget(self.vsrcCurrentComplianceSpinBox)
        vsrcBiasGroupBoxLayout.addWidget(self.vsrcAcceptComplianceCheckBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Mode", self))
        vsrcBiasGroupBoxLayout.addWidget(self.biasModeComboBox)
        vsrcBiasGroupBoxLayout.addStretch()

        self.hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrcCurrentComplianceSpinBox)
        hvsrcGroupBoxLayout.addWidget(self.hvsrcAcceptComplianceCheckBox)
        hvsrcGroupBoxLayout.addStretch()

        self.generalWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)

        generalWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.generalWidget)
        generalWidgetLayout.addWidget(self.hvsrcRampGroupBox)
        generalWidgetLayout.addWidget(self.vsrcBiasGroupBox)
        generalWidgetLayout.addWidget(self.hvsrcGroupBox)
        generalWidgetLayout.setStretch(0, 1)
        generalWidgetLayout.setStretch(1, 1)
        generalWidgetLayout.setStretch(2, 1)

        self.controlTabWidget.addTab(self.generalWidget, "General")

        MatrixMixin(self)
        HVSourceMixin(self)
        VSourceMixin(self)
        ElectrometerMixin(self)
        EnvironmentMixin(self)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["elm"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform["elm"]

        # Bindings

        self.bind("voltage_start", self.voltageStartSpinBox, 0, unit="V")
        self.bind("voltage_stop", self.voltageStopSpinBox, 0, unit="V")
        self.bind("voltage_step", self.voltageStepSpinBox, 0, unit="V")
        self.bind("waiting_time", self.waitingTimeSpinBox, 1, unit="s")
        self.bind("bias_voltage", self.biasVoltageSpinBox, 0, unit="V")
        self.bind("bias_mode", self.biasModeComboBox, "constant")
        self.bind("hvsrc_current_compliance", self.hvsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("hvsrc_accept_compliance", self.hvsrcAcceptComplianceCheckBox, False)
        self.bind("vsrc_current_compliance", self.vsrcCurrentComplianceSpinBox, 0, unit="uA")
        self.bind("vsrc_accept_compliance", self.vsrcAcceptComplianceCheckBox, False)

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series():
                if name in self.plot.series():
                    self.plot.series().clear()
                tr = self.series_transform.get(name, self.series_transform_default)
                if points[0][0] > points[-1][0]:
                    self.plot.axes().get("x").qt.setReverse(True)
                else:
                    self.plot.axes().get("x").qt.setReverse(False)
                for x, y in points:
                    self.plot.series().get(name).append(*tr(x, y))
        self.update_readings()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name in self.plot.series():
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                if self.voltageStartSpinBox.value() > self.voltageStopSpinBox.value():
                    self.plot.axes().get("x").qt.setReverse(True)
                else:
                    self.plot.axes().get("x").qt.setReverse(False)
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
