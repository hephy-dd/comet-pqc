import math

from comet_pqc.core.position import Position


def test_empty():
    p = Position()
    assert math.isnan(p.x)
    assert math.isnan(p.y)
    assert math.isnan(p.z)
    assert not p.is_valid


def test_all():
    p = Position(1.2, 2.3, 3.4)
    assert 1.2 == p.x
    assert 2.3 == p.y
    assert 3.4 == p.z
    assert (1.2, 2.3, 3.4) == tuple(p)
    assert p.is_valid


def test_add():
    p1 = Position(1.2, -2.3, 3.4)
    p2 = Position(2.3, 3.4, 5.5)
    p3 = p1 + p2
    ref = Position(p1.x + p2.x, p1.y + p2.y, p1.z + p2.z)
    assert ref == p1 + p2
    assert ref == p3
    assert p3 == p1 + p2


def test_sub():
    p1 = Position(1.2, -2.3, 3.4)
    p2 = Position(2.3, 3.4, 5.5)
    p3 = p1 - p2
    ref = Position(p1.x - p2.x, p1.y - p2.y, p1.z - p2.z)
    assert ref == p1 - p2
    assert ref == p3
    assert p3 == p1 - p2


def test_eq():
    p1 = Position(1.2, 2.3, 3.4)
    p2 = Position(1.2, 2.3, 3.4)
    p3 = Position(2.3, 3.4, 5.5)
    assert p1 == p2
    assert not p1 != p2
    assert not p2 == p3
    assert p2 != p3


def test_lt():
    p1 = Position(1.2, 2.3, 3.4)
    p2 = Position(2.3, 3.4, 5.5)
    assert p1 < p2
    assert not p1 > p2


def test_le():
    p1 = Position(1.2, 2.3, 3.4)
    p2 = Position(2.3, 3.4, 5.5)
    assert p1 <= p2
    assert not p1 >= p2
