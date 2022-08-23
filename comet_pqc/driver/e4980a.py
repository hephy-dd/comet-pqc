from typing import Tuple

from comet.driver import Driver, Property
from comet.driver.iec60488 import IEC60488, lock

__all__ = ["E4980A"]


class Bias(Driver):

    class Current(Driver):

        @property
        def level(self) -> float:
            return float(self.resource.query(":BIAS:CURR:LEV?"))

        @level.setter
        def level(self, value: float):
            self.resource.write(f":BIAS:CURR:LEV {value:E}")
            self.resource.query("*OPC?")

    class Polarity(Driver):

        class Current(Driver):

            @property
            def level(self) -> float:
                return float(self.resource.query(":BIAS:POL:CURR:LEV?"))

        class Voltage(Driver):

            @property
            def level(self) -> float:
                return float(self.resource.query(":BIAS:POL:VOLT:LEV?"))

        def __init__(self, resource):
            super().__init__(resource)
            self.current = self.Current(resource)
            self.voltage = self.Voltage(resource)

        @Property(values={False: 0, True: 1})
        def auto(self) -> int:
            """Returns True if automatic polarity control is enabled."""
            return int(self.resource.query(":BIAS:POL:AUTO?"))

        @auto.setter
        def auto(self, value: int):
            self.resource.write(f":BIAS:POL:AUTO {value:d}")
            self.resource.query("*OPC?")

    class Range(Driver):

        @Property(values={False: 0, True: 1})
        def auto(self) -> int:
            """Returns True if DC bias range is set to AUTO."""
            return int(self.resource.query(":BIAS:RANG:AUTO?"))

        @auto.setter
        def auto(self, value: int):
            self.resource.write(f":BIAS:RANG:AUTO {value:d}")
            self.resource.query("*OPC?")

    class Voltage(Driver):

        @property
        def level(self) -> float:
            return float(self.resource.query(":BIAS:VOLT:LEV?"))

        @level.setter
        def level(self, value: float):
            self.resource.write(f":BIAS:VOLT:LEV {value:E}")
            self.resource.query("*OPC?")

    def __init__(self, resource):
        super().__init__(resource)
        self.current = self.Current(resource)
        self.polarity = self.Polarity(resource)
        self.range = self.Range(resource)
        self.voltage = self.Voltage(resource)

    @Property(values={False: 0, True: 1})
    def state(self) -> int:
        """Returns True if bias output enabled."""
        return int(self.resource.query(":BIAS:STAT?"))

    @state.setter
    def state(self, value: int):
        self.resource.write(f":BIAS:STAT {value:d}")
        self.resource.query("*OPC?")


class Display(Driver):

    def __init__(self, resource):
        super().__init__(resource)

    def cclear(self):
        """Clears messages from the display."""
        self.resource.write(":DISP:CCL")
        self.resource.query("*OPC?")

    @Property(values={False: 0, True: 1})
    def enable(self) -> int:
        """Enable display updates."""
        return int(self.resource.query(":DISP:ENAB?"))

    @enable.setter
    def enable(self, value: int):
        self.resource.write(f":DISP:ENAB {value:d}")
        self.resource.query("*OPC?")

    @property
    def line(self) -> str:
        """Display message line, limited to 30 ASCII characters."""
        return self.resource.query(":DISP:LINE?")

    @line.setter
    def line(self, value: str):
        self.resource.write(f":DISP:LINE {value[:30]}")
        self.resource.query("*OPC?")


class Fetch(Driver):

    class Impedance(Driver):

        @lock
        def corrected(self) -> Tuple[float]:
            """Return tuple with two corrected values."""
            result = self.resource.query(":FETC:IMP:CORR?")
            return tuple(map(float, result.split(",")))

        @lock
        def formatted(self) -> Tuple[float]:
            """Return tuple with three values."""
            result = self.resource.query(":FETC:IMP:FORM?")
            return tuple(map(float, result.split(",")))

    class SMonitor(Driver):

        @property
        def iac(self) -> float:
            return float(self.resource.query(":FETC:SMON:IAC?"))

        @property
        def idc(self) -> float:
            return float(self.resource.query(":FETC:SMON:IDC?"))

        @property
        def vac(self) -> float:
            return float(self.resource.query(":FETC:SMON:VAC?"))

        @property
        def vdc(self) -> float:
            return float(self.resource.query(":FETC:SMON:VDC?"))

    def __init__(self, resource):
        super().__init__(resource)
        self.impedance = self.Impedance(resource)
        self.smonitor = self.SMonitor(resource)

    @lock
    def __call__(self) -> Tuple[float]:
        """Return tuple with three values."""
        result = self.resource.query(":FETC?")
        return tuple(map(float, result.split(",")))


class Frequency(Driver):

    @property
    def cw(self) -> float:
        """Frequency for measurement."""
        return float(self.resource.query(":FREQ:CW?"))

    @cw.setter
    def cw(self, value: float):
        self.resource.write(f":FREQ:CW {value:d}")
        self.resource.query("*OPC?")


class System(Driver):

    class Beeper(Driver):

        @Property(values={False: 0, True: 1})
        def state(self) -> int:
            return int(self.resource.query(":SYST:BEEP:STAT?"))

        @state.setter
        def state(self, value: int):
            self.resource.write(f":SYST:BEEP:STAT {value:d}")
            self.resource.query("*OPC?")

    @property
    def error(self) -> Tuple[int, str]:
        """Returns current instrument error.
        >>> system.error
        (0, "No error")
        """
        result = self.resource.query(":SYST:ERR?").split(",")
        return int(result[0]), result[1].strip().strip("\"")

    def __init__(self, resource):
        super().__init__(resource)
        self.beeper = self.Beeper(resource)


class E4980A(IEC60488):
    """Keysignt E4980A Precision LCR Meter."""

    def __init__(self, resource, **kwargs):
        super().__init__(resource, **kwargs)
        self.bias = Bias(resource)
        self.display = Display(resource)
        self.fetch = Fetch(resource)
        self.frequency = Frequency(resource)
        self.system = System(resource)
