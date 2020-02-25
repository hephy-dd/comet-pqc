import copy
import sys

from PyQt5 import QtCore, QtWidgets, QtMultimedia, QtMultimediaWidgets

import comet
from comet.driver.keithley import K707B
from comet.driver.keithley import K2657A
from comet.driver.keysight import E4980A
from comet.driver.keithley import K6517B
from comet.driver.keithley import K2410
from comet.driver.corvus import Venus1

from . import config
from . import __version__

from .processes import *
from .trees import *
from .panels import *
from .dialogs import CameraDialog

def main():
    app = comet.Application()
    app.name = "comet-pqc"
    app.version = __version__
    app.title = f"PQC {app.version}"
    app.about = f"COMET application for PQC measurements, version {app.version}."
    app.width = 1280
    app.height = 800

    # Register devices
    app.devices.add("matrix", K707B(comet.Resource(
        resource_name="TCPIP::10.0.0.2::23::SOCKET",
        encoding='latin1',
        read_termination="\r\n"
    )))
    app.devices.add("smu1", K2657A(comet.Resource(
        resource_name="TCPIP::10.0.0.3::23::SOCKET",
        encoding='latin1',
        read_termination="\r\n"
    )))
    app.devices.add("lcr", E4980A(comet.Resource(
        resource_name="TCPIP::10.0.0.4::5025::SOCKET",
        read_termination="\r\n"
    )))
    app.devices.add("elm", K6517B(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10001::SOCKET",
        read_termination="\r\n"
    )))
    app.devices.add("smu2", K2410(comet.Resource(
        resource_name="TCPIP::10.0.0.5::10002::SOCKET",
        read_termination="\r\n"
    )))
    app.devices.add("corvus", Venus1(comet.Resource(
        resource_name="TCPIP::10.0.0.6::23::SOCKET",
        read_termination="\r\n",
        write_termination="\r\n"
    )))
    app.devices.load_settings()

    def on_calibrate():
        result =comet.show_question(
            title="Calibrate table",
            text="Are you sure to calibrate the table?"
        )
        if result:
            # Update buttons
            app.layout.get("calib_btn").enabled = False
            app.layout.get("start_btn").enabled = False
            app.layout.get("manual_btn").enabled = False
            app.layout.get("cont_btn").enabled = False
            app.layout.get("stop_btn").enabled = False
            app.processes.get("calibrate").start()

    def on_start():
        result =comet.show_question(
            title="Start measurement",
            text="Are you sure to start a new measurement?"
        )
        if result:
            # Update buttons
            app.layout.get("calib_btn").enabled = False
            app.layout.get("start_btn").enabled = False
            app.layout.get("manual_btn").enabled = False
            app.layout.get("cont_btn").enabled = False
            app.layout.get("stop_btn").enabled = True
            app.layout.get("tabs").current = 0
            # Reset summary
            on_clear_summary()
            # Start process
            measure = app.processes.get("measure")
            measure.wafers = on_load_wafers()
            measure.start()

    def on_stop():
        result =comet.show_question(
            title="Stop measurement",
            text="Are you sure to stop the running measurement?"
        )
        if result:
            # Update buttons
            app.layout.get("calib_btn").enabled = False
            app.layout.get("start_btn").enabled = False
            app.layout.get("cont_btn").enabled = False
            app.layout.get("stop_btn").enabled = False
            # Stop process
            measure = app.processes.get("measure")
            measure.stop()

    def on_calibrate_finished():
        app.layout.get("calib_btn").enabled = True
        app.layout.get("start_btn").enabled = True
        app.layout.get("manual_btn").enabled = True
        app.layout.get("cont_btn").enabled = False
        app.layout.get("stop_btn").enabled = False
        app.progress = None

    def on_measure_finished():
        app.layout.get("calib_btn").enabled = True
        app.layout.get("start_btn").enabled = True
        app.layout.get("manual_btn").enabled = True
        app.layout.get("cont_btn").enabled = False
        app.layout.get("stop_btn").enabled = False
        app.progress = None

    def on_move_to(name, data):
        """Manually move to socket/reference point."""
        try:
            with app.devices.get("corvus") as corvus:
                corvus.mode = corvus.HOST_MODE
                dialog = CameraDialog(corvus)
                dialog.setWindowTitle(f"Move to {name}")
                data["point"] = None
                if dialog.Accepted == dialog.exec_():
                    data["point"] = corvus.pos
                else:
                    app.processes.get("measure").stop()
            app.processes.get("measure").unpause()
        except Exception as e:
            comet.show_exception(e)
            app.processes.get("measure").stop()

    def on_show_panel(item, measurement):
        """Show measurement specific panel and update panel with measuremens
        attributes.
        """
        for panel in app.layout.get("panels").children:
            panel.visible = False
        panel = app.layout.get(measurement.type)
        panel.load(item, measurement)
        panel.visible = True
        slot = app.layout.get("wafer_tree").qt.currentItem().data(0, 0x2000)
        app.layout.get(slot.id).sync()
        app.processes.get("measure").unpause()

    def on_show_error(exc, tb):
        app.message = "Exception occured!"
        app.progress = None
        comet.show_exception(exc, tb)

    def on_manual_toggle(checked):
        app.processes.get("measure").manual_mode = checked

    def on_auto_toggle(checked):
        app.processes.get("measure").auto_continue = checked

    def on_continue():
        app.layout.get("cont_btn").enabled = False
        app.processes.get("measure").unpause()

    def on_enable_continue():
        app.layout.get("cont_btn").enabled = True

    def on_clear_summary():
        app.layout.get("summary").layout = comet.Column()

    def on_append_summary(name, value):
        app.layout.get("summary").layout.append(comet.Row(
            comet.Label(text=name),
            comet.Label(text=format(value))
        ))

    def on_message(message):
        app.message = message

    def on_progress(value, maximum):
        app.progress = value, maximum

    def on_load_wafers():
        """Load current wafer configs from UI."""
        wafers = []
        for item in app.layout.get("wafer_tree").items:
            sequence_tree = app.layout.get(item.slot.id)
            sequence_tree.clear()
            if item.checked:
                # Duplicate configuration for every wafer
                wafer_config = copy.deepcopy(item.wafer_config)
                sequence_config = copy.deepcopy(item.sequence_config)
                wafers.append(dict(
                    wafer_config=wafer_config,
                    sequence_config=sequence_config
                ))
                sequence_tree.load(sequence_config)
                for flute in sequence_config.items:
                    flute.locked = False
                    flute.state = "" if flute.enabled else ""
                    for measurement in flute.measurements:
                        measurement.locked = False
                        measurement.state = "" if measurement.enabled else ""
                sequence_tree.sync()
        return wafers

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
        move_to=on_move_to,
        show_panel=on_show_panel,
        enable_continue=on_enable_continue,
        append_summary=on_append_summary
    ))

    app.layout = comet.Row(
        comet.Column(
            WaferTree(id="wafer_tree"),
            comet.Column(id="sequences"),
            comet.Button(id="calib_btn", text="Calibrate", enabled=True, clicked=on_calibrate),
            comet.Button(id="start_btn", text="Start", enabled=True, clicked=on_start),
            comet.Row(
                comet.Button(id="manual_btn", text="Manual", checkable=True, checked=False, toggled=on_manual_toggle),
                comet.Button(id="auto_btn", text="Autopilot", checkable=True, checked=True, toggled=on_auto_toggle),
                comet.Button(id="cont_btn", text="Continue", enabled=False, clicked=on_continue),
            ),
            comet.Button(id="stop_btn", text="Stop", enabled=False, clicked=on_stop),
            stretch=(3, 7, 0, 0, 0)
        ),
        comet.Tabs(
            comet.Tab(
                title="Measurement",
                layout=comet.Column(
                    IVRamp(id="iv_ramp", visible=False),
                    BiasIVRamp(id="bias_iv_ramp", visible=False),
                    CVRamp(id="cv_ramp", visible=False),
                    CVRampAlt(id="cv_ramp_alt", visible=False),
                    FourWireIVRamp(id="4wire_iv_ramp", visible=False),
                    id="panels"
                )
            ),
            comet.Tab(
                title="Summary",
                layout=comet.ScrollArea(layout=comet.Column(
                    comet.Widget(id="summary"),
                    comet.Stretch()
                ))
            ),
            id="tabs"
        ),
        stretch=(4, 9)
    )

    # Loading configurations
    chuck_file = config.list_configs(config.CHUCK_DIR)[0][1]
    chuck_config = config.load_chuck(chuck_file)

    wafer_configs = {key: config.load_wafer(value) for key, value in config.list_configs(config.WAFER_DIR)}
    sequence_configs = {key: config.load_sequence(value) for key, value in config.list_configs(config.SEQUENCE_DIR)}

    app.layout.get("wafer_tree").load(chuck_config, wafer_configs, sequence_configs)
    app.processes.get("measure").chuck_config = chuck_config

    column = app.layout.get("sequences")
    for index, slot in enumerate(chuck_config.slots):
        tree = SequenceTree(id=slot.id, slot=slot, visible=(0 == index))
        column.append(tree)
        tree.sync()

    def on_select(current, previous):
        """Show only the current sequence tree."""
        for child in app.layout.get("sequences").children:
            child.visible = False
        app.layout.get(current.slot.id).visible = True
        app.layout.get(current.slot.id).sync()

    app.layout.get("wafer_tree").qt.currentItemChanged.connect(on_select)

    def on_select_item(current, previous):
        if current is not None:
            measurement = current.data(0, 0x2000)
            if isinstance(measurement, config.SequenceMeasurement):
                item = current.parent().data(0, 0x2000)
                for panel in app.layout.get("panels").children:
                    panel.visible = False
                panel = app.layout.get(measurement.type)
                if panel:
                    panel.load(item, measurement)
                    panel.visible = True

    for child in app.layout.get("sequences").children:
        child.qt.currentItemChanged.connect(on_select_item)
    # Init
    on_load_wafers()

    return app.run()

if __name__ == '__main__':
    sys.exit(main())
