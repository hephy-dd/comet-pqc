from .options import OptionsTab
from .table import TableTab
from .webapi import WebAPITab

import qutie as ui

from comet.settings import SettingsMixin
from comet.resource import ResourceMixin
from comet.utils import escape_string, unescape_string

__all__ = ["PreferencesDialog"]


class PreferencesDialog(ui.Dialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(640, 480)
        self.title = "Preferences"
        self.table_tab = TableTab()
        self.tab_widget = WebAPITab()
        self.options_tab = OptionsTab()
        self.tab_widget = ui.Tabs(
            self.table_tab,
            self.tab_widget,
            self.options_tab,
        )
        self.button_box = ui.DialogButtonBox(
            buttons=("apply", "cancel"),
            clicked=self.on_clicked
        )
        self.layout = ui.Column(
            self.tab_widget,
            self.button_box
        )

    def on_clicked(self, value):
        if value == "apply":
            self.on_apply()
        self.close()

    def on_apply(self):
        ui.show_info(text="Application restart required for changes to take effect.")
        for tab in self.tab_widget:
            tab.store()

    def run(self):
        for tab in self.tab_widget:
            tab.load()
        super().run()
