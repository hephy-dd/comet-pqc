import datetime
import logging
import time

from comet.driver import Driver
from comet.driver import lock, Property, Action
from comet.driver import IEC60488

__all__ = ['K707B']

class K707B(IEC60488):
    """Keithley Models 707B Switching Matrix."""

    class Channel(Driver):

        @Action()
        def getclose(self):
            result = self.resource.query('print(channel.getclose("allslots"))')
            if result == 'nil':
                return []
            return result.split(';')

        @Action()
        @lock
        def close(self, channels):
            channels = ','.join(channels)
            self.resource.write(f'channel.close("{channels}")')
            self.resource.query('*OPC?')

        @Action()
        @lock
        def open(self, channels=None):
            if channels is None:
                channels = 'allslots'
            else:
                channels = ','.join(channels)
            self.resource.write(f'channel.open("{channels}")')
            self.resource.query('*OPC?')

    def __init__(self, resource):
        super().__init__(resource)
        self.channel = self.Channel(resource)
