from collections import namedtuple
from typing import Callable, Dict, List, Tuple

import comet
from comet import ui, SettingsMixin
from PyQt5 import QtCore, QtWidgets

from ..utils import stitch_pixmaps

__all__ = ["BasicPanel", "Panel"]


class BasicPanel(SettingsMixin, QtWidgets.QWidget):

    type: str = ""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.title = ""

        self.titleLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.titleLabel.setStyleSheet("font-size: 16px; font-weight: bold; height: 32px;")
        self.titleLabel.setTextFormat(QtCore.Qt.RichText)

        self.descriptionLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)

        self.rootLayout = QtWidgets.QVBoxLayout(self)
        self.rootLayout.addWidget(self.titleLabel, 0)
        self.rootLayout.addWidget(self.descriptionLabel, 0)

    @property
    def context(self):
        self.property("context")

    def store(self):
        ...

    def restore(self):
        ...

    def clearReadings(self):
        ...

    def lock(self):
        self.setProperty("locked", True)

    def unlock(self):
        self.setProperty("locked", False)

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


class Panel(BasicPanel):
    """Base class for measurement panels."""

    type = "measurement"

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._bindings: Dict[str, Tuple] = {}
        self.state_handlers: List[Callable] = []

        self.dataPanelLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        self.general_tab = ui.Tab(
                title="General",
                layout=ui.Row()
            )

        self.control_tabs = ui.Tabs(self.general_tab)

        self.statusPanelLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()

        self.statusWrapperLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.statusWrapperLayout.addLayout(self.statusPanelLayout)
        self.statusWrapperLayout.addStretch()

        self.controlPanelLayout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self.controlPanelLayout.addWidget(self.control_tabs.qt, 3)
        self.controlPanelLayout.addLayout(self.statusWrapperLayout, 1)

        self.rootLayout.insertLayout(2, self.dataPanelLayout)
        self.rootLayout.insertLayout(3, self.controlPanelLayout)

        self.measurement = None

        self.dataTabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)

        self.dataPanelLayout.addWidget(self.dataTabWidget)

        # Add analysis tab
        self.analysis_tree = ui.Tree(header=["Parameter", "Value"])
        self.dataTabWidget.insertTab(0, self.analysis_tree.qt, "Analysis")

        # Plots
        self.series_transform: Dict[str, object] = {}
        self.series_transform_default = lambda x, y: (x, y)

    def bind(self, key, element, default=None, unit=None):
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
        self.titleLabel.setText(f"{self.title} &rarr; {measurement.name}")
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
            tab = self.dataTabWidget.widget(index).reflection()
            if hasattr(tab, "layout") and hasattr(tab.layout, "series"):
                for series in tab.layout.series.values():
                    series.qt.setPointsVisible(points_in_plots)

    def unmount(self):
        """Unmount measurement from panel."""
        super().unmount()
        self.measurement = None
        self.analysis_tree.clear()

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

    def update_readings(self):
        ...

    def clearReadings(self):
        self.analysis_tree.clear()
        if self.measurement:
            self.measurement.analysis.clear()

    def append_analysis(self, key, values):
        if self.measurement:
            self.measurement.analysis[key] = values
            item = self.analysis_tree.append([key])
            for k, v in values.items():
                item.append([k, format(v)])
            self.analysis_tree.fit()

    def load_analysis(self):
        self.analysis_tree.clear()
        if self.measurement:
            for key, values in self.measurement.analysis.items():
                self.append_analysis(key, values)

    def lock(self):
        super().lock()
        for tab in self.control_tabs:
            tab.enabled = False
        if self.general_tab in self.control_tabs:
            self.control_tabs.current = self.general_tab
        self.control_tabs.enabled = True
        self.statusPanelLayout.enabled = True

    def unlock(self):
        super().unlock()
        for tab in self.control_tabs:
            tab.enabled = True

    def save_to_image(self, filename: str) -> None:
        """Save screenshots of data tabs to stitched image."""
        current: int = self.dataTabWidget.currentIndex()
        pixmaps = []
        png_analysis = self.settings.get("png_analysis") or False
        for index in range(self.dataTabWidget.count()):
            tab = self.dataTabWidget.widget(index)
            self.dataTabWidget.setCurrentIndex(index)
            if hasattr(tab, "layout") and hasattr(tab.layout, "series"):
                tab.layout.fit()
                pixmaps.append(self.dataTabWidget.grab())
            elif tab.layout is self.analysis_tree:
                if png_analysis:
                    pixmaps.append(self.dataTabWidget.grab())
        self.dataTabWidget.setCurrentIndex(current)
        if pixmaps:
            stitch_pixmaps(pixmaps).save(filename)
