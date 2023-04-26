from typing import Optional

from PyQt5 import QtCore, QtWidgets

from comet.ui.preferences import PreferencesTab

from ..settings import settings
from ..utils import from_table_unit, to_table_unit

__all__ = ["TableTab"]


class TableTab(PreferencesTab):
    """Table tab for preferences dialog."""

    def __init__(self):
        super().__init__(title="Table")
        self.table_widget = TableWidget()
        self.qt.layout().addWidget(self.table_widget)

    def load(self) -> None:
        self.table_widget.readSettings()

    def store(self) -> None:
        self.table_widget.writeSettings()


class TableStepDialog(QtWidgets.QDialog):

    def __init__(self, parent = Optional[QtWidgets.QWidget]) -> None:
        super().__init__(parent)

        self.stepSizeLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.stepSizeLabel.setText("Size")
        self.stepSizeLabel.setToolTip("Step size in millimeters")

        self.stepSizeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.stepSizeSpinBox.setDecimals(3)
        self.stepSizeSpinBox.setRange(0, 1000)
        self.stepSizeSpinBox.setSuffix(" mm")

        self.zLimitLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.zLimitLabel.setText("Z-Limit")
        self.zLimitLabel.setToolTip("Z-Limit in millimeters")
        self.zLimitLabel.setVisible(False)

        self.zLimitSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitSpinBox.setDecimals(3)
        self.zLimitSpinBox.setRange(0, 1000)
        self.zLimitSpinBox.setSuffix(" mm")
        self.zLimitSpinBox.setVisible(False)

        self.stepColorLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.stepColorLabel.setText("Color")
        self.stepColorLabel.setToolTip("Color code for step")

        self.stepColorLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.stepSizeLabel)
        layout.addWidget(self.stepSizeSpinBox)
        layout.addWidget(self.zLimitLabel)
        layout.addWidget(self.zLimitSpinBox)
        layout.addWidget(self.stepColorLabel)
        layout.addWidget(self.stepColorLineEdit)
        layout.addWidget(self.buttonBox)

    def stepSize(self) -> float:
        return self.stepSizeSpinBox.value()

    def setStepSize(self, value: float) -> None:
        self.stepSizeSpinBox.setValue(value)

    def zLimit(self) -> float:
        return self.zLimitSpinBox.value()

    def setZLimit(self, value: float) -> None:
        self.zLimitSpinBox.setValue(value)

    def stepColor(self) -> str:
        return self.stepColorLineEdit.text()

    def setStepColor(self, value: str) -> None:
        self.stepColorLineEdit.setText(value)


class TableStepItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, stepSize: float, zLimit: float, stepColor: str) -> None:
        super().__init__()
        self.setStepSize(stepSize)
        self.setZLimit(zLimit)
        self.setStepColor(stepColor)

    def __lt__(self, other):
        if isinstance(other, type(self)):
            return self.stepSize() > other.stepSize()
        return super().__lt__(other)

    def stepSize(self) -> float:
        return self.data(0, 0x2000)

    def setStepSize(self, value: float) -> None:
        self.setData(0, 0x2000, value)
        self.setText(0, f"{value:.3f} mm")

    def zLimit(self) -> float:
        return self.data(1, 0x2000)

    def setZLimit(self, value: float) -> None:
        self.setData(1, 0x2000, value)
        self.setText(1, f"{value:.3f} mm")

    def stepColor(self) -> float:
        return self.data(2, 0x2000)

    def setStepColor(self, color: str) -> None:
        self.setData(2, 0x2000, color)
        self.setText(2, color)


