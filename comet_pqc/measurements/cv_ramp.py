import logging
import datetime
import time
import os
import re

import comet
from comet.driver.keysight import E4980A

from ..driver import K2410
from ..utils import auto_unit
from ..utils import std_mean_filter
from ..formatter import PQCFormatter
from ..estimate import Estimate
from .matrix import MatrixMeasurement

__all__ = ["CVRampMeasurement"]

def check_error(device):
    """Test for error."""
    code, message = device.resource.query(":SYST:ERR?").split(",", 1)
    code = int(code)
    if code != 0:
        message = message.strip("\"")
        logging.error(f"error {code}: {message}")
        raise RuntimeError(f"error {code}: {message}")

def safe_write(device, message):
    """Write, wait for operation complete, test for error."""
    logging.info(f"safe write: {device.__class__.__name__}: {message}")
    device.resource.write(message)
    device.resource.query("*OPC?")
    check_error(device)

class CVRampMeasurement(MatrixMeasurement):
    """CV ramp measurement."""

    type = "cv_ramp"

    def acquire_reading(self, lcr):
        """Return primary and secondary LCR reading."""
        safe_write(lcr, "TRIG:IMM")
        result = lcr.resource.query("FETC?")
        logging.info("lcr reading: %s", result)
        prim, sec = [float(value) for value in result.split(",")[:2]]
        return prim, sec

    def acquire_filter_reading(self, lcr, maximum=64, threshold=0.005, size=2):
        """Aquire readings until standard deviation (sample) / mean < threshold.

        Size is the number of samples to be used for filter calculation.
        """
        samples = []
        prim = 0.
        sec = 0.
        for _ in range(maximum):
            prim, sec = self.acquire_reading(lcr)
            samples.append(prim)
            samples = samples[-size:]
            if len(samples) >= size:
                if std_mean_filter(samples, threshold):
                    return prim, sec
        logging.warning("maximum sample count reached: %d", maximum)
        return prim, sec

    def vsrc_detect_model(self, vsrc):
        try:
            vsrc_idn = vsrc.resource.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access VSource", vsrc.resource.resource_name, e)
        logging.info("Detected VSource: %s", vsrc_idn)
        result = re.search(r'model\s+([\d\w]+)', vsrc_idn, re.IGNORECASE).groups()
        vsrc_model = ''.join(result) or None
        self.process.emit("state", dict(
            vsrc_model=vsrc_model,
        ))

    def lcr_detect_model(self, lcr):
        try:
            lcr_idn = lcr.resource.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access LCR Meter", lcr.resource.resource_name, e)
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]
        self.process.emit("state", dict(
            lcr_model=lcr_model
        ))

    def env_detect_model(self, env):
        try:
            env_idn = env.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access Environment Box", env.resource_name, e)
        logging.info("Detected Environment Box: %s", env_idn)
        # TODO
        self.process.emit("state", dict(
            env_model=env_idn
        ))

    def quick_ramp_zero(self, vsrc):
        """Ramp to zero voltage without measuring current."""
        self.process.emit("message", "Ramp to zero...")
        self.process.emit("progress", 0, 1)
        parameters = self.measurement_item.parameters
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        vsrc_output_state = self.vsrc_get_output_state(vsrc)
        self.process.emit("state", dict(
            vsrc_output=vsrc_output_state
        ))
        if vsrc_output_state:
            vsrc_voltage_level = self.vsrc_get_voltage_level(vsrc)
            ramp = comet.Range(vsrc_voltage_level, 0, bias_voltage_step)
            for step, voltage in enumerate(ramp):
                self.process.emit("progress", step + 1, ramp.count)
                self.vsrc_set_voltage_level(vsrc, voltage)
                self.process.emit("state", dict(
                    vsrc_voltage=voltage
                ))
        vsrc_output_state = self.vsrc_get_output_state(vsrc)
        self.process.emit("state", dict(
            vsrc_output=vsrc_output_state
        ))
        self.process.emit("message", "")
        self.process.emit("progress", 1, 1)

    def vsrc_reset(self, vsrc):
        safe_write(vsrc, "*RST")
        safe_write(vsrc, "*CLS")
        safe_write(vsrc, ":SYST:BEEP:STAT OFF")

    def vsrc_get_voltage_level(self, vsrc):
        return float(vsrc.resource.query(":SOUR:VOLT:LEV?"))

    def vsrc_set_voltage_level(self, vsrc, voltage):
        logging.info("set VSource voltage level: %s", auto_unit(voltage, "V"))
        safe_write(vsrc, f":SOUR:VOLT:LEV {voltage:E}")

    def vsrc_set_route_termination(self, vsrc, route_termination):
        logging.info("set VSource route termination: '%s'", route_termination)
        value = {"front": "FRON", "rear": "REAR"}[route_termination]
        safe_write(vsrc, f":ROUT:TERM {value:s}")

    def vsrc_set_sense_mode(self, vsrc, sense_mode):
        logging.info("set VSource sense mode: '%s'", sense_mode)
        value = {"remote": "ON", "local": "OFF"}[sense_mode]
        safe_write(vsrc, f":SYST:RSEN {value:s}")

    def vsrc_set_compliance(self, vsrc, compliance):
        logging.info("set VSource compliance: %s", auto_unit(compliance, "A"))
        safe_write(vsrc, f":SENS:CURR:PROT:LEV {compliance:E}")

    def vsrc_compliance_tripped(self, vsrc):
        return bool(int(vsrc.resource.query(":SENS:CURR:PROT:TRIP?")))

    def vsrc_set_auto_range(self, vsrc, enabled):
        logging.info("set VSource auto range (current): %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        safe_write(vsrc, f"SENS:CURR:RANG:AUTO {value:s}")

    def vsrc_set_filter_enable(self, vsrc, enabled):
        logging.info("set VSource filter enable: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        safe_write(vsrc, f":SENS:AVER:STATE {value:s}")

    def vsrc_set_filter_count(self, vsrc, count):
        logging.info("set VSource filter count: %s", count)
        safe_write(vsrc, f":SENS:AVER:COUN {count:d}")

    def vsrc_set_filter_type(self, vsrc, type):
        logging.info("set VSource filter type: %s", type)
        value = {"repeat": "REP", "moving": "MOV"}[type]
        safe_write(vsrc, f":SENS:AVER:TCON {value:s}")

    def vsrc_get_output_state(self, vsrc):
        return bool(int(vsrc.resource.query(":OUTP:STAT?")))

    def vsrc_set_output_state(self, vsrc, enabled):
        logging.info("set VSource output state: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        safe_write(vsrc, f":OUTP:STAT {value:s}")

    def lcr_reset(self, lcr):
        safe_write(lcr, "*RST")
        safe_write(lcr, "*CLS")
        safe_write(lcr, ":SYST:BEEP:STAT OFF")

    def lcr_setup(self, lcr):
        parameters = self.measurement_item.parameters
        lcr_amplitude = parameters.get("lcr_amplitude").to("V").m
        lcr_frequency = parameters.get("lcr_frequency").to("Hz").m
        lcr_integration_time = parameters.get("lcr_integration_time", "medium")
        lcr_averaging_rate = int(parameters.get("lcr_averaging_rate", 1))
        lcr_auto_level_control = bool(parameters.get("lcr_auto_level_control", True))

        safe_write(lcr, f":AMPL:ALC {lcr_auto_level_control:d}")
        safe_write(lcr, f":VOLT {lcr_amplitude:E}V")
        safe_write(lcr, f":FREQ {lcr_frequency:.0f}HZ")
        safe_write(lcr, ":FUNC:IMP:RANG:AUTO ON")
        safe_write(lcr, ":FUNC:IMP:TYPE CPRP")
        integration = {"short": "SHOR", "medium": "MED", "long": "LONG"}[lcr_integration_time]
        safe_write(lcr, f":APER {integration},{lcr_averaging_rate:d}")
        safe_write(lcr, ":INIT:CONT OFF")
        safe_write(lcr, ":TRIG:SOUR BUS")

    def initialize(self, vsrc, lcr):
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 0, 10)

        parameters = self.measurement_item.parameters
        vsrc_current_compliance = parameters.get("vsrc_current_compliance").to("A").m
        vsrc_route_termination = parameters.get("vsrc_route_termination", "rear")
        vsrc_sense_mode = parameters.get("vsrc_sense_mode", "local")
        vsrc_filter_enable = bool(parameters.get("vsrc_filter_enable", False))
        vsrc_filter_count = int(parameters.get("vsrc_filter_count", 10))
        vsrc_filter_type = parameters.get("vsrc_filter_type", "repeat")

        self.vsrc_detect_model(vsrc)
        self.lcr_detect_model(lcr)

        if self.process.get("use_environ"):
            with self.resources.get("environ") as env:
                self.env_detect_model(env)

        self.process.emit("progress", 1, 10)

        # Initialize VSource

        # Bring down VSource voltage if output enabeled
        # Prevents a voltage jump for at device reset.
        self.quick_ramp_zero(vsrc)
        self.vsrc_set_output_state(vsrc, False)
        self.process.emit("message", "Initialize...")
        self.process.emit("progress", 2, 10)

        self.vsrc_reset(vsrc)
        self.process.emit("progress", 3, 10)

        self.vsrc_set_route_termination(vsrc, vsrc_route_termination)
        self.process.emit("progress", 4, 10)

        self.vsrc_set_sense_mode(vsrc,vsrc_sense_mode)
        self.process.emit("progress", 5, 10)

        self.vsrc_set_compliance(vsrc, vsrc_current_compliance)
        self.process.emit("progress", 6, 10)

        self.vsrc_set_auto_range(vsrc, True)
        self.process.emit("progress", 7, 10)

        self.vsrc_set_filter_type(vsrc, vsrc_filter_type)
        self.vsrc_set_filter_count(vsrc, vsrc_filter_count)
        self.vsrc_set_filter_enable(vsrc, vsrc_filter_enable)
        self.process.emit("progress", 8, 10)

        self.vsrc_set_output_state(vsrc, True)
        vsrc_output_state = self.vsrc_get_output_state(vsrc)
        self.process.emit("state", dict(
            vsrc_output=vsrc_output_state,
        ))

        # Initialize LCR

        self.lcr_reset(lcr)
        self.process.emit("progress", 9, 10)

        self.lcr_setup(lcr)
        self.process.emit("progress", 10, 10)

    def measure(self, vsrc, lcr):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name
        parameters = self.measurement_item.parameters
        bias_voltage_start = parameters.get("bias_voltage_start").to("V").m
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        bias_voltage_stop = parameters.get("bias_voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        vsrc_current_compliance = parameters.get("vsrc_current_compliance").to("A").m
        lcr_soft_filter = bool(parameters.get("lcr_soft_filter", True))
        lcr_frequency = parameters.get("lcr_frequency").to("Hz").m
        lcr_amplitude = parameters.get("lcr_amplitude").to("V").m

        # Ramp to start voltage

        vsrc_voltage_level = self.vsrc_get_voltage_level(vsrc)

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", vsrc_voltage_level, bias_voltage_start, bias_voltage_step)
        for voltage in comet.Range(vsrc_voltage_level, bias_voltage_start, bias_voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.emit("message", "Ramp to start... {}".format(auto_unit(voltage, "V")))
            self.vsrc_set_voltage_level(vsrc, voltage)
            time.sleep(.100)
            time.sleep(waiting_time)
            self.process.emit("state", dict(
                vsrc_voltage=voltage,
            ))
            # Compliance?
            compliance_tripped = self.vsrc_compliance_tripped(vsrc)
            if compliance_tripped:
                logging.error("VSource in compliance")
                raise ValueError("compliance tripped!")

            if not self.process.running:
                break

        if not self.process.running:
            return

        with open(os.path.join(output_dir, self.create_filename()), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage_vsrc", "E")
            fmt.add_column("capacitance", "E")
            fmt.add_column("capacitance2", "E")
            fmt.add_column("resistance", "E")
            fmt.add_column("temperature_box", "E")
            fmt.add_column("temperature_chuck", "E")
            fmt.add_column("humidity_box", "E")

            # Write meta data
            fmt.write_meta("measurement_name", measurement_name)
            fmt.write_meta("measurement_type", self.type)
            fmt.write_meta("contact_name", contact_name)
            fmt.write_meta("sample_name", sample_name)
            fmt.write_meta("sample_type", sample_type)
            fmt.write_meta("start_timestamp", datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            fmt.write_meta("bias_voltage_start", f"{bias_voltage_start:G} V")
            fmt.write_meta("bias_voltage_stop", f"{bias_voltage_stop:G} V")
            fmt.write_meta("bias_voltage_step", f"{bias_voltage_step:G} V")
            fmt.write_meta("waiting_time", f"{waiting_time:G} s")
            fmt.write_meta("vsrc_current_compliance", f"{vsrc_current_compliance:G} A")
            fmt.write_meta("ac_frequency", f"{lcr_frequency:G} Hz")
            fmt.write_meta("ac_amplitude", f"{lcr_amplitude:G} V")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            vsrc_voltage_level = self.vsrc_get_voltage_level(vsrc)

            ramp = comet.Range(vsrc_voltage_level, bias_voltage_stop, bias_voltage_step)
            est = Estimate(ramp.count)
            self.process.emit("progress", *est.progress)

            t0 = time.time()

            safe_write(vsrc, "*CLS")
            # VSource reading format: CURR
            safe_write(vsrc, ":FORM:ELEM CURR")

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", vsrc_voltage_level, ramp.end, ramp.step)
            for voltage in ramp:
                self.vsrc_set_voltage_level(vsrc, voltage)
                time.sleep(.100)
                # vsrc_voltage_level = self.vsrc_get_voltage_level(vsrc)
                dt = time.time() - t0
                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.emit("message", "Elapsed {} | Remaining {} | {}".format(elapsed, remaining, auto_unit(voltage, "V")))
                self.process.emit("progress", *est.progress)

                # read VSource
                vsrc_reading = float(vsrc.resource.query(":READ?").split(',')[0])
                logging.info("VSource reading: %E", vsrc_reading)


                # read LCR, for CpRp -> prim: Cp, sec: Rp
                if lcr_soft_filter:
                    lcr_prim, lcr_sec = self.acquire_filter_reading(lcr)
                else:
                    lcr_prim, lcr_sec = self.acquire_reading(lcr)
                try:
                    lcr_prim2 = 1.0 / (lcr_prim * lcr_prim)
                except ZeroDivisionError:
                    lcr_prim2 = 0.0

                self.process.emit("reading", "lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_prim)
                self.process.emit("reading", "lcr2", abs(voltage) if ramp.step < 0 else voltage, lcr_prim2)

                self.process.emit("update", )
                self.process.emit("state", dict(
                    vsrc_voltage=voltage,
                    vsrc_current=vsrc_reading
                ))

                # Environment
                if self.process.get("use_environ"):
                    with self.resources.get("environ") as env:
                        pc_data = env.query("GET:PC_DATA ?").split(",")
                    temperature_box = float(pc_data[2])
                    logging.info("temperature box: %s degC", temperature_box)
                    temperature_chuck = float(pc_data[33])
                    logging.info("temperature chuck: %s degC", temperature_chuck)
                    humidity_box = float(pc_data[1])
                    logging.info("humidity box: %s degC", humidity_box)
                else:
                    temperature_box = float('nan')
                    temperature_chuck = float('nan')
                    humidity_box = float('nan')

                self.process.emit("state", dict(
                    env_chuck_temperature=temperature_chuck,
                    env_box_temperature=temperature_box,
                    env_box_humidity=humidity_box
                ))

                # Write reading
                fmt.write_row(dict(
                    timestamp=dt,
                    voltage_vsrc=voltage,
                    capacitance=lcr_prim,
                    capacitance2=lcr_prim2,
                    resistance=lcr_sec,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()
                time.sleep(waiting_time)

                # Compliance?
                compliance_tripped = self.vsrc_compliance_tripped(vsrc)
                if compliance_tripped:
                    logging.error("VSource in compliance")
                    raise ValueError("compliance tripped!")

                if not self.process.running:
                    break

    def finalize(self, vsrc, lcr):
        self.process.emit("progress", 1, 2)
        self.process.emit("state", dict(
            vsrc_current=None,
        ))

        self.quick_ramp_zero(vsrc)
        self.vsrc_set_output_state(vsrc, False)
        vsrc_output_state = self.vsrc_get_output_state(vsrc)
        self.process.emit("state", dict(
            vsrc_output=vsrc_output_state,
        ))

        self.process.emit("state", dict(
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.emit("progress", 2, 2)

    def code(self, *args, **kwargs):
        with self.resources.get("vsrc") as vsrc_res:
            with self.resources.get("lcr") as lcr_res:
                vsrc = K2410(vsrc_res)
                lcr = E4980A(lcr_res)
                try:
                    self.initialize(vsrc, lcr)
                    self.measure(vsrc, lcr)
                finally:
                    self.finalize(vsrc, lcr)
