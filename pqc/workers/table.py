"""Table control process."""

import logging
import threading
import time
import traceback
import queue

from PyQt5 import QtCore

import comet

from pqc.utils import from_table_unit, to_table_unit
from pqc.core.timer import Timer

from ..core.request import Request
from ..core.position import Position
from ..settings import settings

__all__ = ["TableWorker"]


AXIS_OFFSET: float = 2e9  # TODO
AXIS_NAMES: dict = {
    0: "X",
    1: "Y",
    2: "Z"
}

RETRIES: int = 180

logger = logging.getLogger(__name__)


class TableWorker(comet.Process):
    """Table process base class."""

    def __init__(self, table, **kwargs):
        super().__init__(**kwargs)
        self.table = table

    def run(self):
        while self.running:
            logger.info("start serving table...")
            try:
                with self.table.resource:
                    try:
                        self.initialize(self.table)
                        self.event_loop(self.table)
                    finally:
                        self.finalize(self.table)
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error("%s: %s", type(self).__name__, tb)
                logger.error("%s: %s", type(self).__name__, exc)
            time.sleep(1.0)
        logger.info("stopped serving table")

    def initialize(self, table):
        self.table.configure()

    def finalize(self, table):
        ...

    def event_loop(self, table):
        """Overwrite with custom table control sequence."""

    def set_message(self, message: str) -> None:
        self.emit("message", message)

    def set_progress(self, value: int, maximum: int) -> None:
        self.emit("progress_changed", value, maximum)

    def set_position(self, position: Position) -> None:
        self.emit("position_changed", position)

    def set_caldone(self, position: Position) -> None:
        self.emit("caldone_changed", position)

    def set_joystick_enabled(self, enabled: bool) -> None:
        self.emit("joystick_changed", enabled)


