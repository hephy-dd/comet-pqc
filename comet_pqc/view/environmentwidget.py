import logging
import math
from typing import Dict, List, Optional, Tuple

import QCharted
from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["EnvironmentWidget"]

logger = logging.getLogger(__name__)

SeriesType = List[Tuple[float, float]]


class EnvironmentWidget(QtWidgets.QWidget):

    LightStates: Dict[Optional[bool], str] = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates: Dict[Optional[bool], str] = {True: "OPEN", False: "CLOSED", None: "n/a"}

    SampleCount: int = 60 * 60 * 24

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Data series
        self.box_temperature_series: SeriesType = []
        self.chuck_temperature_series: SeriesType = []
        self.box_humidity_series: SeriesType = []

        #  PlotWidget

        self.chart: QCharted.Chart = QCharted.Chart()
        self.chart.legend().setAlignment(QtCore.Qt.AlignRight)

        self.chartView: QCharted.ChartView = QCharted.ChartView(self)
        self.chartView.setChart(self.chart)

        x = self.chart.addDateTimeAxis(QtCore.Qt.AlignBottom)
        x.setTitleText("Time")
        self.xAxis = x

        y1 = self.chart.addValueAxis(QtCore.Qt.AlignLeft)
        y1.setTitleText("Temperature [°C]")
        y1.setLinePen(QtGui.QColor("red"))

        y2 = self.chart.addValueAxis(QtCore.Qt.AlignRight)
        y2.setTitleText("Humidity [%rel]")
        y2.setLinePen(QtGui.QColor("blue"))

        self.boxTemperatureLineSeries = self.chart.addLineSeries(x, y1)
        self.boxTemperatureLineSeries.setName("Box Temperature")
        self.boxTemperatureLineSeries.setPen(QtGui.QColor("red"))

        self.chuckTemperatureLineSeries = self.chart.addLineSeries(x, y1)
        self.chuckTemperatureLineSeries.setName("Chuck Temperature")
        self.chuckTemperatureLineSeries.setPen(QtGui.QColor("magenta"))

        self.boxHumidityLineSeries = self.chart.addLineSeries(x, y2)
        self.boxHumidityLineSeries.setName("Box Humidity")
        self.boxHumidityLineSeries.setPen(QtGui.QColor("blue"))

        self.boxTemperatureLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.boxTemperatureLineEdit.setReadOnly(True)

        self.boxHumidityLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.boxHumidityLineEdit.setReadOnly(True)

        self.chuckTemperatureLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.chuckTemperatureLineEdit.setReadOnly(True)

        self.boxLuxLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.boxLuxLineEdit.setReadOnly(True)

        self.boxLightLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.boxLightLineEdit.setReadOnly(True)

        self.boxDoorLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.boxDoorLineEdit.setReadOnly(True)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.chartView)
        layout.addWidget(QtWidgets.QLabel("Box Temperature"))
        layout.addWidget(self.boxTemperatureLineEdit)
        layout.addWidget(QtWidgets.QLabel("Box Humidity"))
        layout.addWidget(self.boxHumidityLineEdit)
        layout.addWidget(QtWidgets.QLabel("Chuck Temperature"))
        layout.addWidget(self.chuckTemperatureLineEdit)
        layout.addWidget(QtWidgets.QLabel("Box Light"))
        layout.addWidget(self.boxLuxLineEdit)
        layout.addWidget(QtWidgets.QLabel("Box Light State"))
        layout.addWidget(self.boxLightLineEdit)
        layout.addWidget(QtWidgets.QLabel("Box Door State"))
        layout.addWidget(self.boxDoorLineEdit)
        layout.addStretch()

    def truncateData(self) -> None:
        self.box_temperature_series = self.box_temperature_series[-self.SampleCount:]
        self.chuck_temperature_series = self.chuck_temperature_series[-self.SampleCount:]
        self.box_humidity_series = self.box_humidity_series[-self.SampleCount:]

    def appendData(self, t: float, pc_data) -> None:
        self.boxTemperatureLineEdit.setText("{:.1f} °C".format(pc_data.box_temperature))
        self.boxHumidityLineEdit.setText("{:.1f} %relH".format(pc_data.box_humidity))
        self.chuckTemperatureLineEdit.setText("{:.1f} °C".format(pc_data.chuck_temperature))
        self.boxLuxLineEdit.setText("{:.1f} Lux".format(pc_data.box_lux))
        self.boxLightLineEdit.setText(format(self.LightStates.get(pc_data.box_light_state)))
        self.boxDoorLineEdit.setText(format(self.DoorStates.get(pc_data.box_door_state)))
        # Prevent crashed due to invalid time stamps
        if math.isfinite(t):
            self.box_temperature_series.append((t, pc_data.box_temperature))
            self.chuck_temperature_series.append((t, pc_data.chuck_temperature))
            self.box_humidity_series.append((t, pc_data.box_humidity))
        self.truncateData()
        self.updatePlot()

    def updatePlot(self) -> None:
        self.boxTemperatureLineSeries.data().replace(self.box_temperature_series)
        self.chuckTemperatureLineSeries.data().replace(self.chuck_temperature_series)
        self.boxHumidityLineSeries.data().replace(self.box_humidity_series)
        # Suppress invalid float crashes
        try:
            if self.chart.isZoomed():
                self.chart.updateAxis(self.xAxis, self.xAxis.min(), self.xAxis.max())
            else:
                self.chart.fit()
        except Exception as exc:
            logger.error("failed to resize plot")
            logger.exception(exc)
