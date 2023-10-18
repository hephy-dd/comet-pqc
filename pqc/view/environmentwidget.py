import logging
import math
from typing import Optional

from PyQt5 import QtWidgets, QtChart

from .components import PlotWidget

__all__ = ["EnvironmentWidget"]

logger = logging.getLogger(__name__)


class EnvironmentWidget(QtWidgets.QWidget):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    SampleCount = 60 * 60 * 12

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Data series
        self.box_temperature_series: list = []
        self.chuck_temperature_series: list = []
        self.box_humidity_series: list = []

        # Plot
        self.plotWidget = PlotWidget()
        self.plotWidget.setMinimumHeight(320)
        self.plotWidget.addAxis("x", align="bottom", type="datetime")
        self.plotWidget.addAxis("y1", align="left", text="Temperature [°C]", color="red")
        self.plotWidget.addAxis("y2", align="right", text="Humidity [%rH]", color="blue")
        self.plotWidget.addSeries("box_temperature", "x", "y1", text="Box Temperature", color="red")
        self.plotWidget.addSeries("chuck_temperature", "x", "y1", text="Chuck Temperature", color="magenta")
        self.plotWidget.addSeries("box_humidity", "x", "y2", text="Box Humidity", color="blue")

        self.boxTemperatureLineEdit = QtWidgets.QLineEdit(self)
        self.boxTemperatureLineEdit.setReadOnly(True)

        self.boxHumidityLineEdit = QtWidgets.QLineEdit(self)
        self.boxHumidityLineEdit.setReadOnly(True)

        self.chuckTemperatureLineEdit = QtWidgets.QLineEdit(self)
        self.chuckTemperatureLineEdit.setReadOnly(True)

        self.boxLuxLineEdit = QtWidgets.QLineEdit(self)
        self.boxLuxLineEdit.setReadOnly(True)

        self.boxLightLineEdit = QtWidgets.QLineEdit(self)
        self.boxLightLineEdit.setReadOnly(True)

        self.boxDoorLineEdit = QtWidgets.QLineEdit(self)
        self.boxDoorLineEdit.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.plotWidget)
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
        layout.addStretch(1)

    def truncateData(self) -> None:
        self.box_temperature_series = self.box_temperature_series[-self.SampleCount:]
        self.chuck_temperature_series = self.chuck_temperature_series[-self.SampleCount:]
        self.box_humidity_series = self.box_humidity_series[-self.SampleCount:]

    def appendData(self, t, pc_data) -> None:
        # Prevent crashed due to invalid time stamps
        if math.isfinite(t):
            self.boxTemperatureLineEdit.setText(f"{pc_data.box_temperature:.1f} °C")
            self.boxHumidityLineEdit.setText(f"{pc_data.box_humidity:.1f} %rH")
            self.chuckTemperatureLineEdit.setText(f"{pc_data.chuck_block_temperature:.1f} °C")
            self.boxLuxLineEdit.setText(f"{pc_data.box_lux:.1f} Lux")
            self.boxLightLineEdit.setText(format(self.LightStates.get(pc_data.box_light_state)))
            self.boxDoorLineEdit.setText(format(self.DoorStates.get(pc_data.box_door_state)))
            self.box_temperature_series.append((t, pc_data.box_temperature))
            self.chuck_temperature_series.append((t, pc_data.chuck_temperature))
            self.box_humidity_series.append((t, pc_data.box_humidity))
            self.truncateData()
            self.updatePlot()

    def updatePlot(self) -> None:
        self.updateSeries("box_temperature", self.box_temperature_series)
        self.updateSeries("chuck_temperature", self.chuck_temperature_series)
        self.updateSeries("box_humidity", self.box_humidity_series)
        # Suppress invalid float crashes
        try:
            self.plotWidget.smartFit()
        except Exception as exc:
            logger.exception(exc)
            logger.error("failed to resize plot.")

    def updateSeries(self, key: str, points: list) -> None:
        series = self.plotWidget.series().get("box_temperature")
        if series:
            series.replace(points)
