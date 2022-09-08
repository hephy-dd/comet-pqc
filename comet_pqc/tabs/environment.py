import logging
import math
from typing import List

from PyQt5 import QtWidgets
from comet import ui

__all__ = ["EnvironmentWidget"]

logger = logging.getLogger(__name__)


class EnvironmentWidget(QtWidgets.QWidget):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    SampleCount = 60 * 60 * 12

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        # Data series
        self.box_temperature_series: List = []
        self.chuck_temperature_series: List = []
        self.box_humidity_series: List = []

        # Plot
        self.plot = ui.Plot(legend="right")
        self.plot.add_axis("x", align="bottom", type="datetime")
        self.plot.add_axis("y1", align="left", text="Temperature [°C]", color="red")
        self.plot.add_axis("y2", align="right", text="Humidity [%rH]", color="blue")
        self.plot.add_series("box_temperature", "x", "y1", text="Box Temperature", color="red")
        self.plot.add_series("chuck_temperature", "x", "y1", text="Chuck Temperature", color="magenta")
        self.plot.add_series("box_humidity", "x", "y2", text="Box Humidity", color="blue")

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
        layout.addWidget(self.plot.qt)
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
        self.plot.series.get("box_temperature").replace(self.box_temperature_series)
        self.plot.series.get("chuck_temperature").replace(self.chuck_temperature_series)
        self.plot.series.get("box_humidity").replace(self.box_humidity_series)
        # Suppress invalid float crashes
        try:
            if self.plot.zoomed:
                self.plot.update("x")
            else:
                self.plot.fit()
        except Exception as exc:
            logger.error("failed to resize plot.")
            logger.exception(exc)
