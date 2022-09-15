from PyQt5 import QtCore, QtGui, QtWidgets, QtChart


class PlotWidget(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.chart: QtChart.QChart = QtChart.QChart()
        self.chart.legend().setAlignment(QtCore.Qt.AlignRight)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.setBackgroundRoundness(0)

        self.chartView: QtChart.QChartView = QtChart.QChartView(self.chart, self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.chartView)
        layout.setContentsMargins(0, 0, 0, 0)

    def addValueAxis(self, title: str, alignment):
        axis = QtChart.QValueAxis()
        axis.setTitleText(title)
        self.chart.addAxis(axis, alignment)
        return axis

    def addLineSeries(self, name: str, color: str):
        series = QtChart.QLineSeries()
        series.setName(name)
        series.setColor(QtGui.QColor(color))
        self.chart.addSeries(series)
        return series

    def resizeAxes(self) -> None:
        xmin = None
        xmax = None
        ymin = None
        ymax = None

        for series in self.chart.series():
            if isinstance(series, QtChart.QLineSeries):
                for point in series.pointsVector():

                    if xmin is None:
                        xmin = point.x()
                    if xmax is None:
                        xmax = point.x()
                    xmin = min(xmin, point.x())
                    xmax = max(xmax, point.x())

                    if ymin is None:
                        ymin = point.y()
                    if ymax is None:
                        ymax = point.y()
                    ymin = min(ymin, point.y())
                    ymax = max(ymax, point.y())

        for axis in self.chart.axes(QtCore.Qt.Horizontal):
            if xmin is not None and xmax is not None:
                axis.setRange(xmin, xmax)
            break

        for axis in self.chart.axes(QtCore.Qt.Vertical):
            if ymin is not None and ymax is not None:
                axis.setRange(ymin, ymax)
                if isinstance(axis, QtChart.QValueAxis):
                    axis.applyNiceNumbers()
            break
