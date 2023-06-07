import logging
import math
from typing import List, Optional

from PyQt5 import QtCore, QtWidgets
from QCharted import Chart, ChartView

__all__ = ["EnvironmentWidget"]

logger = logging.getLogger(__name__)


class EnvironmentWidget(QtWidgets.QWidget):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    SampleCount = 60 * 60 * 12

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Data series
        self.box_temperature_series: List = []
        self.chuck_temperature_series: List = []
        self.box_humidity_series: List = []

        # Plot
        self.chart = Chart()
        self.chart.legend().setAlignment(QtCore.Qt.AlignRight)

        self.xAxis = self.chart.addDateTimeAxis(QtCore.Qt.AlignBottom)
        self.xAxis.setTitleText("Time")

        self.y1Axis = self.chart.addValueAxis(QtCore.Qt.AlignLeft)
        self.y1Axis.setTitleText("Temperature [°C]")
        self.y1Axis.setLinePen(QtCore.Qt.red)

        self.y2Axis = self.chart.addValueAxis(QtCore.Qt.AlignRight)
        self.y2Axis.setTitleText("Humidity [%rH]")
        self.y2Axis.setLinePen(QtCore.Qt.blue)

        self.boxTemperatureSeries = self.chart.addLineSeries(self.xAxis, self.y1Axis)
        self.boxTemperatureSeries.setName("Box Temperature")
        self.boxTemperatureSeries.setPen(QtCore.Qt.red)

        self.chucktemperatureSeries = self.chart.addLineSeries(self.xAxis, self.y1Axis)
        self.chucktemperatureSeries.setName("Chuck Temperature")
        self.chucktemperatureSeries.setPen(QtCore.Qt.magenta)

        self.boxHumiditySeries = self.chart.addLineSeries(self.xAxis, self.y2Axis)
        self.boxHumiditySeries.setName("Box Humidity")
        self.boxHumiditySeries.setPen(QtCore.Qt.blue)

        self.chartView = ChartView(self)
        self.chartView.setChart(self.chart)

        # Inputs
        self.boxTemperatureSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.boxTemperatureSpinBox.setSuffix(" °C")
        self.boxTemperatureSpinBox.setDecimals(1)
        self.boxTemperatureSpinBox.setReadOnly(True)
        self.boxTemperatureSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        self.boxHumiditySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.boxHumiditySpinBox.setSuffix(" %rH")
        self.boxHumiditySpinBox.setDecimals(1)
        self.boxHumiditySpinBox.setReadOnly(True)
        self.boxHumiditySpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        self.chuckTemperatureSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.chuckTemperatureSpinBox.setSuffix(" °C")
        self.chuckTemperatureSpinBox.setDecimals(1)
        self.chuckTemperatureSpinBox.setReadOnly(True)
        self.chuckTemperatureSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        self.boxLuxSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.boxLuxSpinBox.setSuffix(" Lux")
        self.boxLuxSpinBox.setDecimals(1)
        self.boxLuxSpinBox.setReadOnly(True)
        self.boxLuxSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        self.boxLightLineEdit = QtWidgets.QLineEdit(self)
        self.boxLightLineEdit.setReadOnly(True)

        self.boxDoorLineEdit = QtWidgets.QLineEdit(self)
        self.boxDoorLineEdit.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.chartView)
        layout.addWidget(QtWidgets.QLabel("Box Temperature"))
        layout.addWidget(self.boxTemperatureSpinBox)
        layout.addWidget(QtWidgets.QLabel("Box Humidity"))
        layout.addWidget(self.boxHumiditySpinBox)
        layout.addWidget(QtWidgets.QLabel("Chuck Temperature"))
        layout.addWidget(self.chuckTemperatureSpinBox)
        layout.addWidget(QtWidgets.QLabel("Box Light"))
        layout.addWidget(self.boxLuxSpinBox)
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
        # Prevent crashed due to invalid time stamps
        if math.isfinite(t):
            self.boxTemperatureSpinBox.setValue(pc_data.box_temperature)
            self.boxHumiditySpinBox.setValue(pc_data.box_humidity)
            self.chuckTemperatureSpinBox.setValue(pc_data.chuck_block_temperature)
            self.boxLuxSpinBox.setValue(pc_data.box_lux)
            self.boxLightLineEdit.setText(self.LightStates.get(pc_data.box_light_state))
            self.boxDoorLineEdit.setText(self.DoorStates.get(pc_data.box_door_state))
            self.box_temperature_series.append((t, pc_data.box_temperature))
            self.chuck_temperature_series.append((t, pc_data.chuck_temperature))
            self.box_humidity_series.append((t, pc_data.box_humidity))
            self.truncateData()
            self.updatePlot()

    def updatePlot(self) -> None:
        self.boxTemperatureSeries.data().replace(self.box_temperature_series)
        self.chucktemperatureSeries.data().replace(self.chuck_temperature_series)
        self.boxHumiditySeries.data().replace(self.box_humidity_series)
        # Suppress invalid float crashes
        try:
            if self.chart.isZoomed():
                self.chart.updateAxis(self.xAxis, self.xAxis.min(), self.xAxis.max())
            else:
                self.chart.fit()
        except Exception as exc:
            logger.error("failed to resize plot.")
            logger.exception(exc)
