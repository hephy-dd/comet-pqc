import datetime
import logging
import random
import time
import threading
import os

import pyvisa

import comet
from comet.resource import ResourceMixin, ResourceError
from comet.process import ProcessMixin
from comet.driver.corvus import Venus1

from ..utils import format_metric
from ..measurements.measurement import ComplianceError
from ..measurements import measurement_factory
from ..driver import EnvironmentBox
from ..driver import K707B

class BaseProcess(comet.Process, ResourceMixin, ProcessMixin):

    def safe_initialize_hvsrc(self, resource):
        resource.query("*IDN?")
        if int(resource.query(":OUTP:STAT?")):
            self.emit("message", "Ramping down HVSource...")
            start_voltage = float(resource.query(":SOUR:VOLT:LEV?"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f":SOUR:VOLT:LEV {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output HVSource...")
            resource.write(":OUTP:STAT OFF")
            resource.query("*OPC?")
        self.emit("message", "Initialized HVSource.")

    def safe_initialize_vsrc(self, resource):
        resource.query("*IDN?")
        if int(float(resource.query("print(smua.source.output)"))):
            self.emit("message", "Ramping down VSource...")
            start_voltage = float(resource.query("print(smua.source.levelv)"))
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                resource.write(f"smua.source.levelv = {voltage:E}")
                resource.query("*OPC?")
            self.emit("message", "Disable output VSource...")
            resource.write("smua.source.output = 0")
            resource.query("*OPC?")
        self.emit("message", "Initialized VSource.")

    def discharge_decoupling(self, context):
        self.emit("message", "Auto-discharging decoupling box...")
        context.discharge()
        self.emit("message", "Auto-discharged decoupling box.")

    def initialize_matrix(self, resource):
        self.emit("message", "Open all matrix channels...")
        matrix = K707B(resource)
        matrix.identification
        logging.info("matrix: open all channels.")
        matrix.channel.open()
        channels = matrix.channel.getclose()
        logging.info("matrix channels: %s", channels)
        self.emit("message", "Opened all matrix channels.")

    def safe_initialize(self):
        try:
            with self.resources.get("hvsrc") as hvsrc:
                self.safe_initialize_hvsrc(hvsrc)
        except Exception:
            logging.error("unable to connect with HVSource")
            raise RuntimeError("Failed to connect with HVSource")
        try:
            with self.resources.get("vsrc") as vsrc:
                self.safe_initialize_vsrc(vsrc)
        except Exception:
            logging.warning("unable to connect with VSource")
        if self.get("use_environ"):
            with self.processes.get("environment") as environment:
                self.discharge_decoupling(environment)
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.error("unable to connect with Matrix")
            raise RuntimeError("Failed to connect with Matrix")

    def safe_finalize(self):
        with self.resources.get("hvsrc") as hvsrc:
            self.safe_initialize_hvsrc(hvsrc)
        try:
            with self.resources.get("vsrc") as vsrc:
                self.safe_initialize_vsrc(vsrc)
        except Exception:
            logging.warning("unable to connect with VSource")
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.warning("unable to connect with: Matrix")
            raise RuntimeError("Failed to connect with Matrix")

class MeasureProcess(BaseProcess):
    """Measure process executing a single measurements."""

    measurement_item = None

    def __init__(self, message, progress, measurement_state, reading, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading
        self.push_summary = None
        self.stopped = False

    def stop(self):
        self.stopped = True
        super().stop()

    def initialize(self):
        self.emit("message", "Initialize measurement...")
        self.stopped = False
        self.safe_initialize()

    def process(self):
        self.emit("message", "Process measurement...")
        timestamp = datetime.datetime.now()
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        # TODO
        measurement = measurement_factory(self.measurement_item.type, self)
        measurement.sample_name = sample_name
        measurement.sample_type = sample_type
        measurement.output_dir = output_dir
        measurement.measurement_item = self.measurement_item
        state = "Active"
        self.emit("measurement_state", self.measurement_item, state)
        try:
            measurement.run()
        except ResourceError as e:
            if isinstance(e.exc, pyvisa.errors.VisaIOError):
                state = "Timeout"
            elif isinstance(e.exc, BrokenPipeError):
                state = "Timeout"
            else:
                state = type(e.exc).__name__
            raise
        except ComplianceError:
            state = "Compliance"
            raise
        except Exception:
            state = "Error"
            raise
        else:
            if self.stopped:
                state = "Stopped"
            else:
                state = "Success"
        finally:
            self.emit("measurement_state", self.measurement_item, state)
            self.emit('push_summary', timestamp, self.get("sample_name"), self.get("sample_type"), self.measurement_item.contact.name, self.measurement_item.name, state)

    def finalize(self):
        self.emit("message", "Finalize measurement...")
        self.measurement_item = None
        self.safe_finalize()
        self.stopped = False

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

    # sequence_tree = []
    contact_item = None

    def __init__(self, message, progress, measurement_state, reading, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.reading = reading
        self.stopped = False

    def stop(self):
        self.stopped = True
        super().stop()

    def initialize(self):
        self.emit("message", "Initialize sequence...")
        self.stopped = False
        self.safe_initialize()

    def process(self):
        self.emit("message", "Process sequence...")
        sample_name = self.get("sample_name")
        sample_type = self.get("sample_type")
        output_dir = self.get("output_dir")
        contact_item = self.contact_item
        self.emit("measurement_state", contact_item, "Active")
        logging.info(" => %s", contact_item.name)
        prev_measurement_item = None
        for measurement_item in contact_item.children:
            if not self.running:
                break
            if not measurement_item.enabled:
                self.emit("measurement_state", measurement_item, "Skipped")
                continue
            if not self.running:
                self.emit("measurement_state", measurement_item, "Stopped")
                break
            logging.info("Run %s", measurement_item.name)
            # TODO
            timestamp = datetime.datetime.now()
            measurement = measurement_factory(measurement_item.type, self)
            measurement.sample_name = sample_name
            measurement.sample_type = sample_type
            measurement.output_dir = output_dir
            measurement.measurement_item = measurement_item
            state = "Active"
            self.emit("measurement_state", measurement_item, state)
            self.emit('show_measurement', prev_measurement_item, measurement_item)
            try:
                measurement.run()
            except ResourceError as e:
                if isinstance(e.exc, pyvisa.errors.VisaIOError):
                    state = "Timeout"
                elif isinstance(e.exc, BrokenPipeError):
                    state = "Timeout"
                else:
                    state = type(e.exc).__name__
                logging.error(format(e))
                logging.error("%s failed.", measurement_item.name)
            except ComplianceError as e:
                logging.error(format(e))
                logging.error("%s failed.", measurement_item.name)
                state = "Compliance"
            except Exception as e:
                logging.error(format(e))
                logging.error("%s failed.", measurement_item.name)
                state = "Error"
            else:
                if self.stopped:
                    state = "Stopped"
                else:
                    state = "Success"
                logging.info("%s done.", measurement_item.name)
            finally:
                self.emit("measurement_state", measurement_item, state)
                self.emit('push_summary', timestamp, self.get("sample_name"), self.get("sample_type"), measurement_item.contact.name, measurement_item.name, state)

            prev_measurement_item = measurement_item
            self.emit("measurement_state", contact_item, None)

    def finalize(self):
        self.emit("message", "Finalize sequence...")
        # self.sequence_tree = []
        self.contact_item = None
        self.stopped = False
        self.safe_finalize()

    def run(self):
        self.emit("message", "Starting sequence...")
        try:
            self.initialize()
            self.process()
        finally:
            self.finalize()
            self.emit("message", "Sequence done.")
