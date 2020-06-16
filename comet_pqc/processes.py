import logging
import random
import time
import threading
import os

import comet
from comet.resource import ResourceMixin, ResourceError
from comet.driver.corvus import Venus1

from .utils import auto_unit
from .measurements import measurement_factory
from .driver import EnvironmentBox
from .driver import K707B

class StatusProcess(comet.Process, ResourceMixin):
    """Reload instruments status."""

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress

    def read_matrix(self):
        self.set("matrix_model", "")
        self.set("matrix_channels", "")
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                model = matrix.identification
                self.set("matrix_model", model)
                channels = matrix.channel.getclose()
                self.set("matrix_channels", ','.join(channels))
        except (ResourceError, OSError):
            pass

    def read_vsrc(self):
        self.set("vsrc_model", "")
        try:
            with self.resources.get("vsrc") as vsrc_res:
                model = vsrc_res.query("*IDN?")
                self.set("vsrc_model", model)
        except (ResourceError, OSError):
            pass

    def read_hvsrc(self):
        self.set("hvsrc_model", "")
        try:
            with self.resources.get("hvsrc") as hvsrc_res:
                model = hvsrc_res.query("*IDN?")
                self.set("hvsrc_model", model)
        except (ResourceError, OSError):
            pass

    def read_lcr(self):
        self.set("lcr_model", "")
        try:
            with self.resources.get("lcr") as lcr_res:
                model = lcr_res.query("*IDN?")
                self.set("lcr_model", model)
        except (ResourceError, OSError):
            pass

    def read_elm(self):
        self.set("elm_model", "")
        try:
            with self.resources.get("elm") as elm_res:
                model = elm_res.query("*IDN?")
                self.set("elm_model", model)
        except (ResourceError, OSError):
            pass

    def read_environ(self):
        self.set("env_model", "")
        self.set("env_pc_data", None)
        try:
            with self.resources.get("environ") as environ_res:
                environ = EnvironmentBox(environ_res)
                model = environ.identification
                self.set("env_model", model)
                pc_data = environ.pc_data
                self.set("env_pc_data", pc_data)
        except (ResourceError, OSError):
            pass

    def run(self):
        self.emit("message", "Reading Matrix...")
        self.emit("progress", 0, 6)
        self.read_matrix()

        self.emit("message", "Reading VSource...")
        self.emit("progress", 1, 6)
        self.read_vsrc()

        self.emit("message", "Read HVSource...")
        self.emit("progress", 2, 6)
        self.read_hvsrc()

        self.emit("message", "Read LCRMeter...")
        self.emit("progress", 3, 6)
        self.read_lcr()

        self.emit("message", "Read Electrometer...")
        self.emit("progress", 4, 6)
        self.read_elm()

        self.emit("message", "Read Environment Box...")
        self.emit("progress", 5, 6)
        self.read_environ()

        self.emit("message", "")
        self.emit("progress", 6, 6)

