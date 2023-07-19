from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..settings import settings
from ..utils import from_table_unit, to_table_unit

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

        self.sizeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.sizeSpinBox.setRange(0, 1000)
        self.sizeSpinBox.setDecimals(3)
        self.sizeSpinBox.setSuffix(" mm")

        self.zLimitLabel = QtWidgets.QLabel(self)
        self.zLimitLabel.setText("Z-Limit")
        self.zLimitLabel.setToolTip("Z-Limit in millimeters")
        self.zLimitLabel.setVisible(False)

        self._z_limit_number: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self._z_limit_number.setRange(0, 1000)
        self._z_limit_number.setDecimals(3)
        self._z_limit_number.setSuffix(" mm")
        self._z_limit_number.setVisible(False)

        self.colorLabel = QtWidgets.QLabel(self)
        self.colorLabel.setText("Color")
        self.colorLabel.setToolTip("Color code for step")

        self.colorLineEdit = QtWidgets.QLineEdit(self)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.sizeLabel)
        layout.addWidget(self.sizeSpinBox)
        layout.addWidget(self.zLimitLabel)
        layout.addWidget(self._z_limit_number)
        layout.addWidget(self.colorLabel)
        layout.addWidget(self.colorLineEdit)
        layout.addWidget(self.buttonBox)

    @property
    def step_size(self) -> float:
        return self.sizeSpinBox.value()

    @step_size.setter
    def step_size(self, value: float) -> None:
        self.sizeSpinBox.setValue(value)

    @property
    def z_limit(self) -> float:
        return self._z_limit_number.value()

    @z_limit.setter
    def z_limit(self, value: float) -> None:
        self._z_limit_number.setValue(value)

    @property
    def step_color(self) -> str:
        return self.colorLineEdit.text()

    @step_color.setter
    def step_color(self, value: str) -> None:
        self.colorLineEdit.setText(str(value or ""))


class ItemDelegate(QtWidgets.QItemDelegate):
    """Item delegate for custom floating point number display."""

    decimals = 3

    def drawDisplay(self, painter, option, rect, text):
        text = format(float(text), f".{self.decimals}f")
        super().drawDisplay(painter, option, rect, text)


class TableStepItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, step_size, z_limit, step_color=None) -> None:
        super().__init__()
        self.step_size = step_size
        self.z_limit = z_limit
        self.step_color = step_color or ""

    @property
    def step_size(self) -> float:
        return self.data(0, 0x2000)

    @step_size.setter
    def step_size(self, value: float) -> None:
        self.setData(0, 0x2000, value)
        self.setText(0, str(value))

    @property
    def z_limit(self) -> float:
        return self.data(1, 0x2000)

    @z_limit.setter
    def z_limit(self, value: float) -> None:
        self.setData(1, 0x2000, value)
        self.setText(1, str(value))

    @property
    def step_color(self) -> str:
        return self.data(2, 0x2000)

    @step_color.setter
    def step_color(self, value: str) -> None:
        self.setData(2, 0x2000, value)
        self.setText(2, str(value))


