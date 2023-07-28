import logging
import math
import time

import analysis_pqc
import comet
from comet.driver.keithley import K6517B

from ..core.filters import std_mean_filter
from ..core.timer import Timer
from ..driver import E4980A
from ..instruments.k2657a import K2657AInstrument
from ..settings import settings
from ..utils import format_metric
from .measurement import ComplianceError, InstrumentError

__all__ = [
    "HVSourceMixin",
    "VSourceMixin",
    "ElectrometerMixin",
    "LCRMixin",
    "EnvironmentMixin",
    "AnalysisMixin"
]

logger = logging.getLogger(__name__)


class Mixin:
    """Base class for measurement mixins."""


class HVSourceMixin(Mixin):

    def register_vsource(self):
        # self.register_parameter("hvsrc_current_compliance", unit="A", required=True)
        self.register_parameter("hvsrc_sense_mode", "local", values=("local", "remote"))
        self.register_parameter("hvsrc_route_terminal", "rear", values=("front", "rear"))
        self.register_parameter("hvsrc_filter_enable", False, type=bool)
        self.register_parameter("hvsrc_filter_count", 10, type=int)
        self.register_parameter("hvsrc_filter_type", "repeat", values=("repeat", "moving"))
        self.register_parameter("hvsrc_source_voltage_autorange_enable", True, type=bool)
        self.register_parameter("hvsrc_source_voltage_range", comet.ureg("20 V"), unit="V")

    def hvsrc_update_meta(self):
        """Update meta data parameters."""
        hvsrc_sense_mode = self.get_parameter("hvsrc_sense_mode")
        hvsrc_route_terminal = self.get_parameter("hvsrc_route_terminal")
        hvsrc_filter_enable = self.get_parameter("hvsrc_filter_enable")
        hvsrc_filter_count = self.get_parameter("hvsrc_filter_count")
        hvsrc_filter_type = self.get_parameter("hvsrc_filter_type")
        hvsrc_source_voltage_autorange_enable = self.get_parameter("hvsrc_source_voltage_autorange_enable")
        hvsrc_source_voltage_range = self.get_parameter("hvsrc_source_voltage_range")

        self.set_meta("hvsrc_sense_mode", hvsrc_sense_mode)
        self.set_meta("hvsrc_route_terminal", hvsrc_route_terminal)
        self.set_meta("hvsrc_filter_enable", hvsrc_filter_enable)
        self.set_meta("hvsrc_filter_count", hvsrc_filter_count)
        self.set_meta("hvsrc_filter_type", hvsrc_filter_type)
        self.set_meta("hvsrc_source_voltage_autorange_enable", hvsrc_source_voltage_autorange_enable)
        self.set_meta("hvsrc_source_voltage_range", f"{hvsrc_source_voltage_range:G} V")

    def hvsrc_create(self, resource):
        """Return HV source instrument instance."""
        return settings.hvsrc_instrument(resource)

    def hvsrc_check_error(self, hvsrc):
        """Test for error."""
        code, message = hvsrc.get_error()
        if code != 0:
            message = message.strip("\"")
            logger.error(f"HV Source error {code}: {message}")
            raise RuntimeError(f"HV Source error {code}: {message}")

    def hvsrc_check_compliance(self, hvsrc):
        """Test for compliance tripped."""
        if self.hvsrc_compliance_tripped(hvsrc):
            logger.error("HV Source in compliance!")
            raise ComplianceError("HV Source in compliance!")

    def hvsrc_reset(self, hvsrc):
        hvsrc.reset()

    def hvsrc_clear(self, hvsrc):
        hvsrc.clear()

    def hvsrc_setup(self, hvsrc):
        hvsrc_route_terminal = self.get_parameter("hvsrc_route_terminal")
        hvsrc_sense_mode = self.get_parameter("hvsrc_sense_mode")
        hvsrc_filter_enable = self.get_parameter("hvsrc_filter_enable")
        hvsrc_filter_count = self.get_parameter("hvsrc_filter_count")
        hvsrc_filter_type = self.get_parameter("hvsrc_filter_type")
        hvsrc_source_voltage_autorange_enable = self.get_parameter("hvsrc_source_voltage_autorange_enable")
        hvsrc_source_voltage_range = self.get_parameter("hvsrc_source_voltage_range")

        self.hvsrc_set_route_terminal(hvsrc, hvsrc_route_terminal)
        self.hvsrc_set_sense_mode(hvsrc, hvsrc_sense_mode)
        self.hvsrc_set_auto_range(hvsrc, True)
        self.hvsrc_set_filter_type(hvsrc, hvsrc_filter_type)
        self.hvsrc_set_filter_count(hvsrc, hvsrc_filter_count)
        self.hvsrc_set_filter_enable(hvsrc, hvsrc_filter_enable)
        if hvsrc_source_voltage_autorange_enable:
            self.hvsrc_set_source_voltage_autorange_enable(hvsrc, hvsrc_source_voltage_autorange_enable)
        else:
            # This will overwrite autorange in Keithley 2400 series
            self.hvsrc_set_source_voltage_range(hvsrc, hvsrc_source_voltage_range)

    def hvsrc_set_function_voltage(self, hvsrc):
        hvsrc.set_source_function(hvsrc.SOURCE_FUNCTION_VOLTAGE)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_function_current(self, hvsrc):
        hvsrc.set_source_function(hvsrc.SOURCE_FUNCTION_CURRENT)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_get_voltage_level(self, hvsrc):
        return hvsrc.get_source_voltage()

    def hvsrc_set_voltage_level(self, hvsrc, voltage):
        logger.info("HV Source set voltage level: %s", format_metric(voltage, "V"))
        hvsrc.set_source_voltage(voltage)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_route_terminal(self, hvsrc, route_terminals):
        logger.info("HV Source set route terminals: %r", route_terminals)
        value = {"front": "FRONT", "rear": "REAR"}[route_terminals]
        hvsrc.set_terminal(value)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_sense_mode(self, hvsrc, sense_mode):
        logger.info("HV Source set sense mode: %r", sense_mode)
        value = {"remote": "REMOTE", "local": "LOCAL"}[sense_mode]
        hvsrc.set_sense_mode(value)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_current_compliance(self, hvsrc, compliance):
        logger.info("HV Source set current compliance: %s", format_metric(compliance, "A"))
        hvsrc.set_compliance_current(compliance)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_voltage_compliance(self, hvsrc, compliance):
        logger.info("HV Source set voltage compliance: %s", format_metric(compliance, "V"))
        hvsrc.set_compliance_voltage(compliance)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_compliance_tripped(self, hvsrc):
        return hvsrc.compliance_tripped()

    def hvsrc_set_auto_range(self, hvsrc, enabled):
        logger.info("HV Source set auto range (current): %s", enabled)
        hvsrc.set_source_current_autorange(enabled)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_filter_enable(self, hvsrc, enabled):
        logger.info("HV Source set filter enable: %s", enabled)
        hvsrc.set_filter_enable(enabled)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_filter_count(self, hvsrc, count):
        logger.info("HV Source set filter count: %s", count)
        hvsrc.set_filter_count(count)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_filter_type(self, hvsrc, type):
        logger.info("HV Source set filter type: %s", type)
        value = {"repeat": "REPEAT", "moving": "MOVING"}[type]
        hvsrc.set_filter_type(value)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_get_output_state(self, hvsrc):
        value = hvsrc.get_output()
        return {hvsrc.OUTPUT_ON: True, hvsrc.OUTPUT_OFF: False}[value]

    def hvsrc_set_output_state(self, hvsrc, enabled):
        logger.info("HV Source set output state: %s", enabled)
        hvsrc.set_output(enabled)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_source_voltage_autorange_enable(self, hvsrc, enabled):
        logger.info("HV Source set source voltage autorange enable: %s", enabled)
        hvsrc.set_source_voltage_autorange(enabled)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_set_source_voltage_range(self, hvsrc, voltage):
        logger.info("HV Source set source voltage range: %s", format_metric(voltage, "V"))
        hvsrc.set_source_voltage_range(voltage)
        self.hvsrc_check_error(hvsrc)

    def hvsrc_read_voltage(self, hvsrc):
        # Set read format to voltage only
        voltage = hvsrc.read_voltage()
        logger.info("HV Source voltage reading: %s", format_metric(voltage, "V"))
        return voltage

    def hvsrc_read_current(self, hvsrc):
        # Set read format to current only
        current = hvsrc.read_current()
        logger.info("HV Source current reading: %s", format_metric(current, "A"))
        return current


