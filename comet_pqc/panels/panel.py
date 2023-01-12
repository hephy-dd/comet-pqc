from collections import namedtuple
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type

import comet
from comet import SettingsMixin, ui
from PyQt5 import QtCore, QtWidgets

from ..components import Metric, PlotWidget
from ..settings import settings
from ..utils import stitch_pixmaps

__all__ = ["Panel", "MeasurementPanel"]


class Bindings:

    def __init__(self) -> None:
        self._bindings: Dict[str, Tuple] = {}
        self._getters: Dict[Type, Callable[[Any], Any]] = {}
        self._setters: Dict[Type, Callable[[Any, Any], None]] = {}

    def register(self, type: Type, getter: Callable[[Any], Any], setter: Callable[[Any, Any], None]) -> None:
        if type in self._getters or type in self._setters:
            raise KeyError(f"Binding type already registered: {type}")
        self._getters[type] = getter
        self._setters[type] = setter

    def bind(self, key: str, element, default=None, unit: Optional[str] = None):
        if type(element) not in self._getters or type(element) not in self._setters:
            raise TypeError(f"No binding for: {type(element)}")
        self._bindings[key] = element, default, unit

    def all(self) -> Dict[str, Tuple]:
        return self._bindings

    def getter(self, element: Any) -> Callable[[Any], Any]:
        getter = self._getters.get(type(element))
        if getter is None:
            raise TypeError(f"No binding for: {type(element)}")
        return getter

    def setter(self, element: Any) -> Callable[[Any, Any], None]:
        setter = self._setters.get(type(element))
        if setter is None:
            raise TypeError(f"No binding for: {type(element)}")
        return setter


class Panel(SettingsMixin, QtWidgets.QWidget):

    type_name: str = ""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._stateHandlers: List[Callable] = []

        self.setTitle("")

        self.titleLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.titleLabel.setStyleSheet("font-size: 16px; font-weight: bold; height: 32px;")
        self.titleLabel.setTextFormat(QtCore.Qt.RichText)

        self.descriptionLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)

        self.rootLayout = QtWidgets.QVBoxLayout(self)
        self.rootLayout.addWidget(self.titleLabel, 0)
        self.rootLayout.addWidget(self.descriptionLabel, 0)

    def title(self) -> str:
        return self.property("title")

    def setTitle(self, title: str) -> None:
        self.setProperty("title", title)

    @property
    def context(self):
        return self.property("context")

    def store(self) -> None:
        ...

    def restore(self) -> None:
        ...

    def clearReadings(self) -> None:
        ...

    def setLocked(self, state: bool) -> None:
        self.setProperty("locked", state)

    def isLocked(self) -> bool:
        return self.property("locked") == True

    def mount(self, context):
        self.unmount()
        self.setProperty("context", context)

    def unmount(self):
        self.setProperty("context", None)
        self.titleLabel.setText("")
        self.descriptionLabel.setText("")
        self.descriptionLabel.setVisible(False)

    def updateState(self, state: dict) -> None:
        for handler in self._stateHandlers:
            handler(state)


