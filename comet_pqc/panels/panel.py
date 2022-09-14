from collections import namedtuple
from typing import Callable, Dict, List, Tuple

import comet
from comet import ui, SettingsMixin
from PyQt5 import QtCore, QtWidgets

from ..utils import stitch_pixmaps

__all__ = ["Panel", "MeasurementPanel"]


class Panel(SettingsMixin, QtWidgets.QWidget):

    type: str = ""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

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


class MeasurementPanel(Panel):
    """Base class for measurement panels."""

    type = "measurement"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._bindings: Dict[str, Tuple] = {}
        self.state_handlers: List[Callable] = []
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

    def bind(self, key: str, element, default=None, unit: str = None):
        """Bind measurement parameter to UI element for syncronization on mount
        and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> self.value = ui.Number()
        >>> self.bind("value", self.value, default=10.0, unit="V")
        """
        self._bindings[key] = element, default, unit

    def mount(self, measurement):
        """Mount measurement to panel."""
        super().mount(measurement)
        self.titleLabel.setText(f"{self.title()} &rarr; {measurement.name}")
        self.descriptionLabel.setText(measurement.description)
        self.descriptionLabel.setVisible(len(measurement.description) > 0)
        self.measurement = measurement
        # Load parameters to UI
        parameters = self.measurement.parameters
        for key, item in self._bindings.items():
            element, default, unit = item
            value = parameters.get(key, default)
            if unit is not None:
                if isinstance(value, comet.ureg.Quantity):
                    value = value.to(unit).m
            if isinstance(element, ui.List):
                setattr(element, "values", value)
            elif isinstance(element, ui.ComboBox):
                setattr(element, "current", value)
            elif isinstance(element, ui.CheckBox):
                setattr(element, "checked", value)
            elif isinstance(element, ui.Text):
                setattr(element, "value", value)
            elif isinstance(element, ui.Label):
                setattr(element, "text", format(value))
            elif isinstance(element, ui.Metric):
                setattr(element, "value", value)
            else:
                setattr(element, "value", value)
        self.load_analysis()
        # Show first tab on mount
        self.dataTabWidget.setCurrentIndex(0)
        # Update plot series style
        points_in_plots = self.settings.get("points_in_plots") or False
        for index in range(self.dataTabWidget.count()):
            widget = self.dataTabWidget.widget(index)
            if widget.property("type") == "plot":
                for series in widget.reflection().series.values():
                    series.qt.setPointsVisible(points_in_plots)

    def unmount(self):
        """Unmount measurement from panel."""
        super().unmount()
        self.measurement = None
        self.analysisTreeWidget.clear()

    def store(self):
        """Store UI element values to measurement parameters."""
        if self.measurement:
            parameters = self.measurement.parameters
            for key, item in self._bindings.items():
                element, default, unit = item
                if isinstance(element, ui.List):
                    value = getattr(element, "values")
                elif isinstance(element, ui.ComboBox):
                    value = getattr(element, "current")
                elif isinstance(element, ui.CheckBox):
                    value = getattr(element, "checked")
                elif isinstance(element, ui.Text):
                    value = getattr(element, "value")
                elif isinstance(element, ui.Label):
                    value = getattr(element, "text")
                elif isinstance(element, ui.Metric):
                    value = getattr(element, "value")
                else:
                    value = getattr(element, "value")
                if unit is not None:
                    value = value * comet.ureg(unit)
                parameters[key] = value

    def restore(self):
        """Restore measurement defaults."""
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            for key, item in self._bindings.items():
                element, default, unit = item
                value = default_parameters.get(key, default)
                if unit is not None:
                    if isinstance(value, comet.ureg.Quantity):
                        value = value.to(unit).m
                if isinstance(element, ui.List):
                    setattr(element, "values", value)
                elif isinstance(element, ui.ComboBox):
                    setattr(element, "current", value)
                elif isinstance(element, ui.CheckBox):
                    setattr(element, "checked", value)
                elif isinstance(element, ui.Text):
                    setattr(element, "value", value)
                elif isinstance(element, ui.Metric):
                    setattr(element, "value", value)
                else:
                    setattr(element, "value", value)

    def state(self, state):
        for handler in self.state_handlers:
            handler(state)

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
        png_analysis = self.settings.get("png_analysis") or False
        for index in range(self.dataTabWidget.count()):
            widget = self.dataTabWidget.widget(index)
            self.dataTabWidget.setCurrentIndex(index)
            if widget.property("type") == "plot":
                widget.reflection().fit()  # type: ignore
                pixmaps.append(self.dataTabWidget.grab())
            elif widget is self.analysisTreeWidget:
                if png_analysis:
                    pixmaps.append(self.dataTabWidget.grab())
        self.dataTabWidget.setCurrentIndex(currentIndex)
        if pixmaps:
            stitch_pixmaps(pixmaps).save(filename)
