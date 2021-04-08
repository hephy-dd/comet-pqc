import socket
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
from wsgiref.simple_server import make_server

import bottle
import comet

__all__ = ['WebAPIProcess']

class WSGIRefServer(bottle.ServerAdapter):
    quiet = True
    def stop(self):
        self.srv.shutdown()
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

        srv = self.srv = make_server(self.host, self.port, app, server_cls, handler_cls)
        srv.serve_forever()
        srv.server_close()

class WebAPIProcess(comet.Process, comet.ProcessMixin):

    host = 'localhost'
    port = 9000

    def stop(self):
        try:
            self.srv.stop()
        finally:
            super().stop()

    def run(self):
        app = self.app = bottle.default_app()

        @app.route('/')
        def index():
            return {'status': 'OK'}

        @app.route('/table')
        def table():
            if self.processes.get('table').running:
                x, y, z = self.processes.get('table').get_cached_position()
                position = {
                    'x': {'value': x, 'unit': 'mm'},
                    'y': {'value': y, 'unit': 'mm'},
                    'z': {'value': z, 'unit': 'mm'}
                }
                cp, rp = self.processes.get('contact_quality').cached_reading()
                contact_quality = {
                    'cp': {'value': cp, 'unit': 'F'},
                    'rp': {'value': rp, 'unit': 'Ohm'}
                }
                return {'table': {'position': position, 'contact_quality': contact_quality}}
            return {}

        self.srv = WSGIRefServer(host=self.host, port=self.port)
        while self.running:
            bottle.run(app, server=self.srv)
