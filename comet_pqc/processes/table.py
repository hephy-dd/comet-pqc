"""Table control process."""

import logging
import queue
import threading
import time
import traceback

import comet
from comet.driver.corvus import Venus1
from comet.resource import ResourceMixin
from PyQt5 import QtCore

from comet_pqc.core.timer import Timer
from comet_pqc.utils import from_table_unit, to_table_unit

from ..core.position import Position
from ..core.request import Request
from ..settings import settings

__all__ = ["TableProcess"]

UNIT_MICROMETER: int = 1
UNIT_MILLIMETER: int = 2

AXIS_OFFSET: float = 2e9  # TODO
AXIS_NAMES: dict = {
    0: "X",
    1: "Y",
    2: "Z"
}

RETRIES: int = 180

logger = logging.getLogger(__name__)


class TableError(Exception):

    ...


class TableMachineError(Exception):

    ...


class TableCalibrationError(Exception):

    ...


class TableErrorHandler:
    """Error handler for table."""

    ERROR_MESSAGES = {
        1: "Internal error.",
        2: "Internal error.",
        3: "Internal error.",
        4: "Internal error.",
        1001: "Invalid parameter.",
        1002: "Not enough parameters on the stack.",
        1003: "Valid range of parameter is exceeded.",
        1007: "Valid range of parameter is exceeded.",
        1004: "Move stopped working, range should run over.",
        1008: "Not enough parameters on the stack.",
        1009: "Not enough space on the stack.",
        1010: "Not enough space on parameter memory.",
        1015: "Parameters outside of working range.",
        2000: "Unknown command."
    }

    MACHINE_ERROR_MESSAGES = {
        1: "Error memory overflow.",
        10: "Motor driver disabled or failing 12V power supply.",
        13: "Exceeded maximum positioning errors in closed loop.",
        23: "RS422 encoder error."
    }

    VALID_CALDONE = 3, 3, 3

    def __init__(self, context):
        self.context = context

    def handle_error(self, ignore=[]):
        """Handle table system error."""
        code = self.context.error
        if code and code not in ignore:
            message = self.ERROR_MESSAGES.get(code, "Unknown error code.")
            raise TableError(f"Table Error {code}: {message}")

    def handle_machine_error(self, ignore=[]):
        """Handle table machine error."""
        code = self.context.merror
        if code and code not in ignore:
            message = self.MACHINE_ERROR_MESSAGES.get(code, "Unknown machine error code.")
            raise TableMachineError(f"Table Machine Error {code}: {message}")

    def handle_calibration_error(self):
        """Handle table calibration error."""
        x, y, z = self.context.x, self.context.y, self.context.z
        caldone = x.caldone, y.caldone, z.caldone
        if caldone != self.VALID_CALDONE:
            raise TableCalibrationError("Table requires calibration.")


class SignalHandler(QtCore.QObject):

    message_changed = QtCore.pyqtSignal(str)
    progress_changed = QtCore.pyqtSignal(int, int)
    position_changed = QtCore.pyqtSignal(Position)
    caldone_changed = QtCore.pyqtSignal(Position)
    joystick_changed = QtCore.pyqtSignal(bool)
    relative_move_finished = QtCore.pyqtSignal()
    absolute_move_finished = QtCore.pyqtSignal()
    calibration_finished = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()


