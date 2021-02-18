import math
import os
import unittest

from comet_pqc.position import Position

class PositionTest(unittest.TestCase):

    def test_empty(self):
        p = Position()
        self.assertTrue(math.isnan(p.x))
        self.assertTrue(math.isnan(p.y))
        self.assertTrue(math.isnan(p.z))
        self.assertEqual(False, p.is_valid)

    def test_all(self):
        p = Position(1.2, 2.3, 3.4)
        self.assertEqual(1.2, p.x)
        self.assertEqual(2.3, p.y)
        self.assertEqual(3.4, p.z)
        self.assertEqual((1.2, 2.3, 3.4), tuple(p))
        self.assertEqual(True, p.is_valid)

    def test_add(self):
        p1 = Position(1.2, -2.3, 3.4)
        p2 = Position(2.3, 3.4, 5.5)
        p3 = p1 + p2
        ref = Position(p1.x+p2.x, p1.y+p2.y, p1.z+p2.z)
        self.assertEqual(ref, p1 + p2)
        self.assertEqual(ref, p3)
        self.assertEqual(p3, p1 + p2)

    def test_sub(self):
        p1 = Position(1.2, -2.3, 3.4)
        p2 = Position(2.3, 3.4, 5.5)
        p3 = p1 - p2
        ref = Position(p1.x - p2.x, p1.y - p2.y, p1.z - p2.z)
        self.assertEqual(ref, p1 - p2)
        self.assertEqual(ref, p3)
        self.assertEqual(p3, p1 - p2)

    def test_eq(self):
        p1 = Position(1.2, 2.3, 3.4)
        p2 = Position(1.2, 2.3, 3.4)
        p3 = Position(2.3, 3.4, 5.5)
        self.assertTrue(p1 == p2)
        self.assertFalse(p1 != p2)
        self.assertFalse(p2 == p3)
        self.assertTrue(p2 != p3)

    def test_le(self):
        p1 = Position(1.2, 2.3, 3.4)
        p2 = Position(2.3, 3.4, 5.5)
        self.assertTrue(p1 < p2)
        self.assertFalse(p1 > p2)

    def test_le(self):
        p1 = Position(1.2, 2.3, 3.4)
        p2 = Position(2.3, 3.4, 5.5)
        self.assertTrue(p1 <= p2)
        self.assertFalse(p1 >= p2)


if __name__ == '__main__':
    unittest.main()
