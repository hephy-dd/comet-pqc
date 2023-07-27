import os

from comet_pqc.core import utils


def test_package_path():
    root_path = os.path.dirname(os.path.dirname(__file__))
    package_path = os.path.join(root_path, "comet_pqc")
    assert package_path == utils.PACKAGE_PATH


def test_make_path():
    filename = os.path.join(utils.PACKAGE_PATH, "assets", "sample.txt")
    assert filename == utils.make_path("assets", "sample.txt")


def test_linear_transform():
    tr = utils.LinearTransform()
    values = tr.calculate((0, 0, 0), (1, 1, 1), 4)
    assert values == [(0.0, 0.0, 0.0), (0.25, 0.25, 0.25), (0.5, 0.5, 0.5), (0.75, 0.75, 0.75), (1.0, 1.0, 1.0)]
