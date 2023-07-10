from comet import ui

__all__ = ["StatusWidget"]


class StatusWidget(ui.Tab):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    def __init__(self, reload=None):
        super().__init__(title="Status")
        self.reload = reload
        self.matrix_model_text = ui.Text(readonly=True)
        self.matrix_channels_text = ui.Text(readonly=True)
        self.hvsrc_model_text = ui.Text(readonly=True)
        self.vsrc_model_text = ui.Text(readonly=True)
        self.lcr_model_text = ui.Text(readonly=True)
        self.elm_model_text = ui.Text(readonly=True)
        self.table_model_text = ui.Text(readonly=True)
        self.table_state_text = ui.Text(readonly=True)
        self.env_model_text = ui.Text(readonly=True)
        self.reload_status_button = ui.Button("&Reload", clicked=self.on_reload)
        self.layout = ui.Column(
            ui.GroupBox(
                title="Matrix",
                layout=ui.Column(
                    ui.Row(
                        ui.Label("Model:"),
                        self.matrix_model_text,
                        stretch=(1, 7)
                    ),
                    ui.Row(
                        ui.Label("Closed channels:"),
                        self.matrix_channels_text,
                        stretch=(1, 7)
                    )
                )
            ),
            ui.GroupBox(
                title="HVSource",
                layout=ui.Row(
                    ui.Label("Model:"),
                    self.hvsrc_model_text,
                    stretch=(1, 7)
                )
            ),
            ui.GroupBox(
                title="VSource",
                layout=ui.Row(
                    ui.Label("Model:"),
                    self.vsrc_model_text,
                    stretch=(1, 7)
                )
            ),
            ui.GroupBox(
                title="LCRMeter",
                layout=ui.Row(
                    ui.Label("Model:"),
                    self.lcr_model_text,
                    stretch=(1, 7)
                )
            ),
            ui.GroupBox(
                title="Electrometer",
                layout=ui.Row(
                    ui.Label("Model:"),
                    self.elm_model_text,
                    stretch=(1, 7)
                )
            ),
            ui.GroupBox(
                title="Table",
                layout=ui.Column(
                    ui.Row(
                        ui.Label("Model:"),
                        self.table_model_text,
                        stretch=(1, 7)
                    ),
                    ui.Row(
                        ui.Label("State:"),
                        self.table_state_text,
                        stretch=(1, 7)
                    )
                )
            ),
            ui.GroupBox(
                title="Environment Box",
                layout=ui.Column(
                    ui.Row(
                        ui.Label("Model:"),
                        self.env_model_text,
                        stretch=(1, 7)
                    )
                )
            ),
            ui.Spacer(),
            self.reload_status_button
        )

    def reset(self):
        self.matrix_model_text.value = ""
        self.matrix_channels_text.value = ""
        self.hvsrc_model_text.value = ""
        self.vsrc_model_text.value = ""
        self.lcr_model_text.value = ""
        self.elm_model_text.value = ""
        self.table_model_text.value = ""
        self.table_state_text.value = ""
        self.env_model_text.value = ""

    def update_status(self, status):
        default = "n/a"
        self.matrix_model_text.value = status.get("matrix_model") or default
        self.matrix_channels_text.value = status.get("matrix_channels")
        self.hvsrc_model_text.value = status.get("hvsrc_model") or default
        self.vsrc_model_text.value = status.get("vsrc_model") or default
        self.lcr_model_text.value = status.get("lcr_model") or default
        self.elm_model_text.value = status.get("elm_model") or default
        self.table_model_text.value = status.get("table_model") or default
        self.table_state_text.value = status.get("table_state") or default
        self.env_model_text.value = status.get("env_model") or default

    def lock(self):
        self.reload_status_button.enabled = False

    def unlock(self):
        self.reload_status_button.enabled = True

    def on_reload(self):
        self.emit(self.reload)
