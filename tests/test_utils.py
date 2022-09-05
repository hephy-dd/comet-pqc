from comet_pqc import utils


class TestUtils:

    def test_format_metric(self):
        assert "4.20 YA" == utils.format_metric(4.2e24, "A", decimals=2)
        assert "-4.200 ZA" == utils.format_metric(-4.2e21, "A")
        assert "4.200 EA" == utils.format_metric(4.2e18, "A")
        assert "-4.200 PA" == utils.format_metric(-4.2e15, "A")
        assert "4.200 TA" == utils.format_metric(4.2e12, "A")
        assert "-4.200 GA" == utils.format_metric(-4.2e9, "A")
        assert "4.200 MA" == utils.format_metric(4.2e6, "A")
        assert "-42.000 kA" == utils.format_metric(-4.2e4, "A")
        assert "4.200 kA" == utils.format_metric(4.2e3, "A")
        assert "-4.200 A" == utils.format_metric(-4.2, "A")
        assert "0.000 V" == utils.format_metric(0, "V")
        assert "0.0 V" == utils.format_metric(0, "V", decimals=1)
        assert "0.000 V" == utils.format_metric(1.0e-32, "V")
        assert "0.000 V" == utils.format_metric(1.0e-26, "V")
        assert "0.000 V" == utils.format_metric(1.0e-25, "V")
        assert "1.000 yV" == utils.format_metric(1.0e-24, "V")
        assert "4.200 mA" == utils.format_metric(4.2e-3, "A")
        assert "-4.200 uA" == utils.format_metric(-4.2e-6, "A")
        assert "4.200 nA" == utils.format_metric(4.2e-9, "A")
        assert "-4.200 pA" == utils.format_metric(-4.2e-12, "A")
        assert "4.200 fA" == utils.format_metric(4.2e-15, "A")
        assert "-4.200 aA" == utils.format_metric(-4.2e-18, "A")
        assert "4.200 zA" == utils.format_metric(4.2e-21, "A")
        assert "-4.200000 yA" == utils.format_metric(-4.2e-24, "A", decimals=6)

    def test_format_switch(self):
        assert "OFF" == utils.format_switch(False)
        assert "ON" == utils.format_switch(True)

    def test_format_table_unit(self):
        assert "1.000 mm" == utils.format_table_unit(1)
        assert "0.420 mm" == utils.format_table_unit(.42)

    def test_from_table_unit(self):
        assert 0.001 == utils.from_table_unit(1.0)
        assert 0.042 == utils.from_table_unit(42.0)

    def test_to_table_unit(self):
        assert 1000.0 == utils.to_table_unit(1)
        assert 420.0 == utils.to_table_unit(.42)
