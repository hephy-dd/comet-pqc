class LinearRange:

    def __init__(self, begin, end, step):
        self.begin = begin
        self.end = end
        self.step = step

    @property
    def distance(self):
        return abs(self.end - self.begin)

    def __len__(self):
        return int(abs(round(self.distance / self.step)))

    def __iter__(self):
        begin, end, step = self.begin, self.end, self.step
        step = -abs(step) if end < begin else abs(step)
        count = len(self)
        return (begin + (i * step) for i in range(count + 1))
