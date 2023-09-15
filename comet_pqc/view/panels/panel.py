from typing import Callable, Dict, Optional

from PyQt5 import QtCore, QtWidgets
from QCharted import ChartView

import comet

from comet_pqc.settings import settings
from ..components import PlotWidget
from ..components import Metric, stitch_pixmaps

__all__ = ["PanelStub", "BasicPanel", "Panel"]


class PanelStub(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

    @property
    def context(self):
        return self.__context

    def store(self):
        ...

    def restore(self):
        ...

    def clearReadings(self) -> None:
        ...

    def setLocked(self, locked: bool) -> None:
        ...

    def mount(self, context):
        self.unmount()
        self.__context = context

    def unmount(self):
        self.__context = None


class BasicPanel(PanelStub):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setName("")

        self.titleLabel = QtWidgets.QLabel(self)
        self.titleLabel.setStyleSheet("font-size: 16px; font-weight: bold; height: 32px;")
        self.titleLabel.setTextFormat(QtCore.Qt.RichText)

        self.descriptionLabel = QtWidgets.QLabel(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.descriptionLabel)
        layout.addStretch(1)

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def setTitle(self, text: str) -> None:
        self.titleLabel.setText(text)

    def setDescription(self, text: str) -> None:
        self.descriptionLabel.setText(text)
        self.descriptionLabel.setVisible(len(self.descriptionLabel.text()) > 0)

    def unmount(self):
        self.titleLabel.clear()
        self.descriptionLabel.clear()
        super().unmount()


class Panel(BasicPanel):
    """Base class for measurement panels."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._bindings: Dict = {}
        self._bindings_types: Dict = {}

        self.state_handlers: list[Callable] = []

        self.measurement = None

        self.data_panel = QtWidgets.QWidget(self)

        data_panel_layout = QtWidgets.QVBoxLayout(self.data_panel)
        data_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.generalWidget = QtWidgets.QWidget(self)
        self.generalWidget.setLayout(QtWidgets.QHBoxLayout())

        self.controlTabWidget = QtWidgets.QTabWidget(self)
        self.controlTabWidget.addTab(self.generalWidget, "General")

        self.statusWidget = QtWidgets.QWidget(self)

        status_widget_layout = QtWidgets.QVBoxLayout(self.statusWidget)
        status_widget_layout.setContentsMargins(0, 0, 0, 0)

        self.control_panel = QtWidgets.QWidget(self)

        control_panel_layout = QtWidgets.QHBoxLayout(self.control_panel)
        control_panel_layout.setContentsMargins(0, 0, 0, 0)
        control_panel_layout.addWidget(self.controlTabWidget, 3)
        l = QtWidgets.QVBoxLayout()
        l.addWidget(self.statusWidget)
        l.addStretch()
        control_panel_layout.addLayout(l, 1)

        self.layout().insertWidget(2, self.data_panel)
        self.layout().insertWidget(3, self.control_panel)

        self.dataTabWidget = QtWidgets.QTabWidget(self)

        data_panel_layout.addWidget(self.dataTabWidget)

        # Add analysis tab
        self.analysisTreeWidget = QtWidgets.QTreeWidget(self)
        self.analysisTreeWidget.setHeaderLabels(["Parameter", "Value"])
        self.dataTabWidget.insertTab(0, self.analysisTreeWidget, "Analysis")

        # Plots
        self.series_transform = {}
        self.series_transform_default = lambda x, y: (x, y)

        self.registerBindType(
            QtWidgets.QSpinBox,
            lambda widget: widget.value(),
            lambda widget, value: widget.setValue(int(value)),
        )
        self.registerBindType(
            QtWidgets.QDoubleSpinBox,
            lambda widget: widget.value(),
            lambda widget, value: widget.setValue(float(value)),
        )
        self.registerBindType(
            QtWidgets.QCheckBox,
            lambda widget: widget.isChecked(),
            lambda widget, value: widget.setChecked(bool(value)),
        )
        self.registerBindType(
            QtWidgets.QLineEdit,
            lambda widget: widget.text(),
            lambda widget, value: widget.setText(str(value)),
        )
        self.registerBindType(
            QtWidgets.QLabel,
            lambda widget: widget.text(),
            lambda widget, value: widget.setText(str(value)),
        )
        self.registerBindType(
            QtWidgets.QComboBox,
            lambda widget: widget.itemText(widget.currentIndex()),
            lambda widget, value: widget.setCurrentIndex(widget.findText(str(value))),
        )
        self.registerBindType(
            Metric,
            lambda widget: widget.value(),
            lambda widget, value: widget.setValue(float(value)),
        )

    def registerBindType(self, type, getter: Callable, setter: Callable) -> None:
        """Register setter and getter bindings for input widgets."""
        self._bindings_types.update({type: (getter, setter)})

    def bind(self, key: str, element, default=None, unit: Optional[str] = None) -> None:
        """Bind measurement parameter to input widget for syncronization on
        mount and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> self.valueSpinBox = QtWidgets.QDoubleSpinBox()
        >>> self.bind("value", self.valueSpinBox, default=10.0, unit="V")
        """
        self._bindings[key] = element, default, unit

    def mount(self, measurement):
        """Mount measurement to panel."""
        super().mount(measurement)

        self.setTitle(f"{self.name()} &rarr; {measurement.name()}")
        self.setDescription(measurement.description() or "")
        self.measurement = measurement

        # Load parameters to UI
        parameters = self.measurement.parameters
        for key, (element, default, unit) in self._bindings.items():
            value = parameters.get(key, default)
            # Convert using pint
            if unit is not None:
                if isinstance(value, comet.ureg.Quantity):
                    value = value.to(unit).m
            if type(element) in self._bindings_types:
                _, setter = self._bindings_types[type(element)]
                setter(element, value)
            else:
                raise TypeError(type(element))
        self.load_analysis()

        # Show first tab on mount
        self.dataTabWidget.setCurrentIndex(0)

        # TODO
        # Update plot series style
        points_in_plots = settings.settings.get("points_in_plots") or False
        for index in range(self.dataTabWidget.count()):
            widget = self.dataTabWidget.widget(index)
            if isinstance(widget, PlotWidget):
                for series in widget.series().values():
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
            for key, (element, default, unit) in self._bindings.items():
                if type(element) in self._bindings_types:
                    getter, _ = self._bindings_types[type(element)]
                    value = getter(element)
                else:
                    raise TypeError(type(element))
                # Convert using pint
                if unit is not None:
                    value = value * comet.ureg(unit)
                parameters[key] = value

    def restore(self):
        """Restore measurement defaults."""
        if self.measurement:
            default_parameters = self.measurement.default_parameters
            for key, (element, default, unit) in self._bindings.items():
                value = default_parameters.get(key, default)
                # Convert using pint
                if unit is not None:
                    if isinstance(value, comet.ureg.Quantity):
                        value = value.to(unit).m
                if type(element) in self._bindings_types:
                    _, setter = self._bindings_types[type(element)]
                    setter(element, value)
                else:
                    raise TypeError(type(element))

    def updateState(self, data: dict) -> None:
        for handler in self.state_handlers:
            handler(data)

    def appendReading(self, name: str, x: float, y: float) -> None:
        ...

    def updateReadings(self) -> None:
        ...

    def clearReadings(self) -> None:
        self.analysisTreeWidget.clear()
        if self.measurement:
            self.measurement.analysis.clear()

    def appendAnalysis(self, key: str, values: dict) -> None:
        if self.measurement:
            self.measurement.analysis[key] = values
            item = QtWidgets.QTreeWidgetItem([key])
            self.analysisTreeWidget.addTopLevelItem(item)
            item.setExpanded(True)
            for k, v in values.items():
                child = QtWidgets.QTreeWidgetItem([k, format(v)])
                item.addChild(child)
            self.analysisTreeWidget.resizeColumnToContents(0)
            self.analysisTreeWidget.resizeColumnToContents(1)

    def load_analysis(self):
        self.analysisTreeWidget.clear()
        if self.measurement:
            for key, values in self.measurement.analysis.items():
                self.appendAnalysis(key, values)

    def setLocked(self, locked: bool) -> None:
        for index in range(self.controlTabWidget.count()):
            widget = self.controlTabWidget.widget(index)
            widget.setEnabled(not locked)
        if locked:
            self.controlTabWidget.setCurrentWidget(self.generalWidget)
            self.controlTabWidget.setEnabled(True)
            self.statusWidget.setEnabled(True)

    def saveToImage(self, filename: str) -> None:
        """Save screenshots of data tabs to stitched image."""
        current = self.dataTabWidget.currentIndex()
        pixmaps = []
        png_analysis = settings.png_analysis
        for index in range(self.dataTabWidget.count()):
            self.dataTabWidget.setCurrentIndex(index)
            widget = self.dataTabWidget.widget(index)
            if isinstance(widget, PlotWidget):
                widget.fit()
                pixmaps.append(self.dataTabWidget.grab())
            elif widget is self.analysisTreeWidget:
                if png_analysis:
                    pixmaps.append(self.dataTabWidget.grab())
        self.dataTabWidget.setCurrentIndex(current)
        stitch_pixmaps(pixmaps).save(filename)
