import time

from comet_pqc.core.timer import Timer


class TestTimer:

    def test_timer(self):
        t = Timer()
        time.sleep(0.002)
        dt = t.delta()
        assert dt >= 0.002
        t.reset()
        time.sleep(0.001)
        dt = t.delta()
        assert dt >= 0.001