class VSourceMixin(Mixin):

    def register_hvsource(self):
        # self.register_parameter("vsrc_current_compliance", unit="A", required=True)
        self.register_parameter("vsrc_sense_mode", "local", values=("local", "remote"))
        self.register_parameter("vsrc_route_terminal", "rear", values=("front", "rear"))
        self.register_parameter("vsrc_filter_enable", False, type=bool)
        self.register_parameter("vsrc_filter_count", 10, type=int)
        self.register_parameter("vsrc_filter_type", "repeat", values=("repeat", "moving"))
        self.register_parameter("vsrc_source_voltage_autorange_enable", True, type=bool)
        self.register_parameter("vsrc_source_voltage_range", comet.ureg("20 V"), unit="V")

    def vsrc_update_meta(self):
        """Update meta data parameters."""
        vsrc_sense_mode = self.get_parameter("vsrc_sense_mode")
        vsrc_route_terminal = self.get_parameter("vsrc_route_terminal")
        vsrc_filter_enable = self.get_parameter("vsrc_filter_enable")
        vsrc_filter_count = self.get_parameter("vsrc_filter_count")
        vsrc_filter_type = self.get_parameter("vsrc_filter_type")
        vsrc_source_voltage_autorange_enable = self.get_parameter("vsrc_source_voltage_autorange_enable")
        vsrc_source_voltage_range = self.get_parameter("vsrc_source_voltage_range")

        self.set_meta("vsrc_sense_mode", vsrc_sense_mode)
        self.set_meta("vsrc_route_terminal", vsrc_route_terminal)
        self.set_meta("vsrc_filter_enable", vsrc_filter_enable)
        self.set_meta("vsrc_filter_count", vsrc_filter_count)
        self.set_meta("vsrc_filter_type", vsrc_filter_type)
        self.set_meta("vsrc_source_voltage_autorange_enable", vsrc_source_voltage_autorange_enable)
        self.set_meta("vsrc_source_voltage_range", f"{vsrc_source_voltage_range:G} V")

    def vsrc_create(self, resource):
        """Return V source instrument instance."""
        return settings.vsrc_instrument(resource)

    def vsrc_check_error(self, vsrc):
        """Test for error."""
        code, message = vsrc.get_error()
        if code != 0:
            logger.error(f"V Source error {code}: {message}")
            raise InstrumentError(f"V Source error {code}: {message}")

    def vsrc_check_compliance(self, vsrc):
        """Test for compliance tripped."""
        if self.vsrc_compliance_tripped(vsrc):
            logger.error("V Source in compliance!")
            raise ComplianceError("V Source in compliance!")

    def vsrc_reset(self, vsrc):
        vsrc.reset()

    def vsrc_clear(self, vsrc):
        vsrc.clear()

    def vsrc_set_function_voltage(self, vsrc):
        vsrc.set_source_function(vsrc.SOURCE_FUNCTION_VOLTAGE)
        self.vsrc_check_error(vsrc)

    def vsrc_set_function_current(self, vsrc):
        vsrc.set_source_function(vsrc.SOURCE_FUNCTION_CURRENT)
        self.vsrc_check_error(vsrc)

    def vsrc_setup(self, vsrc):
        vsrc_sense_mode = self.get_parameter("vsrc_sense_mode")
        vsrc_route_terminal = self.get_parameter("vsrc_route_terminal")
        vsrc_filter_enable = self.get_parameter("vsrc_filter_enable")
        vsrc_filter_count = self.get_parameter("vsrc_filter_count")
        vsrc_filter_type = self.get_parameter("vsrc_filter_type")
        vsrc_source_voltage_autorange_enable = self.get_parameter("vsrc_source_voltage_autorange_enable")
        vsrc_source_voltage_range = self.get_parameter("vsrc_source_voltage_range")

        self.vsrc_set_sense_mode(vsrc, vsrc_sense_mode)
        self.vsrc_set_route_terminal(vsrc, vsrc_route_terminal)
        self.vsrc_set_filter_type(vsrc, vsrc_filter_type)
        self.vsrc_set_filter_count(vsrc, vsrc_filter_count)
        self.vsrc_set_filter_enable(vsrc, vsrc_filter_enable)
        if vsrc_source_voltage_autorange_enable:
            self.vsrc_set_source_voltage_autorange_enable(vsrc, vsrc_source_voltage_autorange_enable)
        else:
            # This will overwrite autorange
            self.vsrc_set_source_voltage_range(vsrc, vsrc_source_voltage_range)

    def vsrc_set_route_terminal(self, vsrc, route_terminals):
        logger.info("V Source set route terminals: %r", route_terminals)
        value = {"front": "FRONT", "rear": "REAR"}[route_terminals]
        vsrc.set_terminal(value)
        self.vsrc_check_error(vsrc)

    def vsrc_get_voltage_level(self, vsrc):
        return vsrc.get_source_voltage()

    def vsrc_set_voltage_level(self, vsrc, voltage):
        logger.info("V Source set voltage level: %s", format_metric(voltage, "V"))
        vsrc.set_source_voltage(voltage)
        self.vsrc_check_error(vsrc)

    def vsrc_get_current_level(self, vsrc):
        return vsrc.get_source_current()

    def vsrc_set_current_level(self, vsrc, current):
        logger.info("V Source set current level: %s", format_metric(current, "A"))
        vsrc.set_source_current(current)
        self.vsrc_check_error(vsrc)

    def vsrc_set_sense_mode(self, vsrc, sense_mode):
        logger.info("V Source set sense mode: %r", sense_mode)
        value = {"remote": vsrc.SENSE_MODE_REMOTE, "local": vsrc.SENSE_MODE_LOCAL}[sense_mode]
        vsrc.set_sense_mode(value)
        self.vsrc_check_error(vsrc)

    def vsrc_set_current_compliance(self, vsrc, compliance):
        logger.info("V Source set current compliance: %s", format_metric(compliance, "A"))
        vsrc.set_compliance_current(compliance)
        self.vsrc_check_error(vsrc)

    def vsrc_set_voltage_compliance(self, vsrc, compliance):
        logger.info("V Source set voltage compliance: %s", format_metric(compliance, "V"))
        vsrc.set_compliance_voltage(compliance)
        self.vsrc_check_error(vsrc)

    def vsrc_compliance_tripped(self, vsrc):
        return vsrc.compliance_tripped()

    def vsrc_set_filter_enable(self, vsrc, enabled):
        logger.info("V Source set filter enable: %s", enabled)
        vsrc.set_filter_enable(enabled)
        self.vsrc_check_error(vsrc)

    def vsrc_set_filter_count(self, vsrc, count):
        logger.info("V Source set filter count: %s", count)
        vsrc.set_filter_count(count)
        self.vsrc_check_error(vsrc)

    def vsrc_set_filter_type(self, vsrc, type):
        logger.info("V Source set filter type: %s", type)
        value = {"repeat": vsrc.FILTER_TYPE_REPEAT, "moving": vsrc.FILTER_TYPE_MOVING}[type]
        vsrc.set_filter_type(value)
        self.vsrc_check_error(vsrc)

    def vsrc_get_output_state(self, vsrc):
        value = vsrc.get_output()
        return {vsrc.OUTPUT_ON: True, vsrc.OUTPUT_OFF: False}[value]

    def vsrc_set_output_state(self, vsrc, enabled):
        logger.info("V Source set output state: %s", enabled)
        vsrc.set_output(enabled)
        self.vsrc_check_error(vsrc)

    def vsrc_set_display(self, vsrc, value):
        if isinstance(vsrc, K2657AInstrument):
            logger.info("V Source set display: %s", value)
            value = {"voltage": "DCVOLTS", "current": "DCAMPS"}[value]
            vsrc.context.resource.write(f"display.smua.measure.func = display.MEASURE_{value}")
            self.vsrc_check_error(vsrc)

    def vsrc_set_source_voltage_autorange_enable(self, vsrc, enabled):
        logger.info("V Source set source voltage autorange enable: %s", enabled)
        vsrc.set_source_voltage_autorange(enabled)
        self.vsrc_check_error(vsrc)

    def vsrc_set_source_voltage_range(self, vsrc, voltage):
        logger.info("V Source set source voltage range: %s", format_metric(voltage, "V"))
        vsrc.set_source_voltage_range(voltage)
        self.vsrc_check_error(vsrc)

    def vsrc_read_current(self, vsrc):
        current = vsrc.read_current()
        logger.info("V Source current reading: %s", format_metric(current, "A"))
        return current

    def vsrc_read_voltage(self, vsrc):
        voltage = vsrc.read_voltage()
        logger.info("V Source voltage reading: %s", format_metric(voltage, "V"))
        return voltage


