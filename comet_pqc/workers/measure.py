import logging
import math
import os
import time
import traceback
import threading
import uuid
from datetime import datetime

from PyQt5 import QtCore

import pyvisa
from comet import safe_filename, make_iso
from comet.resource import ResourceError
import analysis_pqc

from .. import __version__
from ..core.functions import LinearRange
from ..core.request import RequestTimeout
from ..measurements import measurement_factory
from ..measurements.measurement import ComplianceError, serialize_json, serialize_txt
from ..measurements.mixins import AnalysisError
from ..view.sequence import (
    ContactTreeItem,
    MeasurementTreeItem,
    SequenceRootTreeItem,
    SampleTreeItem,
)
from ..settings import settings
from ..utils import format_metric

__all__ = ["MeasureWorker"]

logger = logging.getLogger(__name__)


def timestamp_iso(timestamp: float) -> str:
    """Returns start timestamp as ISO formatted string."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")


class LogFileHandler:
    """Context manager for log files."""

    Format = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    DateFormat = "%Y-%m-%dT%H:%M:%S"

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


class MeasureWorker(QtCore.QObject):
    """Measure process executing a samples, contacts and measurements."""

    failed = QtCore.pyqtSignal(Exception)
    finished = QtCore.pyqtSignal()

    message_changed = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(int, int)

    item_state_changed = QtCore.pyqtSignal(object, object)
    item_recontact_changed = QtCore.pyqtSignal(object, int)
    item_remeasure_changed = QtCore.pyqtSignal(object, int)
    item_reset = QtCore.pyqtSignal(object)
    item_visible = QtCore.pyqtSignal(object)
    item_hidden = QtCore.pyqtSignal(object)
    save_to_image = QtCore.pyqtSignal(object, str)
    summary_pushed = QtCore.pyqtSignal(dict)

    reading_appended = QtCore.pyqtSignal(str, float, float)
    readings_updated = QtCore.pyqtSignal()
    analysis_appended = QtCore.pyqtSignal(str, dict)
    state_changed = QtCore.pyqtSignal(dict)

    def __init__(self, station, config, item):
        super().__init__()
        self.stop_requested: bool = False
        self.station = station
        self.config: dict = {}
        self.sequence_item = item
        # Set default configuration
        self.config.update({
            "before_measurement_delay": 0.0,
            "retry_contact_overdrive": 0.0,
            "table_contact_delay": 0.0,
            "table_move_timeout": 120.0,
            "serialize_json": True,
            "serialize_txt": False,
        })
        # Update custom configuration
        self.config.update(config)

    def abort(self):
        """Stop running measurements."""
        self.stop_requested = True

    def set_message(self, message: str) -> None:
        self.message_changed.emit(message)

    def set_progress(self, value: int, maximum: int) -> None:
        self.progress_changed.emit(value, maximum)

    def set_item_state(self, item, state) -> None:
        self.item_state_changed.emit(item, state)

    def increment_item_recontact(self, item) -> None:
        self.item_recontact_changed.emit(item, item.recontact() + 1)

    def increment_item_remeasure(self, item) -> None:
        self.item_remeasure_changed.emit(item, item.remeasure() + 1)

    def reset_measurement_item(self, item) -> None:
        self.item_reset.emit(item)

    def show_measurement_item(self, item) -> None:
        self.item_visible.emit(item)

    def hide_measurement_item(self, item) -> None:
        self.item_hidden.emit(item)

    def append_reading(self, name, x, y) -> None:
        self.reading_appended.emit(name, x, y)

    def update_readings(self) -> None:
        self.readings_updated.emit()

    def append_analysis(self, key: str, values: dict) -> None:
        self.analysis_appended.emit(key, values)

    def update_state(self, data: dict) -> None:
        self.state_changed.emit(data)

    def safe_recover_hvsrc(self) -> None:
        with self.station.hvsrc_resource as hvsrc_resource:
            hvsrc = settings.hvsrc_instrument(hvsrc_resource)
            if hvsrc.get_output() == hvsrc.OUTPUT_ON:
                self.set_message("Ramping down HV Source...")
                start_voltage = hvsrc.get_source_voltage()
                stop_voltage = 0.0
                step_voltage = min(25.0, max(5.0, start_voltage / 100.))
                for voltage in LinearRange(start_voltage, stop_voltage, step_voltage):
                    hvsrc.set_source_voltage(voltage)
                self.set_message("Disable output HV Source...")
                hvsrc.set_output(hvsrc.OUTPUT_OFF)
        self.set_message("Initialized HVSource.")

    def safe_recover_vsrc(self) -> None:
        with self.station.vsrc_resource as vsrc_resource:
            vsrc = settings.vsrc_instrument(vsrc_resource)
            if vsrc.get_output() == vsrc.OUTPUT_ON:
                self.set_message("Ramping down V Source...")
                start_voltage = vsrc.get_source_voltage()
                stop_voltage = 0.0
                step_voltage = min(25.0, max(5.0, start_voltage / 100.))
                for voltage in LinearRange(start_voltage, stop_voltage, step_voltage):
                    vsrc.set_source_voltage(voltage)
                self.set_message("Disable output V Source...")
                vsrc.set_output(vsrc.OUTPUT_OFF)
        self.set_message("Initialized VSource.")

    def discharge_decoupling(self) -> None:
        self.set_message("Auto-discharging decoupling box...")
        with self.station.environ_process as environ:
            environ.discharge()
        self.set_message("Auto-discharged decoupling box.")

    def safe_recover_matrix(self) -> None:
        self.set_message("Open all matrix channels...")
        self.station.matrix.identify()
        logger.info("matrix: open all channels.")
        self.station.matrix.open_all_channels()
        channels = self.station.matrix.closed_channels()
        logger.info("matrix channels: %s", channels)
        if channels:
            raise RuntimeError("Unable to open matrix channels: %s", channels)
        self.set_message("Opened all matrix channels.")

    def safe_initialize(self) -> None:
        try:
            if self.config.get("use_environ"):
                self.station.set_test_led(True)
        except Exception:
            logger.error("unable to connect with environment box (test LED ON)")
            raise
        try:
            self.safe_recover_hvsrc()
        except Exception:
            logger.error("unable to connect with HVSource")
            raise RuntimeError("Failed to connect with HVSource")
        try:
            self.safe_recover_vsrc()
        except Exception:
            logger.error("unable to connect with VSource")
        try:
            if self.config.get("use_environ"):
                self.discharge_decoupling()
        except Exception:
            logger.error("unable to connect with environment box (discharge decoupling)")
        try:
            self.safe_recover_matrix()
        except Exception:
            logger.error("unable to connect with Matrix")
            raise RuntimeError("Failed to connect with Matrix")

    def safe_finalize(self) -> None:
        try:
            self.safe_recover_hvsrc()
        except Exception:
            logger.error("unable to connect with HVSource")
        try:
            self.safe_recover_vsrc()
        except Exception:
            logger.error("unable to connect with VSource")
        try:
            self.safe_recover_matrix()
        except Exception:
            logger.error("unable to connect with: Matrix")
            raise RuntimeError("Failed to connect with Matrix")
        try:
            if self.config.get("use_environ"):
                self.station.set_test_led(False)
        except Exception:
            logger.error("unable to connect with environment box (test LED OFF)")

    def add_retry_overdrive(self, z: float) -> float:
        retry_contact_overdrive = abs(self.config.get("retry_contact_overdrive"))
        z = z + retry_contact_overdrive
        logger.info(" => applying re-contact overdrive: %g mm", retry_contact_overdrive)
        return z

    def safe_move_table(self, position) -> None:
        table_process = self.station.table_process
        if table_process.running and table_process.enabled:
            logger.info("Safe move table to %s", position)
            self.set_message("Moving table...")
            timeout = self.config.get("table_move_timeout")
            try:
                table_process.safe_absolute_move(*position).get(timeout=timeout)
                self.config.update({"table_position": table_process.get_cached_position()})
                self.set_message("Moving table... done.")
            except RequestTimeout as exc:
                raise TimeoutError(f"Table move timeout after {timeout} s...") from exc
            logger.info("Safe move table to %s... done.", position)

    def apply_contact_delay(self) -> None:
        contact_delay = abs(self.config.get("table_contact_delay"))
        if contact_delay > 0:
            logger.info("Applying contact delay: %s s", contact_delay)
            steps = 25
            contact_delay_fraction = contact_delay / steps
            self.set_message("Applying contact delay of {}...".format(format_metric(contact_delay, unit="s", decimals=1)))
            for step in range(steps):
                self.set_progress(step + 1, steps)
                time.sleep(contact_delay_fraction)

    def initialize(self) -> None:
        self.set_message("Initialize...")
        self.stop_requested = False
        try:
            self.safe_initialize()
        except Exception:
            self.set_message("Initialize... failed.")
            raise
        else:
            self.set_message("Initialize... done.")

    def process(self) -> None:
        item = self.sequence_item
        if isinstance(item, MeasurementTreeItem):
            MeasurementStrategy(self)(item)
        elif isinstance(item, ContactTreeItem):
            ContactStrategy(self)(item)
        elif isinstance(item, SampleTreeItem):
            SampleStrategy(self)(item)
        elif isinstance(item, SequenceRootTreeItem):
            SequenceStrategy(self)(item)
        else:
            raise TypeError(type(item))

    def finalize(self) -> None:
        self.set_message("Finalize...")
        try:
            self.safe_finalize()
        except Exception:
            self.set_message("Finalize... failed.")
            raise
        else:
            self.set_message("Finalize... done.")
        finally:
            self.stop_requested = False

    def __call__(self) -> None:
        try:
            try:
                self.initialize()
                self.process()
            finally:
                self.finalize()
        except Exception as exc:
            logger.exception(exc)
            self.failed.emit(exc)
            self.set_message("Measurement failed.")
        else:
            self.set_message("Measurement done.")
        finally:
            self.finished.emit()


class SequenceStrategy:
    """Strategy for samples sequence."""

    def __init__(self, worker) -> None:
        self.worker = worker

    def __call__(self, sequence_item) -> None:
        self.worker.set_message("Process samples...")
        # Check contact positions
        for sample_item in sequence_item.children():
            if sample_item.isEnabled():
                for contact_item in sample_item.children():
                    if contact_item.isEnabled():
                        if not contact_item.hasPosition():
                            raise RuntimeError(f"No contact position assigned for {contact_item.sample.name} -> {contact_item.name()}")
        for sample_item in sequence_item.children():
            if self.worker.stop_requested:
                break
            if not sample_item.isEnabled():
                continue
            if self.worker.stop_requested:
                self.worker.set_item_state(sample_item, contact_item.StoppedState)
                break
            SampleStrategy(self.worker)(sample_item)
        if self.worker.stop_requested:
            return
        move_to_after_position = self.worker.config.get("move_to_after_position")
        if move_to_after_position is not None:
            self.worker.safe_move_table(move_to_after_position)


class SampleStrategy:
    """Strategy for sample item."""

    def __init__(self, worker) -> None:
        self.worker = worker

    def __call__(self, sample_item) -> object:
        self.worker.set_message("Process sample...")
        self.worker.set_item_state(sample_item, sample_item.ProcessingState)
        # Check contact positions
        for contact_item in sample_item.children():
            if contact_item.isEnabled():
                if not contact_item.hasPosition():
                    raise RuntimeError(f"No contact position assigned for {contact_item.sample.name} -> {contact_item.name()}")
        results = []
        for contact_item in sample_item.children():
            if self.worker.stop_requested:
                break
            if not contact_item.isEnabled():
                continue
            if self.worker.stop_requested:
                self.worker.set_item_state(contact_item, contact_item.StoppedState)
                break
            result = ContactStrategy(self.worker)(contact_item)
            if result != sample_item.SuccessState:
                results.append(result)
        state = sample_item.ErrorState
        if self.worker.stop_requested:
            state = sample_item.StoppedState
        elif not results:
            state = sample_item.SuccessState
        self.worker.set_item_state(sample_item, state)
        if self.worker.stop_requested:
            return state
        move_to_after_position = self.worker.config.get("move_to_after_position")
        if move_to_after_position is not None:
            self.worker.safe_move_table(move_to_after_position)
        return state


class ContactStrategy:
    """Strategy for contact item."""

    def __init__(self, worker) -> None:
        self.worker = worker

    def __call__(self, contact_item) -> object:
        retry_contact_count = settings.retry_contact_count
        retry_measurement_count = settings.retry_measurement_count
        # Queue of measurements for the retry loops.
        measurement_items = [item for item in contact_item.children() if item.isEnabled()]
        # Auto retry table contact
        for retry_contact in range(retry_contact_count + 1):
            if not measurement_items:
                break
            if retry_contact:
                logger.info(f"Retry contact {retry_contact}/{retry_contact_count}...")
                self.worker.increment_item_recontact(contact_item)
            self.worker.set_message("Process contact...")
            self.worker.set_item_state(contact_item, contact_item.ProcessingState)
            logger.info(" => %s", contact_item.name())
            if self.worker.config.get("move_to_contact") and contact_item.hasPosition():
                x, y, z = contact_item.position
                # Add re-contact overdrive
                if retry_contact:
                    z = self.worker.add_retry_overdrive(z)
                # Move table to position
                self.worker.safe_move_table((x, y, z))
                self.worker.apply_contact_delay()
            # Auto retry measurement
            for retry_measurement in range(retry_measurement_count + 1):
                self.worker.set_item_state(contact_item, contact_item.ProcessingState)
                if retry_measurement:
                    logger.info(f"Retry measurement {retry_measurement}/{retry_measurement_count}...")
                measurement_items = self.process_measurement_sequence(measurement_items, retry_measurement)
                state = contact_item.ErrorState if measurement_items else contact_item.SuccessState
                if self.worker.stop_requested:
                    state = contact_item.StoppedState
                self.worker.set_item_state(contact_item, state)
                if not measurement_items:
                    break
        return contact_item.ErrorState if measurement_items else contact_item.SuccessState

    def process_measurement_sequence(self, measurement_items, retry_measurement) -> None:
        """Returns a list of failed measurement items."""
        prev_measurement_item = None
        failed_measurements = []
        for measurement_item in measurement_items:
            if self.worker.stop_requested:
                break
            if not measurement_item.isEnabled():
                continue
            if retry_measurement:
                self.worker.increment_item_remeasure(measurement_item)
            if self.worker.stop_requested:
                self.worker.set_item_state(measurement_item, measurement_item.StoppedState)
                break
            if prev_measurement_item:
                self.worker.hide_measurement_item(prev_measurement_item)
            try:
                MeasurementStrategy(self.worker)(measurement_item)
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error("%s: %s", measurement_item.name(), tb)
                logger.error("%s: %s", measurement_item.name(), exc)
                # TODO: for now only analysis errors trigger retries...
                if isinstance(exc, AnalysisError):
                    failed_measurements.append(measurement_item)
            prev_measurement_item = measurement_item
        if prev_measurement_item:
            self.worker.hide_measurement_item(prev_measurement_item)
        return failed_measurements


class MeasurementStrategy:
    """Strategy for measurement item."""

    def __init__(self, worker) -> None:
        self.worker = worker

    def __call__(self, measurement_item) -> None:
        self.worker.set_message("Process measurement...")
        state = measurement_item.ActiveState
        self.worker.reset_measurement_item(measurement_item)
        self.worker.set_item_state(measurement_item, state)
        self.worker.show_measurement_item(measurement_item)
        sample_name = measurement_item.contact.sample.name()
        sample_type = measurement_item.contact.sample.sampleType()
        sample_position = measurement_item.contact.sample.samplePositionLabel()
        sample_comment = measurement_item.contact.sample.comment()
        output_dir = self.worker.config.get("output_dir", ".")

        time.sleep(self.worker.config.get("before_measurement_delay"))

        sample_output_dir = os.path.join(output_dir, sample_name)
        if not os.path.exists(sample_output_dir):
            os.makedirs(sample_output_dir)

        # TODO
        timestamp = time.time()
        measurement_item.timestamp = timestamp  # TODO
        measurement = measurement_factory(measurement_item.type)(
            process=self.worker,
            measurement_parameters=measurement_item.parameters,
            measurement_default_parameters=measurement_item.default_parameters,
            timestamp=timestamp
        )
        measurement.set_meta("uuid", format(uuid.uuid4()))
        measurement.set_meta("sample_name", sample_name)
        measurement.set_meta("sample_type", sample_type)
        measurement.set_meta("sample_position", sample_position)
        measurement.set_meta("sample_comment", sample_comment)
        measurement.set_meta("contact_name", measurement_item.contact.name())
        measurement.set_meta("measurement_name", measurement_item.name())
        measurement.set_meta("measurement_type", measurement.type)
        measurement.set_meta("measurement_tags", measurement_item.tags())
        measurement.set_meta("table_position", tuple(self.worker.config.get("table_position") or []))
        measurement.set_meta("start_timestamp", timestamp_iso(timestamp))
        measurement.set_meta("operator", self.worker.config.get("operator", ""))
        measurement.set_meta("pqc_version", __version__)
        measurement.set_meta("analysis_pqc_version", analysis_pqc.__version__)

        write_logfiles = self.worker.config.get("write_logfiles")
        log_filename = self.create_filename(measurement_item, suffix=".log") if write_logfiles else None
        plot_filename = self.create_filename(measurement_item, suffix=".png")

        with LogFileHandler(log_filename):
            try:
                measurement.run(self.worker.station)
            except ResourceError as e:
                self.worker.set_message("Process... failed.")
                if isinstance(e.exc, pyvisa.errors.VisaIOError):
                    state = measurement_item.TimeoutState
                elif isinstance(e.exc, BrokenPipeError):
                    state = measurement_item.TimeoutState
                else:
                    state = measurement_item.ErrorState
                raise
            except ComplianceError:
                self.worker.set_message("Process... failed.")
                state = measurement_item.ComplianceState
                raise
            except AnalysisError:
                self.worker.set_message("Process... analysis failed.")
                state = measurement_item.AnalysisErrorState
                raise
            except Exception:
                self.worker.set_message("Process... failed.")
                state = measurement_item.ErrorState
                raise
            else:
                self.worker.set_message("Process... done.")
                if self.worker.stop_requested:
                    state = measurement_item.StoppedState
                else:
                    state = measurement_item.SuccessState
            finally:
                self.worker.set_item_state(measurement_item, state)
                self.worker.save_to_image.emit(measurement_item, plot_filename)
                self.worker.summary_pushed.emit({
                    "timestamp": measurement.timestamp,
                    "sample_name": sample_name,
                    "sample_type": sample_type,
                    "contact_name": measurement_item.contact.name(),
                    "measurement_name": measurement_item.name(),
                    "measurement_state": state,
                })
                if self.worker.config.get("serialize_json"):
                    with open(self.create_filename(measurement_item, suffix=".json"), "w") as fp:
                        serialize_json(measurement.data, fp)
                if self.worker.config.get("serialize_txt"):
                    # See https://docs.python.org/3/library/csv.html#csv.DictWriter
                    with open(self.create_filename(measurement_item, suffix=".txt"), "w", newline="") as fp:
                        serialize_txt(measurement.data, fp)

    def create_basename(self, measurement_item) -> str:
        """Return standardized measurement basename."""
        sample_name = measurement_item.contact.sample.name().strip()
        sample_type = measurement_item.contact.sample.sampleType().strip()
        contact_id = measurement_item.contact.id
        measurement_id = measurement_item.id
        iso_timestamp = make_iso(measurement_item.timestamp)
        return f"{sample_name}_{sample_type}_{contact_id}_{measurement_id}_{iso_timestamp}"

    def create_filename(self, measurement_item, suffix: str) -> None:
        filename = safe_filename(f"{self.create_basename(measurement_item)}{suffix}")
        output_dir = self.worker.config.get("output_dir", ".")
        sample_dir = safe_filename(measurement_item.contact.sample.name())
        return os.path.join(output_dir, sample_dir, filename)
