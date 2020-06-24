import qutie as comet

__all__ = ['Metric']

class MetricUnits:

    class Metric:

        def __init__(self, base, prefix, name):
            self.base = base
            self.prefix =prefix
            self.name = name

    METRICS = (
        Metric(1e+24, 'Y', 'yotta'),
        Metric(1e+21, 'Z', 'zetta'),
        Metric(1e+18, 'E', 'exa'),
        Metric(1e+15, 'P', 'peta'),
        Metric(1e+12, 'T', 'tera'),
        Metric(1e+9, 'G', 'giga'),
        Metric(1e+6, 'M', 'mega'),
        Metric(1e+3, 'k', 'kilo'),
        Metric(1e+0, '', ''),
        Metric(1e-3, 'm', 'milli'),
        Metric(1e-6, 'u', 'micro'),
        Metric(1e-9, 'n', 'nano'),
        Metric(1e-12, 'p', 'pico'),
        Metric(1e-15, 'f', 'femto'),
        Metric(1e-18, 'a', 'atto'),
        Metric(1e-21, 'z', 'zepto'),
        Metric(1e-24, 'y', 'yocto')
    )

    @classmethod
    def get(cls, value):
        for mertric in cls.METRICS:
            if value >= mertric.base:
                return mertric
        return cls.METRICS[-1]

class Metric(comet.Row):
    """Metric input."""

    default_prefixes = 'YZEPTGMk1munpfazy'

    class UnitLabel:

        def __init__(self, metric, unit):
            self.metric = metric
            self.unit = unit

        def __str__(self):
            return f"{self.metric.prefix}{self.unit}"

    def __init__(self, *args, value=None, minimum=None, maximum=None,
                 decimals=None, unit=None, prefixes=None, changed=None,
                 editing_finished=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__number = comet.Number(minimum=minimum, maximum=maximum, adaptive=True)
        self.__combobox = comet.ComboBox()
        self.unit = unit or ''
        self.decimals = decimals or 0
        self.prefixes = prefixes or self.default_prefixes
        self.value = value or 0
        self.append(self.__number)
        self.append(self.__combobox)
        self.stretch = 1, 0
        self.__number.changed = lambda _: self.emit('changed', self.value)
        self.__number.editing_finished = lambda: self.emit('editing_finished')
        self.__combobox.changed = lambda _: self.emit('changed', self.value)
        self.changed = changed
        self.editing_finished = editing_finished

    @property
    def value(self):
        return self.__number.value * self.__combobox.current.metric.base

    @value.setter
    def value(self, value):
        metric = MetricUnits.get(value)
        for item in self.__combobox:
            if item.metric.base == metric.base:
                self.__combobox.current = item
        self.__number.value = value / self.__combobox.current.metric.base

    @property
    def decimals(self):
        return self.__number.decimals

    @decimals.setter
    def decimals(self, value):
        self.__number.decimals = value

    @property
    def unit(self):
        return self.__unit

    @unit.setter
    def unit(self, value):
        self.__unit = value

    @property
    def prefixes(self):
        return [value.metric.prefix for value in self.__combobox.values]

    @prefixes.setter
    def prefixes(self, value):
        self.__combobox.clear()
        for metric in MetricUnits.METRICS:
            if metric.prefix and metric.prefix in value:
                self.__combobox.append(self.UnitLabel(metric, self.__unit))
            elif '1' in value:
                self.__combobox.append(self.UnitLabel(metric, self.__unit))

    @property
    def changed(self):
        return self.__changed

    @changed.setter
    def changed(self, value):
        self.__changed = value

    @property
    def editing_finished(self):
        return self.__editing_finished

    @editing_finished.setter
    def editing_finished(self, value):
        self.__editing_finished = value
