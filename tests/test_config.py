import os

from comet_pqc import config


class TestConfig:

    def test_dirs(self):
        assert os.path.isdir(config.CHUCK_DIR)
        assert os.path.isdir(config.SAMPLE_DIR)
        assert os.path.isdir(config.SEQUENCE_DIR)

    def test_load_schema(self):
        config.load_schema("chuck")
        config.load_schema("sample")
        config.load_schema("sequence")

    def test_validate_config(self):
        config.validate_config({"id": "default", "name": "Default", "positions": []}, "chuck")
        config.validate_config({"id": "default", "name": "Default", "contacts": []}, "sample")
        config.validate_config({"id": "default", "name": "Default", "contacts": []}, "sequence")

    def test_load_chuck(self):
        results = config.list_configs(config.CHUCK_DIR)
        for name, filename in results:
            config.load_chuck(filename)

    def test_load_sample(self):
        results = config.list_configs(config.SAMPLE_DIR)
        for name, filename in results:
            config.load_sample(filename)

    def test_load_sequence(self):
        results = config.list_configs(config.SEQUENCE_DIR)
        for name, filename in results:
            config.load_sequence(filename)
