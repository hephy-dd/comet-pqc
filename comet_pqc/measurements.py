import logging
import random
import time
import os

import comet
from comet.device import DeviceMixin

__all__ = [
    "measurement_factory",
    "Measurement",
    "MatrixSwitch",
    "IVRamp",
    "BiasIVRamp",
    "CVRamp",
    "CVRampAlt",
    "FourWireIVRamp"
]

def measurement_factory(type, *args, **kwargs):
    """Factory function to create a new measurement instance by type.

    >>> meas = measurement_factory("iv_ramp")
    >>> meas.run()
    """
    for cls in globals().values():
        if hasattr(cls, "type"):
            if cls.type == type:
                return cls(*args, **kwargs)

class Measurement:
    """Base measurement class."""

    type = None

    def __init__(self, process, parameters):
        self.process = process
        self.parameters = parameters

    def run(self, *args, **kwargs):
        """Run measurement."""
        return self.code(**kwargs)

    def code(self, *args, **kwargs):
        """Implement custom measurement logic in method `code()`."""
        raise NotImplementedError(f"Method `{self.__class__.__name__}.code()` not implemented.")

class MatrixSwitch(Measurement, DeviceMixin):
    """Base measurement class wrapping code into matrix configuration."""

    type = None

    def __init__(self, process, parameters):
        super().__init__(process, parameters)

    def setup_matrix(self):
        """Setup marix switch."""
        channels = self.parameters.get("matrix_channels", [])
        logging.info("setup matrix channels: %s", channels)

    def reset_matrix(self):
        """Reset marix switch to a save state."""
        logging.info("reset matrix")

    def run(self, *args, **kwargs):
        logging.info(f"running {self.type}...")
        matrix_enabled = self.parameters.get("matrix_enabled", False)
        result = None
        try:
            if matrix_enabled:
                self.reset_matrix()
                self.setup_matrix()
            result = self.code(*args, **kwargs)
        finally:
            if matrix_enabled:
                # Always reset matrix switch!
                self.reset_matrix()
        logging.info(f"finished {self.type}.")
        return result

class IVRamp(MatrixSwitch):
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


        idn = smu.identification
        logging.info("Using SMU: %s", idn)

        smu.clear()

        # set compliance
        logging.info("set compliance to %E A", current_compliance)
        smu.sense.current.protection.level = current_compliance

        error = smu.system.error
        if error[0]:
            logging.error(error)
            raise RuntimeError(f"{error[0]}: {error[1]}")

        self.process.events.progress(1, 5)

        # If output enabled
        if smu.output:
            voltage = smu.source.voltage.level
            step = -abs(voltage_step) if voltage > 0 else abs(voltage_step)

            logging.info("ramp to zero, from %E V to %E V with step %E V", voltage, 0, step)
            for voltage in comet.Range(voltage, 0, step):
                logging.info("set voltage to %E V", voltage)
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
            step = -abs(voltage_step) if voltage > voltage_start else abs(voltage_step)

            # Get configured READ/FETCh elements
            elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))

            logging.info("ramp to start voltage, from %E V to %E V with step %E V", voltage, voltage_start, step)
            for voltage in comet.Range(voltage, voltage_start, step):
                logging.info("set voltage to %E V", voltage)
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
        current_compliance = self.parameters.get("current_compliance").to("A").m
        voltage_start = self.parameters.get("voltage_start").to("V").m
        voltage_step = self.parameters.get("voltage_step").to("V").m
        voltage_stop = self.parameters.get("voltage_stop").to("V").m
        waiting_time = self.parameters.get("waiting_time").to("s").m
        sense_mode = self.parameters.get("sense_mode")

        if self.process.running:

            with open(os.path.join(self.path, f"{self.type}.txt"), "w") as f:
                # TODO
                f.write(f"voltage_start: {voltage_start:E} V\n")
                f.write(f"voltage_stop: {voltage_stop:E} V\n")
                f.write(f"voltage_step: {voltage_step:E} V\n")
                f.write(f"current_compliance: {current_compliance:E} A\n")
                f.write("timestamp [s],voltage [V],current [A]\n")
                f.flush()

                voltage = smu.source.voltage.level
                step = -abs(voltage_step) if voltage > voltage_stop else abs(voltage_step)

                # Get configured READ/FETCh elements
                elements = list(map(str.strip, smu.resource.query(":FORM:ELEM?").split(",")))

                logging.info("ramp to end voltage, from %E V to %E V with step %E V", voltage, voltage_stop, step)
                for voltage in comet.Range(voltage, voltage_stop, step):
                    logging.info("set voltage to %E V", voltage)
                    smu.clear()
                    smu.source.voltage.level = voltage
                    time.sleep(.100)
                    error = smu.system.error
                    if error[0]:
                        logging.error(error)
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
        step = -abs(voltage_step) if voltage > 0 else abs(voltage_step)

        logging.info("ramp to zero, from %E V to %E V with step %E V", voltage, 0, step)
        for voltage in comet.Range(voltage, 0, step):
            logging.info("set voltage to %E V", voltage)
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

class BiasIVRamp(MatrixSwitch):
    """Bias IV ramp measurement."""

    type = "bias_iv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

class CVRamp(MatrixSwitch):
    """CV ramp measurement."""

    type = "cv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

class CVRampAlt(MatrixSwitch):
    """Alternate CV ramp measurement."""

    type = "cv_ramp_alt"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))

class FourWireIVRamp(MatrixSwitch):
    """4 wire IV ramp measurement."""

    type = "4wire_iv_ramp"

    def code(self, *args, **kwargs):
        time.sleep(random.uniform(2.5, 4.0))