class TableWidget(QtWidgets.QWidget):
    """Table limits widget for preferences dialog."""

    temporaryZLimitChanged = QtCore.pyqtSignal(bool)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self.stepsTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.stepsTreeWidget.setHeaderLabels(["Size", "Z-Limit", "Color"])
        self.stepsTreeWidget.setRootIsDecorated(False)
        self.stepsTreeWidget.setSortingEnabled(True)
        # Hide Z-Limit column
        self.stepsTreeWidget.setColumnHidden(1, True)
        self.stepsTreeWidget.currentItemChanged.connect(self.onStepSizeChanged)
        self.stepsTreeWidget.itemDoubleClicked.connect(self.onStepSizeDoubleClicked)

        self.addStepButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.addStepButton.setText("&Add")
        self.addStepButton.setToolTip("Add table step")
        self.addStepButton.clicked.connect(self.onAddStepClicked)

        self.editStepButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.editStepButton.setText("&Edit")
        self.editStepButton.setToolTip("Edit selected table step")
        self.editStepButton.setEnabled(False)
        self.editStepButton.clicked.connect(self.onEditStepClicked)

        self.removeStepButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.removeStepButton.setText("&Remove")
        self.removeStepButton.setToolTip("Remove selected table step")
        self.removeStepButton.setEnabled(False)
        self.removeStepButton.clicked.connect(self.onRemoveStepClicked)

        self.zLimitMovementSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitMovementSpinBox.setDecimals(3)
        self.zLimitMovementSpinBox.setRange(0, 128)
        self.zLimitMovementSpinBox.setSuffix(" mm")

        def createSpinBox():
            spinBox = QtWidgets.QDoubleSpinBox(self)
            spinBox.setDecimals(3)
            spinBox.setRange(0.0, 1000.0)
            spinBox.setSuffix(" mm")
            return spinBox

        self.probecardLimitXMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()
        self.probecardLimitYMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()
        self.probecardLimitZMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.probecardLimitZMaximumCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.probecardLimitZMaximumCheckBox.setText("Temporary Z-Limit")
        self.probecardLimitZMaximumCheckBox.setToolTip("Select to show temporary Z-Limit notice.")

        self.joystickLimitXMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()
        self.joystickLimitYMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()
        self.joystickLimitZMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.probecardContactDelaySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.probecardContactDelaySpinBox.setDecimals(2)
        self.probecardContactDelaySpinBox.setRange(0.0, 3600.0)
        self.probecardContactDelaySpinBox.setSingleStep(0.1)
        self.probecardContactDelaySpinBox.setSuffix(" s")

        self.recontasctOverdriveSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.recontasctOverdriveSpinBox.setDecimals(3)
        self.recontasctOverdriveSpinBox.setRange(0.0, 0.025)
        self.recontasctOverdriveSpinBox.setSingleStep(0.001)
        self.recontasctOverdriveSpinBox.setSuffix(" mm")

        self.stepsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepsGroupBox.setTitle("Control Steps (mm)")

        stepsGroupBoxLayout = QtWidgets.QGridLayout(self.stepsGroupBox)
        stepsGroupBoxLayout.addWidget(self.stepsTreeWidget, 0, 0, 4, 1)
        stepsGroupBoxLayout.addWidget(self.addStepButton, 0, 1)
        stepsGroupBoxLayout.addWidget(self.editStepButton, 1, 1)
        stepsGroupBoxLayout.addWidget(self.removeStepButton, 2, 1)
        stepsGroupBoxLayout.setRowStretch(3, 1)
        stepsGroupBoxLayout.setColumnStretch(0, 1)

        self.movementGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.movementGroupBox.setTitle("Movement Z-Limit")

        movementGroupBoxLayout = QtWidgets.QVBoxLayout(self.movementGroupBox)
        movementGroupBoxLayout.addWidget(self.zLimitMovementSpinBox)

        self.probecardLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.probecardLimitsGroupBox.setTitle("Probe Card Limts")

        probecardLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.probecardLimitsGroupBox)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardLimitXMaximumSpinBox, 1, 0)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardLimitYMaximumSpinBox, 1, 1)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardLimitZMaximumSpinBox, 1, 2)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardLimitZMaximumCheckBox, 1, 5)
        probecardLimitsGroupBoxLayout.setColumnStretch(4, 1)

        self.joystickLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.joystickLimitsGroupBox.setTitle("Joystick Limits")

        joystickLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.joystickLimitsGroupBox)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        joystickLimitsGroupBoxLayout.addWidget(self.joystickLimitXMaximumSpinBox, 1, 0)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        joystickLimitsGroupBoxLayout.addWidget(self.joystickLimitYMaximumSpinBox, 1, 1)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        joystickLimitsGroupBoxLayout.addWidget(self.joystickLimitZMaximumSpinBox, 1, 2)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        joystickLimitsGroupBoxLayout.setColumnStretch(4, 1)

        self.probecardContactGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.probecardContactGroupBox.setTitle("Probecard Contact Delay")

        probecardContactGroupBoxLayout = QtWidgets.QVBoxLayout(self.probecardContactGroupBox)
        probecardContactGroupBoxLayout.addWidget(self.probecardContactDelaySpinBox)

        self.recontactOverdriveGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.recontactOverdriveGroupBox.setTitle("Re-Contact Z-Overdrive (1x)")

        recontactOverdriveGroupBoxLayout = QtWidgets.QVBoxLayout(self.recontactOverdriveGroupBox)
        recontactOverdriveGroupBoxLayout.addWidget(self.recontasctOverdriveSpinBox)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.stepsGroupBox, 0, 0, 1, 2)
        layout.addWidget(self.movementGroupBox, 1, 0, 1, 2)
        layout.addWidget(self.probecardLimitsGroupBox, 2, 0, 1, 2)
        layout.addWidget(self.joystickLimitsGroupBox, 3, 0, 1, 2)
        layout.addWidget(self.probecardContactGroupBox, 4, 0)
        layout.addWidget(self.recontactOverdriveGroupBox, 4, 1)
        layout.setRowStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def onStepSizeChanged(self, current, previous) -> None:
        isEnabled = current is not None
        self.editStepButton.setEnabled(isEnabled)
        self.removeStepButton.setEnabled(isEnabled)

    def onStepSizeDoubleClicked(self, item, column) -> None:
        self.onEditStepClicked()

    def onAddStepClicked(self) -> None:
        dialog = TableStepDialog(self)
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            stepSize = dialog.stepSize()
            zLimit = dialog.zLimit()
            stepColor = dialog.stepColor()
            item = TableStepItem(stepSize, zLimit, stepColor)
            self.stepsTreeWidget.addTopLevelItem(item)

    def onEditStepClicked(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if item:
            dialog = TableStepDialog(self)
            dialog.setStepSize(item.stepSize())
            dialog.setZLimit(item.zLimit())
            dialog.setStepColor(item.stepColor())
            dialog.exec()
            if dialog.result() == dialog.Accepted:
                item.setStepSize(dialog.stepSize())
                item.setZLimit(dialog.zLimit())
                item.setStepColor(dialog.stepColor())

    def onRemoveStepClicked(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if item:
            result = QtWidgets.QMessageBox.question(self, "Remove item", f"Do you want to remove step size {item.text(0)!r}?")
            if result == QtWidgets.QMessageBox.Yes:
                index = self.stepsTreeWidget.indexOfTopLevelItem(item)
                self.stepsTreeWidget.takeTopLevelItem(index)
                if not self.stepsTreeWidget.topLevelItemCount():
                    self.editStepButton.setEnabled(False)
                    self.removeStepButton.setEnabled(False)

    def readSettings(self) -> None:
        table_step_sizes = settings.settings.get("table_step_sizes") or []

        self.stepsTreeWidget.clear()
        for item in table_step_sizes:
            self.stepsTreeWidget.addTopLevelItem(TableStepItem(
                from_table_unit(item.get("step_size")),
                from_table_unit(item.get("z_limit")),
                format(item.get("step_color")),
            ))

        self.zLimitMovementSpinBox.setValue(settings.table_z_limit)

        # Probecard limits
        x, y, z = settings.table_probecard_maximum_limits
        self.probecardLimitXMaximumSpinBox.setValue(x)
        self.probecardLimitYMaximumSpinBox.setValue(y)
        self.probecardLimitZMaximumSpinBox.setValue(z)

        temporary_z_limit = settings.table_temporary_z_limit
        self.probecardLimitZMaximumCheckBox.setChecked(temporary_z_limit)

        # Joystick limits
        x, y, z = settings.table_joystick_maximum_limits
        self.joystickLimitXMaximumSpinBox.setValue(x)
        self.joystickLimitYMaximumSpinBox.setValue(y)
        self.joystickLimitZMaximumSpinBox.setValue(z)

        table_contact_delay = settings.settings.get("table_contact_delay") or 0
        self.probecardContactDelaySpinBox.setValue(table_contact_delay)

        self.recontasctOverdriveSpinBox.setValue(settings.retry_contact_overdrive)

    def writeSettings(self) -> None:
        table_step_sizes = []
        for index in range(self.stepsTreeWidget.topLevelItemCount()):
            item = self.stepsTreeWidget.topLevelItem(index)
            if item:
                table_step_sizes.append({
                    "step_size": to_table_unit(item.stepSize()),
                    "z_limit": to_table_unit(item.zLimit()),
                    "step_color": format(item.stepColor()),
                })

        settings.settings["table_step_sizes"] = table_step_sizes
        settings.table_z_limit = self.zLimitMovementSpinBox.value()

        # Probecard limits
        settings.table_probecard_maximum_limits = [
            self.probecardLimitXMaximumSpinBox.value(),
            self.probecardLimitYMaximumSpinBox.value(),
            self.probecardLimitZMaximumSpinBox.value(),
        ]

        temporary_z_limit = self.probecardLimitZMaximumCheckBox.isChecked()
        settings.table_temporary_z_limit = temporary_z_limit
        self.temporaryZLimitChanged.emit(temporary_z_limit)

        # Joystick limits
        settings.table_joystick_maximum_limits = [
            self.joystickLimitXMaximumSpinBox.value(),
            self.joystickLimitYMaximumSpinBox.value(),
            self.joystickLimitZMaximumSpinBox.value(),
        ]

        table_contact_delay = self.probecardContactDelaySpinBox.value()
        settings.settings["table_contact_delay"] = table_contact_delay

        settings.retry_contact_overdrive = self.recontasctOverdriveSpinBox.value()
