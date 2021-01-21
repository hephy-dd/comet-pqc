import logging
import time
import threading
import traceback

import comet
from comet.resource import ResourceMixin
from comet.driver.corvus import Venus1

from comet_pqc.utils import format_table_unit, from_table_unit, to_table_unit

UNIT_MICROMETER = 1
UNIT_MILLIMETER = 2

AXIS_OFFSET = 2e9 # TODO
AXIS_NAMES = {
    0: "X",
    1: "Y",
    2: "Z"
}

RETRIES = 180

class TableError(Exception): pass

class TableMachineError(Exception): pass

class TableCalibrationError(Exception): pass

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

class TableProcess(comet.Process, ResourceMixin):
    """Table process base class."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        while self.running:
            logging.info("start serving table...")
            try:
                with self.resources.get('table') as resource:
                    table = Venus1(resource)
                    table.mode = 0
                    table.joystick = False
                    table.x.unit = UNIT_MICROMETER
                    table.y.unit = UNIT_MICROMETER
                    table.z.unit = UNIT_MICROMETER
                    time.sleep(.250)
                    self.event_loop(table)
            except Exception as exc:
                tb = traceback.format_exc()
                logging.error("%s: %s", type(self).__name__, tb)
                logging.error("%s: %s", type(self).__name__, exc)
        logging.info("stopped serving table.")

    def event_loop(self, table):
        """Overwrite with custom table control sequence."""


"""Table control process."""

import comet
import time
import threading
import random
import logging

def async_request(method):
    def async_request(self, *args, **kwargs):
        self._async_request(lambda context: method(self, context, *args, **kwargs))
    return async_request

class AlternateTableProcess(TableProcess):
    """Table control process."""

    update_interval = 1.0
    throttle_interval = .025

    maximum_z = 23.800

    def __init__(self, message_changed=None, progress_changed=None,
                 position_changed=None, caldone_changed=None,
                 relative_move_finished=None, absolute_move_finished=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.__lock = threading.RLock()
        self.__queue = []
        self.message_changed = message_changed
        self.progress_changed = progress_changed
        self.position_changed = position_changed
        self.caldone_changed = caldone_changed
        self.relative_move_finished = relative_move_finished
        self.absolute_move_finished = absolute_move_finished

    def wait(self):
        with self.__lock:
            return True

    def _async_request(self, request):
        self.__queue.append(request)

    @async_request
    def position(self, table):
        x, y, z = [from_table_unit(v) for v in table.pos]
        self.emit('position_changed', x, y, z)

    @async_request
    def caldone(self, table):
        x, y, z = table.x.caldone, table.y.caldone, table.z.caldone
        self.emit('caldone_changed', x, y, z)

    @async_request
    def relative_move(self, table, x, y, z):
        error_handler = TableErrorHandler(table)

        # error_handler.handle_machine_error()
        # error_handler.handle_error()
        # error_handler.handle_calibration_error()

        self.emit("message_changed", f"moving table relative to x={x:.3f}, y={y:.3f}, z={z:.3f} mm")
        table.rmove(
            to_table_unit(x),
            to_table_unit(y),
            to_table_unit(z)
        )

        error_handler.handle_machine_error()
        error_handler.handle_error()
        error_handler.handle_calibration_error()

        x, y, z = table.pos
        self.emit('position_changed', from_table_unit(x), from_table_unit(y), from_table_unit(z))
        self.emit('relative_move_finished')
        self.emit("message_changed", "Ready")

    @async_request
    def absolute_move(self, table, x, y, z):
        self.set("z_warning", False)
        self.emit("message_changed", "Moving...")
        z_origin = z
        x = to_table_unit(x)
        y = to_table_unit(y)
        target_z = min(to_table_unit(z), to_table_unit(self.get('z_limit', self.maximum_z)))

        retries = RETRIES
        delay = 1.0

        error_handler = TableErrorHandler(table)

        error_handler.handle_machine_error()
        error_handler.handle_error()
        error_handler.handle_calibration_error()

        def handle_abort():
            if not self.running:
                self.emit("progress_changed", 0, 0)
                self.emit("message_changed", "Moving aborted.")
                raise comet.StopRequest()

        def update_status(x, y, z):
            x, y, z = [from_table_unit(v) for v in (x, y, z)]
            self.emit("message_changed", "Table x={}, y={}, z={} mm".format(x, y, z))
            self.emit('position_changed', x, y, z)

        def update_caldone():
            self.emit('caldone_changed', table.x.caldone, table.y.caldone, table.z.caldone)

        handle_abort()
        update_caldone()

        self.emit("progress_changed", 1, 4)
        self.emit("message_changed", "Retreating Z axis...")

        # Moving into limit switch generates error 1004
        table.rmove(0, 0, -AXIS_OFFSET)
        for i in range(retries):
            handle_abort()
            pos = table.pos
            update_status(*pos)
            if pos[2] == 0:
                break
            time.sleep(delay)
        if pos[2] != 0:
            raise RuntimeError(f"failed to relative move, current pos: {pos}")
        # Clear error 1004
        error_handler.handle_error(ignore=[1004])

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 2, 4)
        self.emit("message_changed", "Move X Y axes...")
        table.move(x, y, 0)
        for i in range(retries):
            handle_abort()
            pos = table.pos
            update_status(*pos)
            if pos[:2] == (x, y):
                break
            time.sleep(delay)
        if pos[:2] != (x, y):
            raise RuntimeError(f"failed to absolute move, current pos: {pos}")

        self.emit("progress_changed", 3, 4)
        self.emit("message_changed", "Move up Z axis...")
        table.rmove(0, 0, target_z)
        for i in range(retries):
            handle_abort()
            pos = table.pos
            update_status(*pos)
            if pos[2] >= target_z:
                break
            time.sleep(delay)
        if pos != (x, y, target_z):
            raise RuntimeError(f"failed to relative move, current pos: {pos}")

        handle_abort()
        update_caldone()
        update_status(*table.pos)

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 7, 7)
        self.emit("message_changed", "Movement successful.")

        self.set("z_warning", z_origin > z)

        x, y, z = table.x.caldone, table.y.caldone, table.z.caldone
        self.emit('caldone_changed', x, y, z)

        self.emit('absolute_move_finished')

    @async_request
    def calibarte_table(self, table):
        self.emit("message_changed", "Calibrating...")
        retries = RETRIES
        delay = 1.0
        axes = table.x, table.y, table.z

        error_handler = TableErrorHandler(table)

        def handle_abort():
            if not self.running:
                self.emit("progress_changed", 0, 0)
                self.emit("message_changed", "Calibration aborted.")
                raise comet.StopRequest()

        def update_status(x, y, z):
            x, y, z = [from_table_unit(v) for v in (x, y, z)]
            self.emit("message_changed", "Table x={}, y={}, z={} mm".format(x, y, z))
            self.emit('position_changed', x, y, z)

        def update_caldone():
            self.emit('caldone', table.x.caldone, table.y.caldone, table.z.caldone)

        def ncal(axis):
            index = axes.index(axis)
            logging.info("ncal %s...", AXIS_NAMES.get(index))
            axis.ncal()
            for i in range(retries + 1):
                handle_abort()
                update_status()
                # Axis reached origin?
                pos = table.pos
                update_status(*pos)
                if pos[index] == 0.0:
                    logging.info("ncal %s... done.", AXIS_NAMES.get(index))
                    break
                time.sleep(delay)
            return i < retries

        def nrm(axis):
            index = axes.index(axis)
            logging.info("nrm %s...", AXIS_NAMES.get(index))
            axis.nrm()
            pos = table.pos
            time.sleep(delay)
            for i in range(retries + 1):
                handle_abort()
                pos = table.pos
                update_status(*pos)
                # Axis stopped moving?
                if pos[index] == pos[index]:
                    logging.info("nrm %s... done.", AXIS_NAMES.get(index))
                    break
                time.sleep(delay)
                pos = table.pos
            return i < retries

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 0, 7)
        self.emit("message_changed", "Retreating Z axis...")
        if table.z.enabled:
            if not ncal(table.z):
                raise RuntimeError("failed retreating Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 1, 7)
        self.emit("message_changed", "Calibrating Y axis...")
        if table.y.enabled:
            if not ncal(table.y):
                raise RuntimeError("failed to calibrate Y axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 2, 7)
        self.emit("message_changed", "Calibrating X axis...")
        if table.x.enabled:
            if not ncal(table.x):
                raise RuntimeError("failed to calibrate Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 3, 7)
        self.emit("message_changed", "Range measure X axis...")
        if table.x.enabled:
            if not nrm(table.x):
                raise RuntimeError("failed to ragne measure X axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 4, 7)
        self.emit("message_changed", "Range measure Y axis...")
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
            pos = table.pos
            update_status(*pos)
            if pos[:2] == (0, 0):
                break
            time.sleep(delay)
        if pos[:2] != (0, 0):
            raise RuntimeError(f"failed to relative move, current pos: {pos}")
        # Clear error 1004
        error_handler.handle_error(ignore=[1004])

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 5, 7)
        self.emit("message_changed", "Calibrating Z axis minimum...")
        if table.z.enabled:
            if not ncal(table.z):
                raise RuntimeError("failed to calibrate Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 6, 7)
        self.emit("message_changed", "Range measure Z axis maximum...")
        if table.z.enabled:
            if not nrm(table.z):
                raise RuntimeError("failed to range measure Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        # Moving into limit switch generates error 1004
        table.rmove(0, 0, -AXIS_OFFSET)
        for i in range(retries):
            handle_abort()
            pos = table.pos
            update_status(*pos)
            if pos == (0, 0, 0):
                break
            time.sleep(delay)
        if pos != (0, 0, 0):
            raise RuntimeError(f"failed to calibrate axes, current pos: {pos}")
        # Clear error 1004
        error_handler.handle_error(ignore=[1004])

        update_status()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress_changed", 7, 7)
        self.emit("message_changed", "Calibration successful.")

    def event_loop(self, table):
        t = time.time()
        while self.running:
            with self.__lock:
                if self.__queue:
                    request = self.__queue.pop(0)
                    try:
                        request(table)
                    except Exception as exc:
                        self.emit('message_changed', exc)
                        raise
                else:
                    if time.time() > t + self.update_interval:
                        self.position()
                        self.caldone()
                        t = time.time()
            time.sleep(self.throttle_interval)
