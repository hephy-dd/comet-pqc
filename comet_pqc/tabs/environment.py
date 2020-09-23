from comet import ui

__all__ = ['EnvironmentTab']

class EnvironmentTab(ui.Tab):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    def __init__(self):
        super().__init__(title="Environment")
        # Inputs
        self.box_temperature_number = ui.Number(suffix="°C", decimals=1, readonly=True)
        self.box_humidity_number = ui.Number(suffix="%rH", decimals=1, readonly=True)
        self.chuck_temperature_number = ui.Number(suffix="°C", decimals=1, readonly=True)
        self.box_lux_number = ui.Number(suffix="Lux", decimals=1, readonly=True)
        self.box_light_text = ui.Text(readonly=True)
        self.box_door_text = ui.Text(readonly=True)
        # Layout
        self.layout = ui.Column(
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

    def update_data(self, pc_data):
        self.box_temperature_number.value = pc_data.box_temperature
        self.box_humidity_number.value = pc_data.box_humidity
        self.chuck_temperature_number.value = pc_data.chuck_block_temperature
        self.box_lux_number.value = pc_data.box_lux
        self.box_light_text.value = self.LightStates.get(pc_data.box_light_state)
        self.box_door_text.value = self.DoorStates.get(pc_data.box_door_state)