class ElectrometerMixin(Mixin):

    def register_elm(self):
        self.register_parameter("elm_read_timeout", comet.ureg("60 s"), unit="s")

    def elm_update_meta(self):
        """Update meta data parameters."""

    def elm_create(self, resource):
        """Return ELM instrument instance."""
        return K6517B(resource)  # TODO

    def elm_check_error(self, elm):
        try:
            result = elm.resource.query(":SYST:ERR?")
        except Exception as exc:
            raise RuntimeError(f"Failed to read error state from ELM: {exc}") from exc
        try:
            code, label = result.split(",", 1)
            code = int(code)
        except ValueError as exc:
            raise RuntimeError(f"Failed to read electrometer error state, device returned: {result!r}") from exc
        if code != 0:
            label = label.strip("\"")
            logger.error(f"Error {code}: {label}")
            raise RuntimeError(f"Error {code}: {label}")

    def elm_safe_write(self, elm, message):
        """Write, wait for operation complete, test for errors."""
        try:
            elm.resource.write(message)
        except Exception as exc:
            raise RuntimeError(f"Failed to write to ELM: {message!r}, {exc}") from exc
        try:
            elm.resource.query("*OPC?")
        except Exception as exc:
            raise RuntimeError(f"Failed to read operation complete from ELM for message: {message!r}, {exc}") from exc
        self.elm_check_error(elm)

    def elm_read(self, elm, timeout=60.0, interval=0.25):
        """Perform electrometer reading with timeout."""
        # Request operation complete
        elm.resource.write("*CLS")
        elm.resource.write("*OPC")
        # Initiate measurement
        logger.info("Initiate ELM measurement...")
        elm.resource.write(":INIT")
        t = Timer()
        interval = min(timeout, interval)
        logger.info("Poll ELM event status register...")
        while t.delta() < timeout:
            # Read event status
            if int(elm.resource.query("*ESR?")) & 0x1:
                logger.info("Fetch ELM reading...")
                try:
                    result = elm.resource.query(":FETCH?")
                    return float(result.split(",")[0])
                except Exception as exc:
                    raise RuntimeError(f"Failed to fetch ELM reading: {exc}") from exc
            time.sleep(interval)
        raise RuntimeError(f"Electrometer reading timeout, exceeded {timeout:G} s")

    def elm_get_zero_check(self, elm):
        try:
            return bool(int(elm.resource.query(":SYST:ZCH?")))
        except Exception as exc:
            raise RuntimeError(f"Failed to get zero check from ELM: {exc}") from exc

    def elm_set_zero_check(self, elm, enabled):
        value = {False: "OFF", True: "ON"}.get(enabled)
        try:
            self.elm_safe_write(elm, f":SYST:ZCH {value}")
        except Exception as exc:
            raise RuntimeError(f"Failed to set zero check to ELM: {exc}") from exc


