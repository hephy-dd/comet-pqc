import os
import unittest

from comet_pqc import utils

class UtilsTest(unittest.TestCase):

    def test_PACKAGE_PATH(self):
        root_path = os.path.dirname(os.path.dirname(__file__))
        package_path = os.path.join(root_path, 'comet_pqc')
        self.assertEqual(package_path, utils.PACKAGE_PATH)

    def test_make_path(self):
        filename = os.path.join(utils.PACKAGE_PATH, 'assets', 'sample.txt')
        self.assertEqual(filename, utils.make_path('assets', 'sample.txt'))

    def test_format_metric(self):
        self.assertEqual('4.20 YA', utils.format_metric(4.2e24, 'A', decimals=2))
        self.assertEqual('-4.200 ZA', utils.format_metric(-4.2e21, 'A'))
        self.assertEqual('4.200 EA', utils.format_metric(4.2e18, 'A'))
        self.assertEqual('-4.200 PA', utils.format_metric(-4.2e15, 'A'))
        self.assertEqual('4.200 TA', utils.format_metric(4.2e12, 'A'))
        self.assertEqual('-4.200 GA', utils.format_metric(-4.2e9, 'A'))
        self.assertEqual('4.200 MA', utils.format_metric(4.2e6, 'A'))
        self.assertEqual('-42.000 kA', utils.format_metric(-4.2e4, 'A'))
        self.assertEqual('4.200 kA', utils.format_metric(4.2e3, 'A'))
        self.assertEqual('-4.200 A', utils.format_metric(-4.2, 'A'))
        self.assertEqual('0.000 V', utils.format_metric(0, 'V'))
        self.assertEqual('0.0 V', utils.format_metric(0, 'V', decimals=1))
        self.assertEqual('0.000 V', utils.format_metric(1.0e-32, 'V'))
        self.assertEqual('0.000 V', utils.format_metric(1.0e-26, 'V'))
        self.assertEqual('0.000 V', utils.format_metric(1.0e-25, 'V'))
        self.assertEqual('1.000 yV', utils.format_metric(1.0e-24, 'V'))
        self.assertEqual('4.200 mA', utils.format_metric(4.2e-3, 'A'))
        self.assertEqual('-4.200 uA', utils.format_metric(-4.2e-6, 'A'))
        self.assertEqual('4.200 nA', utils.format_metric(4.2e-9, 'A'))
        self.assertEqual('-4.200 pA', utils.format_metric(-4.2e-12, 'A'))
        self.assertEqual('4.200 fA', utils.format_metric(4.2e-15, 'A'))
        self.assertEqual('-4.200 aA', utils.format_metric(-4.2e-18, 'A'))
        self.assertEqual('4.200 zA', utils.format_metric(4.2e-21, 'A'))
        self.assertEqual('-4.200000 yA', utils.format_metric(-4.2e-24, 'A', decimals=6))

    def test_format_switch(self):
        self.assertEqual('OFF', utils.format_switch(False))
        self.assertEqual('ON', utils.format_switch(True))

    def test_format_table_unit(self):
        self.assertEqual('1.000 mm', utils.format_table_unit(1))
        self.assertEqual('0.420 mm', utils.format_table_unit(.42))

    def test_std_mean_filter(self):
        self.assertTrue(utils.std_mean_filter([0.250, 0.249], threshold=0.005))
        self.assertFalse(utils.std_mean_filter([0.250, 0.224], threshold=0.005))

if __name__ == '__main__':
    unittest.main()