class CalibrateProcess(comet.Process, ResourceMixin):
    """Calibration process for Corvus table."""

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress

    def run(self):
        self.set("success", False)
        self.emit("message", "Calibrating...")
        with self.resources.get('corvus') as resource:
            corvus = Venus1(resource)
            corvus.mode = 0
            retries = 180
            delay = 1.0

            def handle_error():
                time.sleep(delay)
                error = corvus.error
                if error:
                    raise RuntimeError(f"Corvus: {error}")
                time.sleep(delay)

            def ncal(axis):
                axis.ncal()
                for i in range(retries + 1):
                    self.emit("message", "x={}, y={}, z={}".format(*corvus.pos))
                    if axis is corvus.x:
                        if corvus.pos[0] == 0.0:
                            logging.info("caldone -> OK")
                            break
                    if axis is corvus.y:
                        if corvus.pos[1] == 0.0:
                            logging.info("caldone -> OK")
                            break
                    if axis is corvus.z:
                        if corvus.pos[2] == 0.0:
                            logging.info("caldone -> OK")
                            break
                    time.sleep(delay)
                return i < retries

            def nrm(axis):
                pos = corvus.pos
                axis.nrm()
                time.sleep(delay)
                for i in range(retries + 1):
                    self.emit("message", "x={}, y={}, z={}".format(*corvus.pos))
                    if axis is corvus.x:
                        if corvus.pos[0] == pos[0]:
                            logging.info("caldone -> OK")
                            break
                    if axis is corvus.y:
                        if corvus.pos[1] == pos[1]:
                            logging.info("caldone -> OK")
                            break
                    if axis is corvus.z:
                        if corvus.pos[2] == pos[2]:
                            logging.info("caldone -> OK")
                            break
                    time.sleep(delay)
                    pos = corvus.pos
                return i < retries

            #handle_error()
            self.emit("progress", 0, 7)
            self.emit("message", "Retreating Z axis...")
            if corvus.z.enabled:
                if not ncal(corvus.z):
                    raise RuntimeError("failed retreating Z axis")
            time.sleep(delay)

            #handle_error()
            self.emit("progress", 1, 7)
            self.emit("message", "Calibrating Y axis...")
            if corvus.y.enabled:
                if not ncal(corvus.y):
                    raise RuntimeError("failed to calibrate Y axis")
            time.sleep(delay)

            #handle_error()
            self.emit("progress", 2, 7)
            self.emit("message", "Calibrating X axis...")
            if corvus.x.enabled:
                if not ncal(corvus.x):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            #handle_error()
            self.emit("progress", 3, 7)
            self.emit("message", "Range measure X axis...")
            if corvus.x.enabled:
                if not nrm(corvus.x):
                    raise RuntimeError("failed to ragne measure X axis")
            time.sleep(delay)

            #handle_error()
            self.emit("progress", 4, 7)
            self.emit("message", "Range measure Y axis...")
            if corvus.y.enabled:
                if not nrm(corvus.y):
                    raise RuntimeError("failed to range measure Y axis")
            time.sleep(delay)

            #handle_error()
            corvus.rmove(-1000, -1000, 0)
            for i in range(retries):
                pos = corvus.pos
                self.emit("message", "x={}, y={}, z={}".format(*pos))
                if pos[:2] == (0, 0):
                    break
                time.sleep(delay)
            if pos[:2] != (0, 0):
                raise RuntimeError("failed to relative move, current pos: {}".format(pos))

            #handle_error()
            self.emit("progress", 5, 7)
            self.emit("message", "Calibrating Z axis minimum...")
            if corvus.z.enabled:
                if not ncal(corvus.z):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            #handle_error()
            self.emit("progress", 6, 7)
            self.emit("message", "Range measure Z axis maximum...")
            if corvus.z.enabled:
                if not nrm(corvus.z):
                    raise RuntimeError("failed to range measure Z axis")
            time.sleep(delay)

            #handle_error()
            corvus.rmove(0, 0, -1000)
            for i in range(retries):
                pos = corvus.pos
                self.emit("message", "x={}, y={}, z={}".format(*pos))
                if pos == (0, 0, 0):
                    break
                time.sleep(delay)
            if pos != (0, 0, 0):
                raise RuntimeError("failed to calibrate axes, current pos: {}".format(pos))

            #handle_error()
            self.emit("progress", 7, 7)
            self.emit("message", None)

            corvus.joystick = True

        self.set("success", True)

