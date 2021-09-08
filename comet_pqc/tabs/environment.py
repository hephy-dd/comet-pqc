import math
import logging

from comet import ui

__all__ = ['EnvironmentTab']

logger = logging.getLogger(__name__)

class EnvironmentTab(ui.Tab):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    SampleCount = 60 * 60 * 12

    def __init__(self):
        super().__init__(title="Environment")

        # Data series
        self.box_temperature_series = []
        self.chuck_temperature_series = []
        self.box_humidity_series = []

        # Plot
        self.plot = ui.Plot(legend="right")
        self.plot.add_axis("x", align="bottom", type="datetime")
        self.plot.add_axis("y1", align="left", text="Temperature [°C]", color="red")
        self.plot.add_axis("y2", align="right", text="Humidity [%rH]", color="blue")
        self.plot.add_series("box_temperature", "x", "y1", text="Box Temperature", color="red")
        self.plot.add_series("chuck_temperature", "x", "y1", text="Chuck Temperature", color="magenta")
        self.plot.add_series("box_humidity", "x", "y2", text="Box Humidity", color="blue")

        # Inputs
        self.box_temperature_number = ui.Number(suffix="°C", decimals=1, readonly=True)
        self.box_humidity_number = ui.Number(suffix="%rH", decimals=1, readonly=True)
        self.chuck_temperature_number = ui.Number(suffix="°C", decimals=1, readonly=True)
        self.box_lux_number = ui.Number(suffix="Lux", decimals=1, readonly=True)
        self.box_light_text = ui.Text(readonly=True)
        self.box_door_text = ui.Text(readonly=True)

        # Layout
        self.layout = ui.Column(
            self.plot,
            ui.Label("Box Temperature"),
            self.box_temperature_number,
            ui.Label("Box Humidity"),
            self.box_humidity_number,
            ui.Label("Chuck Temperature"),
            self.chuck_temperature_number,
            ui.Label("Box Light"),
            self.box_lux_number,
            ui.Label("Box Light State"),
            self.box_light_text,
            ui.Label("Box Door State"),
            self.box_door_text,
            ui.Spacer()
        )

    def truncate_data(self):
        self.box_temperature_series = self.box_temperature_series[-self.SampleCount:]
        self.chuck_temperature_series = self.chuck_temperature_series[-self.SampleCount:]
        self.box_humidity_series = self.box_humidity_series[-self.SampleCount:]

    def append_data(self, t, pc_data):
        # Prevent crashed due to invalid time stamps
        if math.isfinite(t):
            self.box_temperature_number.value = pc_data.box_temperature
            self.box_humidity_number.value = pc_data.box_humidity
            self.chuck_temperature_number.value = pc_data.chuck_block_temperature
            self.box_lux_number.value = pc_data.box_lux
            self.box_light_text.value = self.LightStates.get(pc_data.box_light_state)
            self.box_door_text.value = self.DoorStates.get(pc_data.box_door_state)
            self.box_temperature_series.append((t, pc_data.box_temperature))
            self.chuck_temperature_series.append((t, pc_data.chuck_temperature))
            self.box_humidity_series.append((t, pc_data.box_humidity))
            self.truncate_data()
            self.update_plot()

    def update_plot(self):
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
