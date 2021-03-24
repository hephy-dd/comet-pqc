import logging
import math
import time
import traceback
import os

import pyvisa

import comet
from comet.resource import ResourceMixin, ResourceError
from comet.process import ProcessMixin
from comet.driver.keithley import K707B

from ..measurements.measurement import ComplianceError
from ..measurements import measurement_factory
from ..measurements.mixins import AnalysisError
from ..settings import settings
from ..utils import format_metric

from ..sequence import MeasurementTreeItem
from ..sequence import ContactTreeItem
from ..sequence import SampleTreeItem
from ..sequence import SamplesItem

__all__ = ['MeasureProcess']

class LogFileHandler:
    """Context manager for log files."""

    Format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    DateFormat = '%Y-%m-%dT%H:%M:%S'

    def __init__(self, filename=None):
        self.__filename = filename
        self.__handler = None
        self.__logger = logging.getLogger()

    def create_path(self, filename):
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

    def create_handler(self, filename):
        self.create_path(filename)
        handler = logging.FileHandler(filename=filename)
        handler.setFormatter(logging.Formatter(
            fmt=self.Format,
            datefmt=self.DateFormat
        ))
        return handler

    def __enter__(self):
        if self.__filename:
            self.__handler = self.create_handler(self.__filename)
            self.__logger.addHandler(self.__handler)
        return self

    def __exit__(self, *exc):
        if self.__handler is not None:
            self.__logger.removeHandler(self.__handler)
        return False

class BaseProcess(comet.Process, ResourceMixin, ProcessMixin):

    def create_filename(self, measurement, suffix=''):
        filename = comet.safe_filename(f"{measurement.basename}{suffix}")
        return os.path.join(self.get('output_dir'), measurement.sample_name, filename)

    def safe_initialize_hvsrc(self, resource):
        context = settings.hvsrc_instrument(resource)
        if context.get_output() == context.OUTPUT_ON:
            self.emit("message", "Ramping down HV Source...")
            start_voltage = context.get_source_voltage()
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                context.set_source_voltage(voltage)
            self.emit("message", "Disable output HV Source...")
            context.set_output(context.OUTPUT_OFF)
        self.emit("message", "Initialized HVSource.")

    def safe_initialize_vsrc(self, resource):
        context = settings.vsrc_instrument(resource)
        if context.get_output() == context.OUTPUT_ON:
            self.emit("message", "Ramping down V Source...")
            start_voltage = context.get_source_voltage()
            stop_voltage = 0.0
            step_voltage = min(25.0, max(5.0, start_voltage / 100.))
            for voltage in comet.Range(start_voltage, stop_voltage, step_voltage):
                context.set_source_voltage(voltage)
            self.emit("message", "Disable output V Source...")
            context.set_output(context.OUTPUT_OFF)
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
            if self.get("use_environ"):
                with self.processes.get("environ") as environment:
                    environment.set_test_led(True)
        except Exception:
            logging.error("unable to connect with environment box (test LED ON)")
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
            logging.error("unable to connect with VSource")
        try:
            if self.get("use_environ"):
                with self.processes.get("environ") as environment:
                    self.discharge_decoupling(environment)
        except Exception:
            logging.error("unable to connect with environment box (discharge decoupling)")
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
            logging.error("unable to connect with VSource")
        try:
            with self.resources.get("matrix") as matrix:
                self.initialize_matrix(matrix)
        except Exception:
            logging.error("unable to connect with: Matrix")
            raise RuntimeError("Failed to connect with Matrix")
        try:
            if self.get("use_environ"):
                with self.processes.get("environ") as environment:
                    environment.set_test_led(False)
        except Exception:
            logging.error("unable to connect with environment box (test LED OFF)")

