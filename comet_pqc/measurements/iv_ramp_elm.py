import datetime
import logging
import time
import os
import re

import comet

from ..estimate import Estimate
from ..formatter import PQCFormatter
from .matrix import MatrixMeasurement

__all__ = ["IVRampElmMeasurement"]

def check_error(smu):
    error = smu.system.error
    if error[0]:
        logging.error(error)
        raise RuntimeError(f"{error[0]}: {error[1]}")

class IVRampElmMeasurement(MatrixMeasurement):
    """IV ramp with electrometer measurement.

    * set compliance
    * if output enabled brings source voltage to zero
    * ramps to start voltage
    * ramps to end voltage
    * ramps back to zero

    In case of compliance, stop requests or errors ramps to zero before exit.
    """

    type = "iv_ramp_elm"

    def initialize(self, smu, elm):
        self.process.events.progress(0, 5)

        parameters = self.measurement_item.parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        sense_mode = parameters.get("sense_mode")
        route_termination = parameters.get("route_termination")
        average_enabled = bool(parameters.get("average_enabled"))
        average_count = int(parameters.get("average_count"))
        average_type = parameters.get("average_type")
        zero_correction = parameters.get("zero_correction")
        integration_rate = parameters.get("integration_rate")

        smu_idn = smu.identification
        logging.info("Detected SMU: %s", smu_idn)
        result = re.search(r'model\s+([\d\w]+)', smu_idn, re.IGNORECASE).groups()
        smu_model = ''.join(result) or None

        self.process.events.progress(1, 5)

        elm_idn = elm.identification
        logging.info("Detected Electrometer: %s", elm_idn)
        result = re.search(r'model\s+([\d\w]+)', elm_idn, re.IGNORECASE).groups()
        elm_model = ''.join(result) or None

        self.process.events.progress(2, 5)

        self.process.events.state(dict(
            smu_model=smu_model,
            smu_voltage=smu.source.voltage.level,
            smu_current=None,
            smu_output=smu.output,
            elm_model=elm_model,
            elm_current=None,
        ))

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
                self.process.events.state(dict(
                    smu_voltage=voltage
                ))
                if not self.process.running:
                    break

        # Beeper off
        smu.reset()
        smu.clear()
        smu.system.beeper.status = False
        check_error(smu)

        self.process.events.state(dict(
            smu_voltage=smu.source.voltage.level,
            smu_current=None,
            smu_output=smu.output,
            elm_current=None
        ))

        # Select rear terminal
        if route_termination == "front":
            smu.resource.write(":ROUT:TERM FRONT")
        elif route_termination == "rear":
            smu.resource.write(":ROUT:TERM REAR")
        smu.resource.query("*OPC?")
        check_error(smu)

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

        # Compliance
        logging.info("set compliance: %E A", current_compliance)
        smu.sense.current.protection.level = current_compliance
        check_error(smu)

        # Range
        current_range = 1.05E-6
        smu.resource.write(":SENS:CURR:RANG:AUTO ON")
        smu.resource.write(":SENS:VOLT:RANG:AUTO ON")
        smu.resource.query("*OPC?")
        check_error(smu)
        #smu.resource.write(f":SENS:CURR:RANG {current_range:E}")
        #smu.resource.query("*OPC?")
        #check_error(smu)

        # Filter
        if average_enabled:
            smu.resource.write(":SENS:AVER:STATE ON")
        else:
            smu.resource.write(":SENS:AVER:STATE OFF")
        smu.resource.query("*OPC?")
        check_error(smu)
        smu.resource.write(f":SENS:AVER:COUN {average_count:d}")
        smu.resource.query("*OPC?")
        check_error(smu)
        if average_type == "repeat":
            smu.resource.write(":SENS:AVER:TCON REP")
        elif average_type == "repeat":
            smu.resource.write(":SENS:AVER:TCON MOV")
        smu.resource.query("*OPC?")
        check_error(smu)

        self.process.events.progress(1, 5)

        # If output disabled
        voltage = 0
        smu.source.voltage.level = voltage
        check_error(smu)
        smu.output = True
        check_error(smu)
        time.sleep(.100)

        self.process.events.state(dict(
            smu_output=smu.output
        ))

        self.process.events.progress(2, 5)

        if self.process.running:

            voltage = smu.source.voltage.level

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, voltage_step)
            for voltage in comet.Range(voltage, voltage_start, voltage_step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.source.voltage.level = voltage
                # check_error(smu)
                time.sleep(.100)
                time.sleep(waiting_time)

                self.process.events.state(dict(
                    smu_voltage=voltage,
                ))
                # Compliance?
                compliance_tripped = smu.sense.current.protection.tripped
                if compliance_tripped:
                    logging.error("SMU in compliance")
                    raise ValueError("compliance tripped")
                if not self.process.running:
                    break

        def elm_safe_write(message):
            """Write, wait for operation complete, test for errors."""
            elm.resource.write(message)
            elm.resource.query("*OPC?")
            code, label = elm.resource.query(":SYST:ERR?").split(",", 1)
            code = int(code)
            label = label.strip("\"")
            if code != 0:
                logging.error(f"error {code}: {label} returned by '{message}'")
                raise RuntimeError(f"error {code}: {label} returned by '{message}'")

        elm_safe_write("*RST")
        elm_safe_write("*CLS")

        nplc = integration_rate / 10.
        elm_safe_write(f":SENS:VOLT:NPLC {nplc:02f}") # 20pA

        elm_safe_write(":SYST:ZCH ON") # enable zero check
        assert elm.resource.query(":SYST:ZCH?") == '1', "failed to enable zero check"

        elm_safe_write(":SENS:FUNC 'CURR'") # note the quotes!
        assert elm.resource.query(":SENS:FUNC?") == '"CURR:DC"', "failed to set sense function to current"

        elm_safe_write(":SENS:CURR:RANG 20e-12") # 20pA
        if zero_correction:
            elm_safe_write(":SYST:ZCOR ON") # perform zero correction
        elm_safe_write(":SENS:CURR:RANG:AUTO ON")
        elm_safe_write(":SENS:CURR:RANG:AUTO:LLIM 2.000000E-11")
        elm_safe_write(":SENS:CURR:RANG:AUTO:ULIM 2.000000E-2")

        elm_safe_write(":SYST:ZCH OFF") # disable zero check
        assert elm.resource.query(":SYST:ZCH?") == '0', "failed to disable zero check"

        self.process.events.progress(3, 5)

    def measure(self, smu, elm):
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

        if self.process.running:
            iso_timestamp = comet.make_iso()
            filename = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
            with open(os.path.join(output_dir, filename), "w", newline="") as f:
                # Create formatter
                fmt = PQCFormatter(f)
                fmt.add_column("timestamp", ".3f")
                fmt.add_column("voltage", "E")
                fmt.add_column("current_smu", "E")
                fmt.add_column("current_elm", "E")
                fmt.add_column("temperature", "E")
                fmt.add_column("humidity", "E")

                # Write meta data
                fmt.write_meta("sample_name", sample_name)
                fmt.write_meta("sample_type", sample_type)
                fmt.write_meta("contact_name", contact_name)
                fmt.write_meta("measurement_name", measurement_name)
                fmt.write_meta("measurement_type", self.type)
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

                # Electrometer reading format: READ
                elm.resource.write(":FORM:ELEM READ")
                elm.resource.query("*OPC?")

                ramp = comet.Range(voltage, voltage_stop, voltage_step)
                est = Estimate(ramp.count)
                self.process.events.progress(*est.progress)

                t0 = time.time()

                logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, ramp.end, ramp.step)
                for voltage in ramp:
                    logging.info("set voltage: %E V", voltage)
                    smu.clear()
                    smu.source.voltage.level = voltage
                    time.sleep(.100)
                    # check_error(smu)
                    dt = time.time() - t0

                    est.next()
                    elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
                    remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
                    self.process.events.message(f"Elapsed {elapsed} | Remaining {remaining} | {voltage:.3f} V")
                    self.process.events.progress(*est.progress)

                    # read SMU
                    smu_reading = float(smu.resource.query(":READ?").split(',')[0])
                    logging.info("SMU reading: %E", smu_reading)
                    self.process.events.reading("smu", abs(voltage) if ramp.step < 0 else voltage, smu_reading)

                    # read ELM
                    elm_reading = float(elm.resource.query(":READ?").split(',')[0])
                    logging.info("ELM reading: %E", elm_reading)
                    self.process.events.reading("elm", abs(voltage) if ramp.step < 0 else voltage, elm_reading)

                    self.process.events.update()
                    self.process.events.state(dict(
                        smu_voltage=voltage,
                        smu_current=smu_reading,
                        elm_current=elm_reading
                    ))

                    # Write reading
                    fmt.write_row(dict(
                        timestamp=dt,
                        voltage=voltage,
                        current_smu=smu_reading,
                        current_elm=elm_reading,
                        temperature=float('nan'),
                        humidity=float('nan')
                    ))
                    fmt.flush()
                    time.sleep(waiting_time)

                    # Compliance?
                    compliance_tripped = smu.sense.current.protection.tripped
                    if compliance_tripped:
                        logging.error("SMU in compliance")
                        raise ValueError("compliance tripped")
                    # check_error(smu)
                    if not self.process.running:
                        break

        self.process.events.progress(4, 5)

    def finalize(self, smu, elm):
        elm.resource.write(":SYST:ZCH ON")
        elm.resource.query("*OPC?")

        self.process.events.state(dict(
            smu_current=None,
            elm_current=None
        ))

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
            self.process.events.state(dict(
                smu_voltage=voltage,
            ))

        smu.output = False
        check_error(smu)

        self.process.events.state(dict(
            smu_output=smu.output,
        ))

        self.process.events.progress(5, 5)

    def code(self, *args, **kwargs):
        with self.devices.get("k2410") as smu:
            with self.devices.get("k6517") as elm:
                try:
                    self.initialize(smu, elm)
                    self.measure(smu, elm)
                finally:
                    self.finalize(smu, elm)
