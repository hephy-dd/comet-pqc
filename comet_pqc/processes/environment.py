import logging
import time

from comet.driver.hephy import EnvironmentBox
from .resource import ResourceProcess

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
        self.set_box_light(False)
        self.set_microscope_light(False)
        self.set_probecard_light(False)

    def identification(self):
        def request(context):
            return context.identification
        return self.request(request)

    def discharge(self):
        logging.info("Discharge Decoupling Box...")
        def request(context):
            context.discharge()
        return self.request(request)

    def set_laser_sensor(self, state):
        logging.info("Laser Sensor: %s", "ON" if state else "OFF")
        def request(context):
            context.laser_sensor = state
        return self.request(request)

    def set_box_light(self, state):
        logging.info("Box Light: %s", "ON" if state else "OFF")
        def request(context):
            context.box_light = state
        return self.request(request)

    def set_microscope_light(self, state):
        logging.info("Microscope Light: %s", "ON" if state else "OFF")
        def request(context):
            context.microscope_light = state
        return self.request(request)

    def set_microscope_camera(self, state):
        logging.info("Microscope Camera: %s", "ON" if state else "OFF")
        def request(context):
            context.microscope_camera = state
        return self.request(request)

    def set_microscope_control(self, state):
        logging.info("Microscope Power: %s", "ON" if state else "OFF")
        def request(context):
            context.microscope_control = state
        return self.request(request)

    def set_probecard_light(self, state):
        logging.info("Probecard Light: %s", "ON" if state else "OFF")
        def request(context):
            context.probecard_light = state
        return self.request(request)

    def set_probecard_camera(self, state):
        logging.info("Probecard Camera: %s", "ON" if state else "OFF")
        def request(context):
            context.probecard_camera = state
        return self.request(request)

    def set_pid_control(self, state):
        logging.info("PID Control: %s", "ON" if state else "OFF")
        def request(context):
            context.pid_control = state
        return self.request(request)

    def set_test_led(self, state):
        logging.info("Test LED: %s", "ON" if state else "OFF")
        def request(context):
            context.test_led = state
        return self.request(request)
