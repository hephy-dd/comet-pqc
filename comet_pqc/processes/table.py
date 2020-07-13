import logging
import time
import threading

import comet
from comet.resource import ResourceMixin
from comet.driver.corvus import Venus1

UNIT_MICROMETER = 1
UNIT_MILLIMETER = 2

AXIS_OFFSET = 2e6
RETRIES = 180

class ControlProcess(comet.Process, ResourceMixin):
    """Control process for Corvus table."""

    update_interval = 1.0

    def __init__(self, message=None, progress=None, **kwargs):
        super().__init__(**kwargs)
        self.queue = []
        self.lock = threading.RLock()
        self.position = None
        self.caldone = None
        self.z_warning = None
        self.message = message
        self.progress = progress

    def push(self, *args):
        with self.lock:
            self.queue.append(args)

    def run(self):
        with self.resources.get('table') as table_res:
            table = Venus1(table_res)
            table.mode = 0
            table.joystick = False
            table.x.unit = UNIT_MICROMETER
            table.y.unit = UNIT_MICROMETER
            table.z.unit = UNIT_MICROMETER

            def handle_error():
                error = table.error
                if error:
                    raise RuntimeError(f"Error: {error}")
                merror = table.merror
                if merror:
                    raise RuntimeError(f"Machine Error: {merror}")

            t = time.time()
            while self.running:
                with self.lock:
                    if self.queue:
                        assert table.x.unit == UNIT_MICROMETER
                        assert table.y.unit == UNIT_MICROMETER
                        assert table.z.unit == UNIT_MICROMETER
                        args = self.queue.pop(0)
                        handle_error()
                        table.rmove(*args)
                        self.emit('position', *table.pos)
                        handle_error()
                        continue
                if (time.time() - t) > self.update_interval:
                    t = time.time()
                    handle_error()
                    self.emit('position', *table.pos)
                    self.emit('caldone', table.x.caldone, table.y.caldone, table.z.caldone)
                time.sleep(.025)

class MoveProcess(comet.Process, ResourceMixin):
    """Move process for Corvus table."""

    MAXIMUM_Z = 22000

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.position = None
        self.caldone = None

    def peek(self):
        if not self.alive:
            with self.resources.get('table') as resource:
                corvus = Venus1(resource)
                corvus.mode = 0
                corvus.x.unit = UNIT_MICROMETER
                corvus.y.unit = UNIT_MICROMETER
                corvus.z.unit = UNIT_MICROMETER
                self.emit('position', *corvus.pos)
                self.emit('caldone', corvus.x.caldone, corvus.y.caldone, corvus.z.caldone)

    def run(self):
        self.set("success", False)
        self.set("z_warning", False)
        self.emit("message", "Moving...")
        x = self.get('x', 0)
        y = self.get('y', 0)
        z = min(self.get('z', 0), self.MAXIMUM_Z)
        with self.resources.get('table') as resource:
            corvus = Venus1(resource)
            corvus.mode = 0
            corvus.joystick = False
            corvus.x.unit = UNIT_MICROMETER
            corvus.y.unit = UNIT_MICROMETER
            corvus.z.unit = UNIT_MICROMETER
            retries = RETRIES
            delay = 1.0

            def handle_error():
                time.sleep(delay)
                error = corvus.error
                if error:
                    raise RuntimeError(f"Error: {error}")
                merror = corvus.merror
                if merror:
                    raise RuntimeError(f"Machine Error: {merror}")
                time.sleep(delay)

            def handle_abort():
                if not self.running:
                    corvus.joystick = True
                    self.emit("progress", 0, 0)
                    self.emit("message", "Moving aborted.")
                    raise comet.StopRequest()

            def update_status():
                self.emit("message", "Table x={} um, y={} um, z={} um".format(*corvus.pos))
                self.emit('position', *corvus.pos)

            def update_caldone():
                self.emit('caldone', corvus.x.caldone, corvus.y.caldone, corvus.z.caldone)

            handle_abort()
            update_caldone()

            self.emit("progress", 1, 4)
            self.emit("message", "Retreating Z axis...")
            corvus.rmove(0, 0, -AXIS_OFFSET)
            for i in range(retries):
                handle_abort()
                update_status()
                pos = corvus.pos
                if pos[2] == 0:
                    break
                time.sleep(delay)
            if pos[2] != 0:
                raise RuntimeError("failed to relative move, current pos: {}".format(pos))

            handle_abort()
            update_caldone()

            self.emit("progress", 2, 4)
            self.emit("message", "Move X Y axes...")
            corvus.move(x, y, 0)
            for i in range(retries):
                handle_abort()
                update_status()
                pos = corvus.pos
                if pos[:2] == (x, y):
                    break
                time.sleep(delay)
            if pos[:2] != (x, y):
                raise RuntimeError("failed to absolute move, current pos: {}".format(pos))

            self.emit("progress", 3, 4)
            self.emit("message", "Move up Z axis...")
            corvus.rmove(0, 0, z)
            for i in range(retries):
                handle_abort()
                update_status()
                pos = corvus.pos
                if pos[2] >= z:
                    break
                time.sleep(delay)
            if pos != (x, y, z):
                raise RuntimeError("failed to relative move, current pos: {}".format(pos))

            self.emit("progress", 7, 7)
            self.emit("message", "Movement successful.")

        self.set("z_warning", self.get('z') > z)
        self.set("success", True)

