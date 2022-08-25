import logging

from comet.driver.hephy import EnvironmentBox

from .resource import ResourceProcess

__all__ = ["EnvironmentProcess"]

logger = logging.getLogger(__name__)


class EnvironmentProcess(ResourceProcess):

    Driver = EnvironmentBox

    update_monitoring_interval: float = 2.0

    def __init__(self, *args, pc_data_updated=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pc_data_updated = pc_data_updated
        self._cached_pc_data = None

    def pc_data(self, cached=True):
        if not self._cached_pc_data or not cached:
            self.request_pc_data().get()
        return self._cached_pc_data

    def request_pc_data(self):
        def request(context):
            self._cached_pc_data = context.pc_data
            self.emit("pc_data_updated", self._cached_pc_data)
            return self._cached_pc_data
        return self.async_request(request)

    def has_lights(self):
        """Return True if any light source is enabled."""
        def request(context):
            return \
                context.box_light or \
                context.microscope_light or \
                context.probecard_light
        return self.async_request(request).get()

    def dim_lights(self):
        """Switch off all light sources."""
        self.set_box_light(False)
        self.set_microscope_light(False)
        self.set_probecard_light(False)

    def identification(self):
        def request(context):
            return context.identification
        return self.async_request(request).get()

    def discharge(self):
        logger.info("Discharge Decoupling Box...")

        def request(context):
            context.discharge()
        return self.async_request(request).get()

    def set_laser_sensor(self, state):
        logger.info("Laser Sensor: %s", "ON" if state else "OFF")
        def request(context):
            context.laser_sensor = state
        return self.async_request(request).get()

    def set_box_light(self, state):
        logger.info("Box Light: %s", "ON" if state else "OFF")
        def request(context):
            context.box_light = state
        return self.async_request(request).get()

    def set_microscope_light(self, state):
        logger.info("Microscope Light: %s", "ON" if state else "OFF")
        def request(context):
            context.microscope_light = state
        return self.async_request(request).get()

    def set_microscope_camera(self, state):
        logger.info("Microscope Camera: %s", "ON" if state else "OFF")
        def request(context):
            context.microscope_camera = state
        return self.async_request(request).get()

    def set_microscope_control(self, state):
        logger.info("Microscope Power: %s", "ON" if state else "OFF")
        def request(context):
            context.microscope_control = state
        return self.async_request(request).get()

    def set_probecard_light(self, state):
        logger.info("Probecard Light: %s", "ON" if state else "OFF")
        def request(context):
            context.probecard_light = state
        return self.async_request(request).get()

    def set_probecard_camera(self, state):
        logger.info("Probecard Camera: %s", "ON" if state else "OFF")
        def request(context):
            context.probecard_camera = state
        return self.async_request(request).get()

    def set_pid_control(self, state):
        logger.info("PID Control: %s", "ON" if state else "OFF")
        def request(context):
            context.pid_control = state
        return self.async_request(request).get()

    def set_test_led(self, state):
        logger.info("Test LED: %s", "ON" if state else "OFF")
        def request(context):
            context.test_led = state
        return self.async_request(request).get()

    def update_monitoring(self):
        self.request_pc_data()
