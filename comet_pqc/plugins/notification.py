import logging
import json
import urllib.request

from PyQt5 import QtCore, QtWidgets

__all__ = ["NotificationPlugin"]


class NotificationPlugin:

    def __init__(self, window):
        self.window = window

    def install(self):
        self.preferencesWidget = PreferencesWidget()
        self.window.preferencesDialog.tab_widget.qt.addTab(self.preferencesWidget, "Notifications")

    def uninstall(self):
        index = self.window.preferencesDialog.tab_widget.qt.indexOf(self.preferencesWidget)
        self.window.preferencesDialog.tab_widget.qt.removeTab(index)
        self.preferencesWidget.deleteLater()

    def on_notification(self, message: str) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.notify")
        slack_webhook_url = settings.value("slackWebhookUrl", "", str)
        settings.endGroup()
        if slack_webhook_url:
            send_slack_message(slack_webhook_url, message)


def send_slack_message(webhook_url: str, message: str) -> None:
    data = {
        "text": message
    }
    body = bytes(json.dumps(data), encoding="utf-8")

    req = urllib.request.Request(webhook_url, data=body, headers={"content-type": "application/json"})
    response = urllib.request.urlopen(req)

    logging.info(response.read().decode("utf8"))


class PreferencesWidget(QtWidgets.QWidget):

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
