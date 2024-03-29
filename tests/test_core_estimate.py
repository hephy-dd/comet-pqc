from pqc.core.estimate import Estimate


def test_estimate_progress():
    est = Estimate(42)
    assert est.count == 42
    assert est.passed == 0
    assert est.progress == (0, 42)
    for i in range(est.count + 1):
        est.advance()
        assert est.passed == i + 1
        assert est.progress == (i + 1, 42)
