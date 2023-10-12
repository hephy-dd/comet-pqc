import json
import logging
import math

import analysis_pqc
import comet
from flask import Flask, jsonify
from PyQt5 import QtCore
from waitress.server import TcpWSGIServer

from pqc import __version__

__all__ = ["WebAPIWorker"]

logger = logging.getLogger(__name__)


def metric(value, unit):
    """Return metric dictionary."""
    if value is None:
        return None
    return {"value": value, "unit": unit}


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


class WebAPIWorker(comet.Process):

    host = "localhost"
    port = 9000
    enabled = False
    server = None

    def __init__(self, station) -> None:
        super().__init__()
        self.station = station

    def stop(self):
        super().stop()
        server = self.server
        if server:
            server.shutdown()

    def run(self):
        settings = QtCore.QSettings()
        settings.beginGroup("plugin.webapi")
        self.enabled = settings.value("enabled", type(self).enabled, bool)
        self.host = settings.value("hostname",  type(self).host, str)
        self.port = settings.value("port", type(self).port, int)
        settings.endGroup()

        if not self.enabled:
            return

        logger.info("start serving webapi... %s:%s", self.host, self.port)

        app = Flask(__name__)

        @app.route("/")
        def index():
            return jsonify({
                "pqc_version": __version__,
                "comet_version": comet.__version__,
                "analysis_pqc_version": analysis_pqc.__version__,
            })

        @app.route("/table")
        def table():
            enabled = self._table_enabled()
            position = self._table_position()
            contact_quality = self._contact_quality()
            return jsonify({
                "table": {
                    "enabled": enabled,
                    "position": position,
                    "contact_quality": contact_quality
                }
            })

        self.server = WSGIServer(app, host=self.host, port=self.port)
        self.server.run()
        self.server = None
        logger.info("stopped serving webapi")

    def _table_enabled(self):
        table_worker = self.station.table_worker
        if table_worker:
            return table_worker.enabled
        return False

    def _table_position(self):
        x, y, z = None, None, None
        table_worker = self.station.table_worker
        if table_worker and table_worker.running:
            if table_worker.enabled:
                x, y, z = table_worker.get_cached_position()
        return {
            "x": metric(x, "mm"),
            "y": metric(y, "mm"),
            "z": metric(z, "mm")
        }

    def _contact_quality(self):
        contact_quality = self.station.state.get("contact_quality", {})
        cp = contact_quality.get("cp")
        rp = contact_quality.get("rp")
        return {
            "cp": metric(cp, "F"),
            "rp": metric(rp, "Ohm")
        }
