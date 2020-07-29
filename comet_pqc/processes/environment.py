import logging
import time

from .resource import ResourceProcess
from ..driver.environmentbox import EnvironmentBox

class EnvironmentProcess(ResourceProcess):

    Driver = EnvironmentBox

    def pc_data(self):
        def request(context):
            return context.pc_data
        return self.request(request)

    def has_lights(self):
        """Return True if any light source is enabled."""
        def request(context):
            return \
                context.box_light or \
                context.microscope_light or \
                context.probecard_light
        return self.request(request)

    def dim_lights(self):
        """Switch off all light sources."""
        def request(context):
            context.box_light = False
            context.microscope_light = False
            context.probecard_light = False
        return self.request(request)

    def identification(self):
        def request(context):
            return context.identification
        return self.request(request)

    def discharge(self):
        def request(context):
            context.discharge()
        return self.request(request)

    def set_laser_sensor(self, state):
        def request(context):
            context.laser_sensor = state
        return self.request(request)

    def set_box_light(self, state):
        def request(context):
            context.box_light = state
        return self.request(request)

    def set_microscope_light(self, state):
        def request(context):
            context.microscope_light = state
        return self.request(request)

    def set_microscope_camera(self, state):
        def request(context):
            context.microscope_camera = state
        return self.request(request)

    def set_microscope_control(self, state):
        def request(context):
            context.microscope_control = state
        return self.request(request)

    def set_probecard_light(self, state):
        def request(context):
            context.probecard_light = state
        return self.request(request)

    def set_probecard_camera(self, state):
        def request(context):
            context.probecard_camera = state
        return self.request(request)

    def set_pid_control(self, state):
        def request(context):
            context.pid_control = state
        return self.request(request)

    def toggle_box_light(self):
        def request(context):
            state = context.box_light
            context.box_light = not state
        return self.request(request)

    def toggle_microscope_light(self):
        def request(context):
            state = context.microscope_light
            context.microscope_light = not state
        return self.request(request)

    def toggle_microscope_camera(self):
        def request(context):
            state = context.microscope_camera
            context.microscope_camera = not state
        return self.request(request)

    def toggle_probecard_light(self):
        def request(context):
            state = context.probecard_light
            context.probecard_light = not state
        return self.request(request)

    def toggle_probecard_camera(self):
        def request(context):
            state = context.probecard_camera
            context.probecard_camera = not state
        return self.request(request)
