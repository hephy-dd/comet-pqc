from typing import List

from PyQt5 import QtCore, QtWidgets

__all__ = ["Metric"]


class MetricUnit:

    def __init__(self, base: float, prefix: str, name: str):
        self.base: float = base
        self.prefix: str =prefix
        self.name: str = name


class MetricUnits:

    default_unit: MetricUnit = MetricUnit(1e+0, "", "")

    metric_units: List[MetricUnit] = [
        MetricUnit(1e+24, "Y", "yotta"),
        MetricUnit(1e+21, "Z", "zetta"),
        MetricUnit(1e+18, "E", "exa"),
        MetricUnit(1e+15, "P", "peta"),
        MetricUnit(1e+12, "T", "tera"),
        MetricUnit(1e+9, "G", "giga"),
        MetricUnit(1e+6, "M", "mega"),
        MetricUnit(1e+3, "k", "kilo"),
        default_unit,
        MetricUnit(1e-3, "m", "milli"),
        MetricUnit(1e-6, "u", "micro"),
        MetricUnit(1e-9, "n", "nano"),
        MetricUnit(1e-12, "p", "pico"),
        MetricUnit(1e-15, "f", "femto"),
        MetricUnit(1e-18, "a", "atto"),
        MetricUnit(1e-21, "z", "zepto"),
        MetricUnit(1e-24, "y", "yocto")
    ]

    @classmethod
    def get(cls, value: float) -> MetricUnit:
        for mertric in cls.metric_units:
            if value >= mertric.base:
                return mertric
        return cls.default_unit


class MetricItem:
    """Metric item used for combo box selection."""

    def __init__(self, metric: MetricUnit, unit: str):
        self.metric: MetricUnit = metric
        self.unit: str = unit

    def __str__(self):
        return f"{self.metric.prefix}{self.unit}"


class Metric(QtWidgets.QWidget):
    """Metric input widget."""

    DefaultPrefixes = "YZEPTGMk1munpfazy"

    valueChanged = QtCore.pyqtSignal(float)
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, unit: str, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.valueSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.valueSpinBox.setStepType(QtWidgets.QDoubleSpinBox.AdaptiveDecimalStepType)

        self.unitComboBox = QtWidgets.QComboBox(self)

        self.setUnit(unit)
        self.setDecimals(0)
        self.setPrefixes(type(self).DefaultPrefixes)
        self.setValue(0)

        self.valueSpinBox.valueChanged.connect(self.valueChanged.emit)
        self.valueSpinBox.editingFinished.connect(self.editingFinished.emit)

        self.unitComboBox.currentIndexChanged.connect(lambda _: self.valueChanged.emit(self.value()))

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.valueSpinBox, 1)
        layout.addWidget(self.unitComboBox, 0)

    def value(self) -> float:
        return self.valueSpinBox.value() * self.unitComboBox.currentData().metric.base

    def setValue(self, value: float) -> None:
        metric = MetricUnits.get(value)
        for index in range(self.unitComboBox.count()):
            item = self.unitComboBox.itemData(index)
            if item.metric.base == metric.base:
                index = self.unitComboBox.findData(item)
                self.unitComboBox.setCurrentIndex(index)
        self.valueSpinBox.setValue(value / self.unitComboBox.currentData().metric.base)

    def decimals(self) -> int:
        return self.valueSpinBox.decimals()

    def setDecimals(self, decimals: int) -> None:
        self.valueSpinBox.setDecimals(decimals)

    def setRange(self, minimum: float, maximum: float) -> None:
        self.valueSpinBox.setRange(minimum, maximum)

    def unit(self) -> str:
        return self.property("unit")

    def setUnit(self, unit: str) -> None:
        self.setProperty("unit", unit)

    def prefixes(self) -> str:
        prefixes = []
        for index in range(self.unitComboBox.count()):
            prefixes.append(self.unitComboBox.itemData(index).metric.prefix)
        return "".join(prefixes)

    def setPrefixes(self, prefixes: str) -> None:
        with QtCore.QSignalBlocker(self.unitComboBox):
            self.unitComboBox.clear()
            for metric in MetricUnits.metric_units:
                item = MetricItem(metric, self.unit())
                if metric.prefix and metric.prefix in prefixes:
                    self.unitComboBox.addItem(format(item), item)
                elif "1" in prefixes:
                    self.unitComboBox.addItem(format(item), item)
        self.valueChanged.emit(self.value())
