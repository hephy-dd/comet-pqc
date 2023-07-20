import os

from comet_pqc.core import config


def test_dirs():
    assert os.path.isdir(config.CHUCK_DIR)
    assert os.path.isdir(config.SAMPLE_DIR)
    assert os.path.isdir(config.SEQUENCE_DIR)


def test_load_schema():
    config.load_schema("chuck")
    config.load_schema("sample")
    config.load_schema("sequence")


def test_validate_config():
    config.validate_config({"id": "default", "name": "Default", "positions": []}, "chuck")
    config.validate_config({"id": "default", "name": "Default", "contacts": []}, "sample")
    config.validate_config({"id": "default", "name": "Default", "contacts": []}, "sequence")


def test_load_chuck():
    results = config.list_configs(config.CHUCK_DIR)
    for name, filename in results:
        config.load_chuck(filename)


def test_load_sample():
    results = config.list_configs(config.SAMPLE_DIR)
    for name, filename in results:
        config.load_sample(filename)


def test_load_sequence():
    results = config.list_configs(config.SEQUENCE_DIR)
    for name, filename in results:
        config.load_sequence(filename)
