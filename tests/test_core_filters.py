from comet_pqc.core.filters import std_mean_filter


class TestCoreFilters():

    def test_std_mean_filter(self):
        assert std_mean_filter([0.250, 0.249], 0.005)
        assert not std_mean_filter([0.250, 0.249], 0.0005)
