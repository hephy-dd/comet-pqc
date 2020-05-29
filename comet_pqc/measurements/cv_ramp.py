import logging
import datetime
import time
import os
import re

import comet

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

    def smu_detect_model(self, smu):
        try:
            smu_idn = smu.resource.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access SMU1", smu.resource.resource_name, e)
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None
        self.process.events.state(dict(
            smu_model=smu_model,
        ))

    def lcr_detect_model(self, lcr):
        try:
            lcr_idn = lcr.resource.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access LCR Meter", lcr.resource.resource_name, e)
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]
        self.process.events.state(dict(
            lcr_model=lcr_model
        ))

    def env_detect_model(self, env):
        try:
            env_idn = env.resource.query("*IDN?")
        except Exception as e:
            raise RuntimeError("Failed to access Environment Box", env.resource.resource_name, e)
        logging.info("Detected Environment Box: %s", env_idn)
        # TODO
        self.process.events.state(dict(
            env_model=env_idn
        ))

    def quick_ramp_zero(self, smu):
        """Ramp to zero voltage without measuring current."""
        self.process.events.message("Ramp to zero...")
        self.process.events.progress(0, 1)
        parameters = self.measurement_item.parameters
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        smu_output_state = self.smu_get_output_state(smu)
        self.process.events.state(dict(
            smu_output=smu_output_state
        ))
        if smu_output_state:
            smu_voltage_level = self.smu_get_voltage_level(smu)
            ramp = comet.Range(smu_voltage_level, 0, bias_voltage_step)
            for step, voltage in enumerate(ramp):
                self.process.events.progress(step + 1, ramp.count)
                self.smu_set_voltage_level(smu, voltage)
                self.process.events.state(dict(
                    smu_voltage=voltage
                ))
        smu_output_state = self.smu_get_output_state(smu)
        self.process.events.state(dict(
            smu_output=smu_output_state
        ))
        self.process.events.message("")
        self.process.events.progress(1, 1)

    def smu_reset(self, smu):
        safe_write(smu, "*RST")
        safe_write(smu, "*CLS")
        safe_write(smu, ":SYST:BEEP:STAT OFF")

    def smu_get_voltage_level(self, smu):
        return float(smu.resource.query(":SOUR:VOLT:LEV?"))

    def smu_set_voltage_level(self, smu, voltage):
        logging.info("set SMU voltage level: %s", auto_unit(voltage, "V"))
        safe_write(smu, f":SOUR:VOLT:LEV {voltage:E}")

    def smu_set_route_termination(self, smu, route_termination):
        logging.info("set SMU route termination: '%s'", route_termination)
        value = {"front": "FRON", "rear": "REAR"}[route_termination]
        safe_write(smu, f":ROUT:TERM {value:s}")

    def smu_set_sense_mode(self, smu, sense_mode):
        logging.info("set SMU sense mode: '%s'", sense_mode)
        value = {"remote": "ON", "local": "OFF"}[sense_mode]
        safe_write(smu, f":SYST:RSEN {value:s}")

    def smu_set_compliance(self, smu, compliance):
        logging.info("set SMU compliance: %s", auto_unit(compliance, "A"))
        safe_write(smu, f":SENS:CURR:PROT:LEV {compliance:E}")

    def smu_compliance_tripped(self, smu):
        return bool(int(smu.resource.query(":SENS:CURR:PROT:TRIP?")))

    def smu_set_auto_range(self, smu, enabled):
        logging.info("set SMU auto range (current): %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        safe_write(smu, f"SENS:CURR:RANG:AUTO {value:s}")

    def smu_set_filter_enable(self, smu, enabled):
        logging.info("set SMU filter enable: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        safe_write(smu, f":SENS:AVER:STATE {value:s}")

    def smu_set_filter_count(self, smu, count):
        logging.info("set SMU filter count: %s", count)
        safe_write(smu, f":SENS:AVER:COUN {count:d}")

    def smu_set_filter_type(self, smu, type):
        logging.info("set SMU filter type: %s", type)
        value = {"repeat": "REP", "moving": "MOV"}[type]
        safe_write(smu, f":SENS:AVER:TCON {value:s}")

    def smu_get_output_state(self, smu):
        return bool(int(smu.resource.query(":OUTP:STAT?")))

    def smu_set_output_state(self, smu, enabled):
        logging.info("set SMU output state: %s", enabled)
        value = {True: "ON", False: "OFF"}[enabled]
        safe_write(smu, f":OUTP:STAT {value:s}")

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

    def initialize(self, smu, lcr):
        self.process.events.message("Initialize...")
        self.process.events.progress(0, 10)

        parameters = self.measurement_item.parameters

        self.smu_detect_model(smu)
        self.lcr_detect_model(lcr)

        if self.process.get("use_environ"):
            with self.devices.get("environ") as env:
                self.env_detect_model(env)

        self.process.events.progress(1, 10)

        # Initialize SMU

        # Bring down SMU voltage if output enabeled
        # Prevents a voltage jump for at device reset.
        self.quick_ramp_zero(smu)
        self.smu_set_output_state(smu, False)
        self.process.events.message("Initialize...")
        self.process.events.progress(2, 10)

        self.smu_reset(smu)
        self.process.events.progress(3, 10)

        route_termination = parameters.get("route_termination", "rear")
        self.smu_set_route_termination(smu, route_termination)
        self.process.events.progress(4, 10)

        sense_mode = parameters.get("sense_mode", "local")
        self.smu_set_sense_mode(smu, sense_mode)
        self.process.events.progress(5, 10)

        current_compliance = parameters.get("current_compliance").to("A").m
        self.smu_set_compliance(smu, current_compliance)
        self.process.events.progress(6, 10)

        self.smu_set_auto_range(smu, True)
        self.process.events.progress(7, 10)

        smu_filter_type = parameters.get("smu_filter_type", "repeat")
        self.smu_set_filter_type(smu, smu_filter_type)
        smu_filter_count = int(parameters.get("smu_filter_count", 10))
        self.smu_set_filter_count(smu, smu_filter_count)
        smu_filter_enable = bool(parameters.get("smu_filter_enable", False))
        self.smu_set_filter_enable(smu, smu_filter_enable)
        self.process.events.progress(8, 10)

        self.smu_set_output_state(smu, True)
        smu_output_state = self.smu_get_output_state(smu)
        self.process.events.state(dict(
            smu_output=smu_output_state,
        ))

        # Initialize LCR

        self.lcr_reset(lcr)
        self.process.events.progress(9, 10)

        self.lcr_setup(lcr)
        self.process.events.progress(10, 10)

    def measure(self, smu, lcr):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        bias_voltage_start = parameters.get("bias_voltage_start").to("V").m
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        bias_voltage_stop = parameters.get("bias_voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        lcr_soft_filter = bool(parameters.get("lcr_soft_filter", True))
        lcr_frequency = parameters.get("lcr_frequency").to("Hz").m
        lcr_amplitude = parameters.get("lcr_amplitude").to("V").m

        # Ramp to start voltage

        smu_voltage_level = self.smu_get_voltage_level(smu)

        logging.info("ramp to start voltage: from %E V to %E V with step %E V", smu_voltage_level, bias_voltage_start, bias_voltage_step)
        for voltage in comet.Range(smu_voltage_level, bias_voltage_start, bias_voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.events.message("Ramp to start... {}".format(auto_unit(voltage, "V")))
            self.smu_set_voltage_level(smu, voltage)
            time.sleep(.100)
            time.sleep(waiting_time)
            self.process.events.state(dict(
                smu_voltage=voltage,
            ))
            # Compliance?
            compliance_tripped = self.smu_compliance_tripped(smu)
            if compliance_tripped:
                logging.error("SMU in compliance")
                raise ValueError("compliance tripped!")

            if not self.process.running:
                break

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
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
            fmt.write_meta("bias_voltage_start", f"{bias_voltage_start:E} V")
            fmt.write_meta("bias_voltage_stop", f"{bias_voltage_stop:E} V")
            fmt.write_meta("bias_voltage_step", f"{bias_voltage_step:E} V")
            fmt.write_meta("current_compliance", f"{current_compliance:E} A")
            fmt.write_meta("ac_frequency", f"{lcr_frequency:E} Hz")
            fmt.write_meta("ac_amplitude", f"{lcr_amplitude:E} V")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            smu_voltage_level = self.smu_get_voltage_level(smu)

            ramp = comet.Range(smu_voltage_level, bias_voltage_stop, bias_voltage_step)
            est = Estimate(ramp.count)
            self.process.events.progress(*est.progress)

            t0 = time.time()

            safe_write(smu, "*CLS")
            # SMU reading format: CURR
            safe_write(smu, ":FORM:ELEM CURR")

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", smu_voltage_level, ramp.end, ramp.step)
            for voltage in ramp:
                self.smu_set_voltage_level(smu, voltage)
                time.sleep(.100)
                # smu_voltage_level = self.smu_get_voltage_level(smu)
                dt = time.time() - t0
                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.events.message("Elapsed {} | Remaining {} | {}".format(elapsed, remaining, auto_unit(voltage, "V")))
                self.process.events.progress(*est.progress)

                # read SMU
                smu_reading = float(smu.resource.query(":READ?").split(',')[0])
                logging.info("SMU reading: %E", smu_reading)


                # read LCR, for CpRp -> prim: Cp, sec: Rp
                if lcr_soft_filter:
                    lcr_prim, lcr_sec = self.acquire_filter_reading(lcr)
                else:
                    lcr_prim, lcr_sec = self.acquire_reading(lcr)
                try:
                    lcr_prim2 = 1.0 / (lcr_prim * lcr_prim)
                except ZeroDivisionError:
                    lcr_prim2 = 0.0

                self.process.events.reading("lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_prim)
                self.process.events.reading("lcr2", abs(voltage) if ramp.step < 0 else voltage, lcr_prim2)

                self.process.events.update()
                self.process.events.state(dict(
                    smu_voltage=voltage,
                    smu_current=smu_reading
                ))

                # Environment
                if self.process.get("use_environ"):
                    with self.devices.get("environ") as env:
                        pc_data = env.resource.query("GET:PC_DATA ?").split(",")
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

                self.process.events.state(dict(
                    env_chuck_temperature=temperature_chuck,
                    env_box_temperature=temperature_box,
                    env_box_humidity=humidity_box
                ))

                # Write reading
                fmt.write_row(dict(
                    timestamp=dt,
                    voltage=voltage,
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
                compliance_tripped = self.smu_compliance_tripped(smu)
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped!")

                if not self.process.running:
                    break

    def finalize(self, smu, lcr):
        self.process.events.progress(1, 2)
        self.process.events.state(dict(
            smu_current=None,
        ))

        self.quick_ramp_zero(smu)
        self.smu_set_output_state(smu, False)
        smu_output_state = self.smu_get_output_state(smu)
        self.process.events.state(dict(
            smu_output=smu_output_state,
        ))

        self.process.events.state(dict(
            env_chuck_temperature=None,
            env_box_temperature=None,
            env_box_humidity=None
        ))

        self.process.events.progress(2, 2)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            with self.devices.get("lcr") as lcr:
                try:
                    self.initialize(smu, lcr)
                    self.measure(smu, lcr)
                finally:
                    self.finalize(smu, lcr)
