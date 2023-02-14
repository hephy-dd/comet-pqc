from typing import List, Optional

from PyQt5 import QtCore, QtWidgets

__all__ = ["MetricWidget"]


class MetricUnit:

    def __init__(self, base: float, prefix: str, name: str) -> None:
        self.base: float = base
        self.prefix: str = prefix
        self.name: str = name


class MetricUnits:

    default_metric_unit = MetricUnit(1e+0, "", "")
    metric_units: List[MetricUnit] = [
        MetricUnit(1e+24, "Y", "yotta"),
        MetricUnit(1e+21, "Z", "zetta"),
        MetricUnit(1e+18, "E", "exa"),
        MetricUnit(1e+15, "P", "peta"),
        MetricUnit(1e+12, "T", "tera"),
        MetricUnit(1e+9, "G", "giga"),
        MetricUnit(1e+6, "M", "mega"),
        MetricUnit(1e+3, "k", "kilo"),
        default_metric_unit,
        MetricUnit(1e-3, "m", "milli"),
        MetricUnit(1e-6, "u", "micro"),
        MetricUnit(1e-9, "n", "nano"),
        MetricUnit(1e-12, "p", "pico"),
        MetricUnit(1e-15, "f", "femto"),
        MetricUnit(1e-18, "a", "atto"),
        MetricUnit(1e-21, "z", "zepto"),
        MetricUnit(1e-24, "y", "yocto"),
    ]

    @classmethod
    def get(cls, value: float) -> MetricUnit:
        for metric_unit in cls.metric_units:
            if value >= metric_unit.base:
                return metric_unit
        return cls.default_metric_unit


class MetricItem:
    """Metric item used for combo box selection."""

    def __init__(self, metric: MetricUnit, unit: str) -> None:
        self.metric: MetricUnit = metric
        self.unit: str = unit

    def __str__(self) -> str:
        return f"{self.metric.prefix}{self.unit}"


class MetricWidget(QtWidgets.QWidget):
    """Metric input."""

    valueChanged = QtCore.pyqtSignal(float)
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, unit: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        minimum: float = -9_999.999
        maximum: float = +9_999.999

        self._valueSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self._valueSpinBox.setRange(minimum, maximum)
        self._valueSpinBox.setStepType(QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)

        self._unitComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)

        self.setUnit(unit)
        self.setDecimals(3)
        self.setPrefixes("1")
        self.setValue(0)

        layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self._valueSpinBox)
        layout.addWidget(self._unitComboBox)

        layout.setStretch(0, 1)
        layout.setStretch(1, 0)

        # Signals

        self._valueSpinBox.valueChanged.connect(lambda _: self.valueChanged.emit(self.value()))
        self._valueSpinBox.editingFinished.connect(lambda: self.editingFinished.emit())
        self._unitComboBox.currentIndexChanged.connect(lambda: self.valueChanged.emit(self.value()))

    def unit(self) -> str:
        return str(self._unit)

    def setUnit(self, unit: str) -> None:
        self._unit = str(unit)

    def value(self) -> float:
        item = self._unitComboBox.currentData()
        if isinstance(item, MetricItem):
            return round(self._valueSpinBox.value(), self.decimals()) * item.metric.base
        return round(self._valueSpinBox.value(), self.decimals())

    def setValue(self, value: float) -> None:
        metric = MetricUnits.get(value)
        for index in range(self._unitComboBox.count()):
            item = self._unitComboBox.itemData(index)
            if isinstance(item, MetricItem):
                if item.metric.base == metric.base:
                    with QtCore.QSignalBlocker(self._unitComboBox):
                        self._unitComboBox.setCurrentIndex(index)
                    self._valueSpinBox.setValue(round(value / item.metric.base, self.decimals()))
                    break

    def setMinimum(self, minimum: float) -> None:  # TODO
        self._valueSpinBox.setMinimum(minimum)

    def decimals(self) -> int:
        return self._valueSpinBox.decimals()

    def setDecimals(self, value: int) -> None:
        self._valueSpinBox.setDecimals(value)

    def prefixes(self) -> str:
        prefixes = []
        for index in range(self._unitComboBox.count()):
            item = self._unitComboBox.itemData(index)
            if isinstance(item, MetricItem):
                prefixes.append(item.metric.prefix)
        return "".join(prefixes)

    def setPrefixes(self, value: str) -> None:
        unit = self.unit()
        with QtCore.QSignalBlocker(self._unitComboBox):
            self._unitComboBox.clear()
            for metric in MetricUnits.metric_units:
                item = MetricItem(metric, unit)
                if metric.prefix and metric.prefix in value:
                    self._unitComboBox.addItem(format(item), item)
                elif "1" in value and not metric.prefix:
                    self._unitComboBox.addItem(format(item), item)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = MetricWidget("V")
    w.setDecimals(3)
    w.setMinimum(0)
    w.setPrefixes("k1m")
    w.valueChanged.connect(lambda value: print(f"valueChanged({value!r})"))
    w.editingFinished.connect(lambda: print("editingFinished()"))
    w.setValue(0.004217)
    assert round(w.value(), 6) == 0.004217
    w.show()
    app.exec()
