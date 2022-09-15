import comet
from comet import ui
from PyQt5 import QtCore, QtWidgets

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, VSourceMixin

__all__ = ["IVRamp4WirePanel"]


class IVRamp4WirePanel(MatrixPanel, VSourceMixin, EnvironmentMixin):
    """Panel for 4 wire IV ramp measurements."""

    type = "iv_ramp_4_wire"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setTitle("4 Wire IV Ramp")

        self.register_vsource()
        self.register_environment()

        self.plot = ui.Plot(height=300, legend="right")
        self.plot.add_axis("x", align="bottom", text="Current [uA] (abs)")
        self.plot.add_axis("y", align="right", text="Voltage [V]")
        self.plot.add_series("vsrc", "x", "y", text="V Source", color="blue")
        self.plot.add_series("xfit", "x", "y", text="Fit", color="magenta")
        self.plot.qt.setProperty("type", "plot")
        self.dataTabWidget.insertTab(0, self.plot.qt, "IV Curve")

        self.current_start = ui.Number(decimals=3, suffix="uA")
        self.current_stop = ui.Number(decimals=3, suffix="uA")
        self.current_step = ui.Number(minimum=0, decimals=3, suffix="uA")
        self.waiting_time = ui.Number(minimum=0, decimals=2, suffix="s")
        self.vsrc_voltage_compliance = ui.Number(decimals=3, suffix="V")

        self.vsrc_accept_compliance: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.vsrc_accept_compliance.setText("Accept Compliance")

        self.bind("current_start", self.current_start, 0, unit="uA")
        self.bind("current_stop", self.current_stop, 0, unit="uA")
        self.bind("current_step", self.current_step, 0, unit="uA")
        self.bind("waiting_time", self.waiting_time, 1, unit="s")
        self.bind("vsrc_voltage_compliance", self.vsrc_voltage_compliance, 0, unit="V")
        self.bind("vsrc_accept_compliance", self.vsrc_accept_compliance, False)

        currentRampGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        currentRampGroupBox.setTitle("Current Ramp")

        currentRampGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(currentRampGroupBox)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Start", self))
        currentRampGroupBoxLayout.addWidget(self.current_start.qt)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        currentRampGroupBoxLayout.addWidget(self.current_stop.qt)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        currentRampGroupBoxLayout.addWidget(self.current_step.qt)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        currentRampGroupBoxLayout.addWidget(self.waiting_time.qt)
        currentRampGroupBoxLayout.addStretch()

        vsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        vsrcGroupBox.setTitle("V Source")

        vsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(vsrcGroupBox)
        vsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        vsrcGroupBoxLayout.addWidget(self.vsrc_voltage_compliance.qt)
        vsrcGroupBoxLayout.addWidget(self.vsrc_accept_compliance)
        vsrcGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(currentRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(vsrcGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        ampere = comet.ureg("A")
        volt = comet.ureg("V")

        self.series_transform["vsrc"] = lambda x, y: ((x * ampere).to("uA").m, (y * volt).to("V").m)
        self.series_transform["xfit"] = self.series_transform.get("vsrc")

    def mount(self, measurement):
        super().mount(measurement)
        self.plot.series.get("xfit").qt.setVisible(False)
        for name, points in measurement.series.items():
            if name in self.plot.series:
                self.plot.series.clear()
            tr = self.series_transform.get(name, self.series_transform_default)
            for x, y in points:
                self.plot.series.get(name).append(*tr(x, y))
            self.plot.series.get(name).qt.setVisible(True)
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
        super().updateReadings()
        if self.measurement:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.qt.chart().zoomOut() # HACK
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
