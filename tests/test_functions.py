from comet_pqc import functions


class TestFunctions:

    def assert_range(self, begin, end, step, ref):
        values = []
        for value in functions.LinearRange(begin, end, step):
            values.append(value)
            if len(values) > len(ref):
                break
        assert values == ref

    def test_range(self):
        self.assert_range(0, 0, 0, [])
        self.assert_range(0, 1, 0, [])
        self.assert_range(1, 0, 0, [])
        self.assert_range(1, 1, 0, [])

        self.assert_range(0, 0, 0, [])
        self.assert_range(0, -1, 0, [])
        self.assert_range(-1, 0, 0, [])
        self.assert_range(-1, -1, 0, [])

        self.assert_range(0, 0, 1, [])
        self.assert_range(0, 1, 2, [])
        self.assert_range(0, 1, 1, [0, 1])
        self.assert_range(1, 0, 1, [1, 0])  # auto step
        self.assert_range(1, 1, 1, [])

        self.assert_range(0, 0, 1, [])
        self.assert_range(0, -1, 1, [0, -1])  # auto step
        self.assert_range(-1, 0, 1, [-1, 0])
        self.assert_range(-1, -1, 1, [])

        self.assert_range(0, 0, -1, [])
        self.assert_range(0, 1, -1, [0, 1])  # auto step
        self.assert_range(1, 0, -1, [1, 0])
        self.assert_range(1, 1, -1, [])

        self.assert_range(0, 0, -1, [])
        self.assert_range(0, -1, -1, [0, -1])
        self.assert_range(-1, 0, -1, [-1, 0])  # auto step
        self.assert_range(-1, -1, -1, [])

        self.assert_range(0, 0, 0, [])
        self.assert_range(0, 5, 0, [])
        self.assert_range(5, 0, 0, [])
        self.assert_range(5, 5, 0, [])

        self.assert_range(0, 0, 0, [])
        self.assert_range(0, -5, 0, [])
        self.assert_range(-5, 0, 0, [])
        self.assert_range(-5, -5, 0, [])

        self.assert_range(0, 0, 2.5, [])
        self.assert_range(0, 5, 2.5, [0, 2.5, 5])
        self.assert_range(5, 0, 2.5, [5, 2.5, 0])  # auto step
        self.assert_range(5, 5, 2.5, [])

        self.assert_range(0, 0, 2.5, [])
        self.assert_range(0, -5, 2.5, [0, -2.5, -5])  # auto step
        self.assert_range(-5, 0, 2.5, [-5, -2.5, 0])
        self.assert_range(-5, -5, 2.5, [])

        self.assert_range(0, 0, -2.5, [])
        self.assert_range(0, 5, -2.5, [0, 2.5, 5])  # auto step
        self.assert_range(5, 0, -2.5, [5, 2.5, 0])
        self.assert_range(5, 5, -2.5, [])

        self.assert_range(0, 0, -2.5, [])
        self.assert_range(0, -5, -2.5, [0, -2.5, -5])
        self.assert_range(-5, 0, -2.5, [-5, -2.5, 0])  # auto step
        self.assert_range(-5, -5, -2.5, [])

        self.assert_range(-2.5, 2.5, -2.5, [-2.5, 0, 2.5])  # auto step
        self.assert_range(-2.5, 2.5, 2.5, [-2.5, 0, 2.5])
        self.assert_range(2.5, -2.5, 2.5, [2.5, 0, -2.5])  # auto step
        self.assert_range(2.5, -2.5, -2.5, [2.5, 0, -2.5])

        self.assert_range(0, 1e-5, 2e-6, [0, 2e-6, 4e-6, 6e-6, 8e-6, 1e-5])
        self.assert_range(1e-5, 0, 2e-6, [1e-5, 8e-6, 6e-6, 4e-6, 2e-6, 0])

        self.assert_range(0, 1, .3, [0, .3, .6, .9, 1.])
        self.assert_range(1, 0, -.3, [1, .7, .4, .1, 0])

        self.assert_range(0, .7, .2, [0, .2, .4, .6, .7])
        self.assert_range(.7, 0, -.2, [.7, .5, .3, .1, 0])
