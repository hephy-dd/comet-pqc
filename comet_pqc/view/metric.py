from typing import Optional

from PyQt5 import QtCore, QtWidgets

__all__ = ["Metric"]


class MetricUnit:

    def __init__(self, base: float, prefix: str, name: str) -> None:
        self.base: float = base
        self.prefix: str =prefix
        self.name: str = name


class MetricUnits:

    default_unit = MetricUnit(1e+0, "", "")

    metric_units = (
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
    )

    @classmethod
    def get(cls, value: float) -> MetricUnit:
        for mertric in cls.metric_units:
            if value >= mertric.base:
                return mertric
        return cls.default_unit


class MetricItem:
    """Metric item used for combo box selection."""

    def __init__(self, metric: MetricUnit, unit: str) -> None:
        self.metric: MetricUnit = metric
        self.unit: str = unit

    def __str__(self) -> str:
        return f"{self.metric.prefix}{self.unit}"


class Metric(QtWidgets.QWidget):
    """Metric input."""

    valueChanged = QtCore.pyqtSignal(float)
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._valueSpinBox = QtWidgets.QDoubleSpinBox(self)
        self._valueSpinBox.setStepType(QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        self._unitComboBox = QtWidgets.QComboBox(self)
        self.setUnit("")
        self.setDecimals(0)
        self.setRange(float("-inf"), float("+inf"))
        self.setPrefixes("YZEPTGMk1munpfazy")
        self.setValue(0)
        self._valueSpinBox.valueChanged.connect(lambda _: self.valueChanged.emit(self.value()))
        self._valueSpinBox.editingFinished.connect(self.editingFinished.emit)
        self._unitComboBox.currentIndexChanged.connect(lambda _: self.valueChanged.emit(self.value()))

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._valueSpinBox, 1)
        layout.addWidget(self._unitComboBox, 0)

    def setRange(self, minimum: float, maximum: float) -> None:
        self._valueSpinBox.setRange(minimum, maximum)

    def value(self) -> float:
        index = self._unitComboBox.currentIndex()
        item = self._unitComboBox.itemData(index)
        if isinstance(item, MetricItem):
            base = item.metric.base
        else:
            base = 1.0
        return self._valueSpinBox.value() * base

    def setValue(self, value: float) -> None:
        metric = MetricUnits.get(value)
        for index in range(self._unitComboBox.count()):
            item = self._unitComboBox.itemData(index)
            if isinstance(item, MetricItem):
                if item.metric.base == metric.base:
                    self._unitComboBox.setCurrentIndex(index)
        index = self._unitComboBox.currentIndex()
        item = self._unitComboBox.itemData(index)
        if isinstance(item, MetricItem):
            self._valueSpinBox.setValue(value / item.metric.base)

    def decimals(self) -> int:
        return self._valueSpinBox.decimals()

    def setDecimals(self, decimals: int) -> None:
        self._valueSpinBox.setDecimals(decimals)

    def unit(self) -> str:
        return self._unit

    def setUnit(self, unit: str) -> None:
        self._unit = unit

    def prefixes(self) -> str:
        prefixes = ""
        for index in range(self._unitComboBox.count()):
            value = self._unitComboBox.itemData(index)
            prefixes += value.metric.prefix
        return prefixes

    def setPrefixes(self, prefixes: str) -> None:
        self._unitComboBox.clear()
        for metric in MetricUnits.metric_units:
            item = MetricItem(metric, self._unit)
            if metric.prefix and metric.prefix in prefixes:
                self._unitComboBox.addItem(str(item), item)
            elif "1" in prefixes:
                self._unitComboBox.addItem(str(item), item)
