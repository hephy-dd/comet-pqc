import logging
import os
import time
import traceback
import uuid
from datetime import datetime

import pyvisa
from comet import safe_filename, make_iso
from comet.resource import ResourceError
import analysis_pqc

from . import __version__
from .measurements import measurement_factory
from .measurements.measurement import ComplianceError, serialize_json, serialize_txt
from .measurements.mixins import AnalysisError
from .view.sequence import GroupTreeItem, SampleTreeItem

__all__ = ["SequenceStrategy", "GroupStrategy", "SampleStrategy", "ContactStrategy", "MeasurementStrategy"]

logger = logging.getLogger(__name__)


def timestamp_iso(timestamp: float) -> str:
    """Returns start timestamp as ISO formatted string."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")


class LogFileWriter:
    """Context manager for log files."""

    FORMAT: str = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, filename=None) -> None:
        self.filename = filename
        self.handler = None
        self.logger = logging.getLogger()

    def create_path(self, filename: str) -> None:
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

    def create_handler(self, filename: str) -> logging.FileHandler:
        self.create_path(filename)
        handler = logging.FileHandler(filename=filename)
        handler.setFormatter(logging.Formatter(
            fmt=self.FORMAT,
            datefmt=self.DATE_FORMAT
        ))
        return handler

    def __enter__(self):
        if self.filename:
            self.handler = self.create_handler(self.filename)
            self.logger.addHandler(self.handler)
        return self

    def __exit__(self, *exc):
        if self.handler is not None:
            self.logger.removeHandler(self.handler)
        return False


class InitializeStrategy:
    """Strategy applied before a sequence."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self) -> None:
        try:
            if self.context.config.get("use_environ"):
                self.context.station.set_test_led(True)
        except Exception:
            logger.error("unable to connect with environment box (test LED ON)")
            raise
        try:
            self.context.safe_recover_hvsrc()
        except Exception:
            logger.error("unable to recover HVSource")
            raise RuntimeError("Failed to recover HVSource")
        try:
            self.context.safe_recover_vsrc()
        except Exception:
            logger.error("unable to recover VSource")
        try:
            if self.context.config.get("use_environ"):
                self.context.discharge_decoupling()
        except Exception:
            logger.error("unable to connect with environment box (discharge decoupling)")
        try:
            self.context.safe_recover_matrix()
        except Exception:
            logger.error("unable to recover Matrix")
            raise RuntimeError("Failed to recover Matrix")


class FinalizeStrategy:
    """Strategy applied after a sequence."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self) -> None:
        try:
            self.context.safe_recover_hvsrc()
        except Exception:
            logger.error("unable to recover HVSource")
        try:
            self.context.safe_recover_vsrc()
        except Exception:
            logger.error("unable to recover VSource")
        try:
            self.context.safe_recover_matrix()
        except Exception:
            logger.error("unable to connect with: Matrix")
            raise RuntimeError("Failed to recover Matrix")
        try:
            if self.context.config.get("use_environ"):
                self.context.station.set_test_led(False)
        except Exception:
            logger.error("unable to connect with environment box (test LED OFF)")


class SequenceStrategy:
    """Strategy for samples sequence."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self, sequence_item) -> None:
        self.context.set_message("Process samples...")
        self.validate(sequence_item)
        for sample_item in sequence_item.children():
            if self.context.stop_requested:
                break
            if not sample_item.isEnabled():
                continue
            if self.context.stop_requested:
                self.context.set_item_state(sample_item, sample_item.StoppedState)
                break
            if isinstance(sample_item,GroupTreeItem):
                GroupStrategy(self.context)(sample_item)
            elif isinstance(sample_item, SampleTreeItem):
                SampleStrategy(self.context)(sample_item)
        if self.context.stop_requested:
            return
        self.final_movement()

    def final_movement(self) -> None:
        move_to_after_position = self.context.config.get("move_to_after_position")
        if move_to_after_position is not None:
            self.context.safe_move_table(move_to_after_position)

    def validate(self, sequence_item) -> None:
        # Check contact positions
        for sample_item in sequence_item.children():
            if sample_item.isEnabled():
                if isinstance(sample_item, SampleTreeItem):
                    for contact_item in sample_item.children():
                        if contact_item.isEnabled():
                            if not contact_item.hasPosition():
                                self.context.set_item_state(sample_item, sample_item.ErrorState)
                                sample_name = contact_item.sample.name()
                                contact_name = contact_item.name()
                                raise RuntimeError(f"No contact position assigned for {sample_name} -> {contact_name}")
                elif isinstance(sample_item, GroupTreeItem):
                    self.validate(sample_item)


