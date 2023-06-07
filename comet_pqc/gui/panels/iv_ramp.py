from typing import Optional

from comet import ureg
from PyQt5 import QtCore, QtWidgets
from QCharted import Chart, ChartView

from .matrix import MatrixPanel
from .mixins import EnvironmentMixin, HVSourceMixin
from .panel import Metric

__all__ = ["IVRampPanel"]


class IVRampPanel(MatrixPanel, HVSourceMixin, EnvironmentMixin):
    """Panel for IV ramp measurements."""

    type_name = "iv_ramp"

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("IV Ramp")

        self.register_hvsource()
        self.register_environment()

        self.chart = Chart()
        self.chart.legend().setAlignment(QtCore.Qt.AlignRight)

        self.xAxis = self.chart.addValueAxis(QtCore.Qt.AlignBottom)
        self.xAxis.setTitleText("Voltage [V] (abs)")

        self.yAxis = self.chart.addValueAxis(QtCore.Qt.AlignRight)
        self.yAxis.setTitleText("Current [uA]")

        self.hvsrcSeries = self.chart.addLineSeries(self.xAxis, self.yAxis)
        self.hvsrcSeries.setName("HV Source")
        self.hvsrcSeries.setPen(QtCore.Qt.red)
        self.series["hvsrc"] = self.hvsrcSeries

        self.xfitSeries = self.chart.addLineSeries(self.xAxis, self.yAxis)
        self.xfitSeries.setName("Fit")
        self.xfitSeries.setPen(QtCore.Qt.magenta)
        self.series["xfit"] = self.xfitSeries

        self.chartView = ChartView(self)
        self.chartView.setChart(self.chart)
        self.chartView.setMaximumHeight(300)

        self.dataTabWidget.insertTab(0, self.chartView, "IV Curve")

        self.voltage_start: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_start.setRange(-2.1e3, +2.1e3)
        self.voltage_start.setDecimals(3)
        self.voltage_start.setSuffix(" V")

        self.voltage_stop: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_stop.setRange(-2.1e3, +2.1e3)
        self.voltage_stop.setDecimals(3)
        self.voltage_stop.setSuffix(" V")

        self.voltage_step: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.voltage_step.setRange(0, 200)
        self.voltage_step.setDecimals(3)
        self.voltage_step.setSuffix(" V")

        self.waiting_time: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.waiting_time.setRange(0, 60)
        self.waiting_time.setDecimals(2)
        self.waiting_time.setSuffix(" s")

        self.hvsrc_current_compliance: Metric = Metric("A", self)
        self.hvsrc_current_compliance.setPrefixes("mun")
        self.hvsrc_current_compliance.setDecimals(3)
        self.hvsrc_current_compliance.setRange(0, 2.1e3)

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
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_start)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Stop", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_stop)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Step", self))
        hvsrcRampGroupBoxLayout.addWidget(self.voltage_step)
        hvsrcRampGroupBoxLayout.addWidget(QtWidgets.QLabel("Waiting Time", self))
        hvsrcRampGroupBoxLayout.addWidget(self.waiting_time)
        hvsrcRampGroupBoxLayout.addStretch()

        hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(hvsrcGroupBox)
        hvsrcGroupBoxLayout.addWidget(QtWidgets.QLabel("Compliance", self))
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_current_compliance)
        hvsrcGroupBoxLayout.addWidget(self.hvsrc_accept_compliance)
        hvsrcGroupBoxLayout.addStretch()

        self.generalWidgetLayout.addWidget(hvsrcRampGroupBox, 1)
        self.generalWidgetLayout.addWidget(hvsrcGroupBox, 1)
        self.generalWidgetLayout.addStretch(1)

        ampere = ureg("A")
        volt = ureg("V")

        self.series_transform["hvsrc"] = lambda x, y: ((x * volt).to("V").m, (y * ampere).to("uA").m)
        self.series_transform["xfit"] = self.series_transform.get("hvsrc")

    def mount(self, measurement):
        super().mount(measurement)
        for name, points in measurement.series.items():
            series = self.series.get(name)
            if series is not None:
                series.data().clear()
                tr = self.series_transform.get(name, self.series_transform_default)
                for x, y in points:
                    series.data().append(*tr(x, y))
        self.updateReadings()

    def append_reading(self, name, x, y):
        if self.measurement:
            series = self.sereis.get(name)
            if series is not None:
                if name not in self.measurement.series:
                    self.measurement.series[name] = []
                self.measurement.series[name].append((x, y))
                tr = self.series_transform.get(name, self.series_transform_default)
                series.data().append(*tr(x, y))
                series.setVisible(True)

    def updateReadings(self):
        if self.measurement:
            if self.chart.isZoomed():
                self.chart.updateAxis(self.xAxis, self.xAxis.min(), self.xAxis.max())
            else:
                self.chart.fit()

    def clearReadings(self):
        super().clearReadings()
        self.xfitSeries.setVisible(False)
        for series in self.series.values():
            series.data().clear()
        if self.measurement:
            for name, points in self.measurement.series.items():
                self.measurement.series[name] = []
        self.chart.fit()
