import logging
import time
import os

import comet

from .matrix import MatrixMeasurement

__all__ = ["IVRampMeasurement"]

# TODO: integrate into comet.Range
def auto_step(start, stop, step):
    """Returns positive/negative step according to start and stop value."""
    return -abs(step) if start > stop else abs(step)

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

        current_compliance = self.parameters.get("current_compliance").to("A").m
        voltage_start = self.parameters.get("voltage_start").to("V").m
        voltage_step = self.parameters.get("voltage_step").to("V").m
        waiting_time = self.parameters.get("waiting_time").to("s").m
        sense_mode = self.parameters.get("sense_mode")


        idn = smu.identification
        logging.info("Using SMU: %s", idn)

        # Beeper off
        smu.system.beeper.status = False
        smu.clear()

        # set sense mode
        logging.info("set sense mode: '%s'", sense_mode)
        if sense_mode == "remote":
            smu.resource.write(":SYST:RSEN ON")
        else:
            smu.resource.write(":SYST:RSEN OFF")
        smu.resource.query("*OPC?")

        # set compliance
        logging.info("set compliance: %E A", current_compliance)
        smu.sense.current.protection.level = current_compliance

        error = smu.system.error
        if error[0]:
            logging.error(error)
            raise RuntimeError(f"{error[0]}: {error[1]}")

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
                time.sleep(.100)
                if not self.process.running:
                    break
        # If output disabled
        else:
            voltage = 0
            smu.source.voltage.level = voltage
            smu.output = True
            time.sleep(.100)

        error = smu.system.error
        if error[0]:
            logging.error(error)
            raise RuntimeError(f"{error[0]}: {error[1]}")

        self.process.events.progress(2, 5)

        if self.process.running:

            voltage = smu.source.voltage.level
            step = auto_step(voltage, voltage_start, voltage_step)

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))

            logging.info("ramp to start voltage: from %E V to %E V with step %E V", voltage, voltage_start, step)
            for voltage in comet.Range(voltage, voltage_start, step):
                logging.info("set voltage: %E V", voltage)
                self.process.events.message(f"{voltage:.3f} V")
                smu.source.voltage.level = voltage
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
        sample_name = self.process.get('sample_name')
        measurement_name = self.process.get('measurement_name')
        current_compliance = self.parameters.get("current_compliance").to("A").m
        voltage_start = self.parameters.get("voltage_start").to("V").m
        voltage_step = self.parameters.get("voltage_step").to("V").m
        voltage_stop = self.parameters.get("voltage_stop").to("V").m
        waiting_time = self.parameters.get("waiting_time").to("s").m

        if self.process.running:

            with open(os.path.join(self.path, f"{sample_name}-{measurement_name}.txt".replace(" ", "_")), "w") as f:
                # TODO
                f.write(f"sample_name: {sample_name}\n")
                f.write(f"measurement_name: {measurement_name}\n")
                f.write(f"voltage_start: {voltage_start:E} V\n")
                f.write(f"voltage_stop: {voltage_stop:E} V\n")
                f.write(f"voltage_step: {voltage_step:E} V\n")
                f.write(f"current_compliance: {current_compliance:E} A\n")
                f.write("timestamp [s],voltage [V],current [A]\n")
                f.flush()

                voltage = smu.source.voltage.level
                step = auto_step(voltage, voltage_stop, voltage_step)

                # Get configured READ/FETCh elements
                elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))

                logging.info("ramp to end voltage: from %E V to %E V with step %E V", voltage, voltage_stop, step)
                for voltage in comet.Range(voltage, voltage_stop, step):
                    logging.info("set voltage: %E V", voltage)
                    self.process.events.message(f"{voltage:.3f} V")
                    smu.clear()
                    smu.source.voltage.level = voltage
                    time.sleep(.100)
                    error = smu.system.error
                    if error[0]:
                        logging.error(error)
                        self.process.events.message(error)
                        smu.clear()
                        #raise RuntimeError(f"{error[0]}: {error[1]}")
                    timestamp = time.time()
                    # Returns <elements> comma separated
                    values = list(map(float, smu.resource.query(":READ?").split(",")))
                    error = smu.system.error
                    if error[0]:
                        logging.error(error)
                        smu.clear()
                        #raise RuntimeError(f"{error[0]}: {error[1]}")
                    data = dict(zip(elements, values))
                    reading_voltage = data.get("VOLT")
                    reading_current = data.get("CURR")
                    logging.info("SMU reading: %E V %E A", reading_voltage, reading_current)
                    self.process.events.reading("series", abs(voltage) if step < 0 else voltage, reading_current)
                    # TODO
                    f.write(f"{timestamp:.3f},{voltage:E},{reading_current:E}\n")
                    f.flush()
                    time.sleep(waiting_time)
                    # Compliance?
                    compliance_tripped = smu.sense.current.protection.tripped
                    if compliance_tripped:
                        logging.error("SMU in compliance")
                        raise ValueError("compliance tripped")
                    error = smu.system.error
                    if error[0]:
                        logging.error(error)
                        smu.clear()
                        #raise RuntimeError(f"{error[0]}: {error[1]}")
                    if not self.process.running:
                        break

        self.process.events.progress(4, 5)

    def finalize(self, smu):
        voltage_step = self.parameters.get("voltage_step").to("V").m
        voltage = smu.source.voltage.level
        step = auto_step(voltage, 0, voltage_step)

        logging.info("ramp to zero: from %E V to %E V with step %E V", voltage, 0, step)
        for voltage in comet.Range(voltage, 0, step):
            logging.info("set voltage: %E V", voltage)
            self.process.events.message(f"{voltage:.3f} V")
            smu.source.voltage.level = voltage
            time.sleep(.100)

        smu.output = False

        self.process.events.progress(5, 5)

    def code(self, path, *args, **kwargs):
        self.path = path
        with self.devices.get("k2410") as smu:
            try:
                self.initialize(smu)
                self.measure(smu)
            finally:
                self.finalize(smu)
