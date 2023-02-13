import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import comet
from PyQt5 import QtCore, QtGui, QtWidgets

from comet_pqc.settings import settings

from ..components import stitchPixmaps
from ..plotwidget import PlotWidget

__all__ = ["Panel", "MeasurementPanel"]

TransformType = Callable[[Any, Any], Tuple[Any, Any]]


class Panel(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._locked: bool = False
        self._context = None

        self.titleLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.titleLabel.setTextFormat(QtCore.Qt.RichText)
        self.titleLabel.setStyleSheet("font-size: 16px; font-weight: bold; height: 32px;")

        self.descriptionLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)

        self.panelLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        self.panelLayout.addWidget(self.titleLabel)
        self.panelLayout.addWidget(self.descriptionLabel)
        self.panelLayout.addStretch()

    def setTitle(self, title: str) -> None:
        self.titleLabel.setText(title)

    def setDescription(self, description: str) -> None:
        self.descriptionLabel.setText(description)
        self.descriptionLabel.setVisible(len(description) != 0)

    @property
    def context(self):
        return self._context

    def store(self) -> None:
        ...

    def restore(self) -> None:
        ...

    def clearReadings(self) -> None:
        ...

    def isLocked(self) -> bool:
        return self._locked

    def setLocked(self, locked: bool) -> None:
        self._locked = locked

    def mount(self, context) -> None:
        self.unmount()
        self._context = context

    def unmount(self) -> None:
        self.setTitle("")
        self.setDescription("")
        self._context = None


