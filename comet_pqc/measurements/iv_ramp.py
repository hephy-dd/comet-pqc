import datetime
import logging
import time
import os

import comet

from ..formatter import PQCFormatter
from ..utils import auto_step, safe_filename
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

    def initialize(self, smu):
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

        idn = smu.identification
        logging.info("Using SMU: %s", idn)

        # Beeper off
        smu.system.beeper.status = False
        smu.clear()
        check_error(smu)

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

        # If output enabled
        if smu.output:
            voltage = smu.source.voltage.level
            step = auto_step(voltage, 0, voltage_step)

            logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, step)
            for voltage in comet.Range(voltage, 0, step):
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
            step = auto_step(voltage, voltage_start, voltage_step)

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))
            check_error(smu)

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, step)
            for voltage in comet.Range(voltage, voltage_start, step):
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

        self.process.events.progress(3, 5)

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
        filename = safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}-{contact_name}-{measurement_name}.txt")
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            # Create formatter
            fmt = PQCFormatter(f)
            fmt.add_column("timestamp", ".3f")
            fmt.add_column("voltage", "E")
            fmt.add_column("current", "E")
            fmt.add_column("temperature", "E")
            fmt.add_column("humidity", "E")

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
            step = auto_step(voltage, voltage_stop, voltage_step)

            # SMU reading format: CURR
            smu.resource.write(":FORM:ELEM CURR")
            smu.resource.query("*OPC?")

            t0 = time.time()

            logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, voltage_stop, step)
            for voltage in comet.Range(voltage, voltage_stop, step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.clear()
                smu.source.voltage.level = voltage
                time.sleep(.100)
                # check_error(smu)
                td = time.time() - t0
                reading_current = float(smu.resource.query(":READ?"))
                logging.info("SMU reading: %E A", reading_current)
                self.process.events.reading("series", abs(voltage) if step < 0 else voltage, reading_current)

                # Write reading
                fmt.write_row(dict(
                    timestamp=td,
                    voltage=voltage,
                    current=reading_current,
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

    def finalize(self, smu):
        parameters = self.measurement_item.parameters
        voltage_step = parameters.get("voltage_step").to("V").m
        voltage = smu.source.voltage.level
        step = auto_step(voltage, 0, voltage_step)

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, step)
        for voltage in comet.Range(voltage, 0, step):
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
