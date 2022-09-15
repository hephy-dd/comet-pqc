from comet import ui, ureg
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import (ElectrometerMixin, EnvironmentMixin, HVSourceMixin,
                     VSourceMixin)

__all__ = ["IVRampBiasElmPanel"]


class IVRampBiasElmPanel(MatrixPanel, HVSourceMixin, VSourceMixin, ElectrometerMixin, EnvironmentMixin):
    """Panel for bias IV ramp measurements."""

    type = "iv_ramp_bias_elm"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setTitle("IV Ramp Bias Elm")

        self.register_hvsource()
        self.register_vsource()
        self.register_electrometer()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V]")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("elm", "x", "y", text="Electrometer", color="blue")
        self.plot.add_series("xfit", "x", "y", text="Fit", color="magenta")
        self.plot.qt.setProperty("type", "plot")
        self.dataTabWidget.insertTab(0, self.plot.qt, "IV Curve")

        self.voltage_start: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_start.setRange(-2.1e3, 2.1e3)
        self.voltage_start.setDecimals(3)
        self.voltage_start.setSuffix(" V")

        self.voltage_stop: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_stop.setRange(-2.1e3, 2.1e3)
        self.voltage_stop.setDecimals(3)
        self.voltage_stop.setSuffix(" V")

        self.voltage_step: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_step.setRange(0, 2.1e2)
        self.voltage_step.setDecimals(3)
        self.voltage_step.setSuffix(" V")

        self.waiting_time: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time.setRange(0, 60)
        self.waiting_time.setDecimals(2)
        self.waiting_time.setSuffix(" s")

        self.bias_voltage: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.bias_voltage.setRange(-2.1e3, 2.1e3)
        self.bias_voltage.setDecimals(3)
        self.bias_voltage.setSuffix(" V")

        self.bias_mode: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        self.bias_mode.addItem("constant", "constant")
        self.bias_mode.addItem("offset", "offset")

        self.hvsrc_current_compliance: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.hvsrc_current_compliance.setRange(0, 2.1e6)
        self.hvsrc_current_compliance.setDecimals(3)
        self.hvsrc_current_compliance.setSuffix(" uA")

        self.hvsrc_accept_compliance: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrc_accept_compliance.setText("Accept Compliance")

        self.vsrc_current_compliance: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrc_current_compliance.setRange(0, 2.1e6)
        self.vsrc_current_compliance.setDecimals(3)
        self.vsrc_current_compliance.setSuffix(" uA")

        self.vsrc_accept_compliance: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.vsrc_accept_compliance.setText("Accept Compliance")

        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 0, unit="V")
        self.bind("voltage_step", self.voltage_step, 0, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("bias_voltage", self.bias_voltage, 0, unit="V")
        self.bind("bias_mode", self.bias_mode, "constant")
        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="uA")
        self.bind("hvsrc_accept_compliance", self.hvsrc_accept_compliance, False)
        self.bind("vsrc_current_compliance", self.vsrc_current_compliance, 0, unit="uA")
        self.bind("vsrc_accept_compliance", self.vsrc_accept_compliance, False)

        hvsrcRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcRampGroupBox.setTitle("HV Source Ramp")

        hvsrcRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcRampGroupBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_start)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_stop)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_step)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        hvsrcRampGroupBoxLayout.addWidget(self.waiting_time)
        hvsrcRampGroupBoxLayout.addStretch()

        vsrcBiasGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        vsrcBiasGroupBox.setTitle("V Source Bias")

        vsrcBiasGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(vsrcBiasGroupBox)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Voltage", self))
        vsrcBiasGroupBoxLayout.addWidget(self.bias_voltage)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Compliance", self))
        vsrcBiasGroupBoxLayout.addWidget(self.vsrc_current_compliance)
        vsrcBiasGroupBoxLayout.addWidget(self.vsrc_accept_compliance)
        vsrcBiasGroupBoxLayout.addWidget(QtWidgets.QLabel("Bias Mode", self))
        vsrcBiasGroupBoxLayout.addWidget(self.bias_mode)
        vsrcBiasGroupBoxLayout.addStretch()

        hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_current_compliance)
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_accept_compliance)
        hvsrcGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(hvsrcRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(vsrcBiasGroupBox, 1)
        self.generalWidgetLayout.addWidget(hvsrcGroupBox, 1)

        ampere = ureg("A")
        volt = ureg("V")

        self.series_transform["elm"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform.get("elm")

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                if name in self.plot.series:
                    self.plot.series.clear()
                tr = self.series_transform.get(name, self.series_transform_default)
                if points[0][0] > points[-1][0]:
                    self.plot.axes.get("x").qt.setReverse(True)
                else:
                    self.plot.axes.get("x").qt.setReverse(False)
                for x, y in points:
                    self.plot.series.get(name).append(*tr(x, y))
        self.updateReadings()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                if self.voltage_start.value > self.voltage_stop.value:
                    self.plot.axes.get("x").qt.setReverse(True)
                else:
                    self.plot.axes.get("x").qt.setReverse(False)
                tr = self.series_transform.get(name, self.series_transform_default)
                self.plot.series.get(name).append(*tr(x, y))
                self.plot.series.get(name).qt.setVisible(True)

    def updateReadings(self):
        if self.measurement:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.fit()

    def clearReadings(self):
        super().clearReadings()
        self.plot.series.get("xfit").qt.setVisible(False)
        for series in self.plot.series.values():
            series.clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.plot.fit()
