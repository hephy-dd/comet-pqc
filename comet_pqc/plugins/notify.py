import logging
import json
import urllib.request

from PyQt5 import QtCore, QtWidgets

from . import Plugin

__all__ = ["NotiftPlugin"]


def send_slack_message(webhook_url: str, message: str) -> None:
    data = {
        "text": message
    }
    body = bytes(json.dumps(data), encoding="utf-8")

    req = urllib.request.Request(webhook_url, data=body, headers={"content-type": "application/json"})
    response = urllib.request.urlopen(req)

    logging.info(response.read().decode("utf8"))


class NotifyWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)


class NotifyPlugin(Plugin):

    def __init__(self, window):
        self.window = window

    def install(self):
        self.notify_widget = NotifyWidget()
        self.window.preferences_dialog.tab_widget.qt.addTab(self.notify_widget, "Notifications")

    def uninstall(self):
        index = self.window.preferences_dialog.tab_widget.qt.indexOf(self.notify_widget)
        self.window.preferences_dialog.tab_widget.qt.removeTab(index)
        self.notify_widget.deleteLater()

    def handle_notification(self, message: str) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugins.notify")
        webhook_url = settings.value("webhook_url", "", str)
        settings.endGroup()
        if webhook_url:
            send_slack_message(webhook_url, message)
