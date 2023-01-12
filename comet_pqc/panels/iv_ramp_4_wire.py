from typing import Optional

from comet import ui, ureg
from PyQt5 import QtChart, QtCore, QtWidgets

from ..components import PlotWidget
from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, VSourceMixin

__all__ = ["IVRamp4WirePanel"]


class IVRamp4WirePanel(MatrixPanel, VSourceMixin, EnvironmentMixin):
    """Panel for 4 wire IV ramp measurements."""

    type_name = "iv_ramp_4_wire"

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
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

        self.plotWidget = PlotWidget(self)
        self.dataTabWidget.insertTab(0, self.plotWidget, "IV Curve (New)")

        xAxis = self.plotWidget.addValueAxis(title="Current [uA] (abs)", alignment=QtCore.Qt.AlignBottom)
        yAxis = self.plotWidget.addValueAxis(title="Voltage [V]", alignment=QtCore.Qt.AlignRight)

        self.vsrcSeries = self.plotWidget.addLineSeries(name="V Source", color="blue")
        self.vsrcSeries.attachAxis(xAxis)
        self.vsrcSeries.attachAxis(yAxis)

        self.xfitSeries = self.plotWidget.addLineSeries(name="Fit", color="magenta")
        self.xfitSeries.attachAxis(xAxis)
        self.xfitSeries.attachAxis(yAxis)

        self.dataSeries = {
            "vsrc": self.vsrcSeries,
            "xfit": self.xfitSeries
        }

        self.current_start: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.current_start.setRange(-2.1e6, 2.1e6)
        self.current_start.setDecimals(3)
        self.current_start.setSuffix(" uA")

        self.current_stop: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.current_stop.setRange(-2.1e6, 2.1e6)
        self.current_stop.setDecimals(3)
        self.current_stop.setSuffix(" uA")

        self.current_step: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.current_step.setRange(-2.1e6, 2.1e6)
        self.current_step.setDecimals(3)
        self.current_step.setSuffix(" uA")

        self.waiting_time: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time.setRange(0, 60)
        self.waiting_time.setDecimals(2)
        self.waiting_time.setSuffix(" s")

        self.vsrc_voltage_compliance: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.vsrc_voltage_compliance.setRange(0, 2.1e3)
        self.vsrc_voltage_compliance.setDecimals(3)
        self.vsrc_voltage_compliance.setSuffix(" V")

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
        currentRampGroupBoxLayout.addWidget(self.current_start)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        currentRampGroupBoxLayout.addWidget(self.current_stop)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        currentRampGroupBoxLayout.addWidget(self.current_step)
        currentRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        currentRampGroupBoxLayout.addWidget(self.waiting_time)
        currentRampGroupBoxLayout.addStretch()

        vsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        vsrcGroupBox.setTitle("V Source")

        vsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(vsrcGroupBox)
        vsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        vsrcGroupBoxLayout.addWidget(self.vsrc_voltage_compliance)
        vsrcGroupBoxLayout.addWidget(self.vsrc_accept_compliance)
        vsrcGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(currentRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(vsrcGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        ampere = ureg("A")
        volt = ureg("V")

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

        self.xfitSeries.setVisible(False)

        for name, series in self.dataSeries.items():
            series.clear()
            points = measurement.series.get(name)
            if points is not None:
                tr = self.series_transform.get(name, self.series_transform_default)
                for x, y in points:
                    x, v = tr(x, y)
                    series.append(x, v)
                series.setVisible(True)

        self.updateReadings()

    def append_reading(self, name, x, y):
        if self.measurement:
            if name not in self.measurement.series:
                self.measurement.series[name] = []
            self.measurement.series[name].append((x, y))

            if name in self.plot.series:
                tr = self.series_transform.get(name, self.series_transform_default)
                self.plot.series.get(name).append(*tr(x, y))
                self.plot.series.get(name).qt.setVisible(True)

            series = self.dataSeries.get(name)
            if series is not None:
                tr = self.series_transform.get(name, self.series_transform_default)
                x, y = tr(x, y)
                series.append(x, y)
                series.setVisible(True)

    def updateReadings(self):
        super().updateReadings()
        if self.measurement:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.qt.chart().zoomOut() # HACK
                self.plot.fit()

        self.plotWidget.resizeAxes()

    def clearReadings(self):
        super().clearReadings()

        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []

        self.plot.series.get("xfit").qt.setVisible(False)
        for series in self.plot.series.values():
            series.clear()
        self.plot.fit()

        self.xfitSeries.setVisible(False)
        for series in self.dataSeries.values():
            series.clear()