class CalibrateProcess(comet.Process, ResourceMixin):
    """Calibration process for Corvus table."""

    def __init__(self, message, progress, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress
        self.position = None
        self.caldone = None

    def peek(self):
        if not self.alive:
            with self.resources.get('table') as resource:
                corvus = Venus1(resource)
                corvus.mode = 0
                corvus.x.unit = UNIT_MICROMETER
                corvus.y.unit = UNIT_MICROMETER
                corvus.z.unit = UNIT_MICROMETER
                self.emit('position', *corvus.pos)
                self.emit('caldone', corvus.x.caldone, corvus.y.caldone, corvus.z.caldone)

    def run(self):
        self.set("success", False)
        self.emit("message", "Calibrating...")
        with self.resources.get('table') as resource:
            corvus = Venus1(resource)
            corvus.mode = 0
            corvus.joystick = False
            corvus.x.unit = UNIT_MICROMETER
            corvus.y.unit = UNIT_MICROMETER
            corvus.z.unit = UNIT_MICROMETER
            retries = RETRIES
            delay = 1.0

            def handle_error():
                time.sleep(delay)
                error = corvus.error
                if error:
                    raise RuntimeError(f"Error: {error}")
                merror = corvus.merror
                if merror:
                    raise RuntimeError(f"Machine Error: {merror}")
                time.sleep(delay)

            def handle_abort():
                if not self.running:
                    corvus.joystick = True
                    self.emit("progress", 0, 0)
                    self.emit("message", "Calibration aborted.")
                    raise comet.StopRequest()

            def update_status():
                self.emit("message", "Table x={} um, y={} um, z={} um".format(*corvus.pos))
                self.emit('position', *corvus.pos)

            def update_caldone():
                self.emit('caldone', corvus.x.caldone, corvus.y.caldone, corvus.z.caldone)

            def ncal(axis):
                axis.ncal()
                for i in range(retries + 1):
                    handle_abort()
                    update_status()
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
                    handle_abort()
                    update_status()
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

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 0, 7)
            self.emit("message", "Retreating Z axis...")
            if corvus.z.enabled:
                if not ncal(corvus.z):
                    raise RuntimeError("failed retreating Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 1, 7)
            self.emit("message", "Calibrating Y axis...")
            if corvus.y.enabled:
                if not ncal(corvus.y):
                    raise RuntimeError("failed to calibrate Y axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 2, 7)
            self.emit("message", "Calibrating X axis...")
            if corvus.x.enabled:
                if not ncal(corvus.x):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 3, 7)
            self.emit("message", "Range measure X axis...")
            if corvus.x.enabled:
                if not nrm(corvus.x):
                    raise RuntimeError("failed to ragne measure X axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 4, 7)
            self.emit("message", "Range measure Y axis...")
            if corvus.y.enabled:
                if not nrm(corvus.y):
                    raise RuntimeError("failed to range measure Y axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            corvus.rmove(-AXIS_OFFSET, -AXIS_OFFSET, 0)
            for i in range(retries):
                handle_abort()
                update_status()
                pos = corvus.pos
                if pos[:2] == (0, 0):
                    break
                time.sleep(delay)
            if pos[:2] != (0, 0):
                raise RuntimeError("failed to relative move, current pos: {}".format(pos))

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 5, 7)
            self.emit("message", "Calibrating Z axis minimum...")
            if corvus.z.enabled:
                if not ncal(corvus.z):
                    raise RuntimeError("failed to calibrate Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            self.emit("progress", 6, 7)
            self.emit("message", "Range measure Z axis maximum...")
            if corvus.z.enabled:
                if not nrm(corvus.z):
                    raise RuntimeError("failed to range measure Z axis")
            time.sleep(delay)

            handle_abort()
            update_caldone()

            #handle_error()
            corvus.rmove(0, 0, -AXIS_OFFSET)
            for i in range(retries):
                handle_abort()
                update_status()
                pos = corvus.pos
                if pos == (0, 0, 0):
                    break
                time.sleep(delay)
            if pos != (0, 0, 0):
                raise RuntimeError("failed to calibrate axes, current pos: {}".format(pos))

            #handle_error()
            update_status()
            update_caldone()

            self.emit("progress", 7, 7)
            self.emit("message", "Calibration successful.")

        self.set("success", True)