class GroupStrategy:
    """Strategy for group item."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self, group_item) -> object:
        self.context.set_message("Process group...")
        self.context.set_item_state(group_item, group_item.ProcessingState)
        results = []
        for child in group_item.children():
            if self.context.stop_requested:
                break
            if not child.isEnabled():
                continue
            if self.context.stop_requested:
                self.context.set_item_state(child, child.StoppedState)
                break
            if isinstance(child, GroupTreeItem):
                result = GroupStrategy(self.context)(child)
            else:
                result = SampleStrategy(self.context)(child)
            if result != group_item.SuccessState:
                results.append(result)
        state = group_item.ErrorState
        if self.context.stop_requested:
            state = group_item.StoppedState
        elif not results:
            state = group_item.SuccessState
        self.context.set_item_state(group_item, state)
        if self.context.stop_requested:
            return state
        return state


class SampleStrategy:
    """Strategy for sample item."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self, sample_item) -> object:
        self.context.set_message("Process sample...")
        self.context.set_item_state(sample_item, sample_item.ProcessingState)
        self.validate(sample_item)
        results = []
        for contact_item in sample_item.children():
            if self.context.stop_requested:
                break
            if not contact_item.isEnabled():
                continue
            if self.context.stop_requested:
                self.context.set_item_state(contact_item, contact_item.StoppedState)
                break
            result = ContactStrategy(self.context)(contact_item)
            if result != sample_item.SuccessState:
                results.append(result)
        state = sample_item.ErrorState
        if self.context.stop_requested:
            state = sample_item.StoppedState
        elif not results:
            state = sample_item.SuccessState
        self.context.set_item_state(sample_item, state)
        if self.context.stop_requested:
            return state
        self.final_movement()
        return state

    def final_movement(self) -> None:
        move_to_after_position = self.context.config.get("move_to_after_position")
        if move_to_after_position is not None:
            self.context.safe_move_table(move_to_after_position)

    def validate(self, sample_item) -> None:
        # Check contact positions
        for contact_item in sample_item.children():
            if contact_item.isEnabled():
                if not contact_item.hasPosition():
                    self.context.set_item_state(sample_item, sample_item.ErrorState)
                    sample_name = contact_item.sample.name()
                    contact_name = contact_item.name()
                    raise RuntimeError(f"No contact position assigned for {sample_name} -> {contact_name}")


