from typing import Optional

from PyQt5 import QtCore, QtWidgets

from pqc.settings import settings
from pqc.utils import from_table_unit, to_table_unit

__all__ = ["TableWidget"]


def createPositionSpinBox(parent: QtWidgets.QWidget):
    spinBox = QtWidgets.QDoubleSpinBox(parent)
    spinBox.setRange(0, 1000)
    spinBox.setDecimals(3)
    spinBox.setSuffix(" mm")
    return spinBox


class TableStepDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.sizeLabel = QtWidgets.QLabel(self)
        self.sizeLabel.setText("Size")
        self.sizeLabel.setToolTip("Step size in millimeters")

        self.sizeSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.sizeSpinBox.setDecimals(3)
        self.sizeSpinBox.setRange(0, 1000)
        self.sizeSpinBox.setSuffix(" mm")

        self.zLimitLabel = QtWidgets.QLabel(self)
        self.zLimitLabel.setText("Z-Limit")
        self.zLimitLabel.setToolTip("Z-Limit in millimeters")
        self.zLimitLabel.setVisible(False)

        self.zLimitSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitSpinBox.setDecimals(3)
        self.zLimitSpinBox.setRange(0, 1000)
        self.zLimitSpinBox.setSuffix(" mm")
        self.zLimitSpinBox.setVisible(False)

        self.colorLabel = QtWidgets.QLabel(self)
        self.colorLabel.setText("Color")
        self.colorLabel.setToolTip("Color code for step")

        self.colorLineEdit = QtWidgets.QLineEdit(self)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.sizeLabel)
        layout.addWidget(self.sizeSpinBox)
        layout.addWidget(self.zLimitLabel)
        layout.addWidget(self.zLimitSpinBox)
        layout.addWidget(self.colorLabel)
        layout.addWidget(self.colorLineEdit)
        layout.addWidget(self.buttonBox)

    def stepSize(self) -> float:
        return self.sizeSpinBox.value()

    def setStepSize(self, value: float) -> None:
        self.sizeSpinBox.setValue(value)

    def zLimit(self) -> float:
        return self.zLimitSpinBox.value()

    def setZLimit(self, value: float) -> None:
        self.zLimitSpinBox.setValue(value)

    def stepColor(self) -> str:
        return self.colorLineEdit.text()

    def setStepColor(self, value: str) -> None:
        self.colorLineEdit.setText(str(value or ""))


class TableStepItem(QtWidgets.QTreeWidgetItem):

    def __init__(self) -> None:
        super().__init__()
        self.setStepSize(0.0)
        self.setZLimit(0.0)
        self.setStepColor("")

    def stepSize(self) -> float:
        return self.data(0, 0x2000)

    def setStepSize(self, value: float) -> None:
        self.setData(0, 0x2000, value)
        self.setText(0, f"{value:.3f} mm")

    def zLimit(self) -> float:
        return self.data(1, 0x2000)

    def setZLimit(self, value: float) -> None:
        self.setData(1, 0x2000, value)
        self.setText(1, str(value))

    def stepColor(self) -> str:
        return self.data(2, 0x2000)

    def setStepColor(self, value: str) -> None:
        self.setData(2, 0x2000, value)
        self.setText(2, str(value))

    def __lt__(self, other):
        if isinstance(other, type(self)):
            widget = self.treeWidget()
            if widget is not None:
                column = widget.sortColumn()
                if column == 0:
                    return self.stepSize() < other.stepSize()
        return super().__lt__(other)