class BaseProcess(comet.Process, ResourceMixin):

    def safe_initialize_vsrc(self, resource):
        resource.query("*IDN?")
        if int(resource.query(":OUTP:STAT?")):
            self.emit("message", "Ramping down VSource...")
            start_voltage = float(resource.query(":SOUR:VOLT:LEV?"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f":SOUR:VOLT:LEV {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output VSource...")
            resource.write(":OUTP:STAT OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized VSource.")

    def safe_initialize_hvsrc(self, resource):
        resource.query("*IDN?")
        if int(resource.query("print(smua.source.output)")):
            self.emit("message", "Ramping down HVSource...")
            start_voltage = float(resource.query("print(smua.source.levelv)"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f"smua.source.levelv = {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output HVSource...")
            resource.write("smua.source.output = smua.OUTPUT_OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized HVSource.")

    def discarge_decoupling(self, device):
        device.identification
        self.emit("message", "Auto-discharging decoupling box...")
        device.discharge()
        self.emit("message", "Auto-discharged decoupling box.")

    def initialize_matrix(self, resource):
        matrix = K707B(resource)
        matrix.identification
        logging.info("matrix: open all channels.")
        matrix.channel.open()
        channels = matrix.channel.getclose()
        logging.info("matrix channels: %s", channels)
        # self.emit("message", "Initialized Matrix.")

    def safe_initialize(self):
        try:
            with self.resources.get("vsrc") as vsrc:
                self.safe_initialize_vsrc(vsrc)
        except Exception:
            logging.error("unable to connect with VSource")
            raise RuntimeError("Failed to connect with VSource")
        try:
            with self.resources.get("hvsrc") as hvsrc:
                self.safe_initialize_hvsrc(hvsrc)
        except Exception:
            logging.warning("unable to connect with HVSource")
        if self.get("use_environ"):
            with self.resources.get("environ") as environ_resource:
                environ = EnvironmentBox(environ_resource)
                self.discarge_decoupling(environ)
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.error("unable to connect with Matrix")
            raise RuntimeError("Failed to connect with Matrix")

    def safe_finalize(self):
        with self.resources.get("vsrc") as vsrc:
            self.safe_initialize_vsrc(vsrc)
        try:
            with self.resources.get("hvsrc") as hvsrc:
                self.safe_initialize_hvsrc(hvsrc)
        except Exception:
            logging.warning("unable to connect with HVSource")
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.warning("unable to connect with: Matrix")

class MeasureProcess(BaseProcess):
    """Measure process executing a single measurements."""

    measurement_item = None

    def __init__(self, message, progress, measurement_state, reading, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading

    def initialize(self):
        self.emit("message", "Initialize measurement...")
        self.safe_initialize()

    def process(self):
        self.emit("message", "Process measurement...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        # TODO
        measurement = measurement_factory(self.measurement_item.type, self)
        measurement.sample_name = sample_name
        measurement.sample_type = sample_type
        measurement.output_dir = output_dir
        measurement.measurement_item = self.measurement_item
        try:
            self.emit("measurement_state", self.measurement_item, "Active")
            measurement.run()
        except Exception:
            self.emit("measurement_state", self.measurement_item, "Failed")
            raise
        else:
            self.emit("measurement_state", self.measurement_item, "Success")

    def finalize(self):
        self.emit("message", "Finalize measurement...")
        self.measurement_item = None
        self.safe_finalize()

    def run(self):
        self.emit("message", "Starting measurement...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.emit("message", "Measurement done.")

class SequenceProcess(BaseProcess):
    """Sequence process executing a sequence of measurements."""

    sequence_tree = []

    def __init__(self, message, progress, continue_contact, continue_measurement,
                 measurement_state, reading, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.continue_contact = continue_contact
        self.continue_measurement = continue_measurement
        self.measurement_state = measurement_state
        self.reading = reading

    def initialize(self):
        self.emit("message", "Initialize sequence...")
        self.safe_initialize()

    def process(self):
        self.emit("message", "Process sequence...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        for contact_item in self.sequence_tree:
            if not self.running:
                break
            if not contact_item.enabled:
                continue
            self.emit("measurement_state", contact_item, "Active")
            self.set("continue_contact", False)
            self.emit("continue_contact", contact_item)
            while self.running:
                if self.get("continue_contact", False):
                    break
                time.sleep(.100)
            self.set("continue_contact", False)
            if not self.running:
                break
            logging.info(" => %s", contact_item.name)
            for measurement_item in contact_item.children:
                if not self.running:
                    break
                if not measurement_item.enabled:
                    self.emit("measurement_state", measurement_item, "Skipped")
                    continue
                autopilot = self.get("autopilot", False)
                logging.info("Autopilot: %s", ["OFF", "ON"][autopilot])
                if not autopilot:
                    logging.info("Waiting for %s", measurement_item.name)
                    self.emit("measurement_state", measurement_item, "Waiting")
                    self.set("continue_measurement", False)
                    self.emit("continue_measurement", measurement_item)
                    while self.running:
                        if self.get("continue_measurement", False):
                            break
                        time.sleep(.100)
                    self.set("continue_measurement", False)
                if not self.running:
                    self.emit("measurement_state", measurement_item, "Aborted")
                    break
                logging.info("Run %s", measurement_item.name)
                self.emit("measurement_state", measurement_item, "Active")
                # TODO
                measurement = measurement_factory(measurement_item.type, self)
                measurement.sample_name = sample_name
                measurement.sample_type = sample_type
                measurement.output_dir = output_dir
                measurement.measurement_item = measurement_item
                try:
                    measurement.run()
                except Exception as e:
                    logging.error(format(e))
                    logging.error("%s failed.", measurement_item.name)
                    self.emit("measurement_state", measurement_item, "Failed")
                    ## raise
                else:
                    logging.info("%s done.", measurement_item.name)
                    self.emit("measurement_state", measurement_item, "Success")
            self.emit("measurement_state", contact_item, None)

    def finalize(self):
        self.emit("message", "Finalize sequence...")
        self.sequence_tree = []
        self.safe_finalize()

    def run(self):
        self.emit("message", "Starting sequence...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.emit("message", "Sequence done.")
