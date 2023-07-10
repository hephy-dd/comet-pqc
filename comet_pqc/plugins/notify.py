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

        self.webhookUrlLabel = QtWidgets.QLabel()
        self.webhookUrlLabel.setText("Slack Webhook URL")

        self.webhookUrlLineEdit = QtWidgets.QLineEdit()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.webhookUrlLabel)
        layout.addWidget(self.webhookUrlLineEdit)
        layout.addStretch(1)

    def reflection(self):  # TODO
        return self

    def load(self):
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.notify")
        slack_webhook_url = settings.value("slackWebhookUrl", "", str)
        settings.endGroup()
        self.webhookUrlLineEdit.setText(slack_webhook_url)

    def store(self):
        slack_webhook_url = self.webhookUrlLineEdit.text()
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.notify")
        settings.setValue("slackWebhookUrl", slack_webhook_url)
        settings.endGroup()


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
        settings.beginGroup("plugin.notify")
        slack_webhook_url = settings.value("slackWebhookUrl", "", str)
        settings.endGroup()
        if slack_webhook_url:
            send_slack_message(slack_webhook_url, message)