class MeasurementPanel(Panel):
    """Base class for measurement panels."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._bindings: Dict[str, Tuple] = {}
        self.state_handlers: List[Callable[[Dict], None]] = []

        self.controlTabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)

        self.statusWidget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        QtWidgets.QVBoxLayout(self.statusWidget)

        self.dataTabWidget: QtWidgets.QTabWidget = QtWidgets.QTabWidget(self)

        self.controlLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
        self.controlLayout.addWidget(self.controlTabWidget, 0, 0, 2, 1)
        self.controlLayout.addWidget(self.statusWidget, 0, 1)
        self.controlLayout.setRowStretch(1, 1)
        self.controlLayout.setColumnStretch(0, 7)
        self.controlLayout.setColumnStretch(1, 3)

        self.panelLayout.insertWidget(2, self.dataTabWidget)
        self.panelLayout.insertLayout(3, self.controlLayout)

        self.measurement = None

        # Add analysis tab
        self.analysisTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.analysisTreeWidget.setHeaderLabels(["Parameter", "Value"])

        self.dataTabWidget.insertTab(0, self.analysisTreeWidget, "Analysis")

        # Plots
        self.series_transform: Dict[str, TransformType] = {}
        self.series_transform_default = lambda x, y: (x, y)

    def bind(self, key: str, element, default: Optional[Any] = None, unit: Optional[str] = None) -> None:
        """Bind measurement parameter to UI element for syncronization on mount
        and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> valueSpinBox = QtWidgets.QDoubleSplinBox()
        >>> self.bind("value", valueSpinBox, default=10.0, unit="V")
        """
        if key in self._bindings:
            raise KeyError(f"key already exists: {key!r}")
        self._bindings[key] = element, default, unit

    def mount(self, measurement):
        """Mount measurement to panel."""
        super().mount(measurement)
        self.setTitle(f"{self.title} &rarr; {measurement.name}")
        self.setDescription(measurement.description())
        self.measurement = measurement
        # Load parameters to UI
        parameters = self.measurement.parameters
        for key, item in self._bindings.items():
            element, default, unit = item
            value = parameters.get(key, default)
            if unit is not None:
                if isinstance(value, comet.ureg.Quantity):
                    value = value.to(unit).m

            if type(element) is QtWidgets.QCheckBox:
                element.setChecked(value)
            elif type(element) is QtWidgets.QLineEdit:
                element.setText(value)
            elif type(element) is QtWidgets.QLabel:
                element.setText(value)
            elif type(element) is QtWidgets.QSpinBox:
                element.setValue(value)
            elif type(element) is QtWidgets.QDoubleSpinBox:
                element.setValue(value)
            elif type(element) is QtWidgets.QComboBox:
                index = element.findData(value)
                element.setCurrentIndex(index)
            else:
                element.setValue(value)
        self.loadAnalysis()
        # Show first tab on mount
        self.dataTabWidget.setCurrentIndex(0)
        # Update plot series style
        enabled = settings.value("points_in_plots", False, bool)
        self.setPointsVisible(enabled)

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

                if type(element) is QtWidgets.QCheckBox:
                    value = element.isChecked()
                elif type(element) is QtWidgets.QLineEdit:
                    value = element.text()
                elif type(element) is QtWidgets.QLabel:
                    value = element.text()
                elif type(element) is QtWidgets.QSpinBox:
                    value = element.value()
                elif type(element) is QtWidgets.QDoubleSpinBox:
                    value = element.value()
                elif type(element) is QtWidgets.QComboBox:
                    value = element.currentData()
                else:
                    value = element.value()
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

                if type(element) is QtWidgets.QCheckBox:
                    element.setChecked(value)
                elif type(element) is QtWidgets.QLineEdit:
                    element.setText(value)
                elif type(element) is QtWidgets.QLabel:
                    element.setText(value)
                elif type(element) is QtWidgets.QSpinBox:
                    element.setValue(value)
                elif type(element) is QtWidgets.QDoubleSpinBox:
                    element.setValue(value)
                elif type(element) is QtWidgets.QComboBox:
                    index = element.findData(value)
                    element.setCurrentIndex(index)
                else:
                    element.setValue(value)

    def state(self, state: Dict) -> None:  # TODO
        for handler in self.state_handlers:
            handler(state)

    def addStateHandler(self, handler: Callable[[Dict], None]) -> None:
        self.state_handlers.append(handler)

    def append_reading(self, name, x, y):
        ...

    def update_readings(self):
        ...

    def clearReadings(self):
        self.analysisTreeWidget.clear()
        if self.measurement:
            self.measurement.analysis.clear()

    def append_analysis(self, key, values):
        if self.measurement:
            self.measurement.analysis[key] = values
            item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem()
            item.setText(0, format(key))
            self.analysisTreeWidget.addTopLevelItem(item)
            item.setExpanded(True)
            for k, v in values.items():
                child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem()
                child.setText(0, format(k))
                child.setText(0, format(v))
                item.addChild(child)
            self.analysisTreeWidget.resizeColumnToContents(0)
            self.analysisTreeWidget.resizeColumnToContents(1)

    def loadAnalysis(self) -> None:
        self.analysisTreeWidget.clear()
        if self.measurement:
            for key, values in self.measurement.analysis.items():
                self.append_analysis(key, values)

    def setPointsVisible(self, enabled: bool) -> None:
        for index in range(self.dataTabWidget.count()):
            widget = self.dataTabWidget.widget(index)
            if isinstance(widget, PlotWidget):
                for series in widget.series().values():
                    series.qt.setPointsVisible(enabled)

    def setLocked(self, locked: bool) -> None:
        super().setLocked(locked)
        for index in range(self.controlTabWidget.count()):
            self.controlTabWidget.widget(index).setEnabled(not locked)
        if locked:
            self.controlTabWidget.setCurrentIndex(0)
            self.controlTabWidget.setEnabled(True)
            self.statusWidget.setEnabled(True)

    def saveToImage(self, filename: str) -> None:
        """Save screenshots of data tabs to stitched image."""
        currentIndex = self.dataTabWidget.currentIndex()
        pixmaps: List[QtGui.QPixmap] = []
        png_analysis = settings.value("png_analysis", False, bool)
        for index in range(self.dataTabWidget.count()):
            self.dataTabWidget.setCurrentIndex(index)
            widget = self.dataTabWidget.widget(index)
            if isinstance(widget, PlotWidget):
                widget.fit()
                pixmaps.append(self.dataTabWidget.grab())
            elif widget is self.analysisTreeWidget:
                if png_analysis:
                    pixmaps.append(self.dataTabWidget.grab())
        self.dataTabWidget.setCurrentIndex(currentIndex)
        try:
            stitchPixmaps(pixmaps).save(filename)
        except Exception as exc:
            logging.exception(exc)
            logging.error(f"Failed to save image to: {filename!r}")
