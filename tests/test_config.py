import os
import logging
import unittest

from comet_pqc import config

class ConfigTest(unittest.TestCase):

    def testChuckConfig(self):
        logging.info("listing chuck configurations:")
        results = config.list_configs(config.CHUCK_DIR)
        for name, filename in results:
            logging.info("name=%s, filename=%s", name, filename)
            chuck = config.load_chuck(filename)
            logging.info("chuck=%s", chuck.__dict__)

    def testWaferConfig(self):
        logging.info("listing wafer configurations:")
        results = config.list_configs(config.WAFER_DIR)
        for name, filename in results:
            logging.info("name=%s, filename=%s", name, filename)
            wafer= config.load_wafer(filename)
            logging.info("wafer=%s", wafer)

    def testSequenceConfig(self):
        logging.info("listing sequence configurations:")
        results = config.list_configs(config.SEQUENCE_DIR)
        for name, filename in results:
            logging.info("name=%s, filename=%s", name, filename)
            sequence= config.load_sequence(filename)
            logging.info("sequence=%s", sequence)

if __name__ == '__main__':
    unittest.main()
