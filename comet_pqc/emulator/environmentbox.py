"""HEPHY Environment Box emulator."""

import random
import time
import re
import logging

from comet.emulator.emulator import message, run
from comet.emulator.iec60488 import IEC60488Handler

__all__ = ['EnvironmentBoxHandler']

class EnvironmentBoxHandler(IEC60488Handler):

    identification = "Spanish Inquisition Inc., Environment Box, v1.0"

    laser_sensor = False
    box_light = False
    microscope_control = False
    microscope_light = False
    microscope_camera = False
    probecard_light = False
    probecard_camera = False
    discharge_time = 1000
    pid_control = False

    @classmethod
    def pc_data(cls):
        pc_data = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
        pc_data[4] = int(cls.pid_control)
        power_relay_states = 0
        if cls.microscope_control:
            power_relay_states |= 1 << 0
        if cls.box_light:
            power_relay_states |= 1 << 1
        if cls.probecard_light:
            power_relay_states |= 1 << 2
        if cls.laser_sensor:
            power_relay_states |= 1 << 3
        if cls.probecard_camera:
            power_relay_states |= 1 << 4
        if cls.microscope_camera:
            power_relay_states |= 1 << 5
        if cls.microscope_light:
            power_relay_states |= 1 << 6
        pc_data[23] = power_relay_states
        return pc_data

    @message(r'GET:PC_DATA ?')
    def query_get_pc_data(self, message):
        return ','.join(map(format, type(self).pc_data()))

    @message(r'SET:LASER_SENSOR (ON|OFF)')
    def query_set_laser_sensor(self, message):
        type(self).laser_sensor = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'SET:BOX_LIGHT (ON|OFF)')
    def query_set_box_light(self, message):
        type(self).box_light = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'GET:MICROSCOPE_LIGHT ?')
    def query_get_microscope_light(self, message):
        return int(type(self).microscope_light)

    @message(r'SET:MICROSCOPE_LIGHT (ON|OFF)')
    def query_set_microscope_light(self, message):
        type(self).microscope_light = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'GET:MICROSCOPE_CAM ?')
    def query_get_microscope_camera(self, message):
        return int(type(self).microscope_camera)

    @message(r'SET:MICROSCOPE_CAM (ON|OFF)')
    def query_set_microscope_camera(self, message):
        type(self).microscope_camera = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'GET:MICROSCOPE_CTRL ?')
    def query_get_microscope_control(self, message):
        return int(type(self).microscope_control)

    @message(r'SET:MICROSCOPE_CTRL (ON|OFF)')
    def query_set_microscope_control(self, message):
        type(self).microscope_control = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'GET:PROBCARD_LIGHT ?')
    def query_get_probecard_light(self, message):
        return int(type(self).probecard_light)

    @message(r'SET:PROBCARD_LIGHT (ON|OFF)')
    def query_set_probecard_light(self, message):
        type(self).probecard_light = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'GET:PROBCARD_CAM ?')
    def query_get_probecard_camera(self, message):
        return int(type(self).probecard_camera)

    @message(r'SET:PROBCARD_CAM (ON|OFF)')
    def query_set_probecard_camera(self, message):
        type(self).probecard_camera = message.split()[-1].strip() == 'ON'
        return 'OK'

    @message(r'GET:DISCHARGE_TIME ?')
    def query_get_discharge_time(self, message):
        return format(type(self).discharge_time)

    @message(r'SET:DISCHARGE AUTO')
    def query_set_discharge_auto(self, message):
        return 'OK'

    @message(r'SET:CTRL (ON|OFF)')
    def query_set_pid_control(self, message):
        type(self).pid_control = message.split()[-1].strip() == 'ON'
        return 'OK'

if __name__ == "__main__":
    run(EnvironmentBoxHandler)
