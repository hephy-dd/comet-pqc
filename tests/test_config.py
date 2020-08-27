import os
import unittest

from comet_pqc import config

class ConfigTest(unittest.TestCase):

    def test_dirs(self):
        os.path.isdir(config.CHUCK_DIR)
        os.path.isdir(config.SAMPLE_DIR)
        os.path.isdir(config.SEQUENCE_DIR)

    def test_load_schema(self):
        config.load_schema('chuck')
        config.load_schema('sample')
        config.load_schema('sequence')

    def test_validate_config(self):
        config.validate_config(dict(id="default", name="Default", positions=[]), 'chuck')
        config.validate_config(dict(id="default", name="Default", contacts=[]), 'sample')
        config.validate_config(dict(id="default", name="Default", contacts=[]), 'sequence')

    def test_load_chuck(self):
        results = config.list_configs(config.CHUCK_DIR)
        for name, filename in results:
            chuck = config.load_chuck(filename)

    def test_load_sample(self):
        results = config.list_configs(config.SAMPLE_DIR)
        for name, filename in results:
            sample = config.load_sample(filename)

    def test_load_sequence(self):
        results = config.list_configs(config.SEQUENCE_DIR)
        for name, filename in results:
            sequence = config.load_sequence(filename)

if __name__ == '__main__':
    unittest.main()
