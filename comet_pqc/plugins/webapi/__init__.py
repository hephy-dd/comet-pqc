from comet_pqc.plugins import Plugin

from .preferences import WebAPIWidget
from .processes import WebAPIProcess

__all__ = ["WebAPIPlugin"]


class WebAPIPlugin(Plugin):

    def __init__(self, window):
        self.window = window
        self.window.processes.add("webapi", WebAPIProcess(
            failed=self.window.show_exception
        ))

    def install(self):
        self.webapi_widget = WebAPIWidget()
        self.window.preferences_dialog.tab_widget.qt.addTab(self.webapi_widget, "WebAPI")

    def uninstall(self):
        index = self.window.preferences_dialog.tab_widget.qt.indexOf(self.webapi_widget)
        self.window.preferences_dialog.tab_widget.qt.removeTab(index)
        self.webapi_widget.deleteLater()
