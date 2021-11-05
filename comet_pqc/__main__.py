import argparse
import logging
import os
import sys

from logging import Formatter
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

import comet

from . import __version__
from .utils import user_home

from .application import Application

from .settings import settings

CONTENTS_URL = 'https://hephy-dd.github.io/comet-pqc/'
GITHUB_URL = 'https://github.com/hephy-dd/comet-pqc/'

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def configure_logging():
    logger = logging.getLogger()
    # Stream handler
    stream_formatter = Formatter(
        fmt='%(levelname)s:%(name)s:%(message)s'
    )
    stream_handler = StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)
    # Rotating file handler
    filename = os.path.join(user_home(), 'comet-pqc.log')
    file_formatter = Formatter(
        fmt='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    file_handler = RotatingFileHandler(
        filename=filename,
        maxBytes=10485760,
        backupCount=10
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)


def main():
    args = parse_args()

    configure_logging()

    app = Application()
    app.load_settings()
    app.event_loop()
    app.store_settings()


if __name__ == '__main__':
    sys.exit(main())