class TableWidget(QtWidgets.QWidget):
    """Table limits tab for preferences dialog."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.stepsTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.stepsTreeWidget.setHeaderLabels(["Size", "Z-Limit", "Color"])
        self.stepsTreeWidget.setRootIsDecorated(False)
        # Hide Z-Limit column
        self.stepsTreeWidget.setColumnHidden(1, True)
        self.stepsTreeWidget.itemSelectionChanged.connect(self.on_position_selected)
        self.stepsTreeWidget.itemDoubleClicked.connect(self.on_steps_tree_double_clicked)
        self.stepsTreeWidget.setItemDelegateForColumn(0, ItemDelegate(self.stepsTreeWidget))
        self.stepsTreeWidget.setItemDelegateForColumn(1, ItemDelegate(self.stepsTreeWidget))

        self.addStepButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.addStepButton.setText("&Add")
        self.addStepButton.setToolTip("Add table step")
        self.addStepButton.clicked.connect(self.addStep)

        self.editStepButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.editStepButton.setText("&Edit")
        self.editStepButton.setToolTip("Edit selected table step")
        self.editStepButton.setEnabled(False)
        self.editStepButton.clicked.connect(self.editCurrentStep)

        self.removeStepButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.removeStepButton.setText("&Remove")
        self.removeStepButton.setToolTip("Remove selected table step")
        self.removeStepButton.setEnabled(False)
        self.removeStepButton.clicked.connect(self.removeCurrentStep)

        self.zLimitMovementSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitMovementSpinBox.setRange(0, 128)
        self.zLimitMovementSpinBox.setDecimals(3)
        self.zLimitMovementSpinBox.setSuffix(" mm")

        self.xLimitProbecardSpinBox: QtWidgets.QDoubleSpinBox = createPositionSpinBox(self)
        self.yLimitProbecardSpinBox: QtWidgets.QDoubleSpinBox = createPositionSpinBox(self)
        self.zLimitProbecardSpinBox: QtWidgets.QDoubleSpinBox = createPositionSpinBox(self)

        self.zLimitNoticeCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.zLimitNoticeCheckBox.setText("Temporary Z-Limit")
        self.zLimitNoticeCheckBox.setToolTip("Select to show temporary Z-Limit notice.")

        self.xLimitJoystickSpinBox: QtWidgets.QDoubleSpinBox = createPositionSpinBox(self)
        self.yLimitJoystickSpinBox: QtWidgets.QDoubleSpinBox = createPositionSpinBox(self)
        self.zLimitJoystickSpinBox: QtWidgets.QDoubleSpinBox = createPositionSpinBox(self)

        self.probecardContactDelaySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.probecardContactDelaySpinBox.setRange(0, 3600)
        self.probecardContactDelaySpinBox.setDecimals(2)
        self.probecardContactDelaySpinBox.setSingleStep(0.1)
        self.probecardContactDelaySpinBox.setSuffix(" s")

        self.recontactOverdriveSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.recontactOverdriveSpinBox.setRange(0, 0.025)
        self.recontactOverdriveSpinBox.setDecimals(3)
        self.recontactOverdriveSpinBox.setSingleStep(0.001)
        self.recontactOverdriveSpinBox.setSuffix(" mm")

        # Control Steps

        self.stepsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepsGroupBox.setTitle("Control Steps (mm)")

        stepsGroupBoxLayout = QtWidgets.QGridLayout(self.stepsGroupBox)
        stepsGroupBoxLayout.addWidget(self.stepsTreeWidget, 0, 0, 4, 1)
        stepsGroupBoxLayout.addWidget(self.addStepButton, 0, 1)
        stepsGroupBoxLayout.addWidget(self.editStepButton, 1, 1)
        stepsGroupBoxLayout.addWidget(self.removeStepButton, 2, 1)
        stepsGroupBoxLayout.setColumnStretch(0, 1)
        stepsGroupBoxLayout.setRowStretch(3, 1)

        # Movement Z-Limit

        self.zLimitGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.zLimitGroupBox.setTitle("Movement Z-Limit")

        zLimitGroupBoxLayout = QtWidgets.QHBoxLayout(self.zLimitGroupBox)
        zLimitGroupBoxLayout.addWidget(self.zLimitMovementSpinBox)
        zLimitGroupBoxLayout.addStretch()

        # Probe Card Limts

        self.probecardLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
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

        self.joystickLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
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

        self.contactDelayGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.contactDelayGroupBox.setTitle("Probecard Contact Delay")

        contactDelayGroupBoxLayout = QtWidgets.QHBoxLayout(self.contactDelayGroupBox)
        contactDelayGroupBoxLayout.addWidget(self.probecardContactDelaySpinBox)
        contactDelayGroupBoxLayout.addStretch()

        # Re-Contact Z-Overdrive

        self.overdriveGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.overdriveGroupBox.setTitle("Re-Contact Z-Overdrive (1x)")

        overdriveGroupBoxLayout = QtWidgets.QHBoxLayout(self.overdriveGroupBox)
        overdriveGroupBoxLayout.addWidget(self.recontactOverdriveSpinBox)
        overdriveGroupBoxLayout.addStretch()

        bottomLayout = QtWidgets.QHBoxLayout()
        bottomLayout.addWidget(self.contactDelayGroupBox, 0)
        bottomLayout.addWidget(self.overdriveGroupBox, 1)

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
            step_size = dialog.step_size
            z_limit = dialog.z_limit
            step_color = dialog.step_color
            self.stepsTreeWidget.addTopLevelItem(TableStepItem(step_size, z_limit, step_color))
            self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def editCurrentStep(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if item:
            dialog = TableStepDialog()
            dialog.step_size = item.step_size
            dialog.z_limit = item.z_limit
            dialog.step_color = item.step_color
            if dialog.exec() == dialog.Accepted:
                item.step_size = dialog.step_size
                item.z_limit = dialog.z_limit
                item.step_color = dialog.step_color
                self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def removeCurrentStep(self) -> None:
        item = self.stepsTreeWidget.currentItem()
        if item:
            if QtWidgets.QMessageBox.question(self, "Remove Step", f"Do you want to remove step size {item.step_size!r}?"):
                index = self.stepsTreeWidget.indexOfTopLevelItem(item)
                self.stepsTreeWidget.takeTopLevelItem(index)
                if not self.stepsTreeWidget.topLevelItemCount():
                    self.editStepButton.setEnabled(False)
                    self.removeStepButton.setEnabled(False)
                self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def readSettings(self) -> None:
        table_step_sizes = settings.settings.get("table_step_sizes") or []
        self.stepsTreeWidget.clear()
        for item in table_step_sizes:
            self.stepsTreeWidget.addTopLevelItem(TableStepItem(
                step_size=from_table_unit(item.get("step_size")),
                z_limit=from_table_unit(item.get("z_limit")),
                step_color=format(item.get("step_color"))
            ))
        self.stepsTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)
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
        table_contact_delay = float(settings.settings.get("table_contact_delay", 0))
        self.probecardContactDelaySpinBox.setValue(table_contact_delay)
        self.recontactOverdriveSpinBox.setValue(settings.retry_contact_overdrive)

    def writeSettings(self) -> None:
        table_step_sizes = []
        for index in range(self.stepsTreeWidget.topLevelItemCount()):
            item = self.stepsTreeWidget.topLevelItem(index)
            table_step_sizes.append({
                "step_size": to_table_unit(item.step_size),
                "z_limit": to_table_unit(item.z_limit),
                "step_color": format(item.step_color),
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
        settings.settings["table_contact_delay"] = self.probecardContactDelaySpinBox.value()
        settings.retry_contact_overdrive = self.recontactOverdriveSpinBox.value()
