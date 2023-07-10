from comet_pqc.plugins import Plugin

from .widgets import StatusWidget
from .process import StatusProcess

__all__ = ["StatusPlugin"]


class StatusPlugin(Plugin):

    def __init__(self, window):
        self.window = window
        self.status_process = StatusProcess(
            failed=self.window.show_exception,
            message=self.window.show_message,
            progress=self.window.show_progress,
        )
        self.status_process.finished = self.on_status_finished
        self.window.processes.add("status", self.status_process)

    def install(self):
        self.status_widget = StatusWidget(reload=self.on_status_start)
        self.window.dashboard.tab_widget.qt.addTab(self.status_widget.qt, "Status")

    def uninstall(self):
        index = self.window.dashboard.tab_widget.qt.indexOf(self.status_widget.qt)
        self.window.dashboard.tab_widget.qt.removeTab(index)
        self.status_widget.qt.deleteLater()

    def handle_lock_controls(self, enabled):
        if enabled:
            self.status_widget.lock()
        else:
            self.status_widget.unlock()

    def on_status_start(self):
        self.window.dashboard.lock_controls()
        self.status_widget.reset()
        self.status_process.set("use_environ", self.window.dashboard.use_environment())
        self.status_process.set("use_table", self.window.dashboard.use_table())
        self.status_process.start()
        # Fix: stay in status tab
        self.window.dashboard.tab_widget.qt.setCurrentWidget(self.status_widget.qt)

    def on_status_finished(self):
        self.window.dashboard.unlock_controls()
        self.status_widget.update_status(self.status_process)
