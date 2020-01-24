import sys

import comet

from . import config
from . import __version__

def main():
    app = comet.Application('comet-pqc')
    app.version = __version__
    app.title = f"PQC {app.version}"

    # Demo, loading configurations

    chucks = config.list_configs(config.CHUCK_DIR)
    wafers = config.list_configs(config.WAFER_DIR)
    sequences = config.list_configs(config.SEQUENCE_DIR)

    app.layout = comet.Column(
        comet.Label(text="Chucks"),
        comet.List(values=chucks),
        comet.Label(text="Wafers"),
        comet.List(values=wafers),
        comet.Label(text="Sequences"),
        comet.List(values=sequences),
        comet.Stretch()
    )

    return app.run()

if __name__ == '__main__':
    sys.exit(main())
