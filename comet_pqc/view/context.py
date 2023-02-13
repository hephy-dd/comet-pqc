from comet import ProcessMixin, Resource, ResourceMixin

from ..processes import (AlternateTableProcess, ContactQualityProcess,
                         EnvironmentProcess, MeasureProcess, StatusProcess)


class Context(ProcessMixin, ResourceMixin):

    def __init__(self) -> None:
        self.resources.add("matrix", Resource(
            resource_name="TCPIP::10.0.0.2::5025::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("hvsrc", Resource(
            resource_name="TCPIP::10.0.0.5::10002::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=4000
        ))
        self.resources.add("vsrc", Resource(
            resource_name="TCPIP::10.0.0.3::5025::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("lcr", Resource(
            resource_name="TCPIP::10.0.0.4::5025::SOCKET",
            read_termination="\n",
            write_termination="\n",
            timeout=8000
        ))
        self.resources.add("elm", Resource(
            resource_name="TCPIP::10.0.0.5::10001::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("table", Resource(
            resource_name="TCPIP::10.0.0.6::23::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("environ", Resource(
            resource_name="TCPIP::10.0.0.8::10001::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n"
        ))

        self.environ_process = EnvironmentProcess(name="environ")
        self.processes.add("environ", self.environ_process)

        self.status_process = StatusProcess()
        self.processes.add("status", self.status_process)

        self.table_process = AlternateTableProcess()
        self.processes.add("table", self.table_process)

        self.measure_process = MeasureProcess()
        self.processes.add("measure", self.measure_process)

        self.contact_quality_process = ContactQualityProcess()
        self.processes.add("contact_quality", self.contact_quality_process)

    def shutdown(self):
        self.processes.stop()
        self.processes.join()

    def table_enabled(self) -> bool:
        return self.table_process.enabled

    def table_position(self) -> tuple:
        return self.table_process.get_cached_position()
