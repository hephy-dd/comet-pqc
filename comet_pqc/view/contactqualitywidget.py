from typing import Optional, Tuple

from PyQt5 import QtCore, QtChart, QtGui, QtWidgets

__all__ = ["ContactQualityWidget"]


class ContactQualityWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMaximumPoints(1000)

        chart = QtChart.QChart()
        chart.legend().hide()
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundVisible(False)
        chart.setMargins(QtCore.QMargins(0, 0, 0, 0))

        self.xAxis = QtChart.QValueAxis()
        self.xAxis.setTickCount(3)
        self.xAxis.setMinorTickCount(4)
        self.xAxis.setLabelFormat("%.3f mm")
        chart.addAxis(self.xAxis, QtCore.Qt.AlignBottom)

        self.yAxis = QtChart.QValueAxis()
        self.yAxis.setTickCount(2)
        self.yAxis.setMinorTickCount(3)
        self.yAxis.setLabelFormat("%.2g Ohm")
        chart.addAxis(self.yAxis, QtCore.Qt.AlignLeft)

        self.lineSeries = QtChart.QLineSeries()
        self.lineSeries.setColor(QtGui.QColor("magenta"))

        chart.addSeries(self.lineSeries)
        self.lineSeries.attachAxis(self.xAxis)
        self.lineSeries.attachAxis(self.yAxis)

        self.readingsSeries = QtChart.QScatterSeries()
        self.readingsSeries.setName("R")
        self.readingsSeries.setMarkerSize(3)
        self.readingsSeries.setBorderColor(QtGui.QColor("red"))
        self.readingsSeries.setColor(QtGui.QColor("red"))

        chart.addSeries(self.readingsSeries)
        self.readingsSeries.attachAxis(self.xAxis)
        self.readingsSeries.attachAxis(self.yAxis)

        self.markerSeries = QtChart.QScatterSeries()
        self.markerSeries.setMarkerSize(9)
        self.markerSeries.setBorderColor(QtGui.QColor("red"))
        self.markerSeries.setColor(QtGui.QColor("red"))

        chart.addSeries(self.markerSeries)
        self.markerSeries.attachAxis(self.xAxis)
        self.markerSeries.attachAxis(self.yAxis)

        self.setMinimumSize(160, 60)

        self.chartView = QtChart.QChartView(chart, self)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chartView)

    def maximumPoints(self) -> int:
        return self.property("maximumPoints") or 0

    def setMaximumPoints(self, count: int) -> None:
        self.setProperty("maximumPoints", count)

    def yLimits(self) -> Tuple[float, float]:
        values = [point.y() for point in self.readingsSeries.pointsVector()]
        if not values:
            return 0., 1.
        return min(values), max(values)

    def clear(self) -> None:
        self.readingsSeries.clear()

    def truncate(self) -> None:
        while self.readingsSeries.count() > self.maximumPoints():
            self.readingsSeries.remove(0)

    def append(self, x: float, y: float) -> None:
        self.truncate()
        self.readingsSeries.append(QtCore.QPointF(x, y))
        self.setMarker(x, y)

    def setLimits(self, x: float) -> None:
        self.xAxis.setRange(x - 0.050, x + 0.050)
        limits = self.yLimits()
        if limits:
            self.yAxis.setRange(min(limits), max(limits))
            self.yAxis.applyNiceNumbers()
            self.yAxis.setTickCount(2)

    def setLine(self, x: float) -> None:
        """Draw vertical line."""
        self.lineSeries.clear()
        self.lineSeries.append(x, self.yAxis.min())
        self.lineSeries.append(x, self.yAxis.max())

    def setMarker(self, x: float, y: float) -> None:
        """Draw marker symbol."""
        self.markerSeries.clear()
        self.markerSeries.append(x, y)
