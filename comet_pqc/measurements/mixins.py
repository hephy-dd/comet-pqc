import logging
import time

import comet

from ..utils import format_metric
from ..utils import std_mean_filter

__all__ = [
    'HVSourceMixin',
    'VSourceMixin',
    'ElectrometerMixin',
    'LCRMixin',
    'EnvironmentMixin'
]

class HVSourceMixin:

    def register_hvsource(self):
        ##self.register_parameter('hvsrc_current_compliance', unit='A', required=True)
        self.register_parameter('hvsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('hvsrc_route_termination', 'rear', values=('front', 'rear'))
        self.register_parameter('hvsrc_filter_enable', False, type=bool)
        self.register_parameter('hvsrc_filter_count', 10, type=int)
        self.register_parameter('hvsrc_filter_type', 'repeat', values=('repeat', 'moving'))
        self.register_parameter('hvsrc_source_voltage_autorange_enable', True, type=bool)
        self.register_parameter('hvsrc_source_voltage_range', 20, unit='V')

    def hvsrc_update_meta(self):
        """Update meta data parameters."""
        hvsrc_sense_mode = self.get_parameter('hvsrc_sense_mode')
        hvsrc_route_termination = self.get_parameter('hvsrc_route_termination')
        hvsrc_filter_enable = self.get_parameter('hvsrc_filter_enable')
        hvsrc_filter_count = self.get_parameter('hvsrc_filter_count')
        hvsrc_filter_type = self.get_parameter('hvsrc_filter_type')
        hvsrc_source_voltage_autorange_enable = self.get_parameter('hvsrc_source_voltage_autorange_enable')
        hvsrc_source_voltage_range = self.get_parameter('hvsrc_source_voltage_range')

        self.set_meta("hvsrc_sense_mode", hvsrc_sense_mode)
        self.set_meta("hvsrc_route_termination", hvsrc_route_termination)
        self.set_meta("hvsrc_filter_enable", hvsrc_filter_enable)
        self.set_meta("hvsrc_filter_count", hvsrc_filter_count)
        self.set_meta("hvsrc_filter_type", hvsrc_filter_type)
        self.set_meta("hvsrc_source_voltage_autorange_enable", hvsrc_source_voltage_autorange_enable)
        self.set_meta("hvsrc_source_voltage_range", f"{hvsrc_source_voltage_range:G} V")

    def hvsrc_check_error(self, device):
        """Test for error."""
        code, message = device.resource.query(":SYST:ERR?").split(",", 1)
        code = int(code)
        if code != 0:
            message = message.strip("\"")
            logging.error(f"HV Source error {code}: {message}")
            raise RuntimeError(f"HV Source error {code}: {message}")

    def hvsrc_safe_write(self, device, message):
        """Write, wait for operation complete, test for error."""
        logging.info(f"safe write: {device.__class__.__name__}: {message}")
        device.resource.write(message)
        device.resource.query("*OPC?")
        self.hvsrc_check_error(device)

    def hvsrc_reset(self, hvsrc):
        self.hvsrc_safe_write(hvsrc, "*RST")
        self.hvsrc_safe_write(hvsrc, "*CLS")
        self.hvsrc_safe_write(hvsrc, ":SYST:BEEP:STAT OFF")

    def hvsrc_setup(self, hvsrc):
        hvsrc_route_termination = self.get_parameter('hvsrc_route_termination')
        hvsrc_sense_mode = self.get_parameter('hvsrc_sense_mode')
        hvsrc_filter_enable = self.get_parameter('hvsrc_filter_enable')
        hvsrc_filter_count = self.get_parameter('hvsrc_filter_count')
        hvsrc_filter_type = self.get_parameter('hvsrc_filter_type')
        hvsrc_source_voltage_autorange_enable = self.get_parameter('hvsrc_source_voltage_autorange_enable')
        hvsrc_source_voltage_range = self.get_parameter('hvsrc_source_voltage_range')

        self.hvsrc_set_route_termination(hvsrc, hvsrc_route_termination)
        self.hvsrc_set_sense_mode(hvsrc,hvsrc_sense_mode)
        self.hvsrc_set_auto_range(hvsrc, True)
        self.hvsrc_set_filter_type(hvsrc, hvsrc_filter_type)
        self.hvsrc_set_filter_count(hvsrc, hvsrc_filter_count)
        self.hvsrc_set_filter_enable(hvsrc, hvsrc_filter_enable)
        if hvsrc_source_voltage_autorange_enable:
            self.hvsrc_set_source_voltage_autorange_enable(hvsrc, hvsrc_source_voltage_autorange_enable)
        else:
            # This will overwrite autorange in Keithley 2400 series
            self.hvsrc_set_source_voltage_range(hvsrc, hvsrc_source_voltage_range)

    def hvsrc_get_voltage_level(self, hvsrc):
        return float(hvsrc.resource.query(":SOUR:VOLT:LEV?"))

    def hvsrc_set_voltage_level(self, hvsrc, voltage):
        logging.info("set HV Source voltage level: %s", format_metric(voltage, "V"))
        self.hvsrc_safe_write(hvsrc, f":SOUR:VOLT:LEV {voltage:E}")

    def hvsrc_set_route_termination(self, hvsrc, route_termination):
        logging.info("set HV Source route termination: '%s'", route_termination)
        value = {"front": "FRON", "rear": "REAR"}[route_termination]
        self.hvsrc_safe_write(hvsrc, f":ROUT:TERM {value:s}")

    def hvsrc_set_sense_mode(self, hvsrc, sense_mode):
        logging.info("set HV Source sense mode: '%s'", sense_mode)
        value = {"remote": "ON", "local": "OFF"}[sense_mode]
        self.hvsrc_safe_write(hvsrc, f":SYST:RSEN {value:s}")

    def hvsrc_set_compliance(self, hvsrc, compliance):
        logging.info("set HV Source compliance: %s", format_metric(compliance, "A"))
        self.hvsrc_safe_write(hvsrc, f":SENS:CURR:PROT:LEV {compliance:E}")

    def hvsrc_compliance_tripped(self, hvsrc):
        return bool(int(hvsrc.resource.query(":SENS:CURR:PROT:TRIP?")))

    def hvsrc_set_auto_range(self, hvsrc, enabled):
        logging.info("set HV Source auto range (current): %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        self.hvsrc_safe_write(hvsrc, f"SENS:CURR:RANG:AUTO {value:s}")

    def hvsrc_set_filter_enable(self, hvsrc, enabled):
        logging.info("set HV Source filter enable: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        self.hvsrc_safe_write(hvsrc, f":SENS:AVER:STATE {value:s}")

    def hvsrc_set_filter_count(self, hvsrc, count):
        logging.info("set HV Source filter count: %s", count)
        self.hvsrc_safe_write(hvsrc, f":SENS:AVER:COUN {count:d}")

    def hvsrc_set_filter_type(self, hvsrc, type):
        logging.info("set HV Source filter type: %s", type)
        value = {"repeat": "REP", "moving": "MOV"}[type]
        self.hvsrc_safe_write(hvsrc, f":SENS:AVER:TCON {value:s}")

    def hvsrc_get_output_state(self, hvsrc):
        return bool(int(hvsrc.resource.query(":OUTP:STAT?")))

    def hvsrc_set_output_state(self, hvsrc, enabled):
        logging.info("set HV Source output state: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        self.hvsrc_safe_write(hvsrc, f":OUTP:STAT {value:s}")

    def hvsrc_set_source_voltage_autorange_enable(self, hvsrc, enabled):
        logging.info("set HV Source source voltage autorange enable: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        self.hvsrc_safe_write(hvsrc, f":SOUR:VOLT:RANG:AUTO {value:s}")

    def hvsrc_set_source_voltage_range(self, hvsrc, voltage):
        logging.info("set HV Source source voltage range: %s", format_metric(voltage, "V"))
        self.hvsrc_safe_write(hvsrc, f":SOUR:VOLT:RANG {voltage:E}")

class VSourceMixin:

    def register_vsource(self):
        ##self.register_parameter('vsrc_current_compliance', unit='A', required=True)
        self.register_parameter('vsrc_sense_mode', 'local', values=('local', 'remote'))
        self.register_parameter('vsrc_filter_enable', False, type=bool)
        self.register_parameter('vsrc_filter_count', 10, type=int)
        self.register_parameter('vsrc_filter_type', 'repeat', values=('repeat', 'moving'))

    def vsrc_update_meta(self):
        """Update meta data parameters."""
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        self.set_meta("vsrc_sense_mode", vsrc_sense_mode)
        self.set_meta("vsrc_filter_enable", vsrc_filter_enable)
        self.set_meta("vsrc_filter_count", vsrc_filter_count)
        self.set_meta("vsrc_filter_type", vsrc_filter_type)

    def vsrc_reset(self, vsrc):
        vsrc.reset()
        vsrc.clear()
        vsrc.beeper.enable = False
        vsrc.source.func = 'DCVOLTS'

    def vsrc_setup(self, vsrc):
        vsrc_sense_mode = self.get_parameter('vsrc_sense_mode')
        vsrc_filter_enable = self.get_parameter('vsrc_filter_enable')
        vsrc_filter_count = self.get_parameter('vsrc_filter_count')
        vsrc_filter_type = self.get_parameter('vsrc_filter_type')

        self.vsrc_set_sense_mode(vsrc, vsrc_sense_mode)
        self.vsrc_set_filter_type(vsrc, vsrc_filter_type)
        self.vsrc_set_filter_count(vsrc, vsrc_filter_count)
        self.vsrc_set_filter_enable(vsrc, vsrc_filter_enable)

    def vsrc_get_voltage_level(self, vsrc):
        return vsrc.source.levelv

    def vsrc_set_voltage_level(self, vsrc, voltage):
        logging.info("set V Source voltage level: %s", format_metric(voltage, "V"))
        vsrc.source.levelv = voltage

    def vsrc_set_sense_mode(self, vsrc, sense_mode):
        logging.info("set V Source sense mode: '%s'", sense_mode)
        value = {"remote": "REMOTE", "local": "LOCAL"}[sense_mode]
        vsrc.sense = value

    def vsrc_set_current_compliance(self, vsrc, compliance):
        logging.info("set V Source current compliance: %s", format_metric(compliance, "A"))
        vsrc.source.limiti = compliance

    def vsrc_set_voltage_compliance(self, vsrc, compliance):
        logging.info("set V Source voltage compliance: %s", format_metric(compliance, "V"))
        vsrc.source.limitv = compliance

    def vsrc_compliance_tripped(self, vsrc):
        return vsrc.source.compliance

    def vsrc_set_filter_enable(self, vsrc, enabled):
        logging.info("set V Source filter enable: %s", enabled)
        vsrc.measure.filter.enable = enabled

    def vsrc_set_filter_count(self, vsrc, count):
        logging.info("set V Source filter count: %s", count)
        vsrc.measure.filter.count = count

    def vsrc_set_filter_type(self, vsrc, type):
        logging.info("set V Source filter type: %s", type)
        value = {"repeat": "REPEAT", "moving": "MOVING"}[type]
        vsrc.measure.filter.type = value

    def vsrc_set_output_state(self, vsrc, enabled):
        logging.info("set V Source output state: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        vsrc.source.output = value

class ElectrometerMixin:

    def register_elm(self):
        self.register_parameter('elm_read_timeout', comet.ureg('60 s'), unit='s')

    def elm_update_meta(self):
        """Update meta data parameters."""

    def elm_check_error(self, elm):
        result = elm.resource.query(":SYST:ERR?")
        try:
            code, label = result.split(",", 1)
            code = int(code)
        except ValueError as exc:
            raise RuntimeError(f"failed to read electrometer error state, device returned '{result}'")
        if code != 0:
            label = label.strip("\"")
            logging.error(f"Error {code}: {label}")
            raise RuntimeError(f"Error {code}: {label}")

    def elm_safe_write(self, elm, message):
        """Write, wait for operation complete, test for errors."""
        elm.resource.write(message)
        elm.resource.query("*OPC?")
        self.elm_check_error(elm)

    def elm_read(self, elm, timeout=60.0, interval=0.25):
        """Perform electrometer reading with timeout."""
        # Request operation complete
        elm.resource.write('*CLS')
        elm.resource.write('*OPC')
        # Initiate measurement
        elm.resource.write(":INIT")
        threshold = time.time() + timeout
        interval = min(timeout, interval)
        while time.time() < threshold:
            # Read event status
            if int(elm.resource.query('*ESR?')) & 0x1:
                return float(elm.resource.query(":FETCH?").split(',')[0])
            time.sleep(interval)
        raise RuntimeError(f"electrometer reading timeout, exceeded {timeout:G} s")

class LCRMixin:

    def register_lcr(self):
        self.register_parameter('lcr_soft_filter', True, type=bool)
        self.register_parameter('lcr_amplitude', unit='V', required=True)
        self.register_parameter('lcr_frequency', unit='Hz', required=True)
        self.register_parameter('lcr_integration_time', 'medium', values=('short', 'medium', 'long'))
        self.register_parameter('lcr_averaging_rate', 1, type=int)
        self.register_parameter('lcr_auto_level_control', True, type=bool)
        self.register_parameter('lcr_open_correction_mode', 'single', values=('single', 'multi'))
        self.register_parameter('lcr_open_correction_channel', 0, type=int)

    def lcr_update_meta(self):
        """Update meta data parameters."""
        lcr_amplitude = self.get_parameter('lcr_amplitude')
        lcr_frequency = self.get_parameter('lcr_frequency')
        lcr_integration_time = self.get_parameter('lcr_integration_time')
        lcr_averaging_rate = self.get_parameter('lcr_averaging_rate')
        lcr_auto_level_control = self.get_parameter('lcr_auto_level_control')
        lcr_open_correction_mode = self.get_parameter('lcr_open_correction_mode')
        lcr_open_correction_channel = self.get_parameter('lcr_open_correction_channel')
        lcr_soft_filter = self.get_parameter('lcr_soft_filter')

        self.set_meta("lcr_amplitude", f"{lcr_amplitude:G} V")
        self.set_meta("lcr_frequency", f"{lcr_frequency:G} Hz")
        self.set_meta("lcr_integration_time", lcr_integration_time)
        self.set_meta("lcr_averaging_rate", lcr_averaging_rate)
        self.set_meta("lcr_auto_level_control", lcr_auto_level_control)
        self.set_meta("lcr_open_correction_mode", lcr_open_correction_mode)
        self.set_meta("lcr_open_correction_channel", lcr_open_correction_channel)
        self.set_meta("lcr_soft_filter", lcr_soft_filter)

    def lcr_check_error(self, device):
        """Test for error."""
        code, message = device.resource.query(":SYST:ERR?").split(",", 1)
        code = int(code)
        if code != 0:
            message = message.strip("\"")
            logging.error(f"LCR error {code}: {message}")
            raise RuntimeError(f"LCR error {code}: {message}")

    def lcr_safe_write(self, device, message):
        """Write, wait for operation complete, test for error."""
        logging.info(f"safe write: {device.__class__.__name__}: {message}")
        device.resource.write(message)
        device.resource.query("*OPC?")
        self.lcr_check_error(device)

    def lcr_reset(self, lcr):
        self.lcr_safe_write(lcr, "*RST")
        self.lcr_safe_write(lcr, "*CLS")
        self.lcr_safe_write(lcr, ":SYST:BEEP:STAT OFF")

    def lcr_setup(self, lcr):
        lcr_amplitude = self.get_parameter('lcr_amplitude')
        lcr_frequency = self.get_parameter('lcr_frequency')
        lcr_integration_time = self.get_parameter('lcr_integration_time')
        lcr_averaging_rate = self.get_parameter('lcr_averaging_rate')
        lcr_auto_level_control = self.get_parameter('lcr_auto_level_control')
        lcr_open_correction_mode = self.get_parameter('lcr_open_correction_mode')
        lcr_open_correction_channel = self.get_parameter('lcr_open_correction_channel')

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
        result = lcr.resource.query("FETC?")
        logging.info("lcr reading: %s", result)
        prim, sec = [float(value) for value in result.split(",")[:2]]
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
        logging.warning("maximum sample count reached: %d", maximum)
        return prim, sec

class EnvironmentMixin:

    def register_environment(self):
        self.environment_clear()

    def environment_update_meta(self):
        """Update meta data parameters."""

    def environment_clear(self):
        self.environment_temperature_box = float('nan')
        self.environment_temperature_chuck = float('nan')
        self.environment_humidity_box = float('nan')

    def environment_update(self):
        self.environment_clear()
        if self.process.get("use_environ"):
            with self.processes.get("environment") as environment:
                pc_data = environment.pc_data()
            self.environment_temperature_box = pc_data.box_temperature
            logging.info("temperature box: %s degC", self.environment_temperature_box)
            self.environment_temperature_chuck = pc_data.chuck_temperature
            logging.info("temperature chuck: %s degC", self.environment_temperature_chuck)
            self.environment_humidity_box = pc_data.box_humidity
            logging.info("humidity box: %s degC", self.environment_humidity_box)
