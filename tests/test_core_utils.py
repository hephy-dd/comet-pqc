import os

from comet_pqc.core import utils


class TestCoreUtils:

    def test_package_path(self):
        root_path = os.path.dirname(os.path.dirname(__file__))
        package_path = os.path.join(root_path, "comet_pqc")
        assert package_path == utils.PACKAGE_PATH

    def test_make_path(self):
        filename = os.path.join(utils.PACKAGE_PATH, "assets", "sample.txt")
        assert filename == utils.make_path("assets", "sample.txt")
