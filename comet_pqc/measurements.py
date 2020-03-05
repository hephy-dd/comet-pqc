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

    def run(self, *args, **kwargs):
        """Run measurement."""
        return self.code(**kwargs)

    def code(self, *args, **kwargs):
        """Implement custom measurement logic in method `code()`."""
        raise NotImplementedError(f"Method `{self.__class__.__name__}.code()` not implemented.")

class MatrixSwitch(Measurement, DeviceMixin):
    """Base measurement class wrapping code into matrix configuration."""

    type = None

    def __init__(self):
        super().__init__()

    def setup_matrix(self):
        """Setup marix switch."""
        logging.info("setup matrix")

    def reset_matrix(self):
        """Reset marix switch to a save state."""
        logging.info("reset matrix")

    def run(self, *args, **kwargs):
        logging.info(f"starting {self.type}")
        result = None
        exception = None
        try:
            self.reset_matrix()
            self.setup_matrix()
            result = self.code(*args, **kwargs)
        except Exception as e:
            # Re-raise exception after matrix switch reset!
            exception = e
        finally:
            # Always reset matrix switch!
            self.reset_matrix()
        if exception is not None:
            raise exception
        logging.info(f"finished {self.type}")
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

    def code(self, proc, parameters, path, *args, **kwargs):
        # Collect measurement parameters
        current_compliance = parameters.get("current_compliance").to("A").m
        voltage_start = parameters.get("voltage_start").to("V").m
        voltage_step = parameters.get("voltage_step").to("V").m
        voltage_stop = parameters.get("voltage_stop").to("V").m
        waiting_time = parameters.get("waiting_time").to("s").m
        sense_mode = parameters.get("sense_mode")

        with self.devices.get("k2410") as k2410:
            idn = k2410.identification
            logging.info("Using SMU: %s", idn)

            # set compliance
            logging.info("set compliance to %E A", current_compliance)
            k2410.sense.current.protection.level = current_compliance

            proc.events.progress(1, 5)

            # Holds the current source voltage throughout the entire measurement.
            value = 0.0

            # If output enabled
            if k2410.output:
                logging.info("ramp to zero")
                value = k2410.source.voltage.level
                step = -abs(voltage_step) if value > 0 else abs(voltage_step)
                for value in comet.Range(value, 0, step):
                    logging.info("set voltage to %E V", value)
                    k2410.source.voltage.level = value
                    time.sleep(.100)
                    if not proc.running:
                        break
            # If output disabled
            else:
                value = 0
                k2410.source.voltage.level = value
                k2410.output = True
                time.sleep(.100)

            proc.events.progress(2, 5)

            compliance_tripped = False

            if proc.running:

                logging.info("ramp to start voltage")
                step = -abs(voltage_step) if value > voltage_start else abs(voltage_step)
                for value in comet.Range(value, voltage_start, step):
                    logging.info("set voltage to %E V", value)
                    k2410.source.voltage.level = value
                    time.sleep(.100)
                    data = k2410.read()
                    time.sleep(waiting_time)
                    # Compliance?
                    compliance_tripped = k2410.sense.current.protection.tripped
                    if compliance_tripped:
                        logging.error("SMU in compliance")
                        break
                    if not proc.running:
                        break

            proc.events.progress(3, 5)

            if proc.running:
                if not compliance_tripped:

                    with open(os.path.join(path, f"{self.type}.txt"), "w") as f:
                        f.write(f"voltage_start: {voltage_start:E} V")
                        f.write(os.linesep)
                        f.write(f"voltage_stop: {voltage_stop:E} V")
                        f.write(os.linesep)
                        f.write(f"voltage_step: {voltage_step:E} V")
                        f.write(os.linesep)
                        f.write(f"current_compliance: {current_compliance:E} A")
                        f.write(os.linesep)

                        logging.info("ramp to end voltage")
                        step = -abs(voltage_step) if value > voltage_stop else abs(voltage_step)
                        for value in comet.Range(value, voltage_start, step):
                            logging.info("set voltage to %E V", value)
                            k2410.source.voltage.level = value
                            time.sleep(.100)
                            data = k2410.read()
                            f.write(format(data))
                            f.write(os.linesep)
                            time.sleep(waiting_time)
                            # Compliance?
                            compliance_tripped = k2410.sense.current.protection.tripped
                            if compliance_tripped:
                                logging.error("SMU in compliance")
                                break

            proc.events.progress(4, 5)

            logging.info("ramp to zero")
            #voltage = k2410.source.voltage.level
            step = -abs(voltage_step) if value > 0 else abs(voltage_step)
            for value in comet.Range(value, 0, step):
                logging.info("set voltage to %E V", value)
                k2410.source.voltage.level = value
                time.sleep(.100)

            k2410.output = False

            proc.events.progress(5, 5)

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