class LCRMixin(Mixin):

    def register_lcr(self):
        self.register_parameter("lcr_soft_filter", True, type=bool)
        self.register_parameter("lcr_amplitude", unit="V", required=True)
        self.register_parameter("lcr_frequency", unit="Hz", required=True)
        self.register_parameter("lcr_integration_time", "medium", values=("short", "medium", "long"))
        self.register_parameter("lcr_averaging_rate", 1, type=int)
        self.register_parameter("lcr_auto_level_control", True, type=bool)
        self.register_parameter("lcr_open_correction_mode", "single", values=("single", "multi"))
        self.register_parameter("lcr_open_correction_channel", 0, type=int)

    def lcr_update_meta(self):
        """Update meta data parameters."""
        lcr_amplitude = self.get_parameter("lcr_amplitude")
        lcr_frequency = self.get_parameter("lcr_frequency")
        lcr_integration_time = self.get_parameter("lcr_integration_time")
        lcr_averaging_rate = self.get_parameter("lcr_averaging_rate")
        lcr_auto_level_control = self.get_parameter("lcr_auto_level_control")
        lcr_open_correction_mode = self.get_parameter("lcr_open_correction_mode")
        lcr_open_correction_channel = self.get_parameter("lcr_open_correction_channel")
        lcr_soft_filter = self.get_parameter("lcr_soft_filter")

        self.set_meta("lcr_amplitude", f"{lcr_amplitude:G} V")
        self.set_meta("lcr_frequency", f"{lcr_frequency:G} Hz")
        self.set_meta("lcr_integration_time", lcr_integration_time)
        self.set_meta("lcr_averaging_rate", lcr_averaging_rate)
        self.set_meta("lcr_auto_level_control", lcr_auto_level_control)
        self.set_meta("lcr_open_correction_mode", lcr_open_correction_mode)
        self.set_meta("lcr_open_correction_channel", lcr_open_correction_channel)
        self.set_meta("lcr_soft_filter", lcr_soft_filter)

    def lcr_create(self, resource):
        """Return LCR instrument instance."""
        return E4980A(resource)  # TODO

    def lcr_check_error(self, device):
        """Test for error."""
        code, message = device.resource.query(":SYST:ERR?").split(",", 1)
        code = int(code)
        if code != 0:
            message = message.strip("\"")
            logger.error(f"LCR error {code}: {message}")
            raise RuntimeError(f"LCR error {code}: {message}")

    def lcr_safe_write(self, device, message):
        """Write, wait for operation complete, test for error."""
        logger.info(f"safe write: {device.__class__.__name__}: {message}")
        device.resource.write(message)
        device.resource.query("*OPC?")
        self.lcr_check_error(device)

    def lcr_reset(self, lcr):
        lcr.reset()
        lcr.clear()
        self.lcr_check_error(lcr)
        lcr.system.beeper.state = False
        self.lcr_check_error(lcr)

    def lcr_setup(self, lcr):
        lcr_amplitude = self.get_parameter("lcr_amplitude")
        lcr_frequency = self.get_parameter("lcr_frequency")
        lcr_integration_time = self.get_parameter("lcr_integration_time")
        lcr_averaging_rate = self.get_parameter("lcr_averaging_rate")
        lcr_auto_level_control = self.get_parameter("lcr_auto_level_control")
        lcr_open_correction_mode = self.get_parameter("lcr_open_correction_mode")
        lcr_open_correction_channel = self.get_parameter("lcr_open_correction_channel")

        self.lcr_safe_write(lcr, f":AMPL:ALC {lcr_auto_level_control:d}")
        self.lcr_safe_write(lcr, f":VOLT {lcr_amplitude:E}V")
        self.lcr_safe_write(lcr, f":FREQ {lcr_frequency:.0f}HZ")
        self.lcr_safe_write(lcr, ":FUNC:IMP:RANG:AUTO ON")
        self.lcr_safe_write(lcr, ":FUNC:IMP:TYPE CPRP")
        integration = {"short": "SHOR", "medium": "MED", "long": "LONG"}[lcr_integration_time]
        self.lcr_safe_write(lcr, f":APER {integration},{lcr_averaging_rate:d}")
        self.lcr_safe_write(lcr, ":INIT:CONT OFF")
        self.lcr_safe_write(lcr, ":TRIG:SOUR BUS")
        method = {"single": "SING", "multi": "MULT"}[lcr_open_correction_mode]
        self.lcr_safe_write(lcr, f":CORR:METH {method}")
        self.lcr_safe_write(lcr, f":CORR:USE:CHAN {lcr_open_correction_channel:d}")

    def lcr_acquire_reading(self, lcr):
        """Return primary and secondary LCR reading."""
        self.lcr_safe_write(lcr, "TRIG:IMM")
        prim, sec = lcr.fetch()[:2]
        logger.info("LCR Meter reading: %s-%s", prim, sec)
        return prim, sec

    def lcr_acquire_filter_reading(self, lcr, maximum=64, threshold=0.005, size=2):
        """Aquire readings until standard deviation (sample) / mean < threshold.

        Size is the number of samples to be used for filter calculation.
        """
        samples = []
        prim = 0.
        sec = 0.
        for _ in range(maximum):
            prim, sec = self.lcr_acquire_reading(lcr)
            samples.append(prim)
            samples = samples[-size:]
            if len(samples) >= size:
                if std_mean_filter(samples, threshold):
                    return prim, sec
        logger.warning("maximum sample count reached: %d", maximum)
        return prim, sec

    def lcr_get_bias_voltage_level(self, lcr):
        return lcr.bias.voltage.level

    def lcr_set_bias_voltage_level(self, lcr, voltage):
        logger.info("LCR Meter set voltage level: %s", format_metric(voltage, "V"))
        lcr.bias.voltage.level = voltage
        self.lcr_check_error(lcr)

    def lcr_get_bias_polarity_current_level(self, lcr):
        current = lcr.bias.polarity.current.level
        logger.info("LCR Meter bias polarity current: %s", format_metric(current, "A"))
        return current

    def lcr_get_bias_state(self, lcr):
        return lcr.bias.state

    def lcr_set_bias_state(self, lcr, enabled):
        logger.info("LCR Meter set voltage output state: %s", enabled)
        lcr.bias.state = enabled
        self.lcr_check_error(lcr)


