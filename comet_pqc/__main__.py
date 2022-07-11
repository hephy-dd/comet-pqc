import argparse
import logging
import os
import sys

from logging import Formatter
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

from . import __version__
from .utils import user_home

from .application import Application

from .settings import settings

CONTENTS_URL: str = 'https://hephy-dd.github.io/comet-pqc/'
GITHUB_URL: str = 'https://github.com/hephy-dd/comet-pqc/'
LOG_FILENAME: str = os.path.expanduser("~/comet-pqc.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help="show debug messages")
    parser.add_argument('--logfile', metavar="<file>", default=LOG_FILENAME, help="write to custom logfile")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def add_stream_handler(logger: logging.Logger) -> None:
    formatter = Formatter(
        "%(asctime)s::%(name)s::%(levelname)s::%(message)s",
        "%Y-%m-%dT%H:%M:%S"
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


def configure_logger(logger: logging.Logger, debug: bool = False, filename: str = None) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    add_stream_handler(logger)

    if filename:
        add_rotating_file_handle(logger, filename)


def main() -> None:
    args = parse_args()

    configure_logger(logging.getLogger(), debug=args.debug, filename=args.logfile)

    app = Application()
    app.load_settings()
    app.event_loop()
    app.store_settings()


if __name__ == '__main__':
    main()
