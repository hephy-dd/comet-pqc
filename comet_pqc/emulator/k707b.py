"""Keithley 707B matrix emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler
from comet.emulator.keithley.k2400 import SystemMixin

__all__ = ['K707BHandler']

class ChannelMixin:

    closed_channels = []

    @message(r'print\(channel\.getclose\(([^\)]+)\)\)')
    def query_channel_getclose(self, message):
        if not type(self).closed_channels:
            return 'nil'
        return ';'.join(type(self).closed_channels)

    @message(r'channel\.close\(([^\)]+)\)')
    def write_channel_close(self, message):
        r = re.match(r'channel\.close\(([^\)]+)\)', message)
        if r:
            channels = r.group(1).strip('"').split(',')
            type(self).closed_channels = channels

    @message(r'channel\.open\(([^\)]+)\)')
    def write_channel_open(self, message):
        r = re.match(r'channel\.open\(([^\)]+)\)', message)
        if r:
            channels = r.group(1).strip('"').split(',')
            if channels == ['allslots']:
                type(self).closed_channels = []
            else:
                for channel in channels:
                    if channel in type(self).closed_channels:
                        type(self).closed_channels.remove(channel)

class K707BHandler(IEC60488Handler, ChannelMixin):

    identification = "Spanish Inquisition Inc., Model 707B, 12345678, v1.0"

if __name__ == "__main__":
    run(K707BHandler)
