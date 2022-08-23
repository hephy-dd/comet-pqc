import pytest

from comet_pqc.core.request import Request, RequestTimeout


class TestRequest:

    def test_request(self):
        r = Request(lambda: 42)
        r()
        assert r.get(timeout=.025) == 42

    def test_request_exception(self):
        r = Request(lambda: 1 / 0)
        r()
        with pytest.raises(ZeroDivisionError):
            r.get(timeout=.025)

    def test_request_timeout(self):
        r = Request(lambda: None)
        with pytest.raises(RequestTimeout):
            r.get(timeout=.025)
