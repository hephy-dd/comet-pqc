import pytest

from comet_pqc.core.request import Request, RequestTimeout


class TestCoreRequest:

    def test_request(self):
        req = Request(lambda: 42)
        req()
        assert req.get(timeout=.001) == 42

    def test_request_exception(self):
        req = Request(lambda: 1 / 0)
        req()
        with pytest.raises(ZeroDivisionError):
            req.get(timeout=.001)

    def test_request_timeout(self):
        req = Request(lambda: None)
        with pytest.raises(RequestTimeout):
            req.get(timeout=.001)
