import unittest

from comet_pqc import functions

class FunctionsTest(unittest.TestCase):

    def assertRange(self, begin, end, step, ref):
        l = []
        for value in functions.LinearRange(begin, end, step):
            l.append(value)
            if len(l) > len(ref):
                break
        self.assertEqual(l, ref)

    def test_range(self):
        self.assertRange(0, 0, 0, [])
        self.assertRange(0, 1, 0, [])
        self.assertRange(1, 0, 0, [])
        self.assertRange(1, 1, 0, [])

        self.assertRange(0, 0, 0, [])
        self.assertRange(0, -1, 0, [])
        self.assertRange(-1, 0, 0, [])
        self.assertRange(-1, -1, 0, [])

        self.assertRange(0, 0, 1, [])
        self.assertRange(0, 1, 1, [0, 1])
        self.assertRange(1, 0, 1, [1, 0]) # auto step
        self.assertRange(1, 1, 1, [])

        self.assertRange(0, 0, 1, [])
        self.assertRange(0, -1, 1, [0, -1]) # auto step
        self.assertRange(-1, 0, 1, [-1, 0])
        self.assertRange(-1, -1, 1, [])

        self.assertRange(0, 0, -1, [])
        self.assertRange(0, 1, -1, [0, 1]) # auto step
        self.assertRange(1, 0, -1, [1, 0])
        self.assertRange(1, 1, -1, [])

        self.assertRange(0, 0, -1, [])
        self.assertRange(0, -1, -1, [0, -1])
        self.assertRange(-1, 0, -1, [-1, 0]) # auto step
        self.assertRange(-1, -1, -1, [])

        self.assertRange(0, 0, 0, [])
        self.assertRange(0, 5, 0, [])
        self.assertRange(5, 0, 0, [])
        self.assertRange(5, 5, 0, [])

        self.assertRange(0, 0, 0, [])
        self.assertRange(0, -5, 0, [])
        self.assertRange(-5, 0, 0, [])
        self.assertRange(-5, -5, 0, [])

        self.assertRange(0, 0, 2.5, [])
        self.assertRange(0, 5, 2.5, [0, 2.5, 5])
        self.assertRange(5, 0, 2.5, [5, 2.5, 0]) # auto step
        self.assertRange(5, 5, 2.5, [])

        self.assertRange(0, 0, 2.5, [])
        self.assertRange(0, -5, 2.5, [0, -2.5, -5]) # auto step
        self.assertRange(-5, 0, 2.5, [-5, -2.5, 0])
        self.assertRange(-5, -5, 2.5, [])

        self.assertRange(0, 0, -2.5, [])
        self.assertRange(0, 5, -2.5, [0, 2.5, 5]) # auto step
        self.assertRange(5, 0, -2.5, [5, 2.5, 0])
        self.assertRange(5, 5, -2.5, [])

        self.assertRange(0, 0, -2.5, [])
        self.assertRange(0, -5, -2.5, [0, -2.5, -5])
        self.assertRange(-5, 0, -2.5, [-5, -2.5, 0]) # auto step
        self.assertRange(-5, -5, -2.5, [])

        self.assertRange(-2.5, 2.5, -2.5, [-2.5, 0, 2.5]) # auto step
        self.assertRange(-2.5, 2.5, 2.5, [-2.5, 0, 2.5])
        self.assertRange(2.5, -2.5, 2.5, [2.5, 0, -2.5]) # auto step
        self.assertRange(2.5, -2.5, -2.5, [2.5, 0, -2.5])

if __name__ == '__main__':
    unittest.main()
