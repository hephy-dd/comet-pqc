import logging
import json
import socket
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
from wsgiref.simple_server import make_server

import bottle
import comet

__all__ = ['WebAPIProcess']

def metric(value, unit):
    """Return metric dictionary."""
    if value is None:
        return None
    return {'value': value, 'unit': unit}

class WSGIRefServer(bottle.ServerAdapter):
    """Custom bottle server adapter for WSGI reference server."""

    quiet = True
    """Run server in quiet mode."""

    def stop(self):
        """Stop running server."""
        try:
            logging.info('Request stopping WSGI server...')
            self.srv.shutdown()
            logging.info('Request stopping WSGI server... done.')
        except:
            logging.error('Request stopping WSGI server... failed')

    def run(self, app):
        class FixedHandler(WSGIRequestHandler):
            def address_string(self): # Prevent reverse DNS lookups please.
                return self.client_address[0]
            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls  = self.options.get('server_class', WSGIServer)

        if ':' in self.host: # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        self.srv = make_server(self.host, self.port, app, server_cls, handler_cls)
        with self.srv as srv:
            srv.serve_forever()
        logging.info('WSGI server stopped.')

class JSONErrorBottle(bottle.Bottle):
    """Custom bollte application with default JSON error handling."""

    def default_error_handler(self, res):
        bottle.response.content_type = 'application/json'
        return json.dumps(dict(error=res.body, status_code=res.status_code))

class WebAPIProcess(comet.Process, comet.ProcessMixin):

    host = 'localhost'
    port = 9000
    srv = None

    def stop(self):
        super().stop()
        if self.srv:
            self.srv.stop()

    def run(self):
        self.enabled = self.settings.get('webapi_enabled') or False
        self.port = int(self.settings.get('webapi_port') or 9000)

        if not self.enabled:
            return

        app = JSONErrorBottle()

        # Fix Cross-Origin Request Blocked error on client side
        def apply_cors():
            bottle.response.headers['Access-Control-Allow-Origin'] = '*'
        app.add_hook('after_request', apply_cors)

        @app.route('/')
        def index():
            return {'status': 'OK'}

        @app.route('/table')
        def table():
            enabled = self._table_enabled()
            position = self._table_position()
            contact_quality = self._contact_quality()
            return {'table': {
                'enabled': enabled,
                'position': position,
                'contact_quality': contact_quality
            }}

        self.srv = WSGIRefServer(host=self.host, port=self.port)
        while self.running:
            bottle.run(app, server=self.srv)

    def _table_enabled(self):
        table_process = self.processes.get('table')
        if table_process:
            return table_process.enabled
        return False

    def _table_position(self):
        x, y, z = None, None, None
        table_process = self.processes.get('table')
        if table_process and table_process.running:
            if table_process.enabled:
                x, y, z = table_process.get_cached_position()
        return {
            'x': metric(x, 'mm'),
            'y': metric(y, 'mm'),
            'z': metric(z, 'mm')
        }

    def _contact_quality(self):
        cp, rp = None, None
        contact_quality_process = self.processes.get('contact_quality')
        if contact_quality_process and contact_quality_process.running:
            cp, rp = contact_quality_process.cached_reading()
        return {
            'cp': metric(cp, 'F'),
            'rp': metric(rp, 'Ohm')
        }