class TableWidget(QtWidgets.QWidget):
    """Table limits tab for preferences dialog."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.stepsTreeWidget = QtWidgets.QTreeWidget(self)
        self.stepsTreeWidget.setHeaderLabels(["Size", "Z-Limit", "Color"])
        self.stepsTreeWidget.setRootIsDecorated(False)
        # Hide Z-Limit column
        self.stepsTreeWidget.setColumnHidden(1, True)
        self.stepsTreeWidget.itemSelectionChanged.connect(self.on_position_selected)
        self.stepsTreeWidget.itemDoubleClicked.connect(self.on_steps_tree_double_clicked)

        self.addStepButton = QtWidgets.QPushButton(self)
        self.addStepButton.setText("&Add")
        self.addStepButton.setToolTip("Add table step")
        self.addStepButton.clicked.connect(self.addStep)

        self.editStepButton = QtWidgets.QPushButton(self)
        self.editStepButton.setText("&Edit")
        self.editStepButton.setToolTip("Edit selected table step")
        self.editStepButton.setEnabled(False)
        self.editStepButton.clicked.connect(self.editCurrentStep)

        self.removeStepButton = QtWidgets.QPushButton(self)
        self.removeStepButton.setText("&Remove")
        self.removeStepButton.setToolTip("Remove selected table step")
        self.removeStepButton.setEnabled(False)
        self.removeStepButton.clicked.connect(self.removeCurrentStep)

        self.zLimitMovementSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitMovementSpinBox.setDecimals(3)
        self.zLimitMovementSpinBox.setRange(0, 128)
        self.zLimitMovementSpinBox.setSuffix(" mm")

        self.xLimitProbecardSpinBox = createPositionSpinBox(self)
        self.yLimitProbecardSpinBox = createPositionSpinBox(self)
        self.zLimitProbecardSpinBox = createPositionSpinBox(self)

        self.zLimitNoticeCheckBox = QtWidgets.QCheckBox(self)
        self.zLimitNoticeCheckBox.setText("Temporary Z-Limit")
        self.zLimitNoticeCheckBox.setToolTip("Select to show temporary Z-Limit notice.")

        self.xLimitJoystickSpinBox = createPositionSpinBox(self)
        self.yLimitJoystickSpinBox = createPositionSpinBox(self)
        self.zLimitJoystickSpinBox = createPositionSpinBox(self)

        self.probecardContactDelaySpinBox = QtWidgets.QDoubleSpinBox(self)
        self.probecardContactDelaySpinBox.setDecimals(2)
        self.probecardContactDelaySpinBox.setRange(0, 3600)
        self.probecardContactDelaySpinBox.setSingleStep(0.1)
        self.probecardContactDelaySpinBox.setSuffix(" s")

        self.recontactOverdriveSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.recontactOverdriveSpinBox.setDecimals(3)
        self.recontactOverdriveSpinBox.setRange(0, 0.025)
        self.recontactOverdriveSpinBox.setSingleStep(0.001)
        self.recontactOverdriveSpinBox.setSuffix(" mm")

        self.recontactRadiusSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.recontactRadiusSpinBox.setDecimals(3)
        self.recontactRadiusSpinBox.setRange(0, 0.100)
        self.recontactRadiusSpinBox.setSingleStep(0.001)
        self.recontactRadiusSpinBox.setSuffix(" mm")
        self.recontactRadiusSpinBox.setToolTip("Radius for random re-contact offset")

        self.recontactDistanceSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.recontactDistanceSpinBox.setDecimals(3)
        self.recontactDistanceSpinBox.setRange(0, 0.060)
        self.recontactDistanceSpinBox.setSingleStep(0.001)
        self.recontactDistanceSpinBox.setSuffix(" mm")
        self.recontactDistanceSpinBox.setToolTip("Minimum distance to all previous re-contact positions")

        # Control Steps

        self.stepsGroupBox = QtWidgets.QGroupBox(self)
        self.stepsGroupBox.setTitle("Control Steps (mm)")

        stepsGroupBoxLayout = QtWidgets.QGridLayout(self.stepsGroupBox)
        stepsGroupBoxLayout.addWidget(self.stepsTreeWidget, 0, 0, 4, 1)
        stepsGroupBoxLayout.addWidget(self.addStepButton, 0, 1)
        stepsGroupBoxLayout.addWidget(self.editStepButton, 1, 1)
        stepsGroupBoxLayout.addWidget(self.removeStepButton, 2, 1)
        stepsGroupBoxLayout.setColumnStretch(0, 1)
        stepsGroupBoxLayout.setRowStretch(3, 1)

        # Movement Z-Limit

        self.zLimitGroupBox = QtWidgets.QGroupBox(self)
        self.zLimitGroupBox.setTitle("Movement Z-Limit")

        zLimitGroupBoxLayout = QtWidgets.QHBoxLayout(self.zLimitGroupBox)
        zLimitGroupBoxLayout.addWidget(self.zLimitMovementSpinBox)
        zLimitGroupBoxLayout.addStretch()

        # Probe Card Limts

        self.probecardLimitsGroupBox = QtWidgets.QGroupBox(self)
        self.probecardLimitsGroupBox.setTitle("Probe Card Limts")

        probecardLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.probecardLimitsGroupBox)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        probecardLimitsGroupBoxLayout.addWidget(self.xLimitProbecardSpinBox, 1, 0)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        probecardLimitsGroupBoxLayout.addWidget(self.yLimitProbecardSpinBox, 1, 1)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        probecardLimitsGroupBoxLayout.addWidget(self.zLimitProbecardSpinBox, 1, 2)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        probecardLimitsGroupBoxLayout.addWidget(self.zLimitNoticeCheckBox, 1, 5)
        probecardLimitsGroupBoxLayout.setColumnStretch(4, 1)

        # Joystick Limits

        self.joystickLimitsGroupBox = QtWidgets.QGroupBox(self)
        self.joystickLimitsGroupBox.setTitle("Joystick Limits")

        joystickLimitsGroupBoxLayout = QtWidgets.QGridLayout(self.joystickLimitsGroupBox)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        joystickLimitsGroupBoxLayout.addWidget(self.xLimitJoystickSpinBox, 1, 0)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        joystickLimitsGroupBoxLayout.addWidget(self.yLimitJoystickSpinBox, 1, 1)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        joystickLimitsGroupBoxLayout.addWidget(self.zLimitJoystickSpinBox, 1, 2)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        joystickLimitsGroupBoxLayout.setColumnStretch(3, 1)

        # Probecard Contact Delay

        self.probecardGroupBox = QtWidgets.QGroupBox(self)
        self.probecardGroupBox.setTitle("Probecard")

        probecardGroupBoxLayout = QtWidgets.QGridLayout(self.probecardGroupBox)
        probecardGroupBoxLayout.addWidget(QtWidgets.QLabel("Contact Delay"), 0, 0)
        probecardGroupBoxLayout.addWidget(self.probecardContactDelaySpinBox, 1, 0)

        # Re-Contact Z-Overdrive

        self.recontactGroupBox = QtWidgets.QGroupBox(self)
        self.recontactGroupBox.setTitle("Re-Contact")

        recontactGroupBoxLayout = QtWidgets.QGridLayout(self.recontactGroupBox)
        recontactGroupBoxLayout.addWidget(QtWidgets.QLabel("Z-Overdrive"), 0, 0)
        recontactGroupBoxLayout.addWidget(self.recontactOverdriveSpinBox, 1, 0)
        recontactGroupBoxLayout.addWidget(QtWidgets.QLabel("Offset Radius"), 0, 1)
        recontactGroupBoxLayout.addWidget(self.recontactRadiusSpinBox, 1, 1)
        recontactGroupBoxLayout.addWidget(QtWidgets.QLabel("Min. Distance"), 0, 2)
        recontactGroupBoxLayout.addWidget(self.recontactDistanceSpinBox, 1, 2)
        recontactGroupBoxLayout.setColumnStretch(3, 1)

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addWidget(self.probecardGroupBox, 0)
        bottomLayout.addWidget(self.recontactGroupBox, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.stepsGroupBox, 1)
        layout.addWidget(self.zLimitGroupBox)
        layout.addWidget(self.probecardLimitsGroupBox)
        layout.addWidget(self.joystickLimitsGroupBox)
        layout.addLayout(bottomLayout)

    def on_position_selected(self):
        enabled = self.stepsTreeWidget.currentItem() is not None
        self.editStepButton.setEnabled(enabled)
        self.removeStepButton.setEnabled(enabled)

    def on_steps_tree_double_clicked(self, item, index):
        self.editCurrentStep()

    def addStep(self) -> None:
        dialog = TableStepDialog()
        if dialog.exec() == dialog.Accepted:
            item = TableStepItem()
            item.setStepSize(dialog.stepSize())
            item.setZLimit(dialog.zLimit())
            item.setStepColor(dialog.stepColor())
            self.stepsTreeWidget.addTopLevelItem(item)
            self.stepsTreeWidget.sortItems(0, QtCore.Qt.AscendingOrder)

    def editCurrentStep(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if isinstance(item, TableStepItem):
            dialog = TableStepDialog()
            dialog.setStepSize(item.stepSize())
            dialog.setZLimit(item.zLimit())
            dialog.setStepColor(item.stepColor())
            if dialog.exec() == dialog.Accepted:
                item.setStepSize(dialog.stepSize())
                item.setZLimit(dialog.zLimit())
                item.setStepColor(dialog.stepColor())
                self.stepsTreeWidget.sortItems(0, QtCore.Qt.AscendingOrder)

    def removeCurrentStep(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if isinstance(item, TableStepItem):
            if QtWidgets.QMessageBox.question(self, "Remove Step", f"Do you want to remove step size {item.stepSize()!r}?"):
                index = self.stepsTreeWidget.indexOfTopLevelItem(item)
                self.stepsTreeWidget.takeTopLevelItem(index)
                if not self.stepsTreeWidget.topLevelItemCount():
                    self.editStepButton.setEnabled(False)
                    self.removeStepButton.setEnabled(False)
                self.stepsTreeWidget.sortItems(0, QtCore.Qt.AscendingOrder)

    def readSettings(self) -> None:
        table_step_sizes = settings.settings.get("table_step_sizes", [])
        self.stepsTreeWidget.clear()
        for data in table_step_sizes:
            item = TableStepItem()
            item.setStepSize(from_table_unit(data.get("step_size", 0)))
            item.setZLimit(from_table_unit(data.get("z_limit", 0)))
            item.setStepColor(format(data.get("step_color", "")))
            self.stepsTreeWidget.addTopLevelItem(item)
        self.stepsTreeWidget.sortItems(0, QtCore.Qt.AscendingOrder)
        self.zLimitMovementSpinBox.setValue(settings.table_z_limit)
        # Probecard limits
        x, y, z = settings.table_probecard_maximum_limits
        self.xLimitProbecardSpinBox.setValue(x)
        self.yLimitProbecardSpinBox.setValue(y)
        self.zLimitProbecardSpinBox.setValue(z)
        self.zLimitNoticeCheckBox.setChecked(bool(settings.table_temporary_z_limit))
        # Joystick limits
        x, y, z = settings.table_joystick_maximum_limits
        self.xLimitJoystickSpinBox.setValue(x)
        self.yLimitJoystickSpinBox.setValue(y)
        self.zLimitJoystickSpinBox.setValue(z)
        self.probecardContactDelaySpinBox.setValue(settings.table_contact_delay)
        self.recontactOverdriveSpinBox.setValue(settings.retry_contact_overdrive)
        self.recontactRadiusSpinBox.setValue(settings.retry_contact_radius)
        self.recontactDistanceSpinBox.setValue(settings.retry_contact_distance)

    def writeSettings(self) -> None:
        table_step_sizes = []
        for index in range(self.stepsTreeWidget.topLevelItemCount()):
            item = self.stepsTreeWidget.topLevelItem(index)
            if isinstance(item, TableStepItem):
                table_step_sizes.append({
                    "step_size": to_table_unit(item.stepSize()),
                    "z_limit": to_table_unit(item.zLimit()),
                    "step_color": format(item.stepColor()),
                })
        settings.settings["table_step_sizes"] = table_step_sizes
        settings.table_z_limit = self.zLimitMovementSpinBox.value()
        # Probecard limits
        settings.table_probecard_maximum_limits = [
            self.xLimitProbecardSpinBox.value(),
            self.yLimitProbecardSpinBox.value(),
            self.zLimitProbecardSpinBox.value(),
        ]
        settings.table_temporary_z_limit = self.zLimitNoticeCheckBox.isChecked()
        # Joystick limits
        settings.table_joystick_maximum_limits = [
            self.xLimitJoystickSpinBox.value(),
            self.yLimitJoystickSpinBox.value(),
            self.zLimitJoystickSpinBox.value(),
        ]
        settings.table_contact_delay = self.probecardContactDelaySpinBox.value()
        settings.retry_contact_overdrive = self.recontactOverdriveSpinBox.value()
        settings.retry_contact_radius = self.recontactRadiusSpinBox.value()
        settings.retry_contact_distance = self.recontactDistanceSpinBox.value()