class MeasurementPanel(Panel):
    """Base class for measurement panels."""

    type_name = "measurement"

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.bindings = Bindings()

        self.measurement = None

        self.dataPanelLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        self.generalWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.generalWidgetLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self.generalWidget)

        self.controlTabWidget = QtWidgets.QTabWidget(self)
        self.controlTabWidget.addTab(self.generalWidget, "General")

        self.statusPanelLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        self.statusWrapperLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.statusWrapperLayout.addLayout(self.statusPanelLayout)
        self.statusWrapperLayout.addStretch()

        self.controlPanelLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self.controlPanelLayout.addWidget(self.controlTabWidget, 3)
        self.controlPanelLayout.addLayout(self.statusWrapperLayout, 1)

        self.rootLayout.insertLayout(2, self.dataPanelLayout)
        self.rootLayout.insertLayout(3, self.controlPanelLayout)

        self.dataTabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)

        self.dataPanelLayout.addWidget(self.dataTabWidget)

        # Add analysis tab
        self.analysisTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.analysisTreeWidget.setHeaderLabels(["Parameter", "Value"])

        self.dataTabWidget.insertTab(0, self.analysisTreeWidget, "Analysis")

        # Plots
        self.series_transform: Dict[str, object] = {}
        self.series_transform_default = lambda x, y: (x, y)

        self.bindings.register(QtWidgets.QComboBox, lambda element: element.currentData(), lambda element, value: element.itemData(element.findData(value)))
        self.bindings.register(QtWidgets.QCheckBox, lambda element: element.isChecked(), lambda element, value: element.setChecked(value))
        self.bindings.register(QtWidgets.QDoubleSpinBox, lambda element: element.value(), lambda element, value: element.setValue(value))
        self.bindings.register(QtWidgets.QLabel, lambda element: element.text(), lambda element, value: element.setText(format(value)))
        self.bindings.register(QtWidgets.QLineEdit, lambda element: element.text(), lambda element, value: element.setText(format(value)))
        self.bindings.register(QtWidgets.QSpinBox, lambda element: element.value(), lambda element, value: element.setValue(value))
        self.bindings.register(Metric, lambda element: element.value(), lambda element, value: element.setValue(value))

    def bind(self, key: str, element, default=None, unit: Optional[str] = None):
        """Bind measurement parameter to UI element for syncronization on mount
        and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> element = QtWidgets.QSpinBox()
        >>> self.bind("value", element, default=10.0, unit="V")
        """
        self.bindings.bind(key, element, default, unit)

    def addStateHandler(self, handler: Callable[[dict], None]) -> None:
        self._stateHandlers.append(handler)

    def mount(self, measurement):
        """Mount measurement to panel."""
        super().mount(measurement)
        self.titleLabel.setText(f"{self.title()} &rarr; {measurement.name}")
        self.descriptionLabel.setText(measurement.description)
        self.descriptionLabel.setVisible(len(measurement.description) > 0)
        self.measurement = measurement
        # Load parameters to UI
        parameters = self.measurement.parameters
        for key, item in self.bindings.all().items():
            element, default, unit = item
            value = parameters.get(key, default)
            if unit is not None:
                if isinstance(value, comet.ureg.Quantity):
                    value = value.to(unit).m
            setter = self.bindings.setter(element)
            setter(element, value)
        self.load_analysis()
        # Show first tab on mount
        self.dataTabWidget.setCurrentIndex(0)
        # Update plot series style
        pointsInPlots = settings.isPointsInPlots()
        for index in range(self.dataTabWidget.count()):
            widget = self.dataTabWidget.widget(index)
            if widget.property("type") == "plot":
                for series in widget.reflection().series.values():
                    series.qt.setPointsVisible(pointsInPlots)
            if isinstance(widget, PlotWidget):
                for series in widget.chart.series():
                    series.setPointsVisible(pointsInPlots)

    def unmount(self):
        """Unmount measurement from panel."""
        super().unmount()
        self.measurement = None
        self.analysisTreeWidget.clear()

    def store(self):
        """Store UI element values to measurement parameters."""
        if self.measurement:
            parameters = self.measurement.parameters
            for key, item in self.bindings.all().items():
                element, default, unit = item
                getter = self.bindings.getter(element)
                value = getter(element)
                if unit is not None:
                    value = value * comet.ureg(unit)
                parameters[key] = value

    def restore(self):
        """Restore measurement defaults."""
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            for key, item in self.bindings.all().items():
                element, default, unit = item
                value = default_parameters.get(key, default)
                if unit is not None:
                    if isinstance(value, comet.ureg.Quantity):
                        value = value.to(unit).m
                setter = self.bindings.setter(element)
                setter(element, value)

    def append_reading(self, name, x, y):
        ...

    def updateReadings(self):
        ...

    def clearReadings(self):
        self.analysisTreeWidget.clear()
        if self.measurement:
            self.measurement.analysis.clear()

    def append_analysis(self, key: str, values: dict):
        if self.measurement:
            self.measurement.analysis[key] = values
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, key)
            self.analysisTreeWidget.addTopLevelItem(item)
            for k, v in values.items():
                child = QtWidgets.QTreeWidgetItem()
                child.setText(0, k)
                child.setText(1, format(v))
                item.addChild(child)
            item.setExpanded(True)
            self.analysisTreeWidget.resizeColumnToContents(0)
            self.analysisTreeWidget.resizeColumnToContents(1)

    def load_analysis(self):
        self.analysisTreeWidget.clear()
        if self.measurement:
            for key, values in self.measurement.analysis.items():
                self.append_analysis(key, values)

    def setLocked(self, state: bool) -> None:
        super().setLocked(state)
        for index in range(self.controlTabWidget.count()):
            widget = self.controlTabWidget.widget(index)
            widget.setEnabled(not state)
        if state:
            index = self.controlTabWidget.indexOf(self.generalWidget)
            self.controlTabWidget.setCurrentIndex(index)
            self.controlTabWidget.setEnabled(True)
            self.statusPanelLayout.setEnabled(True)

    def saveToImage(self, filename: str) -> None:
        """Save screenshots of data tabs to stitched image."""
        currentIndex: int = self.dataTabWidget.currentIndex()
        pixmaps: List = []
        for index in range(self.dataTabWidget.count()):
            widget = self.dataTabWidget.widget(index)
            self.dataTabWidget.setCurrentIndex(index)
            if widget.property("type") == "plot":
                widget.reflection().fit()  # type: ignore
                pixmaps.append(self.dataTabWidget.grab())
            elif isinstance(widget, PlotWidget):
                widget.resizeAxes()
                pixmaps.append(self.dataTabWidget.grab())
            elif widget is self.analysisTreeWidget:
                if settings.isPngAnalysis():
                    pixmaps.append(self.dataTabWidget.grab())
        self.dataTabWidget.setCurrentIndex(currentIndex)
        if pixmaps:
            stitch_pixmaps(pixmaps).save(filename)
