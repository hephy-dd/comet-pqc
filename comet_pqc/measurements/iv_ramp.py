import datetime
import logging
import math
import time
import os
import re

import comet

from ..formatter import PQCFormatter
from ..estimate import Estimate
from .matrix import MatrixMeasurement

__all__ = ["IVRampMeasurement"]

def check_error(smu):
    error = smu.system.error
    if error[0]:
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampMeasurement(MatrixMeasurement):
    """IV ramp measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp"

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

    def initialize(self, smu):
        self.process.events.message("Initialize...")
        self.process.events.progress(0, 5)

        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        sense_mode = parameters.get("sense_mode")
        route_termination = parameters.get("route_termination", "rear")
        smu_filter_enable = bool(parameters.get("smu_filter_enable", False))
        smu_filter_count = int(parameters.get("smu_filter_count", 10))
        smu_filter_type = parameters.get("smu_filter_type", "repeat")

        smu_idn = smu.resource.query("*IDN?")
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None

        if self.process.get("use_environ"):
            with self.devices.get("environ") as env:
                self.env_detect_model(env)

        self.process.events.state(dict(
            smu_model=smu_model,
            smu_voltage=smu.source.voltage.level,
            smu_current=None,
            smu_output=smu.output
        ))

        smu.reset()
        check_error(smu)
        smu.clear()
        check_error(smu)

        # Beeper off
        smu.system.beeper.status = False
        check_error(smu)
        self.process.events.progress(1, 5)

        # Select rear terminal
        if route_termination == "front":
            smu.resource.write(":ROUT:TERM FRONT")
        elif route_termination == "rear":
            smu.resource.write(":ROUT:TERM REAR")
        smu.resource.query("*OPC?")
        check_error(smu)
        self.process.events.progress(2, 5)

        # set sense mode
        logging.info("set sense mode: '%s'", sense_mode)
        if sense_mode == "remote":
            smu.resource.write(":SYST:RSEN ON")
        elif sense_mode == "local":
            smu.resource.write(":SYST:RSEN OFF")
        else:
            raise ValueError(f"invalid sense mode: {sense_mode}")
        smu.resource.query("*OPC?")
        check_error(smu)
        self.process.events.progress(3, 5)

        # Compliance
        logging.info("set compliance: %E A", current_compliance)
        smu.sense.current.protection.level = current_compliance
        check_error(smu)

        # Range
        current_range = 1.05E-6
        smu.resource.write(":SENS:CURR:RANG:AUTO ON")
        smu.resource.query("*OPC?")
        check_error(smu)
        #smu.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #smu.resource.query("*OPC?")
        #check_error(smu)

        # Filter

        smu.resource.write(f":SENS:AVER:COUN {smu_filter_count:d}")
        smu.resource.query("*OPC?")
        check_error(smu)

        if smu_filter_type == "repeat":
            smu.resource.write(":SENS:AVER:TCON REP")
        elif smu_filter_type == "repeat":
            smu.resource.write(":SENS:AVER:TCON MOV")
        smu.resource.query("*OPC?")
        check_error(smu)

        if smu_filter_enable:
            smu.resource.write(":SENS:AVER:STATE ON")
        else:
            smu.resource.write(":SENS:AVER:STATE OFF")
        smu.resource.query("*OPC?")
        check_error(smu)

        self.process.events.progress(5, 5)

        # If output enabled
        if smu.output:
            voltage = smu.source.voltage.level

            logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
            for voltage in comet.Range(voltage, 0, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.source.voltage.level = voltage
                # check_error(smu)
                time.sleep(.100)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            smu.source.voltage.level = voltage
            check_error(smu)
            smu.output = True
            check_error(smu)
            time.sleep(.100)

        self.process.events.progress(2, 5)

        if self.process.running:

            voltage = smu.source.voltage.level

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))
            check_error(smu)

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.source.voltage.level = voltage
                # check_error(smu)
                time.sleep(.100)
                # Returns <elements> comma separated
                #values = list(map(float, smu.resource.query(":READ?").split(",")))
                #data = zip(elements, values)
                time.sleep(waiting_time)
                # Compliance?
                compliance_tripped = smu.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        self.process.events.progress(5, 5)

    def measure(self, smu):
        sample_name = self.sample_name
        sample_type = self.sample_type
        output_dir = self.output_dir
        contact_name =  self.measurement_item.contact.name
        measurement_name =  self.measurement_item.name
        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        voltage_stop = parameters.get("voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m

        if not self.process.running:
            return

        iso_timestamp = comet.make_iso()
        filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("current", "E")
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
            fmt.write_meta("voltage_start", f"{voltage_start:E} V")
            fmt.write_meta("voltage_stop", f"{voltage_stop:E} V")
            fmt.write_meta("voltage_step", f"{voltage_step:E} V")
            fmt.write_meta("current_compliance", f"{current_compliance:E} A")
            fmt.flush()

            # Write header
            fmt.write_header()
            fmt.flush()

            voltage = smu.source.voltage.level

            # SMU reading format: CURR
            smu.resource.write(":FORM:ELEM CURR")
            smu.resource.query("*OPC?")

            t0 = time.time()

            ramp = comet.Range(voltage, voltage_stop, voltage_step)
            est = Estimate(ramp.count)
            self.process.events.progress(*est.progress)

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end,  ramp.step)
            for voltage in ramp:
                logging.info("set voltage: %E V", voltage)
                smu.source.voltage.level = voltage
                time.sleep(.100)
                # check_error(smu)
                td = time.time() - t0
                reading_current = float(smu.resource.query(":READ?").split(',')[0])
                logging.info("SMU reading: %E A", reading_current)
                self.process.events.reading("series", abs(voltage) if ramp.step < 0 else voltage, reading_current)

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

                # Write reading
                fmt.write_row(dict(
                    timestamp=td,
                    voltage=voltage,
                    current=reading_current,
                    temperature_box=temperature_box,
                    temperature_chuck=temperature_chuck,
                    humidity_box=humidity_box
                ))
                fmt.flush()
                time.sleep(waiting_time)

                est.next()
                elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                self.process.events.message(f"Elapsed {elapsed} | Remaining {remaining} | {voltage:.3f} V")
                self.process.events.progress(*est.progress)

                # Compliance?
                compliance_tripped = smu.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped")
                # check_error(smu)
                if not self.process.running:
                    break

        self.process.events.progress(0, 0)

    def finalize(self, smu):
        parameters = self.measurement_item.parameters
        voltage_step = parameters.get("voltage_step").to("V").m
        voltage = smu.source.voltage.level

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, voltage_step)
        for voltage in comet.Range(voltage, 0, voltage_step):
            logging.info("set voltage: %E V", voltage)
            self.process.events.message(f"{voltage:.3f} V")
            smu.source.voltage.level = voltage
            time.sleep(.100)
            # check_error(smu)

        smu.output = False
        check_error(smu)

        self.process.events.progress(5, 5)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            try:
                self.initialize(smu)
                self.measure(smu)
            finally:
                self.finalize(smu)
