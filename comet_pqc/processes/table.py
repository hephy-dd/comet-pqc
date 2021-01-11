import logging
import time
import threading

import comet
from comet.resource import ResourceMixin
from comet.driver.corvus import Venus1

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
        self.position = None
        self.caldone = None

    def peek(self):
        if not self.alive:
            with self.resources.get('table') as resource:
                table = Venus1(resource)
                self.initialize(table)
                self.emit('position', *table.pos)
                self.emit('caldone', table.x.caldone, table.y.caldone, table.z.caldone)
                self.finalize(table)

    def run(self):
        with self.resources.get('table') as resource:
            table = Venus1(resource)
            self.initialize(table)
            self.control(table)
            self.finalize(table)

    def initialize(self, table):
        table.mode = 0
        table.joystick = False
        table.x.unit = UNIT_MICROMETER
        table.y.unit = UNIT_MICROMETER
        table.z.unit = UNIT_MICROMETER
        time.sleep(.250)

    def control(self, table):
        """Overwrite with custom table control sequence."""

    def finalize(self, table):
        pass

class ControlProcess(TableProcess):
    """Control process for Corvus table."""

    update_interval = 1.0

    def __init__(self, message=None, progress=None, **kwargs):
        super().__init__(**kwargs)
        self.queue = []
        self.lock = threading.RLock()
        self.z_warning = None
        self.message = message
        self.progress = progress

    def push(self, *args):
        with self.lock:
            self.queue.append(args)

    def control(self, table):
        error_handler = TableErrorHandler(table)

        error_handler.handle_machine_error()
        error_handler.handle_error()
        error_handler.handle_calibration_error()

        t = time.time()
        while self.running:
            with self.lock:
                if self.queue:
                    assert table.x.unit == UNIT_MICROMETER
                    assert table.y.unit == UNIT_MICROMETER
                    assert table.z.unit == UNIT_MICROMETER
                    args = self.queue.pop(0)
                    error_handler.handle_machine_error()
                    error_handler.handle_error()
                    table.rmove(*args)
                    error_handler.handle_machine_error()
                    error_handler.handle_error()
                    self.emit('position', *table.pos)
                    continue
            if (time.time() - t) > self.update_interval:
                t = time.time()
                error_handler.handle_machine_error()
                error_handler.handle_error()
                self.emit('position', *table.pos)
                self.emit('caldone', table.x.caldone, table.y.caldone, table.z.caldone)
            time.sleep(.025)

class MoveProcess(TableProcess):
    """Move process for Corvus table."""

    MAXIMUM_Z = 23800

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress

    def control(self, table):
        self.set("success", False)
        self.set("z_warning", False)
        self.emit("message", "Moving...")
        x = self.get('x', 0)
        y = self.get('y', 0)
        z = min(self.get('z', 0), self.get('z_limit', self.MAXIMUM_Z))

        retries = RETRIES
        delay = 1.0

        error_handler = TableErrorHandler(table)

        error_handler.handle_machine_error()
        error_handler.handle_error()
        error_handler.handle_calibration_error()

        def handle_abort():
            if not self.running:
                self.emit("progress", 0, 0)
                self.emit("message", "Moving aborted.")
                raise comet.StopRequest()

        def update_status():
            self.emit("message", "Table x={} um, y={} um, z={} um".format(*table.pos))
            self.emit('position', *table.pos)

        def update_caldone():
            self.emit('caldone', table.x.caldone, table.y.caldone, table.z.caldone)

        handle_abort()
        update_caldone()

        self.emit("progress", 1, 4)
        self.emit("message", "Retreating Z axis...")

        # Moving into limit switch generates error 1004
        table.rmove(0, 0, -AXIS_OFFSET)
        for i in range(retries):
            handle_abort()
            update_status()
            pos = table.pos
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

        self.emit("progress", 2, 4)
        self.emit("message", "Move X Y axes...")
        table.move(x, y, 0)
        for i in range(retries):
            handle_abort()
            update_status()
            pos = table.pos
            if pos[:2] == (x, y):
                break
            time.sleep(delay)
        if pos[:2] != (x, y):
            raise RuntimeError(f"failed to absolute move, current pos: {pos}")

        self.emit("progress", 3, 4)
        self.emit("message", "Move up Z axis...")
        table.rmove(0, 0, z)
        for i in range(retries):
            handle_abort()
            update_status()
            pos = table.pos
            if pos[2] >= z:
                break
            time.sleep(delay)
        if pos != (x, y, z):
            raise RuntimeError(f"failed to relative move, current pos: {pos}")

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 7, 7)
        self.emit("message", "Movement successful.")

        self.set("z_warning", self.get('z') > z)
        self.set("success", True)

class CalibrateProcess(TableProcess):
    """Calibration process for Corvus table."""

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress

    def control(self, table):
        self.set("success", False)
        self.emit("message", "Calibrating...")
        retries = RETRIES
        delay = 1.0
        axes = table.x, table.y, table.z

        error_handler = TableErrorHandler(table)

        def handle_abort():
            if not self.running:
                self.emit("progress", 0, 0)
                self.emit("message", "Calibration aborted.")
                raise comet.StopRequest()

        def update_status():
            self.emit("message", "Table x={} um, y={} um, z={} um".format(*table.pos))
            self.emit('position', *table.pos)

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
                if table.pos[index] == 0.0:
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
                update_status()
                # Axis stopped moving?
                if table.pos[index] == pos[index]:
                    logging.info("nrm %s... done.", AXIS_NAMES.get(index))
                    break
                time.sleep(delay)
                pos = table.pos
            return i < retries

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 0, 7)
        self.emit("message", "Retreating Z axis...")
        if table.z.enabled:
            if not ncal(table.z):
                raise RuntimeError("failed retreating Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 1, 7)
        self.emit("message", "Calibrating Y axis...")
        if table.y.enabled:
            if not ncal(table.y):
                raise RuntimeError("failed to calibrate Y axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 2, 7)
        self.emit("message", "Calibrating X axis...")
        if table.x.enabled:
            if not ncal(table.x):
                raise RuntimeError("failed to calibrate Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 3, 7)
        self.emit("message", "Range measure X axis...")
        if table.x.enabled:
            if not nrm(table.x):
                raise RuntimeError("failed to ragne measure X axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 4, 7)
        self.emit("message", "Range measure Y axis...")
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
            update_status()
            pos = table.pos
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

        self.emit("progress", 5, 7)
        self.emit("message", "Calibrating Z axis minimum...")
        if table.z.enabled:
            if not ncal(table.z):
                raise RuntimeError("failed to calibrate Z axis")
        time.sleep(delay)

        handle_abort()
        update_caldone()

        error_handler.handle_machine_error()
        error_handler.handle_error()

        self.emit("progress", 6, 7)
        self.emit("message", "Range measure Z axis maximum...")
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
            update_status()
            pos = table.pos
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

        self.emit("progress", 7, 7)
        self.emit("message", "Calibration successful.")

        self.set("success", True)
