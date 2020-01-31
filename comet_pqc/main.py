import sys

from PyQt5 import QtWidgets

import comet

from . import config
from . import __version__

from .processes import *
from .trees import *
from .panels import *

def main():
    app = comet.Application('comet-pqc')
    app.version = __version__
    app.title = f"PQC {app.version}"
    app.qt.window.resize(960, 720)

    def on_calibrate(event):
        result =comet.show_question(
            title="Calibrate table",
            text="Are you sure to calibrate the table?"
        )
        if result:
            app.layout.get("calib_btn").enabled = False
            app.layout.get("start_btn").enabled = False
            app.layout.get("stop_btn").enabled = False
            app.processes.get("calibrate").start()

    def on_start(event):
        result =comet.show_question(
            title="Start measurement",
            text="Are you sure to start a new measurement?"
        )
        if result:
            app.layout.get("calib_btn").enabled = False
            app.layout.get("start_btn").enabled = False
            app.layout.get("stop_btn").enabled = True
            app.processes.get("measure").start()

    def on_stop(event):
        result =comet.show_question(
            title="Stop measurement",
            text="Are you sure to stop the running measurement?"
        )
        if result:
            app.layout.get("calib_btn").enabled = False
            app.layout.get("start_btn").enabled = False
            app.layout.get("stop_btn").enabled = False
            app.processes.get("measure").stop()

    def on_calibrate_finish():
        app.layout.get("calib_btn").enabled = True
        app.layout.get("start_btn").enabled = True
        app.layout.get("stop_btn").enabled = False
        app.progress = None

    def on_measure_finish():
        app.layout.get("calib_btn").enabled = True
        app.layout.get("start_btn").enabled = True
        app.layout.get("stop_btn").enabled = False
        app.progress = None

    def on_show_panel(id):
        for panel in app.layout.get("panels").children:
            panel.visible = False
        app.layout.get(id).visible = True

    def on_message(message):
        app.message = message

    def on_progress(value, maximum):
        app.progress = value, maximum

    app.processes.add("calibrate", CalibrateProcess(
        finish=on_calibrate_finish,
        slots=dict(
            message=on_message,
            progress=on_progress
        )
    ))
    app.processes.add("measure", MeasureProcess(
        finish=on_measure_finish,
        slots=dict(
            message=on_message,
            progress=on_progress,
            show_panel=on_show_panel
        )
    ))

    app.layout = comet.Row(
        comet.Column(
            WaferTree(id="wafer_tree"),
            SequenceTree(id="sequence_tree"),
            comet.Button(id="calib_btn", text="Calibrate", enabled=True, click=on_calibrate),
            comet.Button(id="start_btn", text="Start", enabled=True, click=on_start),
            comet.Button(id="stop_btn", text="Stop", enabled=False, click=on_stop),
            stretch=(3,7,0,0,0)
        ),
        comet.Column(
            IVRamp(id="iv_ramp", visible=False),
            BiasIVRamp(id="bias_iv_ramp", visible=False),
            CVRamp(id="cv_ramp", visible=False),
            CVRampAlt(id="cv_ramp_alt", visible=False),
            FourWireIVRamp(id="4wire_iv_ramp", visible=False),
            id="panels"
        ),
        stretch=(4,9)
    )

    # Loading configurations
    chuck_file = config.list_configs(config.CHUCK_DIR)[0][1]
    chuck_config = config.load_chuck(chuck_file)

    wafers_file = config.list_configs(config.WAFER_DIR)[0][1]
    wafer_config = config.load_wafer(wafers_file)

    sequence_file = config.list_configs(config.SEQUENCE_DIR)[0][1]
    sequence_config = config.load_sequence(sequence_file)

    app.layout.get("wafer_tree").load(chuck_config, wafer_config, sequence_config)
    app.layout.get("sequence_tree").load(sequence_config)
    app.processes.get("measure").sequence_config = sequence_config

    return app.run()

if __name__ == '__main__':
    sys.exit(main())
