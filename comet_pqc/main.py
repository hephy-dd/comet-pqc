import argparse
import copy
import logging
import os
import sys
import time

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
from .processes import SequenceProcess

from .trees import SequenceTree
from .trees import ConnectionTreeItem
from .trees import MeasurementTreeItem

from .panels import IVRamp
from .panels import BiasIVRamp
from .panels import CVRamp
from .panels import CVRampAlt
from .panels import FourWireIVRamp
from .panels import FrequencyScan

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()

def main():

    args = parse_args()

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
    app.devices.add("k2657", K2657A(comet.Resource(
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
    app.devices.add("k2410", K2410(comet.Resource(
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

    # Register callbacks

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

    def on_import_sequence():
        filename = comet.filename_open(
            title="Import Sequence",
            filter="YAML (*.yaml *.yml)"
        )
        if filename:
            try:
                sequence = config.load_sequence(filename)
            except Exception as e:
                logging.error(e)
                comet.show_error(
                    title="Import Sequence Error",
                    text=e.message if hasattr(e, "message") else format(e),
                    details=format(e)
                )
                return
            select = app.layout.get("sequence_select")
            for item in select.values:
                if item.id == sequence.id or item.name == sequence.name:
                    if comet.show_question(
                        title="Sequence already loaded",
                        text=f"Do you want to replace already loaded sequence '{sequence.name}'?"
                    ):
                        select.remove(item)
                    else:
                        return
            select.append(sequence)
            select.current = sequence

    def on_sample_changed(value):
        app.settings["sample"] = value

    def on_load_sequence_tree(index):
        """Clears current sequence tree and loads new sequence tree from configuration."""
        panels = app.layout.get("panels")
        for panel in panels.children:
            panel.unmount()
            panel.visible = False
        tree = app.layout.get("sequence_tree")
        tree.clear()
        select = app.layout.get("sequence_select")
        sequence = copy.deepcopy(select.current)
        for connection in sequence:
            tree.append(ConnectionTreeItem(connection))
        tree.fit()
        if len(tree):
            tree.current = tree[0]

    def on_tree_selected(item):
        panels = app.layout.get("panels")
        for panel in panels.children:
            panel.store()
            panel.unmount()
            panel.clear_readings()
            panel.visible = False
        panel_controls = app.layout.get("panel_controls")
        panel_controls.visible = False
        if isinstance(item, ConnectionTreeItem):
            pass
        if isinstance(item, MeasurementTreeItem):
            panel = app.layout.get(item.type)
            panel.visible = True
            panel.mount(item)
            panel_controls.visible = True

    def on_tree_locked(state):
        for item in app.layout.get("sequence_tree"):
            item.checkable = not state
            for measurement in item.children:
                measurement.checkable = not state

    def on_calibrate_start():
        result =comet.show_question(
            title="Calibrate table",
            text="Are you sure to calibrate the table?"
        )
        if result:
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

    def on_sequence_start():
        result =comet.show_question(
            title="Start sequence",
            text="Are you sure to start a measurement sequence?"
        )
        if result:
            app.layout.get("calibrate_button").enabled = False
            app.layout.get("start_button").enabled = False
            app.layout.get("autopilot_button").enabled = True
            app.layout.get("continue_button").enabled = False
            app.layout.get("stop_button").enabled = True
            on_tree_locked(True)
            sequence = app.processes.get("sequence")
            sequence.start()

    def on_sequence_continue():
        pass

    def on_sequence_stop():
        app.layout.get("stop_button").enabled = False
        app.layout.get("autopilot_button").enabled = False
        app.layout.get("continue_button").enabled = False
        sequence = app.processes.get("sequence")
        sequence.stop()

    def on_sequence_finished():
        app.layout.get("calibrate_button").enabled = True
        app.layout.get("start_button").enabled = True
        app.layout.get("autopilot_button").enabled = True
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = False
        on_tree_locked(False)

    def on_select_output():
        output = app.layout.get("output")
        value = comet.directory_open(
            title="Output",
            path=output.value
        )
        if value:
            output.value = value

    def on_output_changed(value):
        app.settings["output_path"] = value

    def on_measure_restore():
        if comet.show_question(
            title="Restore Defaults",
            text="Do you want to restore to default parameters?"
        ):
            tree = app.layout.get("sequence_tree")
            measurement = tree.current
            panel = app.layout.get(measurement.type)
            panel.restore()

    def on_measure_run():
        if comet.show_question(
            title="Run Measurement",
            text="Do you want to run the current selected measurement?"
        ):
            app.layout.get("restore_measure").enabled = False
            app.layout.get("run_measure").enabled = False
            app.layout.get("stop_measure").enabled = True
            app.layout.get("sample_fieldset").enabled = False
            app.layout.get("sequence_fieldset").enabled = False
            app.layout.get("output_fieldset").enabled = False
            panels = app.layout.get("panels")
            for panel in panels.children:
                panel.locked = True
            tree = app.layout.get("sequence_tree")
            measurement = tree.current
            panel = app.layout.get(measurement.type)
            panel.store()
            # TODO
            panel.clear_readings()
            measure = app.processes.get("measure")
            measure.set('sample_name', app.layout.get("sample_text").value)
            measure.set('output', app.layout.get("output").value)
            measure.set('measurement_type', measurement.type)
            measure.set('measurement_name', measurement.name)
            measure.set('parameters', measurement.parameters)
            measure.events.reading = panel.append_reading
            # TODO
            measure.start()

    def on_measure_stop():
        app.layout.get("restore_measure").enabled = False
        app.layout.get("run_measure").enabled = False
        app.layout.get("stop_measure").enabled = False
        measure = app.processes.get("measure")
        measure.stop()

    def on_measure_finished():
        app.layout.get("restore_measure").enabled = True
        app.layout.get("run_measure").enabled = True
        app.layout.get("stop_measure").enabled = False
        app.layout.get("sample_fieldset").enabled = True
        app.layout.get("sequence_fieldset").enabled = True
        app.layout.get("output_fieldset").enabled = True
        panels = app.layout.get("panels")
        for panel in panels.children:
            panel.locked = False
        measure = app.processes.get("measure")
        measure.events.reading = lambda data: None

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        comet.show_exception(exc, tb)

    def on_message(message):
        app.message = message

    def on_progress(value, maximum):
        app.progress = value, maximum

    # Register processes

    app.processes.add("calibrate", CalibrateProcess(
        events=dict(
            finished=on_calibrate_finished,
            message=on_message,
            progress=on_progress
        )
    ))
    app.processes.add("sequence", SequenceProcess(
        events=dict(
            finished=on_sequence_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress
        )
    ))
    app.processes.add("measure", MeasureProcess(
        events=dict(
            finished=on_measure_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress,
        )
    ))

    # Create layout

    app.layout = comet.Row(
        # Left column
        comet.Column(
            comet.FieldSet(
                id="sample_fieldset",
                title="Sample",
                layout=comet.Row(
                    comet.Column(
                        comet.Label("Name"),
                        comet.Label("Chuck"),
                        comet.Label("Wafer Type"),
                        comet.Label("Sequence")
                    ),
                    comet.Column(
                        comet.Text(
                            id="sample_text",
                            value=app.settings.get("sample", "Unnamed"),
                            changed=on_sample_changed
                        ),
                        comet.Select(id="chuck_select"),
                        comet.Select(id="wafer_select"),
                        comet.Select(id="sequence_select", changed=on_load_sequence_tree)
                    ),
                    stretch=(0, 1)
                )
            ),
            comet.FieldSet(
                id="sequence_fieldset",
                title="Sequence",
                layout=comet.Column(
                    SequenceTree(id="sequence_tree", selected=on_tree_selected),
                    comet.Row(
                        comet.Button(
                            id="start_button",
                            text="Start",
                            tooltip="Start measurement sequence.",
                            clicked=on_sequence_start
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
                            clicked=on_sequence_continue
                        )
                    ),
                    comet.Button(
                        id="stop_button",
                        text="Stop",
                        tooltip="Stop measurement sequence.",
                        enabled=False,
                        clicked=on_sequence_stop
                    )
                )
            ),
            comet.FieldSet(
                id="controls_fieldset",
                title="Controls",
                layout=comet.Row(
                    comet.Button(text="Table", enabled=False, checkable=True, checked=True),
                    comet.Button(text="Joystick", enabled=False, checkable=True, checked=True),
                    comet.Button(text="Light", enabled=False, checkable=True, checked=True),
                    comet.Stretch(),
                    comet.Button(
                        id="calibrate_button",
                        text="Calibrate",
                        tooltip="Calibrate table.",
                        clicked=on_calibrate_start
                    )
                )
            ),
            comet.FieldSet(
                id="output_fieldset",
                title="Output",
                layout=comet.Row(
                    comet.Text(
                        id="output",
                        value=app.settings.get("output_path", os.path.join(os.path.expanduser("~"), "PQC")),
                        changed=on_output_changed
                    ),
                    comet.Button(
                        text="...",
                        width=32,
                        clicked=on_select_output
                    )
                )
            ),
            stretch=(0, 1, 0, 0, 0)
        ),
        # Right column
        comet.Tabs(
            comet.Tab(
                title="Measurement",
                layout=comet.Column(
                    comet.Row(
                        IVRamp(id="iv_ramp", visible=False),
                        BiasIVRamp(id="bias_iv_ramp", visible=False),
                        CVRamp(id="cv_ramp", visible=False),
                        CVRampAlt(id="cv_ramp_alt", visible=False),
                        FourWireIVRamp(id="4wire_iv_ramp", visible=False),
                        FrequencyScan(id="frequency_scan", visible=False),
                        id="panels"
                    ),
                    comet.Row(
                        comet.Button(
                            id="restore_measure",
                            text="Restore Defaults",
                            tooltip="Restore default measurement parameters.",
                            clicked=on_measure_restore
                        ),
                        comet.Stretch(),
                        comet.Button(
                            id="run_measure",
                            text="Run",
                            tooltip="Run current measurement.",
                            clicked=on_measure_run
                        ),
                        comet.Button(
                            id="stop_measure",
                            text="Stop",
                            tooltip="Stop current measurement.",
                            clicked=on_measure_stop,
                            enabled=False
                        ),
                        visible=False,
                        id="panel_controls"
                    ),
                    stretch=(1, 0)
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

    # Tweaks

    app.layout.get("start_button").enabled = False

    app.width = 1280
    app.height = 800

    load_chucks()
    load_wafers()
    load_sequences()

    # There's no hook, so it's a hack.
    # Import sequence
    from PyQt5 import QtWidgets
    ui = app.qt.window.ui
    sequenceMenu = QtWidgets.QMenu("&Sequence")
    ui.fileMenu.insertMenu(ui.quitAction, sequenceMenu)
    importAction = QtWidgets.QAction("&Import...")
    importAction.triggered.connect(on_import_sequence)
    sequenceMenu.addAction(importAction)
    ui.fileMenu.insertSeparator(ui.quitAction)

    return app.run()

if __name__ == '__main__':
    sys.exit(main())
