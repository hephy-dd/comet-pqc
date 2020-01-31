import random
import time

import comet

class CalibrateProcess(comet.Process):
    """Calibration process for CORVUS table."""

    def run(self):
        steps = 8
        self.push("message", "Calibrating...")
        for i in range(steps):
            self.push("progress", i + 1, steps)
            time.sleep(1)
        self.push("message", None)

class MeasureProcess(comet.Process):
    """Measure process executing a sequence of measurements."""

    def run(self):
        self.push("message", "Measuring...")
        config = self.sequence_config
        for item in config.items:
            if not self.running:
                break
            for measurement in item.measurements:
                if not self.running:
                    break
                self.push("progress", 0, 0)
                self.push("show_panel", measurement.type)
                self.push("message", f"Measuring {item.name} {measurement.name}...")
                time.sleep(random.uniform(2.5, 4.0))
        self.push("message", None)
