import json
import logging
import math

import analysis_pqc
import bottle
import comet
from waitress.server import TcpWSGIServer

from .. import __version__

from . import Plugin

__all__ = ["WebAPIPlugin"]

logger = logging.getLogger(__name__)


def metric(value, unit):
    """Return metric dictionary."""
    if value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None  # do not return `NaN` not supported by JSON
    return {"value": value, "unit": unit}


class WebAPIPlugin(Plugin):

    def install(self, window):
        # TODO migrate preferences
        window.processes.add("webapi", WebAPIProcess(
            failed=window.showException
        ))


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


class WebAPIProcess(comet.Process, comet.ProcessMixin):

    host = "localhost"
    port = 9000
    enabled = False
    server = None

    def stop(self):
        super().stop()
        server = self.server
        if server:
            server.shutdown()

    def run(self):
        self.enabled = self.settings.get("webapi_enabled") or type(self).enabled
        self.host = self.settings.get("webapi_host") or type(self).host
        self.port = int(self.settings.get("webapi_port") or type(self).port)

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
            enabled = self.table_enabled()
            position = self.table_position()
            contact_quality = self.contact_quality()
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

    def table_enabled(self):
        table_process = self.processes.get("table")
        if table_process:
            return table_process.enabled
        return False

    def table_position(self):
        x, y, z = None, None, None
        table_process = self.processes.get("table")
        if table_process and table_process.running:
            if table_process.enabled:
                x, y, z = table_process.get_cached_position()
        return {
            "x": metric(x, "mm"),
            "y": metric(y, "mm"),
            "z": metric(z, "mm")
        }

    def contact_quality(self):
        cp, rp = None, None
        contact_quality_process = self.processes.get("contact_quality")
        if contact_quality_process and contact_quality_process.running:
            cp, rp = contact_quality_process.cached_reading()
        return {
            "cp": metric(cp, "F"),
            "rp": metric(rp, "Ohm")
        }
