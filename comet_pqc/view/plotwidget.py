from typing import Optional

import QCharted
from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["PlotWidget"]

AxesTypes = {
    "value": QCharted.ValueAxis,
    "log": QCharted.LogValueAxis,
    "datetime": QCharted.DateTimeAxis,
    "category": QCharted.CategoryAxis,
}

SeriesTypes = {
    "line": QCharted.LineSeries,
    "spline": QCharted.SplineSeries,
    "scatter": QCharted.ScatterSeries,
}

AlignTypes = {
    "top": QtCore.Qt.AlignTop,
    "bottom": QtCore.Qt.AlignBottom,
    "left": QtCore.Qt.AlignLeft,
    "right": QtCore.Qt.AlignRight
}


class Axis:
    """Axis wrapper class provided for convenience."""

    def __init__(self, axis):
        self.qt = axis

    @property
    def text(self):
        return self.qt.titleText()

    @text.setter
    def text(self, value):
        self.qt.setTitleText(value or "")

    @property
    def color(self):
        return self.qt.linePen().color().name()

    @color.setter
    def color(self, value):
        self.qt.setLinePen(QtGui.QColor(value))


class Series:
    """Series wrapper class provided for convenience."""

    def __init__(self, series):
        self.qt = series

    @property
    def text(self):
        return self.qt.name()

    @text.setter
    def text(self, value):
        self.qt.setName(value or "")

    @property
    def color(self):
        return self.qt.pen().color().name()

    @color.setter
    def color(self, value):
        self.qt.setPen(QtGui.QColor(value))

    def append(self, x, y):
        self.qt.data().append(x, y)

    def replace(self, points):
        self.qt.data().replace(points)

    def clear(self):
        self.qt.data().clear()


class  PlotWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.__axes: dict = {}
        self.__series: dict = {}
        self.chartView: QCharted.ChartView = QCharted.ChartView(self)
        self.chart: QCharted.Chart = self.chartView.chart()
        legend = self.chart.legend()
        legend.show()
        legend.setAlignment(QtCore.Qt.AlignRight)
        self.setFixedHeight(300)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.chartView)

    def fit(self):
        self.chart.fit()

    def update(self, axis):
        if isinstance(axis, str):
            axis = self.axes().get(axis)
        self.chart.updateAxis(axis.qt, axis.qt.min(), axis.qt.max())

    def isZoomed(self):
        return self.chart.isZoomed()

    def axes(self) -> dict:
        return self.__axes.copy()

    def addAxis(self, id, align, type="value", text=None, color=None, categories={}):
        axis = Axis(AxesTypes.get(type)())
        axis.text = text
        if color is not None:
            axis.color = color
        if isinstance(axis.qt, QCharted.CategoryAxis):
            axis.qt.setStartValue(0)
            for key, value in categories.items():
                axis.qt.append(value, key)
        align = AlignTypes.get(align)
        self.chart.addAxis(axis.qt, align)
        self.__axes[id] = axis

    def series(self) -> dict:
        return self.__series.copy()

    def addSeries(self, id, x, y, type="line", text=None, color=None):
        series = Series(SeriesTypes.get(type)())
        series.text = text
        if color is not None:
            series.color = color
        x_axis = self.__axes.get(x)
        y_axis = self.__axes.get(y)
        self.chart.addSeries(series.qt, x_axis.qt, y_axis.qt)
        self.__series[id] = series
        return series