class MeasureProcess(BaseProcess):
    """Measure process executing a samples, contacts and measurements."""

    context = None

    def __init__(self, message, progress, measurement_state=None,
                 measurement_reset=None, reading=None, save_to_image=None,
                 push_summary=None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.measurement_state = measurement_state
        self.measurement_reset = measurement_reset
        self.reading = reading
        self.save_to_image = save_to_image
        self.push_summary = push_summary
        self.stop_requested = False

    def stop(self):
        """Stop running measurements."""
        self.stop_requested = True
        super().stop()

    def safe_move_table(self, position):
        table_process = self.processes.get("table")
        if table_process.running and table_process.enabled:
            logging.info("Safe move table to %s", position)
            self.emit("message", "Moving table...")
            self.set("movement_finished", False)
            def absolute_move_finished():
                table_process.absolute_move_finished = None
                self.set("table_position", table_process.get_cached_position())
                self.set("movement_finished", True)
                self.emit("message", "Moving table... done.")
            table_process.absolute_move_finished = absolute_move_finished
            table_process.safe_absolute_move(*position)
            while not self.get("movement_finished"):
                time.sleep(.25)
            logging.info("Safe move table to %s... done.", position)

    def initialize(self):
        self.emit("message", "Initialize...")
        self.stop_requested = False
        try:
            self.safe_initialize()
        except Exception:
            self.emit("message", "Initialize... failed.")
            raise
        else:
            self.emit("message", "Initialize... done.")

    def process_measurement(self, measurement_item):
        self.emit("message", "Process measurement...")
        sample_name = measurement_item.contact.sample.name
        sample_type = measurement_item.contact.sample.sample_type
        sample_position = measurement_item.contact.sample.sample_position
        sample_comment = measurement_item.contact.sample.comment
        tags = measurement_item.tags
        table_position = self.get("table_position")
        operator = self.get("operator")
        output_dir = self.get("output_dir")
        sample_output_dir = os.path.join(output_dir, sample_name)
        if not os.path.exists(sample_output_dir):
            os.makedirs(sample_output_dir)
        write_logfiles = self.get("write_logfiles")
        # TODO
        measurement = measurement_factory(
            measurement_item.type,
            process=self,
            sample_name=sample_name,
            sample_type=sample_type,
            sample_position=sample_position,
            sample_comment=sample_comment,
            table_position=table_position,
            operator=operator,
            tags=tags
        )
        measurement.measurement_item = measurement_item
        log_filename = self.create_filename(measurement, suffix='.log') if write_logfiles else None
        plot_filename = self.create_filename(measurement, suffix='.png')
        state = measurement_item.ActiveState
        self.emit(self.measurement_reset, measurement_item)
        self.emit(self.measurement_state, measurement_item, state)
        self.emit('show_measurement', measurement_item)
        with LogFileHandler(log_filename):
            try:
                measurement.run()
            except ResourceError as e:
                self.emit("message", "Process... failed.")
                if isinstance(e.exc, pyvisa.errors.VisaIOError):
                    state = measurement_item.TimeoutState
                elif isinstance(e.exc, BrokenPipeError):
                    state = measurement_item.TimeoutState
                else:
                    state = measurement_item.ErrorState
                raise
            except ComplianceError:
                self.emit("message", "Process... failed.")
                state = measurement_item.ComplianceState
                raise
            except AnalysisError:
                self.emit("message", "Process... analysis failed.")
                state = measurement_item.AnalysisErrorState
                raise
            except Exception as e:
                self.emit("message", "Process... failed.")
                state = measurement_item.ErrorState
                raise
            else:
                self.emit("message", "Process... done.")
                if self.stop_requested:
                    state = measurement_item.StoppedState
                else:
                    state = measurement_item.SuccessState
            finally:
                self.emit(self.measurement_state, measurement_item, state)
                self.emit("save_to_image", measurement_item, plot_filename)
                self.emit('push_summary', measurement.timestamp, sample_name, sample_type, measurement_item.contact.name, measurement_item.name, state)
                if self.get("serialize_json"):
                    with open(self.create_filename(measurement, suffix='.json'), 'w') as fp:
                        measurement.serialize_json(fp)
                if self.get("serialize_txt"):
                    # See https://docs.python.org/3/library/csv.html#csv.DictWriter
                    with open(self.create_filename(measurement, suffix='.txt'), 'w', newline='') as fp:
                        measurement.serialize_txt(fp)

    def process_contact(self, contact_item):
        retry_contact_count = settings.retry_contact_count
        retry_measurement_count = settings.retry_measurement_count
        # Queue of measurements for the retry loops.
        measurement_items = [item for item in contact_item.children if item.enabled]
        # Auto retry table contact
        for retry_contact in range(retry_contact_count + 1):
            if not measurement_items:
                break
            if retry_contact:
                logging.info(f"Retry contact {retry_contact}/{retry_contact_count}...")
            self.emit("message", "Process contact...")
            self.emit(self.measurement_state, contact_item, contact_item.ProcessingState)
            logging.info(" => %s", contact_item.name)
            self.set("movement_finished", False)
            if self.get("move_to_contact") and contact_item.has_position:
                self.safe_move_table(contact_item.position)
                contact_delay = abs(self.get("contact_delay") or 0)
                if contact_delay > 0:
                    logging.info("Applying contact delay: %s s", contact_delay)
                    contact_delay_step = contact_delay / 25.
                    contact_delay_steps = int(math.ceil(contact_delay / contact_delay_step))
                    for step in range(contact_delay_steps):
                        self.emit("message", f"Applying contact delay of {format_metric(contact_delay, unit='s', decimals=1)}...")
                        self.emit("progress", step + 1, contact_delay_steps)
                        time.sleep(contact_delay_step)
            table_position = self.get("table_position")
            # Auto retry measurement
            for retry_measurement in range(retry_measurement_count + 1):
                self.emit(self.measurement_state, contact_item, contact_item.ProcessingState)
                if retry_measurement:
                    logging.info(f"Retry measurement {retry_measurement}/{retry_measurement_count}...")
                measurement_items = self.process_measurement_sequence(measurement_items)
                state = contact_item.ErrorState if measurement_items else contact_item.SuccessState
                if self.stop_requested:
                    state = contact_item.StoppedState
                self.emit(self.measurement_state, contact_item, state)
                if not measurement_items:
                    break
        return contact_item.ErrorState if measurement_items else contact_item.SuccessState

    def process_measurement_sequence(self, measurement_items):
        """Returns a list of failed measurement items."""
        prev_measurement_item = None
        failed_measurements = []
        for measurement_item in measurement_items:
            if not self.running:
                break
            if not measurement_item.enabled:
                continue
            if not self.running:
                self.emit(self.measurement_state, measurement_item, measurement_item.StoppedState)
                break
            if prev_measurement_item:
                self.emit('hide_measurement', prev_measurement_item)
            try:
                self.process_measurement(measurement_item)
            except Exception as exc:
                tb = traceback.format_exc()
                logging.error("%s: %s", measurement_item.name, tb)
                logging.error("%s: %s", measurement_item.name, exc)
                # TODO: for now only analysis errors trigger retries...
                if isinstance(exc, AnalysisError):
                    failed_measurements.append(measurement_item)
            prev_measurement_item = measurement_item
        if prev_measurement_item:
            self.emit('hide_measurement', prev_measurement_item)
        return failed_measurements

    def process_sample(self, sample_item):
        self.emit("message", "Process sample...")
        self.emit(self.measurement_state, sample_item, sample_item.ProcessingState)
        # Check contact positions
        for contact_item in sample_item.children:
            if contact_item.enabled:
                if not contact_item.has_position:
                    raise RuntimeError(f"No contact position assigned for {contact_item.sample.name} -> {contact_item.name}")
        results = []
        for contact_item in sample_item.children:
            if not self.running:
                break
            if not contact_item.enabled:
                continue
            if not self.running:
                self.emit(self.measurement_state, contact_item, contact_item.StoppedState)
                break
            result = self.process_contact(contact_item)
            if result != sample_item.SuccessState:
                results.append(result)
        state = sample_item.ErrorState
        if self.stop_requested:
            state = sample_item.StoppedState
        if not results:
            state = sample_item.SuccessState
        self.emit(self.measurement_state, sample_item, state)
        if not self.running:
            return
        move_to_after_position = self.get("move_to_after_position")
        if self.get("move_to_after_position") is not None:
            self.safe_move_table(move_to_after_position)

    def process_samples(self, samples_item):
        self.emit("message", "Process samples...")
        # Check contact positions
        for sample_item in samples_item.children:
            if sample_item.enabled:
                for contact_item in sample_item.children:
                    if contact_item.enabled:
                        if not contact_item.has_position:
                            raise RuntimeError(f"No contact position assigned for {contact_item.sample.name} -> {contact_item.name}")
        for sample_item in samples_item.children:
            if not self.running:
                break
            if not sample_item.enabled:
                continue
            if not self.running:
                self.emit(self.measurement_state, sample_item, contact_item.StoppedState)
                break
            self.process_sample(sample_item)
        if not self.running:
            return
        move_to_after_position = self.get("move_to_after_position")
        if self.get("move_to_after_position") is not None:
            self.safe_move_table(move_to_after_position)

    def process(self):
        if isinstance(self.context, MeasurementTreeItem):
            self.process_measurement(self.context)
        elif isinstance(self.context, ContactTreeItem):
            self.process_contact(self.context)
        elif isinstance(self.context, SampleTreeItem):
            self.process_sample(self.context)
        elif isinstance(self.context, SamplesItem):
            self.process_samples(self.context)
        else:
            raise TypeError(type(self.context))

    def finalize(self):
        self.emit("message", "Finalize...")
        self.context = None
        try:
            self.safe_finalize()
        except Exception:
            self.emit("message", "Finalize... failed.")
            raise
        else:
            self.emit("message", "Finalize... done.")
        finally:
            self.stop_requested = False

    def run(self):
        try:
            try:
                self.initialize()
                self.process()
            finally:
                self.finalize()
        except Exception:
            self.emit("message", "Measurement failed.")
            raise
        else:
            self.emit("message", "Measurement done.")
