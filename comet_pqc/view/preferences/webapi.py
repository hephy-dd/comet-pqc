from comet import ui
from comet.ui.preferences import PreferencesTab

__all__ = ["WebAPITab"]


class WebAPITab(PreferencesTab):
    """Web API settings tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Webserver")
        self._enabled_checkbox = ui.CheckBox(
            text="Enable Server"
        )
        self._host_text = ui.Text()
        self._port_number = ui.Number(
            minimum=0,
            maximum=99999,
            step=1
        )
        self.layout = ui.Column(
            ui.GroupBox(
                title="JSON API",
                layout=ui.Column(
                    self._enabled_checkbox,
                    ui.Row(
                        ui.Column(
                            ui.Label("Host"),
                            ui.Label("Port"),
                        ),
                        ui.Column(
                            self._host_text,
                            self._port_number,
                        ),
                        ui.Spacer()
                    ),
                    ui.Spacer(),
                    stretch=(0, 0, 1)
                )
            ),
            ui.Spacer(),
            stretch=(0, 1)
        )

    @property
    def hostname(self):
        return self._host_text.value.strip()

    @property
    def port(self):
        return int(self._port_number.value)

    def load(self):
        enabled = self.settings.get("webapi_enabled") or False
        self._enabled_checkbox.checked = enabled
        host = self.settings.get("webapi_host") or "0.0.0.0"
        self._host_text.value = host
        port = int(self.settings.get("webapi_port") or 9000)
        self._port_number.value = port

    def store(self):
        enabled = self._enabled_checkbox.checked
        self.settings["webapi_enabled"] = enabled
        self.settings["webapi_host"] = self.hostname
        self.settings["webapi_port"] = self.port