class TableProcess(comet.Process, ResourceMixin):
    """Table process base class."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        while self.running:
            logger.info("start serving table...")
            try:
                with self.resources.get("table") as resource:
                    context = Venus1(resource)
                    try:
                        self.initialize(context)
                        self.event_loop(context)
                    finally:
                        self.finalize(context)
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error("%s: %s", type(self).__name__, tb)
                logger.error("%s: %s", type(self).__name__, exc)
        logger.info("stopped serving table")

    def initialize(self, context):
        context.mode = 0
        context.joystick = False
        context.x.unit = UNIT_MICROMETER
        context.y.unit = UNIT_MICROMETER
        context.z.unit = UNIT_MICROMETER
        time.sleep(.250)  # temper

    def finalize(self, context):
        ...

    def event_loop(self, context):
        """Overwrite with custom table control sequence."""


class AlternateTableProcess(TableProcess):
    """Table control process."""

    update_interval = 1.0
    throttle_interval = .025

    maximum_z = 23.800

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.signal_handler = SignalHandler()
        self.message_changed = self.signal_handler.message_changed
        self.progress_changed = self.signal_handler.progress_changed
        self.position_changed = self.signal_handler.position_changed
        self.caldone_changed = self.signal_handler.caldone_changed
        self.joystick_changed = self.signal_handler.joystick_changed
        self.relative_move_finished = self.signal_handler.relative_move_finished
        self.absolute_move_finished = self.signal_handler.absolute_move_finished
        self.calibration_finished = self.signal_handler.calibration_finished
        self.stopped = self.signal_handler.stopped


        self._lock = threading.RLock()
        self._queue = queue.Queue()
        self._cached_position = float("nan"), float("nan"), float("nan")
        self._cached_caldone = float("nan"), float("nan"), float("nan")
        self._stop_event = threading.Event()
        self.enabled = False

    def async_request(self, target) -> Request:
        request = Request(target)
        self._queue.put_nowait(request)
        return request

    def get_identification(self) -> Request:
        def request(table):
            return table.identification
        return self.async_request(request)

    def get_caldone(self) -> Request:
        def request(table):
            return table.x.caldone, table.y.caldone, table.z.caldone
        return self.async_request(request)

    def stop_current_action(self):
        self._stop_event.set()

    def get_cached_position(self):
        return self._cached_position

    def get_cached_caldone(self):
        return self._cached_caldone

    def wait(self):
        with self._lock:
            return True

    def _get_position(self, table) -> Position:
        x, y, z = [from_table_unit(v) for v in table.pos]
        self._cached_position = x, y, z
        return Position(x, y, z)

    def _get_caldone(self, table) -> Position:
        x, y, z = table.x.caldone, table.y.caldone, table.z.caldone
        self._cached_caldone = x, y, z
        return Position(x, y, z)

    def status(self) -> Request:
        def request(table):
            self.position_changed.emit(self._get_position(table))
            self.caldone_changed.emit(self._get_caldone(table))
            self.joystick_changed.emit(table.joystick)
        return self.async_request(request)

    def position(self) -> Request:
        def request(table):
            self.position_changed.emit(self._get_position(table))
        return self.async_request(request)

    def caldone(self) -> Request:
        def request(table):
            self.caldone_changed.emit(self._get_caldone(table))
        return self.async_request(request)

    def joystick(self) -> Request:
        def request(table):
            self.joystick_changed.emit(table.joystick)
        return self.async_request(request)

    def enable_joystick(self, state) -> Request:
        def request(table):
            if state:
                x, y, z = settings.table_joystick_maximum_limits
            else:
                x, y, z = settings.table_probecard_maximum_limits()
            table.limit = (
                (0, to_table_unit(x)),
                (0, to_table_unit(y)),
                (0, to_table_unit(z)),
            )
            table.joystick = state
            limits = table.limit
            logger.info("updated table limits: %s mm", limits)
            self.joystick_changed.emit(table.joystick)
        return self.async_request(request)

    def relative_move(self, x, y, z) -> Request:
        """Relative move table.

        Emits following events:
         - position_changed
         - relative_move_finished
        """
        def request(table):
            error_handler = TableErrorHandler(table)

            self.message_changed.emit(f"moving table relative to x={x:.3f}, y={y:.3f}, z={z:.3f} mm")
            table.rmove(
                to_table_unit(x),
                to_table_unit(y),
                to_table_unit(z)
            )

            error_handler.handle_machine_error()
            error_handler.handle_error()
            error_handler.handle_calibration_error()

            self.position_changed.emit(self._get_position(table))
            self.relative_move_finished.emit()
            self.message_changed.emit("Ready")
        return self.async_request(request)

    def relative_move_vector(self, vector, delay=0.0) -> Request:
        """Relative move table along a given vector.

        Emits following events:
         - position_changed
         - relative_move_finished
        """
        def request(table):
            error_handler = TableErrorHandler(table)

            for x, y, z in vector:
                self.message_changed.emit(f"moving table relative to x={x:.3f}, y={y:.3f}, z={z:.3f} mm")
                table.rmove(
                    to_table_unit(x),
                    to_table_unit(y),
                    to_table_unit(z)
                )

                error_handler.handle_machine_error()
                error_handler.handle_error()
                error_handler.handle_calibration_error()

                self.position_changed.emit(self._get_position(table))

                time.sleep(delay)

            self.relative_move_finished.emit()
            self.message_changed.emit("Ready")
        return self.async_request(request)

    def safe_absolute_move(self, x, y, z) -> Request:
        """Safely move to absolute position while moving X/Y axis at zero Z.
         - move Z down to zero
         - move X and Y
         - move Z up

        Emits following events:
        - position_changed
        - caldone_changed
        - absolute_move_finished
        """
        position = Position(to_table_unit(x), to_table_unit(y), to_table_unit(z))

        def request(table):
            self._stop_event.clear()
            self.message_changed.emit("Moving...")

            retries = RETRIES
            delay = 1.0

            error_handler = TableErrorHandler(table)

            error_handler.handle_machine_error()
            error_handler.handle_error()
            error_handler.handle_calibration_error()

            def handle_abort():
                if self._stop_event.is_set():
                    self.progress_changed.emit(0, 0)
                    self.message_changed.emit("Moving aborted.")
                    raise comet.StopRequest()

            def update_status(x, y, z):
                x, y, z = [from_table_unit(v) for v in (x, y, z)]
                self._cached_position = x, y, z
                self.position_changed.emit(Position(x, y, z))

            def update_caldone():
                x, y, z = table.x.caldone, table.y.caldone, table.z.caldone
                self.caldone_changed.emit(Position(x, y, z))

            handle_abort()
            update_caldone()

            self.progress_changed.emit(1, 4)
            self.message_changed.emit("Retreating Z axis...")

            # Moving into limit switch generates error 1004
            table.rmove(0, 0, -AXIS_OFFSET)
            for i in range(retries):
                handle_abort()
                current_pos = table.pos
                update_status(*current_pos)
                if current_pos[2] == 0:
                    break
                time.sleep(delay)
            current_pos = table.pos
            if current_pos[2] != 0:
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")
            # Clear error 1004
            error_handler.handle_error(ignore=[1004])

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(2, 4)
            self.message_changed.emit("Move X Y axes...")
            table.move(position.x, position.y, 0)
            for i in range(retries):
                handle_abort()
                current_pos = table.pos
                update_status(*current_pos)
                if current_pos[:2] == (position.x, position.y):
                    break
                time.sleep(delay)
            current_pos = table.pos
            if current_pos[:2] != (position.x, position.y):
                raise RuntimeError(f"failed to absolute move, current pos: {current_pos}")

            self.progress_changed.emit(3, 4)
            self.message_changed.emit("Move up Z axis...")
            table.rmove(0, 0, position.z)
            for i in range(retries):
                handle_abort()
                current_pos = table.pos
                update_status(*current_pos)
                if current_pos[2] >= position.z:
                    break
                time.sleep(delay)
            current_pos = table.pos
            if current_pos != (position.x, position.y, position.z):
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")

            handle_abort()
            update_caldone()
            update_status(*table.pos)

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(7, 7)
            self.message_changed.emit("Movement successful.")
            update_caldone()

            self.absolute_move_finished.emit()
        return self.async_request(request)

    def calibrate_table(self) -> Request:
        def request(table):
            self._stop_event.clear()
            self.message_changed.emit("Calibrating...")
            retries = RETRIES
            delay = 1.0
            axes = table.x, table.y, table.z

            error_handler = TableErrorHandler(table)

            def handle_abort():
                if self._stop_event.is_set():
                    self.progress_changed.emit(0, 0)
                    self.message_changed.emit("Calibration aborted.")
                    raise comet.StopRequest()

            def update_status(x, y, z):
                x, y, z = [from_table_unit(v) for v in (x, y, z)]
                self._cached_position = x, y, z
                self.position_changed.emit(Position(x, y, z))

            def update_caldone():
                x, y, z = table.x.caldone, table.y.caldone, table.z.caldone
                self.caldone_changed.emit(Position(x, y, z))

            def ncal(axis):
                index = axes.index(axis)
                logger.info("ncal %s...", AXIS_NAMES.get(index))
                axis.ncal()
                for i in range(retries + 1):
                    handle_abort()
                    # Axis reached origin?
                    current_pos = table.pos
                    update_status(*current_pos)
                    if current_pos[index] == 0.0:
                        logger.info("ncal %s... done.", AXIS_NAMES.get(index))
                        break
                    time.sleep(delay)
                return i < retries

            def nrm(axis):
                index = axes.index(axis)
                logger.info("nrm %s...", AXIS_NAMES.get(index))
                axis.nrm()
                reference_pos = table.pos
                update_status(*reference_pos)
                time.sleep(delay)
                for i in range(retries + 1):
                    handle_abort()
                    current_pos = table.pos
                    update_status(*current_pos)
                    # Axis stopped moving?
                    if reference_pos[index] == current_pos[index]:
                        logger.info("nrm %s... done.", AXIS_NAMES.get(index))
                        break
                    reference_pos = current_pos
                    time.sleep(delay)
                return i < retries

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(0, 7)
            self.message_changed.emit("Retreating Z axis...")
            if table.z.enabled:
                if not ncal(table.z):
                    raise RuntimeError("failed retreating Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(1, 7)
            self.message_changed.emit("Calibrating Y axis...")
            if table.y.enabled:
                if not ncal(table.y):
                    raise RuntimeError("failed to calibrate Y axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(2, 7)
            self.message_changed.emit("Calibrating X axis...")
            if table.x.enabled:
                if not ncal(table.x):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(3, 7)
            self.message_changed.emit("Range measure X axis...")
            if table.x.enabled:
                if not nrm(table.x):
                    raise RuntimeError("failed to ragne measure X axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(4, 7)
            self.message_changed.emit("Range measure Y axis...")
            if table.y.enabled:
                if not nrm(table.y):
                    raise RuntimeError("failed to range measure Y axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            # Moving into limit switches generates error 1004
            table.rmove(-AXIS_OFFSET, -AXIS_OFFSET, 0)
            for i in range(retries):
                handle_abort()
                current_pos = table.pos
                update_status(*current_pos)
                if current_pos[:2] == (0, 0):
                    break
                time.sleep(delay)
            # Verify table position
            current_pos = table.pos
            if current_pos[:2] != (0, 0):
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")
            # Clear error 1004
            error_handler.handle_error(ignore=[1004])

            # Move X=52.000 mm before Z calibration to avoid collisions
            x_offset = 52000
            y_offset = 0
            table.rmove(x_offset, y_offset, 0)
            for i in range(retries):
                handle_abort()
                current_pos = table.pos
                update_status(*current_pos)
                if current_pos[:2] == (x_offset, y_offset):
                    break
                time.sleep(delay)
            # Verify table position
            current_pos = table.pos
            if current_pos[:2] != (x_offset, y_offset):
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(5, 7)
            self.message_changed.emit("Calibrating Z axis minimum...")
            if table.z.enabled:
                if not ncal(table.z):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(6, 7)
            self.message_changed.emit("Range measure Z axis maximum...")
            if table.z.enabled:
                if not nrm(table.z):
                    raise RuntimeError("failed to range measure Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            table.move(0, 0, 0)
            for i in range(retries):
                handle_abort()
                current_pos = table.pos
                update_status(*current_pos)
                if current_pos == (0, 0, 0):
                    break
                time.sleep(delay)
            # Verify table position
            current_pos = table.pos
            if current_pos != (0, 0, 0):
                raise RuntimeError(f"failed to absolute move, current pos: {current_pos}")

            update_status(*current_pos)
            update_caldone()

            error_handler.handle_machine_error()
            error_handler.handle_error()

            self.progress_changed.emit(7, 7)
            self.message_changed.emit("Calibration successful.")

            self.calibration_finished.emit()
        return self.async_request(request)

    def event_loop(self, context):
        t = Timer()
        while self.running:
            with self._lock:
                if self.enabled:
                    try:
                        request = self._queue.get(timeout=0.025)
                    except queue.Empty:
                        ...
                    else:
                        try:
                            request(context)
                        except comet.StopRequest:
                            self.message_changed.emit("Stopped.")
                            self.stopped.emit()
                        except Exception as exc:
                            self.message_changed.emit(format(exc))
                            tb = traceback.format_exc()
                            self.emit("failed", exc, tb)
                            self.stopped.emit()
                            raise
                        finally:
                            self._queue.task_done()
                    if t.delta() > self.update_interval:
                        self.position()
                        self.caldone()
                        self.joystick()
                        t.reset()
            time.sleep(self.throttle_interval)
