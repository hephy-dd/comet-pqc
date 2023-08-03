import logging

import comet
from comet.driver.keithley import K707B

from .processes.table import AlternateTableProcess
from .processes.environment import EnvironmentProcess

__all__ = ["Station"]

logger = logging.getLogger(__name__)


class Station(comet.ResourceMixin):

    def __init__(self) -> None:

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
        self.resources.add("environ", self.environ_resource)

        self.resources.load_settings()

        self.matrix = MatrixRole(self)

        self.environ_process = EnvironmentProcess(name="environ")
        self.table_process = AlternateTableProcess(resource=self.table_resource)

    def shutdown(self) -> None:
        self.environ_process.stop()
        self.table_process.stop()
        self.environ_process.join()
        self.table_process.join()

    def set_test_led(self, enabled: bool) -> None:
        with self.environ_process as environ:
            environ.set_test_led(True)
        logger.info("environbox.test_led = %s", "ON" if enabled else "OFF")


class MatrixRole:  # TODO

    def __init__(self, station):
        self.station = station

    def create_driver(self, resource):
        return K707B(resource)

    def identify(self):
        with self.station.matrix_resource as resource:
            return K707B(resource).identification

    def open_all_channels(self) -> None:
        with self.station.matrix_resource as resource:
            matrix = self.create_driver(resource)
            matrix.channel.open() # open all

    def closed_channels(self):
        with self.station.matrix_resource as resource:
            matrix = K707B(resource)
            return matrix.channel.getclose()

    def safe_close_channels(self, channels: list) -> None:
        with self.station.matrix_resource as resource:
            matrix = self.create_driver(resource)
            closed_channels = matrix.channel.getclose()
            if closed_channels:
                raise RuntimeError("Some matrix channels are still closed, " \
                    f"please verify the situation and open closed channels. Closed channels: {closed_channels}")
            if channels:
                matrix.channel.close(channels)
                closed_channels = matrix.channel.getclose()
                if sorted(closed_channels) != sorted(channels):
                    raise RuntimeError("Matrix mismatch in closed channels")
