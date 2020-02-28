import logging
import os
import sys

import comet
from comet.driver.keithley import K707B
from comet.driver.keithley import K2657A
from comet.driver.keysight import E4980A
from comet.driver.keithley import K6517B
from comet.driver.keithley import K2410
from comet.driver.corvus import Venus1

from . import config
from . import __version__

from .processes import CalibrateProcess
from .processes import MeasureProcess

from .panels import IVRamp
from .panels import BiasIVRamp
from .panels import CVRamp
from .panels import CVRampAlt
from .panels import FourWireIVRamp

class SequenceTree(comet.Tree):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = ["Measurement", "State"]

def main():
    app = comet.Application(
        name="comet-pqc",
        version=__version__,
        title=f"PQC {__version__}",
        about=f"COMET application for PQC measurements, version {__version__}."
    )

    # Register devices
    app.devices.add("matrix", K707B(comet.Resource(
        resource_name="TCPIP::10.0.0.2::23::SOCKET",
        encoding='latin1',
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("smu1", K2657A(comet.Resource(
        resource_name="TCPIP::10.0.0.3::23::SOCKET",
        encoding='latin1',
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("lcr", E4980A(comet.Resource(
        resource_name="TCPIP::10.0.0.4::5025::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("elm", K6517B(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10001::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("smu2", K2410(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10002::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.add("corvus", Venus1(comet.Resource(
        resource_name="TCPIP::10.0.0.6::23::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.load_settings()

    def load_chucks():
        select = app.layout.get("chuck_select")
        select.clear()
        for name, filename in sorted(config.list_configs(config.CHUCK_DIR)):
            select.append(config.load_chuck(filename))

    def load_wafers():
        select = app.layout.get("wafer_select")
        select.clear()
        for name, filename in sorted(config.list_configs(config.WAFER_DIR)):
            select.append(config.load_wafer(filename))

    def load_sequences():
        select = app.layout.get("sequence_select")
        select.clear()
        for name, filename in sorted(config.list_configs(config.SEQUENCE_DIR)):
            select.append(config.load_sequence(filename))

    def on_sequence_changed(index, item):
        dashboard = app.layout.get("dashboard")
        for panel in dashboard.children:
            panel.visible = False
        select = app.layout.get("sequence_select")
        tree = app.layout.get("sequence_tree")
        tree.clear()
        for item in select.selected.items:
            sequence_item = tree.append([item.name, ""])
            sequence_item.name = item.name
            sequence_item.position = item.position
            sequence_item.description = item.description
            sequence_item[0].checkable = True
            sequence_item[0].checked = item.enabled
            for measurement in item.measurements:
                measurement_item = sequence_item.append([measurement.name, ""])
                measurement_item.name = measurement.name
                measurement_item.type = measurement.type
                measurement_item.parameters = measurement.parameters.copy()
                measurement_item.description = measurement.description
                import random
                measurement_item.series = {}
                measurement_item[0].checkable = True
                measurement_item[0].checked = measurement.enabled
        tree.fit()

    def on_tree_selected(item):
        dashboard = app.layout.get("dashboard")
        for panel in dashboard.children:
            panel.visible = False
        if item.qt.parent():
            panel = app.layout.get(item.type)
            panel.visible = True
            panel.load(item)

    def on_tree_locked(state):
        for item in app.layout.get("sequence_tree"):
            item.checkable = not state
            for measurement in item.children:
                measurement.checkable = not state

    def on_calibrate_start():
        app.layout.get("calibrate_button").enabled = False
        app.layout.get("start_button").enabled = False
        app.layout.get("autopilot_button").enabled = False
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = False
        app.processes.get("calibrate").start()

    def on_calibrate_finished():
        app.layout.get("calibrate_button").enabled = True
        app.layout.get("start_button").enabled = True
        app.layout.get("autopilot_button").enabled = True
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = False

    def on_measure_start():
        app.layout.get("calibrate_button").enabled = False
        app.layout.get("start_button").enabled = False
        app.layout.get("autopilot_button").enabled = True
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = True
        on_tree_locked(True)
        app.processes.get("measure").start()

    def on_measure_continue():
        pass

    def on_measure_stop():
        app.layout.get("stop_button").enabled = False
        app.layout.get("autopilot_button").enabled = False
        app.layout.get("continue_button").enabled = False
        app.processes.get("measure").stop()

    def on_measure_finished():
        app.layout.get("calibrate_button").enabled = True
        app.layout.get("start_button").enabled = True
        app.layout.get("autopilot_button").enabled = True
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = False
        on_tree_locked(False)

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        comet.show_exception(exc, tb)

    def on_message(message):
        app.message = message

    def on_progress(value, maximum):
        app.progress = value, maximum

    app.processes.add("calibrate", CalibrateProcess(
        finished=on_calibrate_finished,
        message=on_message,
        progress=on_progress
    ))
    app.processes.add("measure", MeasureProcess(
        finished=on_measure_finished,
        failed=on_show_error,
        message=on_message,
        progress=on_progress,
        ###move_to=on_move_to,
        ###show_panel=on_show_panel,
        ###enable_continue=on_enable_continue,
        ###append_summary=on_append_summary
    ))

    app.layout = comet.Row(
        comet.Column(
            comet.Row(
                comet.Column(
                    comet.Label("Sample"),
                    comet.Label("Chuck"),
                    comet.Label("Wafer"),
                    comet.Label("Sequence")                ),
                comet.Column(
                    comet.Text(id="sample_text", value="Unnamed"),
                    comet.Select(id="chuck_select"),
                    comet.Select(id="wafer_select"),
                    comet.Select(id="sequence_select", changed=on_sequence_changed)
                ),
                stretch=(0, 1)
            ),
            SequenceTree(id="sequence_tree", selected=on_tree_selected),
            comet.Button(
                id="calibrate_button",
                text="Calibrate...",
                tooltip="Calibrate table.",
                clicked=on_calibrate_start
            ),
            comet.Row(
                comet.Button(
                    id="start_button",
                    text="Start",
                    tooltip="Start measurement sequence.",
                    clicked=on_measure_start
                ),
                comet.Button(
                    id="autopilot_button",
                    text="Autopilot",
                    tooltip="Run next measurement automatically.",
                    checkable=True,
                    checked=True
                ),
                comet.Button(
                    id="continue_button",
                    text="Continue",
                    tooltip="Run next measurement manually.",
                    enabled=False,
                    clicked=on_measure_continue
                )
            ),
            comet.Button(
                id="stop_button",
                text="Stop",
                tooltip="Stop measurement sequence.",
                enabled=False,
                clicked=on_measure_stop
            ),
        ),
        comet.Tabs(
            comet.Tab(
                title="Dashboard",
                layout=comet.Column(
                    IVRamp(id="iv_ramp", visible=False),
                    BiasIVRamp(id="bias_iv_ramp", visible=False),
                    CVRamp(id="cv_ramp", visible=False),
                    CVRampAlt(id="cv_ramp_alt", visible=False),
                    FourWireIVRamp(id="4wire_iv_ramp", visible=False),
                    id="dashboard"
                )
            ),
            comet.Tab(
                title="Summary",
                layout=comet.ScrollArea(
                    layout=comet.Column(
                        comet.Stretch()
                    )
                )
            ),
            id="tabs"
        ),
        stretch=(4, 9)
    )

    app.width = 1280
    app.height = 800

    load_chucks()
    load_wafers()
    load_sequences()

    return app.run()

if __name__ == '__main__':
    sys.exit(main())
