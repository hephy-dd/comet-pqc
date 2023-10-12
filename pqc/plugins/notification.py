import logging
import json
import urllib.request
from typing import Optional

from PyQt5 import QtCore, QtWidgets

__all__ = ["NotificationPlugin"]


class NotificationPlugin:

    def __init__(self, window) -> None:
        self.window = window

    def on_install(self) -> None:
        self.preferencesWidget = PreferencesWidget()
        self.window.preferencesDialog.tabWidget.addTab(self.preferencesWidget, "Notifications")

    def on_uninstall(self) -> None:
        index = self.window.preferencesDialog.tabWidget.indexOf(self.preferencesWidget)
        self.window.preferencesDialog.tabWidget.removeTab(index)
        self.preferencesWidget.deleteLater()

    def on_sequence_finished(self, data: dict) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.notification")
        slackEnabled = settings.value("slackEnabled", False, bool)
        slackWebhookUrl = settings.value("slackWebhookUrl", "", str).strip()
        finishedMessage = settings.value("finishedMessage", "", str).strip()
        settings.endGroup()
        if slackEnabled and slackWebhookUrl and finishedMessage:
            send_slack_message(slackWebhookUrl, finishedMessage)


def send_slack_message(webhook_url: str, message: str) -> None:
    data = {
        "text": message
    }
    body = bytes(json.dumps(data), encoding="utf-8")

    req = urllib.request.Request(webhook_url, data=body, headers={"content-type": "application/json"})
    response = urllib.request.urlopen(req)

    logging.info(response.read().decode("utf8"))


class PreferencesWidget(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.webhookUrlLabel = QtWidgets.QLabel(self)
        self.webhookUrlLabel.setText("Webhook URL")

        self.webhookUrlLineEdit = QtWidgets.QLineEdit(self)

        self.webhookNoticeLabel = QtWidgets.QLabel(self)
        self.webhookNoticeLabel.setOpenExternalLinks(True)
        self.webhookNoticeLabel.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.webhookNoticeLabel.setTextFormat(QtCore.Qt.MarkdownText)
        self.webhookNoticeLabel.setText("See also https://api.slack.com/messaging/webhooks")

        self.slackGroupBox = QtWidgets.QGroupBox(self)
        self.slackGroupBox.setTitle("Slack")
        self.slackGroupBox.setCheckable(True)

        slackLayout = QtWidgets.QVBoxLayout(self.slackGroupBox)
        slackLayout.addWidget(self.webhookUrlLabel)
        slackLayout.addWidget(self.webhookUrlLineEdit)
        slackLayout.addWidget(self.webhookNoticeLabel)

        self.finishedMessageLabel = QtWidgets.QLabel(self)
        self.finishedMessageLabel.setText("Sequence finished")

        self.finishedMessageLineEdit = QtWidgets.QLineEdit(self)

        self.messagesGroupBox = QtWidgets.QGroupBox(self)
        self.messagesGroupBox.setTitle("Messages")

        messagesLayout = QtWidgets.QVBoxLayout(self.messagesGroupBox)
        messagesLayout.addWidget(self.finishedMessageLabel)
        messagesLayout.addWidget(self.finishedMessageLineEdit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.slackGroupBox)
        layout.addWidget(self.messagesGroupBox)
        layout.addStretch(1)

    def isSlackEnabled(self) -> bool:
        return self.slackGroupBox.isChecked()

    def setSlackEnabled(self, state: bool) -> None:
        self.slackGroupBox.setChecked(state)

    def slackWebhookUrl(self) -> str:
        return self.webhookUrlLineEdit.text()

    def setSlackWebhookUrl(self, url: str) -> None:
        self.webhookUrlLineEdit.setText(url)

    def finishedMessage(self) -> str:
        return self.finishedMessageLineEdit.text()

    def setFinishedMessage(self, message: str) -> None:
        return self.finishedMessageLineEdit.setText(message)

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.notification")
        self.setSlackEnabled(settings.value("slackEnabled", False, bool))
        self.setSlackWebhookUrl(settings.value("slackWebhookUrl", "", str))
        self.setFinishedMessage(settings.value("finishedMessage", "PQC sequence finished!", str))
        settings.endGroup()

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.notification")
        settings.setValue("slackEnabled", self.isSlackEnabled())
        settings.setValue("slackWebhookUrl", self.slackWebhookUrl())
        settings.setValue("finishedMessage", self.finishedMessage())
        settings.endGroup()
