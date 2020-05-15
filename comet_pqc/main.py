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
from .trees import ContactTreeItem
from .trees import MeasurementTreeItem

from .panels import IVRampPanel
from .panels import IVRampElmPanel
from .panels import IVRampBiasPanel
from .panels import IVRamp4WirePanel
from .panels import CVRampPanel
from .panels import CVRampAltPanel
from .panels import FrequencyScanPanel

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

    logging.info("PQC version %s", __version__)

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
        resource_name="TCPIP::10.0.0.6::5025::SOCKET",
        read_termination="\n",
        write_termination="\n",
        timeout=8000.0
    )))
    app.devices.add("k6517", K6517B(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10001::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n",
        timeout=8000.0
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

    def load_samples():
        select = app.layout.get("sample_select")
        select.clear()
        for name, filename in sorted(config.list_configs(config.SAMPLE_DIR)):
            select.append(config.load_sample(filename))

    def load_sequences():
        select = app.layout.get("sequence_select")
        select.clear()
        for name, filename in sorted(config.list_configs(config.SEQUENCE_DIR)):
            select.append(config.load_sequence(filename))

    def create_output_dir(sample_name, sample_type):
        """Create new timestamp prefixed output directory."""
        base = app.layout.get("output").value
        iso_timestamp = comet.make_iso()
        dirname = comet.safe_filename(f"{iso_timestamp}-{sample_name}-{sample_type}")
        output_dir = os.path.join(base, dirname)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

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
        for contact in sequence:
            tree.append(ContactTreeItem(contact))
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
        if isinstance(item, ContactTreeItem):
            pass
        if isinstance(item, MeasurementTreeItem):
            panel = app.layout.get(item.type)
            panel.visible = True
            panel.mount(item)
            panel_controls.visible = True

    def on_calibrate_start():
        if comet.show_question(
            title="Calibrate table",
            text="Are you sure to calibrate the table?"
        ):
            app.layout.get("sample_fieldset").enabled = False
            app.layout.get("calibrate_button").enabled = False
            app.layout.get("start_button").enabled = False
            app.layout.get("autopilot_button").enabled = False
            app.layout.get("continue_button").enabled = False
            app.layout.get("stop_button").enabled = False
            app.layout.enabled = False
            calibrate = app.processes.get("calibrate")
            calibrate.start()

    def on_calibrate_finished():
        calibrate = app.processes.get("calibrate")
        if calibrate.get("success", False):
            comet.show_info(title="Success", text="Calibrated table successfully.")
        app.layout.get("sample_fieldset").enabled = True
        app.layout.get("calibrate_button").enabled = True
        app.layout.get("start_button").enabled = True
        app.layout.get("autopilot_button").enabled = True
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = False
        app.layout.enabled = True

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
            app.layout.get("calibrate_button").enabled = False
            app.layout.get("restore_measure").enabled = False
            app.layout.get("run_measure").enabled = False
            app.layout.get("stop_measure").enabled = True
            app.layout.get("sample_fieldset").enabled = False
            app.layout.get("sequence_fieldset").enabled = False
            app.layout.get("output_fieldset").enabled = False
            panels = app.layout.get("panels")
            for panel in panels.children:
                panel.lock()
            sequence_tree = app.layout.get("sequence_tree")
            sequence_tree.lock()
            #sequence_tree.reset()
            measurement = sequence_tree.current
            panel = app.layout.get(measurement.type)
            panel.store()
            # TODO
            panel.clear_readings()
            sample_name = app.layout.get("sample_text").value
            sample_type = app.layout.get("sample_select").current.name
            #output_dir = create_output_dir(sample_name, sample_type)
            output_dir = app.layout.get("output").value
            measure = app.processes.get("measure")
            measure.set("sample_name", sample_name)
            measure.set("sample_type", sample_type)
            measure.set("output_dir", output_dir)
            measure.measurement_item = measurement
            measure.events.reading = panel.append_reading
            measure.events.update = panel.update_readings
            measure.events.state = panel.state
            # TODO
            measure.start()

    def on_measure_stop():
        app.layout.get("restore_measure").enabled = False
        app.layout.get("run_measure").enabled = False
        app.layout.get("stop_measure").enabled = False
        measure = app.processes.get("measure")
        measure.stop()

    def on_measure_finished():
        app.layout.get("calibrate_button").enabled = True
        app.layout.get("restore_measure").enabled = True
        app.layout.get("run_measure").enabled = True
        app.layout.get("stop_measure").enabled = False
        app.layout.get("sample_fieldset").enabled = True
        app.layout.get("sequence_fieldset").enabled = True
        app.layout.get("output_fieldset").enabled = True
        panels = app.layout.get("panels")
        for panel in panels.children:
            panel.unlock()
        measure = app.processes.get("measure")
        measure.events.reading = lambda data: None
        app.layout.get("sequence_tree").unlock()

    def on_sequence_start():
        result =comet.show_question(
            title="Start sequence",
            text="Are you sure to start a measurement sequence?"
        )
        if result:
            app.layout.get("sample_fieldset").enabled = False
            app.layout.get("calibrate_button").enabled = False
            app.layout.get("start_button").enabled = False
            app.layout.get("autopilot_button").enabled = True
            app.layout.get("continue_button").enabled = False
            app.layout.get("stop_button").enabled = True
            app.layout.get("panel_controls").enabled = False
            panels = app.layout.get("panels")
            for panel in panels.children:
                panel.lock()
            sequence_tree = app.layout.get("sequence_tree")
            sequence_tree.lock()
            sequence_tree.reset()
            sample_name = app.layout.get("sample_text").value
            sample_type = app.layout.get("sample_select").current.name
            output_dir = create_output_dir(sample_name, sample_type)
            sequence = app.processes.get("sequence")
            sequence.set("sample_name", sample_name)
            sequence.set("sample_type", sample_type)
            sequence.set("output_dir", output_dir)
            sequence.sequence_tree = sequence_tree
            sequence.events.reading = panel.append_reading
            sequence.events.update = panel.update_readings
            sequence.events.state = panel.state
            sequence.start()

    def on_sequence_stop():
        app.layout.get("stop_button").enabled = False
        app.layout.get("autopilot_button").enabled = False
        app.layout.get("continue_button").enabled = False
        sequence = app.processes.get("sequence")
        sequence.stop()

    def on_sequence_finished():
        app.layout.get("sample_fieldset").enabled = True
        app.layout.get("calibrate_button").enabled = True
        app.layout.get("start_button").enabled = True
        app.layout.get("autopilot_button").enabled = True
        app.layout.get("continue_button").enabled = False
        app.layout.get("stop_button").enabled = False
        app.layout.get("panel_controls").enabled = True
        panels = app.layout.get("panels")
        for panel in panels.children:
            panel.unlock()
        sequence_tree = app.layout.get("sequence_tree")
        sequence_tree.unlock()
        sequence = app.processes.get("sequence")
        sequence.set("sample_name", None)
        sequence.set("output_dir", None)

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

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        comet.show_exception(exc, tb)

    def on_message(message):
        logging.info(message)
        app.message = message

    def on_progress(value, maximum):
        app.progress = value, maximum

    def on_autopilot_toggled(state):
        sequence = app.processes.get("sequence")
        sequence.set("autopilot", state)

    def on_continue_contact(contact):
        comet.show_info(
            title=f"Contact {contact.name}",
            text=f"Please contact with {contact.name}."
        )
        sequence = app.processes.get("sequence")
        sequence.set("continue_contact", True)

    def on_continue_measurement(measurement):
        def on_continue():
            if comet.show_question(
                title="Continue sequence",
                text=f"Do you want to continue with {measurement.contact.name}, {measurement.name}?"
            ):
                logging.info("Continuing sequence...")
                app.layout.get("continue_button").enabled = False
                app.layout.get("continue_button").clicked = None
                sequence_tree = app.layout.get("sequence_tree")
                sequence_tree.current = measurement
                sequence = app.processes.get("sequence")
                sequence.set("continue_measurement", True)
        app.layout.get("continue_button").enabled = True
        app.layout.get("continue_button").clicked = on_continue

    def on_measurement_state(item, state):
        item.state = state

    # Register processes

    app.processes.add("calibrate", CalibrateProcess(
        events=dict(
            finished=on_calibrate_finished,
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
            measurement_state=on_measurement_state,
            reading=lambda name, x, y: logging.info("READING: %s %s %s", name, x, y)
        )
    ))
    app.processes.add("sequence", SequenceProcess(
        events=dict(
            finished=on_sequence_finished,
            failed=on_show_error,
            message=on_message,
            progress=on_progress,
            continue_contact=on_continue_contact,
            continue_measurement=on_continue_measurement,
            measurement_state=on_measurement_state,
            reading=lambda name, x, y: logging.info("READING: %s %s %s", name, x, y)
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
                        comet.Label("Sample Type"),
                        comet.Label("Sequence")
                    ),
                    comet.Column(
                        comet.Text(
                            id="sample_text",
                            value=app.settings.get("sample", "Unnamed"),
                            changed=on_sample_changed
                        ),
                        comet.Select(id="chuck_select"),
                        comet.Select(id="sample_select"),
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
                            checked=False,
                            toggled=on_autopilot_toggled
                        ),
                        comet.Button(
                            id="continue_button",
                            text="Continue",
                            tooltip="Run next measurement manually.",
                            enabled=False
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
                        IVRampPanel(id="iv_ramp", visible=False),
                        IVRampElmPanel(id="iv_ramp_elm", visible=False),
                        IVRampBiasPanel(id="bias_iv_ramp", visible=False),
                        CVRampPanel(id="cv_ramp", visible=False),
                        CVRampAltPanel(id="cv_ramp_alt", visible=False),
                        IVRamp4WirePanel(id="4wire_iv_ramp", visible=False),
                        FrequencyScanPanel(id="frequency_scan", visible=False),
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

    app.width = 1280
    app.height = 800

    load_chucks()
    load_samples()
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
