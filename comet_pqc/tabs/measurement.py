from comet import ui

from ..panels import SamplePanel
from ..panels import ContactPanel
from ..panels import IVRampPanel
from ..panels import IVRampElmPanel
from ..panels import IVRampBiasPanel
from ..panels import IVRampBiasElmPanel
from ..panels import IVRamp4WirePanel
from ..panels import CVRampPanel
from ..panels import CVRampHVPanel
from ..panels import CVRampAltPanel
from ..panels import FrequencyScanPanel

__all__ = ['MeasurementTab']

class MeasurementTab(ui.Tab):

    def __init__(self, restore=None):
        super().__init__(title="Measurement")
        self.restore = restore
        self.panels = PanelStack()
        self.measure_restore_button = ui.Button(
            text="Restore Defaults",
            tool_tip="Restore default measurement parameters.",
            clicked=self.on_measure_restore
        )
        self.measure_controls = ui.Row(
            self.measure_restore_button,
            ui.Spacer(),
            visible=False
        )
        self.layout = ui.Column(
            self.panels,
            self.measure_controls,
            stretch=(1, 0)
        )

    def lock(self):
        self.panels.lock()
        self.measure_controls.enabled = False

    def unlock(self):
        self.panels.unlock()
        self.measure_controls.enabled = True

    def on_measure_restore(self):
        self.emit('restore')

class PanelStack(ui.Row):
    """Stack of measurement panels."""

    def __init__(self):
        super().__init__()
        self.append(SamplePanel(visible=False))
        self.append(ContactPanel(visible=False))
        self.append(IVRampPanel(visible=False))
        self.append(IVRampElmPanel(visible=False))
        self.append(IVRampBiasPanel(visible=False))
        self.append(IVRampBiasElmPanel(visible=False))
        self.append(CVRampPanel(visible=False))
        self.append(CVRampHVPanel(visible=False))
        self.append(CVRampAltPanel(visible=False))
        self.append(IVRamp4WirePanel(visible=False))
        self.append(FrequencyScanPanel(visible=False))

    def store(self):
        for child in self:
            child.store()

    def unmount(self):
        for child in self:
            child.unmount()

    def clear_readings(self):
        for child in self:
            child.clear_readings()

    def hide(self):
        for child in self:
            child.visible = False

    def lock(self):
        for child in self:
            child.lock()

    def unlock(self):
        for child in self:
            child.unlock()

    def get(self, type):
        """Get panel by type."""
        for child in self:
            if child.type == type:
                return child
        return None
