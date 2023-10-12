import logging
import time

import comet
from comet.driver.keithley import K707B
from comet.driver.corvus import Venus1
from comet.driver.keithley import K6517B

from .instruments.e4980a import E4980A
from .settings import settings
from .workers.table import AlternateTableWorker
from .workers.environment import EnvironmentWorker

__all__ = ["Station"]

logger = logging.getLogger(__name__)


class Station(comet.ResourceMixin):

    def __init__(self) -> None:
        self.state: dict = {}

        self.matrix_resource = comet.Resource(
            resource_name="TCPIP::localhost::11001::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        )
        self.resources.add("matrix", self.matrix_resource)

        self.hvsrc_resource = comet.Resource(
            resource_name="TCPIP::localhost::11002::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=4000
        )
        self.resources.add("hvsrc", self.hvsrc_resource)

        self.vsrc_resource = comet.Resource(
            resource_name="TCPIP::localhost::11003::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        )
        self.resources.add("vsrc", self.vsrc_resource)

        self.lcr_resource = comet.Resource(
            resource_name="TCPIP::localhost::11004::SOCKET",
            read_termination="\n",
            write_termination="\n",
            timeout=8000
        )
        self.resources.add("lcr", self.lcr_resource)

        self.elm_resource = comet.Resource(
            resource_name="TCPIP::localhost::11005::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        )
        self.resources.add("elm", self.elm_resource)

        self.table_resource = comet.Resource(
            resource_name="TCPIP::localhost::11006::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        )
        self.resources.add("table", self.table_resource)

        self.environ_resource = comet.Resource(
            resource_name="TCPIP::localhost::11007::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n"
        )
        self.resources.add("environ", self.environ_resource)  # TODO

        self.resources.load_settings()

        self.matrix = MatrixRole(self.matrix_resource)
        self.lcr = LCRMeterRole(self.lcr_resource)
        self.table = TableRole(self.table_resource)

        self.environ_worker = EnvironmentWorker(resource=self.environ_resource, name="environ")
        self.table_worker = AlternateTableWorker(table=self.table)

    def create_instrument(self, key: str):
        return {
            "hvsrc": settings.hvsrc_instrument,
            "vsrc": settings.vsrc_instrument,
            "elm": K6517B,
            "lcr": E4980A,
        }.get(key)

    def shutdown(self) -> None:
        self.environ_worker.stop()
        self.table_worker.stop()
        self.environ_worker.join()
        self.table_worker.join()

    def set_test_led(self, enabled: bool) -> None:
        with self.environ_worker as environ:
            environ.set_test_led(True)
        logger.info("environbox.test_led = %s", "ON" if enabled else "OFF")


class MatrixRole:  # TODO

    def __init__(self, resource):
        self.resource = resource
        self.driver = K707B(resource)

    def identify(self) -> str:
        with self.resource:
            return self.driver.identification

    def open_all_channels(self) -> None:
        with self.resource:
            self.driver.channel.open() # open all

    def closed_channels(self) -> list:
        with self.resource:
            return self.driver.channel.getclose()

    def safe_close_channels(self, channels: list) -> None:
        with self.resource:
            closed_channels = self.driver.channel.getclose()
            if closed_channels:
                raise RuntimeError("Some matrix channels are still closed, " \
                    f"please verify the situation and open closed channels. Closed channels: {closed_channels}")
            if channels:
                self.driver.channel.close(channels)
                closed_channels = self.driver.channel.getclose()
                if sorted(closed_channels) != sorted(channels):
                    raise RuntimeError("Matrix mismatch in closed channels")


class LCRMeterRole:

    def __init__(self, resource):
        self.resource = resource
        self.driver = E4980A(resource)

    def reset(self):
        self.driver.reset()
        self.driver.clear()
        self.check_error()
        self.driver.system.beeper.state = False
        self.check_error()

    def safe_write(self, message):
        self.driver.resource.write(message)
        self.driver.resource.query("*OPC?")
        self.check_error()

    def check_error(self):
        """Test for error."""
        code, message = self.driver.system.error
        if code:
            raise RuntimeError(f"LCR Meter error {code}: {message}")

    def quick_setup_cp_rp(self):
        self.safe_write(":FUNC:IMP:RANG:AUTO ON")
        self.safe_write(":FUNC:IMP:TYPE CPRP")
        self.safe_write(":APER SHOR")
        self.safe_write(":INIT:CONT OFF")
        self.safe_write(":TRIG:SOUR BUS")
        self.safe_write(":CORR:METH SING")

    def acquire_reading(self):
        """Return primary and secondary LCR reading."""
        self.safe_write(":TRIG:IMM")
        prim, sec = self.driver.fetch()[:2]
        return prim, sec


class TableError(Exception):
    ...


class TableMachineError(Exception):
    ...


class TableCalibrationError(Exception):
    ...


class TableRole:

    UNIT_MICROMETER: int = 1
    UNIT_MILLIMETER: int = 2

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

    def __init__(self, table_resource):
        self.resource = table_resource
        self.table = Venus1(table_resource)

    def identify(self) -> str:
        return self.table.identification

    @property
    def is_calibrated(self) -> bool:
        return (3, 3, 3) == (self.table.x.caldone, self.table.y.caldone, self.table.z.caldone)

    def move_absolute(self, position) -> None:
        x, y, z = position
        self.table.move(x, y, z)

    def move_relative(self, position) -> None:
        x, y, z = position
        self.table.rmove(x, y, z)

    @property
    def position(self) -> tuple:
        x, y, z = self.table.pos
        return x, y, z

    @property
    def caldone(self) -> tuple:
        x, y, z = self.table.x.caldone, self.table.y.caldone, self.table.z.caldone
        return x, y, z

    @property
    def joystick_enabled(self) -> bool:
        return self.table.joystick

    @joystick_enabled.setter
    def joystick_enabled(self, value: bool) -> None:
        self.table.joystick = value

    def set_limit(self, limit):
        x, y, z = limit
        self.table.limit = x, y, z

    @property
    def limit(self):
        return self.table.limit

    @property
    def axes(self):
        return self.table.x, self.table.y, self.table.z

    @property
    def table_is_moving(self) -> None:
        return (self.table.status & 0x1) == 0x1

    def configure(self) -> None:
        self.table.mode = 0
        self.joystick_enabled = False
        self.table.x.unit = self.UNIT_MICROMETER
        self.table.y.unit = self.UNIT_MICROMETER
        self.table.z.unit = self.UNIT_MICROMETER
        time.sleep(.250)  # temper

    def handle_error(self, ignore=None):
        """Handle table system error."""
        code = self.table.error
        if code and code not in (ignore or []):
            message = type(self).ERROR_MESSAGES.get(code, "Unknown error code.")
            raise TableError(f"Table Error {code}: {message}")

    def handle_machine_error(self, ignore=None):
        """Handle table machine error."""
        code = self.table.merror
        if code and code not in (ignore or []):
            message = type(self).MACHINE_ERROR_MESSAGES.get(code, "Unknown machine error code.")
            raise TableMachineError(f"Table Machine Error {code}: {message}")

    def handle_calibration_error(self):
        """Handle table calibration error."""
        x, y, z = self.table.x, self.table.y, self.table.z
        caldone = x.caldone, y.caldone, z.caldone
        if caldone != type(self).VALID_CALDONE:
            raise TableCalibrationError("Table requires calibration.")
