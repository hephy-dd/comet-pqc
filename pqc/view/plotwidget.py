from typing import List, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets, QtChart

__all__ = [
    "IVPlotWidget",
    "VIPlotWidget",
    "CVPlotWidget",
    "CV2PlotWidget",
]


def auto_scale(minimum: float, maximum: float) -> Tuple[float, str]:
    """Return scale and unit for small ranges."""
    value = max(abs(minimum), abs(maximum))
    if value < 1e-12:
        scale = 1e15
        unit = "f"
    elif value < 1e-9:
        scale = 1e12
        unit = "p"
    elif value < 1e-6:
        scale = 1e9
        unit = "n"
    elif value < 1e-3:
        scale = 1e6
        unit = "u"
    elif value < 1:
        scale = 1e3
        unit = "m"
    else:
        scale = 1e0
        unit = ""
    return scale, unit


class ChartView(QtChart.QChartView):

    def __init__(self, chart, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(chart, parent)

        self.vLine = self.scene().addLine(0, 0, 0, 0)
        self.hLine = self.scene().addLine(0, 0, 0, 0)
        pen = QtGui.QPen(QtCore.Qt.DashLine)
        self.vLine.setPen(pen)
        self.hLine.setPen(pen)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        pos = event.pos()
        rect = self.chart().plotArea()

        if rect.contains(pos):
            self.vLine.setLine(QtCore.QLineF(pos.x(), rect.top(), pos.x(), rect.bottom()))
            self.hLine.setLine(QtCore.QLineF(rect.left(), pos.y(), rect.right(), pos.y()))
            self.vLine.show()
            self.hLine.show()
        else:
            self.vLine.hide()
            self.hLine.hide()


class PlotWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.chart = QtChart.QChart()
        self.chart.setBackgroundRoundness(0)
        self.chart.setMargins(QtCore.QMargins(8, 8, 8, 8))
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.legend().setAlignment(QtCore.Qt.AlignRight)

        self.chartView = ChartView(self.chart, self)
        self.chartView.setFixedHeight(300)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chartView)


class XYPlotWidget(PlotWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.xAxisUnit: str = ""
        self.yAxisUnit: str = ""

        self.xAxisDefaultRange: Tuple[float, float] = 0, 1
        self.yAxisDefaultRange: Tuple[float, float] = 0, 1

        self.dynamicXAxis = QtChart.QValueAxis()
        self.chart.addAxis(self.dynamicXAxis, QtCore.Qt.AlignBottom)

        self.dynamicYAxis = QtChart.QValueAxis()
        self.chart.addAxis(self.dynamicYAxis, QtCore.Qt.AlignRight)

        self.xAxis = QtChart.QValueAxis()
        self.xAxis.setVisible(False)
        self.xAxis.rangeChanged.connect(self.rescaleDynamicXAxis)
        self.chart.addAxis(self.xAxis, QtCore.Qt.AlignBottom)

        self.yAxis = QtChart.QValueAxis()
        self.yAxis.setVisible(False)
        self.yAxis.rangeChanged.connect(self.rescaleDynamicYAxis)
        self.chart.addAxis(self.yAxis, QtCore.Qt.AlignRight)

    def rescaleDynamicXAxis(self, minimum: float, maximum: float) -> None:
        scale, unit = auto_scale(minimum, maximum)
        self.dynamicXAxis.setLabelFormat(f"%.1f {unit}{self.xAxisUnit}")
        self.dynamicXAxis.setRange(minimum * scale, maximum * scale)

    def rescaleDynamicYAxis(self, minimum: float, maximum: float) -> None:
        scale, unit = auto_scale(minimum, maximum)
        self.dynamicYAxis.setLabelFormat(f"%.1f {unit}{self.yAxisUnit}")
        self.dynamicYAxis.setRange(minimum * scale, maximum * scale)

    def series(self) -> List[QtChart.QXYSeries]:
        return [
            series for series in self.chart.series()
            if isinstance(series, QtChart.QXYSeries)
        ]

    def addSeries(self, series: QtChart.QXYSeries) -> None:
        self.chart.addSeries(series)
        series.attachAxis(self.xAxis)
        series.attachAxis(self.yAxis)

    def clear(self) -> None:
        for series in self.series():
            series.clear()

    def resizeAxes(self) -> None:
        x = []
        y = []
        for series in self.series():
            for p in series.pointsVector():
                x.append(p.x())
                y.append(p.y())
        if x:
            a, b  = min(x), max(x)
            self.xAxis.setRange(a, b)
        else:
            a, b = self.xAxisDefaultRange
            self.xAxis.setRange(a, b)
        if y:
            a, b = min(y), max(y)
            with QtCore.QSignalBlocker(self.yAxis):
                self.yAxis.setRange(a, b)
            self.yAxis.applyNiceNumbers()
        else:
            a, b = self.yAxisDefaultRange
            self.yAxis.setRange(a, b)


class IVPlotWidget(XYPlotWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.chart.setTitle("IV Curve")

        self.xAxisUnit = "V"
        self.dynamicXAxis.setTitleText(f"Voltage [{self.xAxisUnit}]")

        self.yAxisUnit = "A"
        self.dynamicYAxis.setTitleText(f"Current [{self.yAxisUnit}]")


class VIPlotWidget(XYPlotWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.chart.setTitle("VI Curve")

        self.xAxisUnit = "A"
        self.xAxisDefaultRange = 0, 1e-2
        self.dynamicXAxis.setTitleText(f"Current [{self.xAxisUnit}]")

        self.yAxisUnit = "V"
        self.yAxisDefaultRange = 0, 1e0
        self.dynamicYAxis.setTitleText(f"Voltage [{self.yAxisUnit}]")

        self.resizeAxes()


class CVPlotWidget(XYPlotWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.chart.setTitle("CV Curve")

        self.xAxisUnit = "V"
        self.dynamicXAxis.setTitleText(f"Voltage [{self.xAxisUnit}]")

        self.yAxisUnit = "F"
        self.dynamicYAxis.setTitleText(f"Capacity [{self.yAxisUnit}]")


class CV2PlotWidget(XYPlotWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.chart.setTitle("1/CV^2 Curve")

        self.xAxisUnit = "V"
        self.dynamicXAxis.setTitleText(f"Voltage [{self.xAxisUnit}]")

        self.yAxisUnit = "1/F^2"
        self.dynamicYAxis.setTitleText(f"Capacity [{self.yAxisUnit}]")
