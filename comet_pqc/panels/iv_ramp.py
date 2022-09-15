import comet
from comet import ui
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin

__all__ = ["IVRampPanel"]


class IVRampPanel(MatrixPanel, HVSourceMixin, EnvironmentMixin):
    """Panel for IV ramp measurements."""

    type = "iv_ramp"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setTitle("IV Ramp")

        self.register_hvsource()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Voltage [V] (abs)")
        self.plot.add_axis("y", align="right", text="Current [uA]")
        self.plot.add_series("hvsrc", "x", "y", text="HV Source", color="red")
        self.plot.add_series("xfit", "x", "y", text="Fit", color="magenta")
        self.plot.qt.setProperty("type", "plot")
        self.dataTabWidget.insertTab(0, self.plot.qt, "IV Curve")

        self.voltage_start = ui.Number(decimals=3, suffix="V")
        self.voltage_stop = ui.Number(decimals=3, suffix="V")
        self.voltage_step = ui.Number(minimum=0, maximum=200, decimals=3, suffix="V")
        self.waiting_time = ui.Number(minimum=0, decimals=2, suffix="s")

        self.hvsrc_current_compliance = ui.Metric(minimum=0, decimals=3, prefixes="mun", unit="A")

        self.hvsrc_accept_compliance: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.hvsrc_accept_compliance.setText("Accept Compliance")
        
        self.bind("voltage_start", self.voltage_start, 0, unit="V")
        self.bind("voltage_stop", self.voltage_stop, 100, unit="V")
        self.bind("voltage_step", self.voltage_step, 1, unit="V")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")

        self.bind("hvsrc_current_compliance", self.hvsrc_current_compliance, 0, unit="A")
        self.bind("hvsrc_accept_compliance", self.hvsrc_accept_compliance, False)

        hvsrcRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcRampGroupBox.setTitle("HV Source Ramp")

        hvsrcRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcRampGroupBox)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_start.qt)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_stop.qt)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_step.qt)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        hvsrcRampGroupBoxLayout.addWidget(self.waiting_time.qt)
        hvsrcRampGroupBoxLayout.addStretch()

        hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_current_compliance.qt)
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_accept_compliance)
        hvsrcGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(hvsrcRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(hvsrcGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["hvsrc"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform.get("hvsrc")

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series.get(name).append(*tr(x, y))
        self.updateReadings()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name in self.plot.series:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
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
