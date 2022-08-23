from comet_pqc.core.estimate import Estimate


class TestEstimate:

    def test_estimate_progress(self):
        e = Estimate(42)
        assert e.count == 42
        assert e.passed == 0
        assert e.progress == (0, 42)
        for i in range(1, 43):
            e.advance()
            assert e.passed == i
            assert e.progress == (i, 42)
