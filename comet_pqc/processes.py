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

    auto_continue = True
    wait_for_continue = False
    wait_interval = .25

    def wait(self):
        self.wait_for_continue = True
        self.push("enable_continue")
        self.push("message", "Waiting for user to continue...")
        while self.wait_for_continue:
            if not self.running:
                return False
            time.sleep(self.wait_interval)
        return True

    def run(self):
        self.push("message", "Measuring...")
        config = self.sequence_config
        count = 0
        for item in config.items:
            for measurement in item.measurements:
                count += 1
        step = 0
        for item in config.items:
            if not self.running:
                break
            for measurement in item.measurements:
                if not self.auto_continue:
                    if not self.wait():
                        break
                if not self.running:
                    break
                step += 1
                self.push("progress", step, count)
                self.push("show_panel", measurement.type)
                self.push("message", f"Measuring {item.name} {measurement.name}...")
                time.sleep(random.uniform(2.5, 4.0))

        self.push("message", None)