class AlternateTableWorker(TableWorker):
    """Table control process."""

    update_interval = 1.0
    throttle_interval = .025

    maximum_z = 23.800

    def __init__(self, message_changed=None, progress_changed=None,
                 position_changed=None, caldone_changed=None, joystick_changed=None,
                 relative_move_finished=None, absolute_move_finished=None,
                 calibration_finished=None, stopped=None, **kwargs):
        super().__init__(**kwargs)
        self._lock = threading.RLock()
        self._queue = queue.Queue()
        self._cached_position = float("nan"), float("nan"), float("nan")
        self._cached_caldone = float("nan"), float("nan"), float("nan")
        self._stop_event = threading.Event()
        self.enabled = False
        self.message_changed = message_changed
        self.progress_changed = progress_changed
        self.position_changed = position_changed
        self.caldone_changed = caldone_changed
        self.joystick_changed = joystick_changed
        self.relative_move_finished = relative_move_finished
        self.absolute_move_finished = absolute_move_finished
        self.calibration_finished = calibration_finished
        self.stopped = stopped

    def async_request(self, target) -> Request:
        request = Request(target)
        self._queue.put_nowait(request)
        return request

    def get_identification(self) -> Request:
        def request(table):
            return table.identify()
        return self.async_request(request)

    def is_calibrated(self) -> Request:
        def request(table):
            return table.is_calibrated
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
        x, y, z = [from_table_unit(v) for v in table.position]
        self._cached_position = x, y, z
        return Position(x, y, z)

    def _get_caldone(self, table) -> Position:
        x, y, z = table.caldone
        self._cached_caldone = x, y, z
        return Position(x, y, z)

    def status(self) -> Request:
        def request(table):
            self.set_position(self._get_position(table))
            self.set_caldone(self._get_caldone(table))
            self.set_joystick_enabled(table.joystick_enabled)
        return self.async_request(request)

    def position(self) -> Request:
        def request(table):
            self.set_position(self._get_position(table))
        return self.async_request(request)

    def caldone(self) -> Request:
        def request(table):
            self.set_caldone(self._get_caldone(table))
        return self.async_request(request)

    def joystick(self) -> Request:
        def request(table):
            self.set_joystick_enabled(table.joystick_enabled)
        return self.async_request(request)

    def enable_joystick(self, state) -> Request:
        def request(table):
            if state:
                x, y, z = settings.table_joystick_maximum_limits
            else:
                x, y, z = settings.table_probecard_maximum_limits
            table.set_limit((
                (0, to_table_unit(x)),
                (0, to_table_unit(y)),
                (0, to_table_unit(z)),
            ))
            table.joystick_enabled = state
            limits = table.limit
            logger.info("updated table limits: %s mm", limits)
            self.set_joystick_enabled(table.joystick_enabled)
        return self.async_request(request)

    def relative_move(self, x, y, z) -> Request:
        """Relative move table.

        Emits following events:
         - position_changed
         - relative_move_finished
        """
        def request(table):
            self.set_message(f"moving table relative to x={x:.3f}, y={y:.3f}, z={z:.3f} mm")
            table.move_relative((
                to_table_unit(x),
                to_table_unit(y),
                to_table_unit(z)
            ))

            table.handle_machine_error()
            table.handle_error()
            table.handle_calibration_error()

            self.set_position(self._get_position(table))
            self.emit("relative_move_finished")
            self.set_message("Ready")
        return self.async_request(request)

    def relative_move_vector(self, vector, delay=0.0) -> Request:
        """Relative move table along a given vector.

        Emits following events:
         - position_changed
         - relative_move_finished
        """
        def request(table):
            for x, y, z in vector:
                self.set_message(f"moving table relative to x={x:.3f}, y={y:.3f}, z={z:.3f} mm")
                table.move_relative((
                    to_table_unit(x),
                    to_table_unit(y),
                    to_table_unit(z)
                ))

                table.handle_machine_error()
                table.handle_error()
                table.handle_calibration_error()

                self.set_position(self._get_position(table))

                time.sleep(delay)

            self.emit("relative_move_finished")
            self.set_message("Ready")
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
            self.set_message("Moving...")

            retries = RETRIES
            delay = 1.0

            table.handle_machine_error()
            table.handle_error()
            table.handle_calibration_error()

            def handle_abort():
                if self._stop_event.is_set():
                    self.set_progress(0, 0)
                    self.set_message("Moving aborted.")
                    raise comet.StopRequest()

            def update_status(x, y, z):
                x, y, z = [from_table_unit(v) for v in (x, y, z)]
                self._cached_position = x, y, z
                self.set_position(Position(x, y, z))

            def update_caldone():
                x, y, z = table.caldone
                self.set_caldone(Position(x, y, z))

            handle_abort()
            update_caldone()

            self.set_progress(1, 4)
            self.set_message("Retreating Z axis...")

            # Moving into limit switch generates error 1004
            table.move_relative((0, 0, -AXIS_OFFSET))
            for i in range(retries):
                handle_abort()
                current_pos = table.position
                update_status(*current_pos)
                if current_pos[2] == 0:
                    break
                time.sleep(delay)
            current_pos = table.position
            if current_pos[2] != 0:
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")
            # Clear error 1004
            table.handle_error(ignore=[1004])

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(2, 4)
            self.set_message("Move X Y axes...")
            table.move_absolute((position.x, position.y, 0))
            for i in range(retries):
                handle_abort()
                current_pos = table.position
                update_status(*current_pos)
                if current_pos[:2] == (position.x, position.y):
                    break
                time.sleep(delay)
            current_pos = table.position
            if current_pos[:2] != (position.x, position.y):
                raise RuntimeError(f"failed to absolute move, current pos: {current_pos}")

            self.set_progress(3, 4)
            self.set_message("Move up Z axis...")
            table.move_relative((0, 0, position.z))
            for i in range(retries):
                handle_abort()
                current_pos = table.position
                update_status(*current_pos)
                if current_pos[2] >= position.z:
                    break
                time.sleep(delay)
            current_pos = table.position
            if current_pos != (position.x, position.y, position.z):
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")

            handle_abort()
            update_caldone()
            update_status(*table.position)

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(7, 7)
            self.set_message("Movement successful.")
            update_caldone()

            self.emit("absolute_move_finished")
        return self.async_request(request)

    def calibrate_table(self) -> Request:
        def request(table):
            self._stop_event.clear()
            self.set_message("Calibrating...")
            retries = RETRIES
            delay = 1.0
            axes = table.axes

            def handle_abort():
                if self._stop_event.is_set():
                    self.set_progress(1, 1)
                    self.set_message("Calibration aborted.")
                    raise comet.StopRequest()

            def update_status(x, y, z):
                x, y, z = [from_table_unit(v) for v in (x, y, z)]
                self._cached_position = x, y, z
                self.set_position(Position(x, y, z))

            def update_caldone():
                x, y, z = table.caldone
                self.set_caldone(Position(x, y, z))

            def ncal(axis):
                index = axes.index(axis)
                logger.info("ncal %s...", AXIS_NAMES.get(index))
                axis.ncal()
                for i in range(retries + 1):
                    handle_abort()
                    # Axis reached origin?
                    current_pos = table.position
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
                reference_pos = table.position
                update_status(*reference_pos)
                time.sleep(delay)
                for i in range(retries + 1):
                    handle_abort()
                    current_pos = table.position
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

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(0, 7)
            self.set_message("Retreating Z axis...")
            if table.table.z.enabled:
                if not ncal(table.table.z):
                    raise RuntimeError("failed retreating Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(1, 7)
            self.set_message("Calibrating Y axis...")
            if table.table.y.enabled:
                if not ncal(table.table.y):
                    raise RuntimeError("failed to calibrate Y axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(2, 7)
            self.set_message("Calibrating X axis...")
            if table.table.x.enabled:
                if not ncal(table.table.x):
                    raise RuntimeError("failed to calibrate X axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(3, 7)
            self.set_message("Range measure X axis...")
            if table.table.x.enabled:
                if not nrm(table.table.x):
                    raise RuntimeError("failed to ragne measure X axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(4, 7)
            self.set_message("Range measure Y axis...")
            if table.table.y.enabled:
                if not nrm(table.table.y):
                    raise RuntimeError("failed to range measure Y axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            # Moving into limit switches generates error 1004
            table.relative_move((-AXIS_OFFSET, -AXIS_OFFSET, 0))
            for i in range(retries):
                time.sleep(delay)
                if not table.is_moving():
                    break
                handle_abort()
                update_status(*table.position)
            # Verify table position
            current_pos = table.position
            if current_pos[:2] != (0, 0):
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")
            # Clear error 1004
            table.handle_error(ignore=[1004])

            # Move X=52.000 mm before Z calibration to avoid collisions
            x_offset = 52000
            y_offset = 0
            table.relative_move((x_offset, y_offset, 0))
            for i in range(retries):
                time.sleep(delay)
                if not table.is_moving():
                    break
                handle_abort()
                update_status(*table.position)
            # Verify table position
            current_pos = table.position
            if current_pos[:2] != (x_offset, y_offset):
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(5, 7)
            self.set_message("Calibrating Z axis minimum...")
            if table.table.z.enabled:
                if not ncal(table.table.z):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(6, 7)
            self.set_message("Range measure Z axis maximum...")
            if table.table.z.enabled:
                if not nrm(table.table.z):
                    raise RuntimeError("failed to range measure Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            # Move Z axis down
            x_offset = 52000
            y_offset = 0
            table.move_absolute((x_offset, y_offset, 0))
            for i in range(retries):
                time.sleep(delay)
                if not table.is_moving():
                    break
                handle_abort()
                update_status(*table.position)
            # Verify table position
            current_pos = table.position
            if current_pos[2] != 0:
                raise RuntimeError(f"failed to relative move, current pos: {current_pos}")

            handle_abort()
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            # Move to default position
            table.move_absolute(0, 0, 0)
            for i in range(retries):
                time.sleep(delay)
                if not table.is_moving():
                    break
                handle_abort()
                update_status(*table.position)
            # Verify table position
            current_pos = table.position
            if current_pos != (0, 0, 0):
                raise RuntimeError(f"failed to absolute move, current pos: {current_pos}")

            update_status(*current_pos)
            update_caldone()

            table.handle_machine_error()
            table.handle_error()

            self.set_progress(7, 7)
            self.set_message("Calibration successful.")

            self.emit("calibration_finished")
        return self.async_request(request)

    def event_loop(self, table):
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
                            request(table)
                        except comet.StopRequest:
                            self.set_message("Stopped.")
                            self.emit("stopped")
                        except Exception as exc:
                            self.set_message(exc)
                            tb = traceback.format_exc()
                            self.emit("failed", exc, tb)
                            self.emit("stopped")
                            raise
                        finally:
                            self._queue.task_done()
                    if t.delta() > self.update_interval:
                        self.position()
                        self.caldone()
                        self.joystick()
                        t.reset()
            time.sleep(self.throttle_interval)
