import os

from pqc.core import utils


def test_make_path():
    filename = os.path.join(utils.PACKAGE_PATH, "assets", "sample.txt")
    assert filename == utils.make_path("assets", "sample.txt")


def test_linear_transform():
    tr = utils.LinearTransform()
    values = tr.calculate((0, 0, 0), (1, 1, 1), 4)
    assert values == [(0.0, 0.0, 0.0), (0.25, 0.25, 0.25), (0.5, 0.5, 0.5), (0.75, 0.75, 0.75), (1.0, 1.0, 1.0)]
