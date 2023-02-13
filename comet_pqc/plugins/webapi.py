import json
import logging

import analysis_pqc
import bottle
import comet
from PyQt5 import QtWidgets
from waitress.server import TcpWSGIServer

from .. import __version__
from ..settings import settings
from . import Plugin

__all__ = ["WebAPIPlugin"]

logger = logging.getLogger(__name__)


def metric(value, unit):
    """Return metric dictionary."""
    if value is None:
        return None
    return {"value": value, "unit": unit}


class WebAPIPlugin(Plugin):

    def install(self, window):
        self.window = window

        self.process = WebAPIProcess(self.window.context)
        self.process.start()

        # self.preferencesAction = QtWidgets.QAction()
        # self.preferencesAction.setText("WebAPI...")
        # self.preferencesAction.triggered.connect(self.showPreferences)

        # self.window.editMenu.addAction(self.preferencesAction)

    def uninstall(self, window):
        self.process.stop()
        # self.window.editMenu.removeAction(self.preferencesAction)
        del self.window

    # def showPreferences(self):
    #     dialog = WebAPIDialog(self.window)
    #     dialog.readSettings()
    #     dialog.exec()
    #     if dialog.result() == WebAPIDialog.Accepted:
    #         dialog.writeSettings()
    #         QtWidgets.QMessageBox.information(self.window, "Restart Required", "Application restart required for changes to take effect.")



class WSGIServer(TcpWSGIServer):

    def run(self):
        self.asyncore.loop(.5, map=self._map)

    def shutdown(self):
        """Shutdown the server, see https://github.com/Pylons/webtest/blob/cf4ccaa0fcd0d73b690855abb379d96d9555d0d5/webtest/http.py#L92"""
        # avoid showing traceback related to asyncore
        self.logger.setLevel(logging.FATAL)
        while self._map:
            triggers = list(self._map.values())
            for trigger in triggers:
                trigger.handle_close()
        self.maintenance(0)
        self.task_dispatcher.shutdown()
        return True


class JSONErrorBottle(bottle.Bottle):
    """Custom bollte application with default JSON error handling."""

    def default_error_handler(self, res):
        bottle.response.content_type = "application/json"
        return json.dumps({"error": res.body, "status_code": res.status_code})


class WebAPIProcess(comet.Process):

    def __init__(self, context) -> None:
        super().__init__()
        self.host: str = "localhost"
        self.port: int = 9000
        self.enabled: bool = False
        self.server = None
        self.context = context

    def stop(self):
        super().stop()
        server = self.server
        if server:
            server.shutdown()

    def run(self):
        self.enabled = settings.value("webapi_enabled", False, bool)
        self.host = settings.value("webapi_host", "localhost", str)
        self.port = settings.value("webapi_port", 9000, int)

        if not self.enabled:
            return

        logger.info("start serving webapi... %s:%s", self.host, self.port)

        app = JSONErrorBottle()

        # Fix Cross-Origin Request Blocked error on client side
        def apply_cors():
            bottle.response.headers["Access-Control-Allow-Origin"] = "*"
        app.add_hook("after_request", apply_cors)

        @app.route("/")
        def index():
            return {
                "pqc_version": __version__,
                "comet_version": comet.__version__,
                "analyze_pqc_version": analysis_pqc.__version__,
            }

        @app.route("/table")
        def table():
            enabled = self._table_enabled()
            position = self._table_position()
            contact_quality = self._contact_quality()
            return {
                "table": {
                    "enabled": enabled,
                    "position": position,
                    "contact_quality": contact_quality
                }
            }

        self.server = WSGIServer(app, host=self.host, port=self.port)
        while self.running:
            self.server.run()
        self.server = None
        logger.info("stopped serving webapi")

    def _table_enabled(self):
        return self.context.table_enabled()

    def _table_position(self):
        x, y, z = self.context.table_process.get_position()
        return {
            "x": metric(x, "mm"),
            "y": metric(y, "mm"),
            "z": metric(z, "mm")
        }

    def _contact_quality(self):
        cp, rp = None, None
        contact_quality_process = self.context.processes.get("contact_quality")
        if contact_quality_process and contact_quality_process.running:
            cp, rp = contact_quality_process.cached_reading()
        return {
            "cp": metric(cp, "F"),
            "rp": metric(rp, "Ohm")
        }


class WebAPIDialog(QtWidgets.QDialog):
    """Web API preferences dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("WebAPI")

        self.enabledCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.enabledCheckBox.setText("Enable Server")

        self.hostLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.portSpinBox: QtWidgets.QSpinBox = QtWidgets.QSpinBox(self)
        self.portSpinBox.setRange(0, 99999)
        self.portSpinBox.setSingleStep(1)

        self.groupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.groupBox.setTitle("Webserver")

        groupBoxLayout: QtWidgets.QFormLayou = QtWidgets.QFormLayout(self.groupBox)
        groupBoxLayout.addWidget(self.enabledCheckBox)
        groupBoxLayout.addRow("Host", self.hostLineEdit)
        groupBoxLayout.addRow("Port", self.portSpinBox)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.groupBox)
        layout.addStretch()
        layout.addWidget(self.buttonBox)

    def isServerEnabled(self) -> bool:
        return self.enabledCheckBox.isChecked()

    def setServerEnabled(self, enabled: bool) -> None:
        self.enabledCheckBox.setChecked(enabled)

    def host(self) -> str:
        return self.hostLineEdit.text().strip()

    def setHost(self, host: str) -> None:
        self.hostLineEdit.setText(host)

    def port(self) -> int:
        return self.portSpinBox.value()

    def setPort(self, port: int) -> None:
        self.portSpinBox.setValue(port)

    def readSettings(self) -> None:
        enabled = settings.value("webapi_enabled", False, bool)
        self.setServerEnabled(enabled)
        host = settings.value("webapi_host", "localhost", str)
        self.setHost(host)
        port = settings.value("webapi_port", 9000, int)
        self.setPort(port)

    def writeSettings(self) -> None:
        settings.setValue("webapi_enabled", self.isServerEnabled())
        settings.setValue("webapi_host", self.host())
        settings.setValue("webapi_port", self.port())
