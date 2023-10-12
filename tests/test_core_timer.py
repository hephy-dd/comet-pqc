import time

from pqc.core.timer import Timer


def test_timer(monkeypatch):
    time_values = iter([1000, 2000, 2000, 4000])  # values to be returned by time.monotonic()

    monkeypatch.setattr(time, "monotonic", lambda: next(time_values))
    monkeypatch.setattr(time, "sleep", lambda sec: None)

    t = Timer()
    time.sleep(1)
    dt = t.delta()
    assert dt == 1000
    t.reset()
    time.sleep(2)
    dt = t.delta()
    assert dt == 2000
