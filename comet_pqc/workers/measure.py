import logging
import os
import time

from PyQt5 import QtCore

from ..core.functions import LinearRange
from ..core.request import RequestTimeout
from ..settings import settings
from ..strategy import InitializeStrategy, FinalizeStrategy, SequenceStrategy, SampleStrategy, ContactStrategy, MeasurementStrategy
from ..utils import format_metric
from ..view.sequence import (
    ContactTreeItem,
    MeasurementTreeItem,
    SequenceRootTreeItem,
    SampleTreeItem,
)

__all__ = ["MeasureWorker"]

logger = logging.getLogger(__name__)


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
        self.station.environ_process.discharge()
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
            x, y, z = position
            try:
                table_process.safe_absolute_move(x, y, z).get(timeout=timeout)
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
            InitializeStrategy(self)()
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
            FinalizeStrategy(self)()
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