class EnvironmentMixin(Mixin):

    def register_environment(self):
        self.environment_clear()

    def environment_update_meta(self):
        """Update meta data parameters."""

    def environment_clear(self):
        self.environment_temperature_box = float("nan")
        self.environment_temperature_chuck = float("nan")
        self.environment_humidity_box = float("nan")

    def environment_update(self):
        self.environment_clear()
        if self.process.get("use_environ"):
            with self.processes.get("environ") as environment:
                pc_data = environment.pc_data()
            self.environment_temperature_box = pc_data.box_temperature
            logger.info("Box temperature: %.2f degC", self.environment_temperature_box)
            self.environment_temperature_chuck = pc_data.chuck_temperature
            logger.info("Chuck temperature: %.2f degC", self.environment_temperature_chuck)
            self.environment_humidity_box = pc_data.box_humidity
            logger.info("Box humidity: %.2f %%rH", self.environment_humidity_box)
        self.process.emit("state", {
            "env_chuck_temperature": self.environment_temperature_chuck,
            "env_box_temperature": self.environment_temperature_box,
            "env_box_humidity": self.environment_humidity_box
        })


class AnalysisError(Exception):

    ...


class AnalysisFunction:

    prefix = "analyse_"

    def __init__(self, config):
        # Auto convert from string
        if isinstance(config, str):
            config = {"type": config}
        if "type" not in config:
            raise KeyError("Missing analysis key: type")
        self.type = config.get("type")
        self.parameters = config.get("parameters", {})
        self.limits = config.get("limits", {})

    def __call__(self, **kwargs):
        f = analysis_pqc.__dict__.get(f"{self.prefix}{self.type}")
        if not callable(f):
            raise KeyError(f"No such analysis function: {self.type}")
        logger.info("Running analysis function %r...", self.type)
        r = f(**kwargs)
        logger.info("Running analysis function %r... done.", self.type)
        return r

    def verify(self, result):
        for key, limit in self.limits.items():
            value = result._asdict().get(key)
            if isinstance(value, (int, float)):
                if math.isnan(value):
                    raise AnalysisError(f"Out of range {key!r} for {self.type}: {value}")
                minimum = limit.get("minimum")
                if isinstance(minimum, (int, float)):
                    if value < float(minimum):
                        raise AnalysisError(f"Out of range {key!r} for {self.type}: {value} < {minimum}")
                maximum = limit.get("maximum")
                if isinstance(maximum, (int, float)):
                    if value > float(maximum):
                        raise AnalysisError(f"Out of range {key!r} for {self.type}: {value} > {maximum}")
            else:
                logger.warning("No such limit: %s for %s", key, self.type)


class AnalysisMixin(Mixin):

    def register_analysis(self):
        self.register_parameter("analysis_functions", [], type=list)

    def analysis_functions(self):
        """Return analysis functions."""
        functions = []
        for config in self.get_parameter("analysis_functions"):
            functions.append(AnalysisFunction(config))
        return functions

    def analysis_iv(self, i, v):
        if len(i) > 1 and len(v) > 1:
            self.analysis_all(i=i, v=v)

    def analysis_cv(self, c, v):
        if len(c) > 1 and len(v) > 1:
            self.analysis_all(c=c, v=v)

    def analysis_all(self, **kwargs):
        results = []
        for f in self.analysis_functions():
            r = f(**kwargs)
            logger.info(r)
            results.append((f, r))
            key, values = type(r).__name__, r._asdict()
            self.set_analysis(key, values)
            self.process.emit("append_analysis", key, values)
            if "x_fit" in r._asdict():
                for x, y in [(x, r.a * x + r.b) for x in r.x_fit]:
                    self.process.emit("reading", "xfit", x, y)
                self.process.emit("update")
        for f, r in results:
            f.verify(r)
