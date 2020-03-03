import logging
import random
import time
import threading

import comet

from .measurements import measurement_factory

class CalibrateProcess(comet.Process):
    """Calibration process for Corvus table."""

    def run(self):
        steps = 8
        self.events.message("Calibrating...")
        for i in range(steps):
            self.events.progress(i + 1, steps)
            time.sleep(1)
        self.events.message(None)

class MeasureProcess(comet.Process):
    """Measure process executing a sequence of measurements."""

    wafers = []

    manual_mode = False
    auto_continue = True
    wait_for_continue = threading.Event()
    wait_interval = .25

    def pause(self):
        self.wait_for_continue.set()
        while self.wait_for_continue.is_set():
            if not self.running:
                return False
            time.sleep(self.wait_interval)
        return True

    def unpause(self):
        self.wait_for_continue.clear()

    def run_measurement(self, item, measurement):
        self.events.show_panel(item, measurement)
        self.pause()
        measurement = measurement_factory(measurement.type)
        if measurement is None:
            raise RuntimeError(f"No such measurement '{measurement.type}'")
        try:
            measurement.run()
        except Exception as e:
            raise e

    def count_measurements(self):
        count = 0
        for wafer in self.wafers:
            for item in wafer["sequence_config"].items:
                if item.enabled:
                    for measurement in item.measurements:
                        if measurement.enabled:
                            count += 1
        return count

    def pick_positions(self, wafer):
        positions = []
        wafer_config = wafer["wafer_config"]
        # TODO
        for position in (wafer_config.positions[0], wafer_config.positions[-1]):
            data = {}
            self.events.message(f"Move to {position.name} @{wafer_config.name} [{position.pos.x}, {position.pos.y}]")
            self.events.move_to(position.name, data)
            if not self.pause():
                return
            positions.append(data.get("point"))
            if not self.running:
                return
        for index, item in enumerate(wafer["sequence_config"].items):
            # TODO: Calculate item (flute) coordinates based on picked positions
            item.pos = positions[0]

    def pick_position(self, item, wafer):
        item.pos = None
        data = {}
        # Find position for item (flute)
        wafer_config = wafer["wafer_config"]
        position = list(filter(lambda position: position.id == item.position, wafer_config.positions))[0]
        self.events.message(f"Move to {item.name} @{wafer_config.name} [{position.pos.x}, {position.pos.y}]")
        self.events.move_to(item.name, data)
        if not self.pause():
            return
        item.pos = data.get("point")

    def run(self):
        self.events.message("Measuring...")
        self.wait_for_continue.clear()
        # Count measurements
        count = self.count_measurements()
        step = 0
        for wafer in self.wafers:
            sequence_config = wafer["sequence_config"]
            for item in sequence_config.items:
                item.pos = None
        # In default mode, pick positions for every wafer
        if not self.manual_mode:
            for wafer in self.wafers:
                self.pick_positions(wafer)
                if not self.running:
                    return
        for wafer in self.wafers:
            wafer_config = wafer["wafer_config"]
            sequence_config = wafer["sequence_config"]
            for item in sequence_config.items:
                if not self.running:
                    break
                item.locked = True
                if item.enabled:
                    item.state = "ACTIVE"
                    # In manual mode, pick current position (flute)
                    if self.manual_mode:
                        self.pick_position(item, wafer)
                        if not self.running:
                            break
                    for measurement in item.measurements:
                        measurement.locked = True
                        if measurement.enabled:
                            measurement.state = "ACTIVE"
                            if not self.auto_continue:
                                self.events.enable_continue()
                                self.events.message("Waiting for user to continue...")
                                if not self.pause():
                                    break
                            if not self.running:
                                break
                            self.events.progress(step, count)
                            self.events.message(f"Measuring {item.name} {measurement.name} @{wafer_config.name}...")
                            self.run_measurement(item, measurement)
                            measurement.state = "DONE"
                            self.events.append_summary(measurement.name, random.random())
                            step += 1

                # Lock all before next flute
                for measurement in item.measurements:
                    measurement.locked = True
                item.state = "DONE"
        self.events.message("Done.")
