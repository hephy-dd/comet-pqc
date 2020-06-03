import logging
import random
import time
import threading
import os

import comet
from comet.resource import ResourceMixin, ResourceError
from comet.driver.corvus import Venus1

from .measurements import measurement_factory

class StatusProcess(comet.Process, ResourceMixin):
    """Reload instruments status."""

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress

    def run(self):
        self.emit("message", "Read Matrix...")
        self.emit("progress", 0, 6)
        try:
            with self.resources.get("matrix") as matrix:
                matrix_model = matrix.query("*IDN?")
                matrix_channels = matrix.query("print(channel.getclose(\"allslots\"))")
        except (ResourceError, OSError):
            matrix_model = ""
            matrix_channels = ""
        self.set("matrix_model", matrix_model)
        self.set("matrix_channels", matrix_channels)

        self.emit("message", "Read SMU1...")
        self.emit("progress", 1, 6)
        try:
            with self.resources.get("smu1") as smu1:
                smu1_model = smu1.query("*IDN?")
        except (ResourceError, OSError):
            smu1_model = ""
        self.set("smu1_model", smu1_model)

        self.emit("message", "Read SMU2...")
        self.emit("progress", 2, 6)
        try:
            with self.resources.get("smu2") as smu2:
                smu2_model = smu2.query("*IDN?")
        except (ResourceError, OSError):
            smu2_model = ""
        self.set("smu2_model", smu2_model)

        self.emit("message", "Read LCRMeter...")
        self.emit("progress", 3, 6)
        try:
            with self.resources.get("lcr") as lcr:
                lcr_model = lcr.query("*IDN?")
        except (ResourceError, OSError):
            lcr_model = ""
        self.set("lcr_model", lcr_model)

        self.emit("message", "Read Electrometer...")
        self.emit("progress", 4, 6)
        try:
            with self.resources.get("elm") as elm:
                elm_model = elm.query("*IDN?")
        except (ResourceError, OSError):
            elm_model = ""
        self.set("elm_model", elm_model)

        self.emit("message", "Read Environment Box...")
        self.emit("progress", 5, 6)
        try:
            with self.resources.get("environ") as environ:
                env_model = environ.query("*IDN?")
        except (ResourceError, OSError):
            env_model = ""
        self.set("env_model", env_model)

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

    def safe_initialize_smu1(self, resource):
        resource.query("*IDN?")
        if int(resource.query(":OUTP:STAT?")):
            self.emit("message", "Ramping down SMU1...")
            start_voltage = float(resource.query(":SOUR:VOLT:LEV?"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f":SOUR:VOLT:LEV {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output SMU1...")
            resource.write(":OUTP:STAT OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized SMU1.")

    def safe_initialize_smu2(self, resource):
        resource.query("*IDN?")
        if int(resource.query("print(smua.source.output)")):
            self.emit("message", "Ramping down SMU2...")
            start_voltage = float(resource.query("print(smua.source.levelv)"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f"smua.source.levelv = {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output SMU2...")
            resource.write("smua.source.output = smua.OUTPUT_OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized SMU2.")

    def discarge_decoupling(self, resource):
        resource.query("*IDN?")
        self.emit("message", "Auto-discharging decoupling box...")
        delay = float(resource.query("GET:DISCHARGE_TIME ?")) / 1e3
        resource.write("SET:DISCHARGE AUTO")
        time.sleep(delay + .25)
        resource.read()
        self.emit("message", "Auto-discharged decoupling box.")

    def initialize_matrix(self, resource):
        resource.query("*IDN?")
        logging.info("matrix: open all channels.")
        resource.write("channel.open(\"allslots\")")
        resource.query("*OPC?")
        channels = resource.query("print(channel.getclose(\"allslots\"))")
        logging.info("matrix channels: %s", channels)
        # self.emit("message", "Initialized Matrix.")

    def safe_initialize(self):
        try:
            with self.resources.get("smu1") as smu1:
                self.safe_initialize_smu1(smu1)
        except Exception:
            logging.error("unable to connect with SMU1")
            raise RuntimeError("Failed to connect with SMU1")
        try:
            with self.resources.get("smu2") as smu2:
                self.safe_initialize_smu2(smu2)
        except Exception:
            logging.warning("unable to connect with SMU2")
        if self.get("use_environ"):
            with self.resources.get("environ") as environ:
                self.discarge_decoupling(environ)
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.error("unable to connect with Matrix")
            raise RuntimeError("Failed to connect with Matrix")

    def safe_finalize(self):
        with self.resources.get("smu1") as smu1:
            self.safe_initialize_smu1(smu1)
        try:
            with self.resources.get("smu2") as smu2:
                self.safe_initialize_smu2(smu2)
        except Exception:
            logging.warning("unable to connect with SMU2")
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
