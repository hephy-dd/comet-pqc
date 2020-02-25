import logging
import random
import time
import threading

import comet

from .measurements import measurement_factory

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
        self.push("show_panel", item, measurement)
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

    def pick_references(self, wafer):
        positions = []
        wafer_config = wafer["wafer_config"]
        for reference in wafer_config.references:
            data = {}
            self.push("message", f"Move to {reference.name} @{wafer_config.name} [{reference.pos.x}, {reference.pos.y}]")
            self.push("move_to", reference.name, data)
            if not self.pause():
                return
            positions.append(data.get("point"))
            if not self.running:
                return
        for index, item in enumerate(wafer["sequence_config"].items):
            # TODO: Calculate item (flute) coordinates based on picked references
            item.pos = positions[0]

    def pick_socket(self, item, wafer):
        item.pos = None
        data = {}
        # Find socket for item (flute)
        wafer_config = wafer["wafer_config"]
        socket = list(filter(lambda socket: socket.id == item.socket, wafer_config.sockets))[0]
        self.push("message", f"Move to {item.name} @{wafer_config.name} [{socket.pos.x}, {socket.pos.y}]")
        self.push("move_to", item.name, data)
        if not self.pause():
            return
        item.pos = data.get("point")

    def run(self):
        self.push("message", "Measuring...")
        self.wait_for_continue.clear()
        # Count measurements
        count = self.count_measurements()
        step = 0
        for wafer in self.wafers:
            sequence_config = wafer["sequence_config"]
            for item in sequence_config.items:
                item.pos = None
        # In default mode, pick reference points for every wafer
        if not self.manual_mode:
            for wafer in self.wafers:
                self.pick_references(wafer)
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
                    # In manual mode, pick current socket (flute)
                    if self.manual_mode:
                        self.pick_socket(item, wafer)
                        if not self.running:
                            break
                    for measurement in item.measurements:
                        measurement.locked = True
                        if measurement.enabled:
                            measurement.state = "ACTIVE"
                            if not self.auto_continue:
                                self.push("enable_continue")
                                self.push("message", "Waiting for user to continue...")
                                if not self.pause():
                                    break
                            if not self.running:
                                break
                            self.push("progress", step, count)
                            self.push("message", f"Measuring {item.name} {measurement.name} @{wafer_config.name}...")
                            self.run_measurement(item, measurement)
                            measurement.state = "DONE"
                            self.push("append_summary", measurement.name, random.random())
                            step += 1

                # Lock all before next flute
                for measurement in item.measurements:
                    measurement.locked = True
                item.state = "DONE"
        self.push("message", "Done.")
