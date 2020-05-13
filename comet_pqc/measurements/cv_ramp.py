import logging
import datetime
import random
import time
import os
import re

import comet

from ..utils import auto_unit
from ..formatter import PQCFormatter
from ..estimate import Estimate
from .matrix import MatrixMeasurement

__all__ = ["CVRampMeasurement"]

def check_error(device):
    """Test for error."""
    code, message = elm.resource.query(":SYST:ERR?").split(",", 1)
    code = int(code)
    if code != 0:
        message = message.strip("\"")
        logging.error(f"error {code}: {message}")
        raise RuntimeError(f"error {code}: {message}")

def safe_write(device, message):
    """Write, wait for operation complete, test for error."""
    logging.info(f"safe write: {device}: {message}")
    device.resource.write(message)
    device.resource.query("*OPC?")
    check_error(device)

class CVRampMeasurement(MatrixMeasurement):
    """CV ramp measurement."""

    type = "cv_ramp"

    def initialize(self, smu, lcr):
        self.process.events.message("Initialize...")
        self.process.events.progress(0, 10)

        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        sense_mode = parameters.get("sense_mode")
        route_termination = parameters.get("route_termination", "rear")
        smu_filter_enable = bool(parameters.get("smu_filter_enable", False))
        smu_filter_count = int(parameters.get("smu_filter_count", 10))
        smu_filter_type = parameters.get("smu_filter_type", "repeat")

        smu_idn = smu.resource.query("*IDN?")
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None

        self.process.events.progress(1, 10)

        lcr_idn = lcr.resource.query("*IDN?")
        logging.info("Detected LCR Meter: %s", lcr_idn)
        lcr_model = lcr_idn.split(",")[1:][0]

        self.process.events.progress(2, 10)

        smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))
        smu_output_state = bool(int(smu.resource.query(":OUTP:STAT?"))),

        self.process.events.state(dict(
            smu_model=smu_model,
            smu_voltage=smu_voltage_level,
            smu_current=None,
            smu_output=smu_output_state,
            lcr_model=lcr_model
        ))

        # Reset SMU
        safe_write(smu, "*RST")
        safe_write(smu, "*CLS")
        safe_write(smu, ":SYST:BEEP:STAT OFF")

        self.process.events.progress(3, 10)

        # Select rear terminal
        if route_termination == "front":
            safe_write(smu, ":ROUT:TERM FRON")
        elif route_termination == "rear":
            safe_write(smu, ":ROUT:TERM REAR")

        self.process.events.progress(4, 10)

        # set sense mode
        logging.info("set sense mode: '%s'", sense_mode)
        if sense_mode == "remote":
            safe_write(smu, ":SYST:RSEN ON")
        elif sense_mode == "local":
            safe_write(smu, ":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {sense_mode}")

        self.process.events.progress(5, 10)

        # Compliance
        logging.info("set compliance: %E A", current_compliance)
        safe_write(smu, ":SENS:CURR:PROT:LEV {current_compliance:E}")

        self.process.events.progress(6, 10)

        # Range
        safe_write(smu, "SENS:CURR:RANG:AUTO ON")

        self.process.events.progress(7, 10)

        # Filter

        safe_write(smu, f":SENS:AVER:COUN {smu_filter_count:d}")
        if smu_filter_type == "repeat":
            safe_write(smu, ":SENS:AVER:TCON REP")
        elif smu_filter_type == "repeat":
            safe_write(smu, ":SENS:AVER:TCON MOV")

        if smu_filter_enable:
            safe_write(smu, ":SENS:AVER:STATE ON")
        else:
            safe_write(smu, ":SENS:AVER:STATE OFF")

        self.process.events.progress(8, 10)

        # If output disabled
        safe_write(smu, ":SOUR:VOLT:LEV 0")
        safe_write(smu, ":OUTP:STAT ON")
        time.sleep(.100)
        smu_output_state = bool(int(smu.resource.query(":OUTP:STAT?")))

        self.process.events.state(dict(
            smu_output=smu_output_state,
        ))

        # LCR
        safe_write(lcr, "*RST")
        safe_write(lcr, "*CLS")
        safe_write(lcr, ":FREQ 1000")
        safe_write(lcr, f":CURR {current_compliance:E}")
        safe_write(lcr, ":AMPL:ALC ON")

        self.process.events.progress(9, 10)

        if self.process.running:

            smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message("Ramp to start... {}".format(auto_unit(voltage, "V")))
                safe_write(smu, ":SOUR:VOLT:LEV {voltage:E}")
                time.sleep(.100)
                time.sleep(waiting_time)
                smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))
                self.process.events.state(dict(
                    smu_voltage=smu_voltage_level,
                ))
                # Compliance?
                compliance_tripped = bool(int(smu.resource.query(":SENS:CURR:PROT:TRIP")))
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped!")

                if not self.process.running:
                    break

        self.process.events.progress(10, 10)

    def measure(self, smu, lcr):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name =  self.measurement_item.contact.name
        measurement_name =  self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        bias_voltage_start = parameters.get("bias_voltage_start").to("V").m
        bias_voltage_step = parameters.get("bias_voltage_step").to("V").m
        bias_voltage_stop = parameters.get("bias_voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("capacity", "E")
            fmt.add_column("temperature", "E")
            fmt.add_column("humidity", "E")

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
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))

            ramp = comet.Range(smu_voltage_level, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.events.progress(*est.progress)

            t0 = time.time()

            safe_write(smu, "*CLS")

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", smu_voltage_level, ramp.end, ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                safe_write(smu, ":SOUR:VOLT:LEV {voltage:E}")
                time.sleep(.100)
                smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))
                dt = time.time() - t0
                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.events.message("Elapsed {} | Remaining {} | {}".format(elapsed, remaining, auto_unit(voltage, "V")))
                self.process.events.progress(*est.progress)

                # read LCR
                save_write(lcr, ":INIT")
                lcr_prim, lcr_sec = [float(value) for value in lcr.resource.query(":FETC?").split(",")]
                logging.info("LCR reading: prim: %E, sec: %E", lcr_prim, lcr_sec)
                self.process.events.reading("lcr", abs(voltage) if ramp.step < 0 else voltage, lcr_sec)

                self.process.events.update()
                self.process.events.state(dict(
                    smu_voltage=smu_voltage_level,
                    smu_current=None,
                ))

                # Write reading
                fmt.write_row(dict(
                    timestamp=dt,
                    voltage=voltage,
                    capacity=lcr_sec,
                    temperature=float('nan'),
                    humidity=float('nan')
                ))
                fmt.flush()
                time.sleep(waiting_time)

                # Compliance?
                compliance_tripped = bool(int(smu.resource.query(":SENS:CURR:PROT:TRIP")))
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped!")

                if not self.process.running:
                    break

    def finalize(self, smu, lcr):
        parameters = self.measurement_item.parameters
        voltage_step = parameters.get("voltage_step").to("V").m
        smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))

        progress_max = int(round(abs(smu_voltage_level) / abs(voltage_step)))
        progress_step = 0
        self.process.events.progress(progress_step, progress_max)

        self.process.events.state(dict(
            smu_current=None,
        ))

        logging.info("ramp to zero: from %E V to %E V with step %E V", smu_voltage_level, 0, voltage_step)
        for voltage in comet.Range(smu_voltage_level, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            progress_step += 1
            self.process.events.progress(progress_step, progress_max)
            self.process.events.message("Ramp down... {}".format(auto_unit(smu_voltage_level, "V")))
            safe_write(smu, ":SOUR:VOLT:LEV {voltage:E}")
            time.sleep(.100)
            smu_voltage_level = float(smu.resource.query(":SOUR:VOLT:LEV?"))
            self.process.events.state(dict(
                smu_voltage=smu_voltage_level,
            ))

        safe_write(smu, ":OUTP:STAT OFF")

        smu_output_state = bool(int(smu.resource.query(":OUTP:STAT?")))

        self.process.events.state(dict(
            smu_output=smu_output_state,
        ))

        self.process.events.progress(progress_step, progress_max)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            with self.devices.get("lcr") as lcr:
                try:
                    self.initialize(smu, lcr)
                    self.measure(smu, lcr)
                finally:
                    self.finalize(smu, lcr)
