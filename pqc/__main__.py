import argparse
import logging
import os
import signal
import sys
import traceback
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets
import analysis_pqc

from . import __version__
from .station import Station
from .utils import make_path
from .view.mainwindow import MainWindow

LOG_FILENAME: str = os.path.expanduser("~/comet-pqc.log")
CONTENTS_URL: str = "https://hephy-dd.github.io/comet-pqc/"
GITHUB_URL: str = "https://github.com/hephy-dd/comet-pqc/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="show debug messages")
    parser.add_argument("--logfile", metavar="<file>", default=LOG_FILENAME, help="write to custom logfile")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def add_stream_handler(logger: logging.Logger) -> None:
    formatter = Formatter(
        fmt="%(asctime)s::%(name)s::%(levelname)s::%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler = StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def add_rotating_file_handle(logger: logging.Logger, filename: str) -> None:
    file_formatter = logging.Formatter(
        fmt="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    file_handler = RotatingFileHandler(
        filename=filename,
        maxBytes=10485760,
        backupCount=10
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)


def configure_logger(logger: logging.Logger, debug: bool = False, filename: Optional[str] = None) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    add_stream_handler(logger)

    if filename:
        add_rotating_file_handle(logger, filename)


def main() -> None:
    args = parse_args()

    configure_logger(logging.getLogger(), debug=args.debug, filename=args.logfile)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("comet-pqc")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("HEPHY")
    app.setOrganizationDomain("hephy.at")
    app.setApplicationDisplayName(f"PQC {__version__}")
    app.setWindowIcon(QtGui.QIcon(make_path("assets", "icons", "pqc.ico")))
    app.setProperty("contentsUrl", CONTENTS_URL)
    app.setProperty("githubUrl", GITHUB_URL)
    app.lastWindowClosed.connect(app.quit)

    # TODO
    app.reflection = lambda: app
    app.name = app.applicationName()
    app.organization = app.organizationName()

    # Register interupt signal handler
    def signal_handler(signum, frame):
        if signum == signal.SIGINT:
            app.quit()

    signal.signal(signal.SIGINT, signal_handler)

    # Handle uncaught exceptions
    def exception_hook(exc_type, exc_value, exc_traceback):
        logging.error("", exc_info=(exc_type, exc_value, exc_traceback))
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        msgbox = QtWidgets.QMessageBox()
        msgbox.setIcon(QtWidgets.QMessageBox.Critical)
        msgbox.setWindowTitle("Uncaught Exception")
        msgbox.setText(f"{exc_type.__name__}: {exc_value}")
        msgbox.setDetailedText(tb)
        msgbox.exec()

    sys.excepthook = exception_hook

    # Run timer to process interrupt signals
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(250)

    station = Station()

    window = MainWindow(station)
    window.readSettings()
    window.plugins.install_plugins()
    window.show()

    logging.info("PQC version %s", __version__)
    logging.info("Analysis-PQC version %s", analysis_pqc.__version__)

    window.startup()  # start workers

    app.exec()

    window.writeSettings()

    window.plugins.uninstall_plugins()


if __name__ == "__main__":
    main()
