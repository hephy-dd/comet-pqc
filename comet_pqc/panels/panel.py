from typing import Optional

import comet
from comet import ui

from PyQt5 import QtCore, QtWidgets

from ..utils import stitch_pixmaps

__all__ = ["PanelStub", "BasicPanel", "Panel"]


class PanelStub(QtWidgets.QWidget):

    type: str = ""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

    @property
    def context(self):
        return self.__context

    def store(self):
        ...

    def restore(self):
        ...

    def clear_readings(self):
        ...

    def setLocked(self, locked: bool) -> None:
        ...

    def mount(self, context):
        self.unmount()
        self.__context = context

    def unmount(self):
        self.__context = None


class BasicPanel(PanelStub, comet.SettingsMixin):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.titleLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.titleLabel.setStyleSheet("font-size: 16px; font-weight: bold; height: 32px;")
        self.titleLabel.setTextFormat(QtCore.Qt.RichText)

        self.descriptionLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.descriptionLabel)
        layout.addStretch(1)

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

    type = "measurement"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = ""
        self._bindings = {}
        self.state_handlers = []
        self.data_panel = ui.Column()
        self.general_tab = ui.Tab(
                title="General",
                layout=ui.Row()
            )
        self.control_tabs = ui.Tabs(self.general_tab)
        self.status_panel = ui.Column()
        self.control_panel = ui.Row(
            self.control_tabs,
            ui.Column(
                self.status_panel,
                ui.Spacer(horizontal=False)
            ),
            stretch=(3, 1)
        )
        self.layout().insertWidget(2, self.data_panel.qt)
        self.layout().insertWidget(3, self.control_panel.qt)
        self.measurement = None
        self.data_tabs = ui.Tabs()
        self.data_panel.append(self.data_tabs)

        # Add analysis tab
        self.analysis_tree = ui.Tree(header=["Parameter", "Value"])
        self.data_tabs.insert(0, ui.Tab(title="Analysis", layout=self.analysis_tree))

        # Plots
        self.series_transform = {}
        self.series_transform_default = lambda x, y: (x, y)

    def bind(self, key, element, default=None, unit=None):
        """Bind measurement parameter to UI element for syncronization on mount
        and store.

        >>> # for measurement parameter "value" of unit "V"
        >>> self.value = QtWidgets.QDoubleSpinBox()
        >>> self.bind("value", self.value, default=10.0, unit="V")
        """
        self._bindings[key] = element, default, unit

    def mount(self, measurement):
        """Mount measurement to panel."""
        super().mount(measurement)
        self.setTitle(f"{self.title} &rarr; {measurement.name}")
        self.setDescription(measurement.description or "")
        self.measurement = measurement
        # Load parameters to UI
        parameters = self.measurement.parameters
        for key, (element, default, unit) in self._bindings.items():
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
        self.data_tabs.qt.setCurrentIndex(0)
        # Update plot series style
        points_in_plots = self.settings.get("points_in_plots") or False
        for tab in self.data_tabs:
            if isinstance(tab.layout, ui.Plot):
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
            for key, (element, default, unit) in self._bindings.items():
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
            for key, (element, default, unit) in self._bindings.items():
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

    def clear_readings(self):
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

    def setLocked(self, locked: bool) -> None:
        for tab in self.control_tabs:
            tab.qt.setEnabled(not locked)
        if locked:
            if self.general_tab in self.control_tabs:
                self.control_tabs.current = self.general_tab
            self.control_tabs.enabled = True
            self.status_panel.enabled = True

    def save_to_image(self, filename):
        """Save screenshots of data tabs to stitched image."""
        current = self.data_tabs.current
        pixmaps = []
        png_analysis = self.settings.get("png_analysis") or False
        for tab in self.data_tabs:
            self.data_tabs.current = tab
            if isinstance(tab.layout, ui.Plot):
                tab.layout.fit()
                pixmaps.append(self.data_tabs.qt.grab())
            elif tab.layout is self.analysis_tree:
                if png_analysis:
                    pixmaps.append(self.data_tabs.qt.grab())
        self.data_tabs.current = current
        stitch_pixmaps(pixmaps).save(filename)