class ContactStrategy:
    """Strategy for contact item."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self, contact_item) -> object:
        retry_contact_count = self.context.config.get("retry_contact_count", 0)
        retry_measurement_count = self.context.config.get("retry_measurement_count", 0)
        # Queue of measurements for the retry loops.
        measurement_items = [item for item in contact_item.children() if item.isEnabled()]
        # Auto retry table contact
        for retry_contact in range(retry_contact_count + 1):
            if not measurement_items:
                break
            if retry_contact:
                logger.info(f"Retry contact {retry_contact}/{retry_contact_count}...")
            self.context.set_message("Process contact...")
            self.context.set_item_state(contact_item, contact_item.ProcessingState)
            logger.info(" => %s", contact_item.name())
            self.move_to_contact(contact_item, retry_contact)
            # Auto retry measurement
            for retry_measurement in range(retry_measurement_count + 1):
                self.context.set_item_state(contact_item, contact_item.ProcessingState)
                if retry_measurement:
                    logger.info(f"Retry measurement {retry_measurement}/{retry_measurement_count}...")
                measurement_items = self.process_measurement_sequence(measurement_items)
                state = contact_item.ErrorState if measurement_items else contact_item.SuccessState
                if self.context.stop_requested:
                    state = contact_item.StoppedState
                self.context.set_item_state(contact_item, state)
                if not measurement_items:
                    break
        return contact_item.ErrorState if measurement_items else contact_item.SuccessState

    def move_to_contact(self, contact_item, retry_contact: int)-> None:
        if self.context.config.get("move_to_contact") and contact_item.hasPosition():
            x, y, z = contact_item.position
            # Add re-contact overdrive and offset
            if retry_contact:
                z = self.context.add_retry_overdrive(z)
                x, y = self.context.add_retry_offset(x, y)
            # Move table to position
            self.context.safe_move_table((x, y, z))
            self.context.apply_contact_delay()

    def process_measurement_sequence(self, measurement_items) -> list:
        """Returns a list of failed measurement items."""
        prev_measurement_item = None
        failed_measurements: list = []
        for measurement_item in measurement_items:
            if self.context.stop_requested:
                break
            if not measurement_item.isEnabled():
                continue
            if self.context.stop_requested:
                self.context.set_item_state(measurement_item, measurement_item.StoppedState)
                break
            if prev_measurement_item:
                self.context.hide_measurement_item(prev_measurement_item)
            try:
                MeasurementStrategy(self.context)(measurement_item)
            except Exception as exc:
                logger.error("%s: %s", measurement_item.name(), exc)
                logger.exception(exc)
                # TODO: for now only analysis errors trigger retries...
                if isinstance(exc, AnalysisError):
                    failed_measurements.append(measurement_item)
            prev_measurement_item = measurement_item
        if prev_measurement_item:
            self.context.hide_measurement_item(prev_measurement_item)
        return failed_measurements


class MeasurementStrategy:
    """Strategy for measurement item."""

    def __init__(self, context) -> None:
        self.context = context

    def __call__(self, measurement_item) -> None:
        self.context.set_message("Process measurement...")
        self.context.reset_measurement_item(measurement_item)
        self.context.set_item_state(measurement_item, measurement_item.ActiveState)
        self.context.show_measurement_item(measurement_item)
        sample_name = measurement_item.contact.sample.name()
        sample_type = measurement_item.contact.sample.sampleType()
        sample_position = measurement_item.contact.sample.samplePositionLabel()
        sample_comment = measurement_item.contact.sample.comment()
        output_dir = self.context.config.get("output_dir", ".")

        self.apply_before_measurement_delay()

        sample_output_dir = os.path.join(output_dir, sample_name)
        if not os.path.exists(sample_output_dir):
            os.makedirs(sample_output_dir)

        # TODO
        timestamp = time.time()
        measurement_item.timestamp = timestamp  # TODO
        measurement = measurement_factory(measurement_item.item_type)(
            process=self.context,
            measurement_parameters=measurement_item.parameters,
            measurement_default_parameters=measurement_item.default_parameters,
            timestamp=timestamp
        )
        meta = {
            "uuid": format(uuid.uuid4()),
            "sample_name": sample_name,
            "sample_type": sample_type,
            "sample_position": sample_position,
            "sample_comment": sample_comment,
            "contact_name": measurement_item.contact.name(),
            "measurement_name": measurement_item.name(),
            "measurement_type": measurement.type,
            "measurement_tags": measurement_item.tags(),
            "table_position": tuple(self.context.config.get("table_position") or []),
            "start_timestamp": timestamp_iso(timestamp),
            "operator": self.context.config.get("operator", ""),
            "pqc_version": __version__,
            "analysis_pqc_version": analysis_pqc.__version__,
        }
        for key, value in meta.items():
            measurement.set_meta(key, value)

        write_logfiles = self.context.config.get("write_logfiles")
        log_filename = self.create_filename(measurement_item, suffix=".log") if write_logfiles else None
        plot_filename = self.create_filename(measurement_item, suffix=".png")

        with LogFileWriter(log_filename):
            state = ""
            try:
                measurement.run(self.context.station)
            except ResourceError as e:
                self.context.set_message("Process... failed.")
                if isinstance(e.exc, pyvisa.errors.VisaIOError):
                    state = measurement_item.TimeoutState
                elif isinstance(e.exc, BrokenPipeError):
                    state = measurement_item.TimeoutState
                else:
                    state = measurement_item.ErrorState
                raise
            except ComplianceError:
                self.context.set_message("Process... failed.")
                state = measurement_item.ComplianceState
                raise
            except AnalysisError:
                self.context.set_message("Process... analysis failed.")
                state = measurement_item.AnalysisErrorState
                raise
            except Exception:
                self.context.set_message("Process... failed.")
                state = measurement_item.ErrorState
                raise
            else:
                self.context.set_message("Process... done.")
                if self.context.stop_requested:
                    state = measurement_item.StoppedState
                else:
                    state = measurement_item.SuccessState
            finally:
                self.context.set_item_state(measurement_item, state)
                self.context.save_to_image.emit(measurement_item, plot_filename)
                self.context.measurement_finished.emit({
                    "timestamp": measurement.timestamp,
                    "sample_name": sample_name,
                    "sample_type": sample_type,
                    "contact_name": measurement_item.contact.name(),
                    "measurement_name": measurement_item.name(),
                    "measurement_state": state,
                })
                if self.context.config.get("serialize_json"):
                    with open(self.create_filename(measurement_item, suffix=".json"), "w") as fp:
                        serialize_json(measurement.data, fp)
                if self.context.config.get("serialize_txt"):
                    # See https://docs.python.org/3/library/csv.html#csv.DictWriter
                    with open(self.create_filename(measurement_item, suffix=".txt"), "w", newline="") as fp:
                        serialize_txt(measurement.data, fp)

    def apply_before_measurement_delay(self) -> None:
        before_measurement_delay = self.context.config.get("before_measurement_delay", 0)
        if before_measurement_delay > 0:
            self.context.set_message(f"Applying before measurement delay: {before_measurement_delay:.3f} s ...")
            time.sleep(before_measurement_delay)

    def create_basename(self, measurement_item) -> str:
        """Return standardized measurement basename."""
        sample_name = measurement_item.contact.sample.name().strip()
        sample_type = measurement_item.contact.sample.sampleType().strip()
        contact_id = measurement_item.contact.id
        measurement_id = measurement_item.id
        iso_timestamp = make_iso(measurement_item.timestamp)
        return f"{sample_name}_{sample_type}_{contact_id}_{measurement_id}_{iso_timestamp}"

    def create_filename(self, measurement_item, suffix: str) -> str:
        filename = safe_filename(f"{self.create_basename(measurement_item)}{suffix}")
        output_dir = self.context.config.get("output_dir", ".")
        sample_dir = safe_filename(measurement_item.contact.sample.name())
        return os.path.join(output_dir, sample_dir, filename)
