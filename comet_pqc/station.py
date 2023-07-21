import comet

__all__ = ["Station"]


class Station(comet.ResourceMixin):

    def __init__(self) -> None:
        self.resources.add("matrix", comet.Resource(
            resource_name="TCPIP::localhost::11001::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("hvsrc", comet.Resource(
            resource_name="TCPIP::localhost::11002::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=4000
        ))
        self.resources.add("vsrc", comet.Resource(
            resource_name="TCPIP::localhost::11003::SOCKET",
            encoding="latin1",
            read_termination="\n",
            write_termination="\n"
        ))
        self.resources.add("lcr", comet.Resource(
            resource_name="TCPIP::localhost::11004::SOCKET",
            read_termination="\n",
            write_termination="\n",
            timeout=8000
        ))
        self.resources.add("elm", comet.Resource(
            resource_name="TCPIP::localhost::11005::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("table", comet.Resource(
            resource_name="TCPIP::localhost::11006::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n",
            timeout=8000
        ))
        self.resources.add("environ", comet.Resource(
            resource_name="TCPIP::localhost::11007::SOCKET",
            read_termination="\r\n",
            write_termination="\r\n"
        ))
        self.resources.load_settings()
