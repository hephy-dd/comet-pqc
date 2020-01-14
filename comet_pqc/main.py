import sys

from comet import Application, MainWindow
from . import __version__

def main():
    app = Application()
    app.setApplicationName('comet-pqc')

    w = MainWindow()
    w.resize(1280, 700)
    w.setWindowTitle("{} {}".format(w.windowTitle(), __version__))
    w.show()

    return app.run()

if __name__ == '__main__':
    sys.exit(main())
