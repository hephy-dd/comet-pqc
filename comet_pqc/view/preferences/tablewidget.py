from typing import Dict, List, Optional

from PyQt5 import QtCore, QtWidgets

from .preferencesdialog import PreferencesWidget

from comet_pqc.settings import settings
from comet_pqc.utils import from_table_unit, to_table_unit

from ..components import showQuestion

from .preferencesdialog import PreferencesWidget


__all__ = ["TableWidget"]


class TableStepDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Step")

        self.sizeLabel: QtWidgets.QLabel = QtWidgets.QLabel("Size", self)
        self.sizeLabel.setToolTip("Step size in millimeters")

        self.stepSizeSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.stepSizeSpinBox.setRange(0, 1_000)
        self.stepSizeSpinBox.setDecimals(3)
        self.stepSizeSpinBox.setSuffix(" mm")

        self.zLimitLabel: QtWidgets.QLabel = QtWidgets.QLabel("Z-Limit", self)
        self.zLimitLabel.setToolTip("Z-Limit in millimeters")
        self.zLimitLabel.setVisible(False)

        self.zLimitSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitSpinBox.setRange(0, 1_000)
        self.zLimitSpinBox.setDecimals(3)
        self.zLimitSpinBox.setSuffix(" mm")
        self.zLimitSpinBox.setVisible(False)

        self.colorLabel: QtWidgets.QLabel = QtWidgets.QLabel("Color", self)
        self.colorLabel.setToolTip("Color code for step")

        self.colorLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.sizeLabel)
        layout.addWidget(self.stepSizeSpinBox)
        layout.addWidget(self.zLimitLabel)
        layout.addWidget(self.zLimitSpinBox)
        layout.addWidget(self.colorLabel)
        layout.addWidget(self.colorLineEdit)
        layout.addWidget(self.buttonBox)

    def stepSize(self) -> float:
        return self.stepSizeSpinBox.value()

    def setStepSize(self, size: float) -> None:
        self.stepSizeSpinBox.setValue(size)

    def zLimit(self) -> float:
        return self.zLimitSpinBox.value()

    def setZLimit(self, limit: float) -> None:
        self.zLimitSpinBox.setValue(limit)

    def stepColor(self) -> str:
        return self.colorLineEdit.text()

    def setStepColor(self, color: str) -> None:
        self.colorLineEdit.setText(color)


class TableStepItem(QtWidgets.QTreeWidgetItem):

    def __init__(self) -> None:
        super().__init__()
        self.setStepSize(0)
        self.setZLimit(0)
        self.setStepColor("")

    def __lt__(self, other):
        if isinstance(other, type(self)):
            return self.stepSize() < other.stepSize()
        return super().__lt__(other)

    def stepSize(self) -> float:
        return self.data(0, QtCore.Qt.UserRole)

    def setStepSize(self, size: float) -> None:
        self.setData(0, QtCore.Qt.UserRole, size)
        self.setText(0, f"{size:.3f} mm")

    def zLimit(self) -> float:
        return self.data(1, QtCore.Qt.UserRole)

    def setZLimit(self, limit: float) -> None:
        self.setData(1, QtCore.Qt.UserRole, limit)
        self.setText(1, f"{limit:.3f} mm")

    def stepColor(self) -> str:
        return self.text(2)

    def setStepColor(self, color: str) -> None:
        self.setText(2, color)


class TableWidget(PreferencesWidget):
    """Table limits tab for preferences dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stepSizesTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.stepSizesTreeWidget.setHeaderLabels(["Size", "Z-Limit", "Color"])
        self.stepSizesTreeWidget.setRootIsDecorated(False)

        # Hide Z-Limit column
        self.stepSizesTreeWidget.setColumnHidden(1, True)
        self.stepSizesTreeWidget.currentItemChanged.connect(self.onCurrentStepChanged)
        self.stepSizesTreeWidget.itemDoubleClicked.connect(self.onStepDoubleClicked)

        self.addStepSizeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.addStepSizeButton.setText("&Add")
        self.addStepSizeButton.setToolTip("Add table step")
        self.addStepSizeButton.clicked.connect(self.addStepSize)

        self.editStepSizeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.editStepSizeButton.setText("&Edit")
        self.editStepSizeButton.setToolTip("Edit selected table step")
        self.editStepSizeButton.setEnabled(False)
        self.editStepSizeButton.clicked.connect(self.editStepSize)

        self.removeStepSizeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.removeStepSizeButton.setText("&Remove")
        self.removeStepSizeButton.setToolTip("Remove selected table step")
        self.removeStepSizeButton.setEnabled(False)
        self.removeStepSizeButton.clicked.connect(self.removeStepSize)

        self.zLimitSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.zLimitSpinBox.setRange(0, 128)
        self.zLimitSpinBox.setDecimals(3)
        self.zLimitSpinBox.setSuffix(" mm")

        def createSpinBox() -> QtWidgets.QDoubleSpinBox:
            spinBox = QtWidgets.QDoubleSpinBox(self)
            spinBox.setRange(0, 1_000)
            spinBox.setDecimals(3)
            spinBox.setSuffix(" mm")
            return spinBox

        self.probecardXMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.probecardYMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.probecardZMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.temporaryZLimitCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.temporaryZLimitCheckBox.setText("Temporary Z-Limit")
        self.temporaryZLimitCheckBox.setToolTip("Select to show temporary Z-Limit notice.")

        self.joystickXMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.joystickYMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.joystickZMaximumSpinBox: QtWidgets.QDoubleSpinBox = createSpinBox()

        self.contactDelaySpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.contactDelaySpinBox.setRange(0, 3_600)
        self.contactDelaySpinBox.setDecimals(2)
        self.contactDelaySpinBox.setSingleStep(0.1)
        self.contactDelaySpinBox.setSuffix(" s")

        self.overdriveSpinBox: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.overdriveSpinBox.setRange(0, 0.025)
        self.overdriveSpinBox.setDecimals(3)
        self.overdriveSpinBox.setSingleStep(0.001)
        self.overdriveSpinBox.setSuffix(" mm")

        self.stepSizesGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.stepSizesGroupBox.setTitle("Control Steps (mm)")

        stepSizesGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.stepSizesGroupBox)
        stepSizesGroupBoxLayout.addWidget(self.stepSizesTreeWidget, 0, 0, 4, 1)
        stepSizesGroupBoxLayout.addWidget(self.addStepSizeButton, 0, 1)
        stepSizesGroupBoxLayout.addWidget(self.editStepSizeButton, 1, 1)
        stepSizesGroupBoxLayout.addWidget(self.removeStepSizeButton, 2, 1)
        stepSizesGroupBoxLayout.setColumnStretch(0, 1)
        stepSizesGroupBoxLayout.setRowStretch(3, 1)

        self.zLimitGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.zLimitGroupBox.setTitle("Movement Z-Limit")

        zLimitGroupBoxLayout = QtWidgets.QVBoxLayout(self.zLimitGroupBox)
        zLimitGroupBoxLayout.addWidget(self.zLimitSpinBox)

        self.probecardLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.probecardLimitsGroupBox.setTitle("Probe Card Limts")

        probecardLimitsGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.probecardLimitsGroupBox)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardXMaximumSpinBox, 1, 0)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardYMaximumSpinBox, 1, 1)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        probecardLimitsGroupBoxLayout.addWidget(self.probecardZMaximumSpinBox, 1, 2)
        probecardLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        probecardLimitsGroupBoxLayout.addWidget(self.temporaryZLimitCheckBox, 1, 5)
        probecardLimitsGroupBoxLayout.setColumnStretch(4, 1)

        self.joystickLimitsGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)

        joystickLimitsGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.joystickLimitsGroupBox)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("X"), 0, 0)
        joystickLimitsGroupBoxLayout.addWidget(self.joystickXMaximumSpinBox, 1, 0)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Y"), 0, 1)
        joystickLimitsGroupBoxLayout.addWidget(self.joystickYMaximumSpinBox, 1, 1)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Z"), 0, 2)
        joystickLimitsGroupBoxLayout.addWidget(self.joystickZMaximumSpinBox, 1, 2)
        joystickLimitsGroupBoxLayout.addWidget(QtWidgets.QLabel("Maximum"), 1, 3)
        joystickLimitsGroupBoxLayout.setColumnStretch(4, 1)

        self.contactDelayGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.contactDelayGroupBox.setTitle("Probecard Contact Delay")

        contactDelayGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.contactDelayGroupBox)
        contactDelayGroupBoxLayout.addWidget(self.contactDelaySpinBox)

        self.overdriveGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.overdriveGroupBox.setTitle("Re-Contact Z-Overdrive (1x)")

        overdriveGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.overdriveGroupBox)
        overdriveGroupBoxLayout.addWidget(self.overdriveSpinBox)

        hboxLayout = QtWidgets.QHBoxLayout()
        hboxLayout.addWidget(self.contactDelayGroupBox)
        hboxLayout.addWidget(self.overdriveGroupBox)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.stepSizesGroupBox)
        layout.addWidget(self.zLimitGroupBox)
        layout.addWidget(self.probecardLimitsGroupBox)
        layout.addWidget(self.joystickLimitsGroupBox)
        layout.addLayout(hboxLayout)
        layout.addStretch()

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def onCurrentStepChanged(self, current, previous):
        enabled = current is not None
        self.editStepSizeButton.setEnabled(enabled)
        self.removeStepSizeButton.setEnabled(enabled)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def onStepDoubleClicked(self, item, column):
        self.editStepSize()

    @QtCore.pyqtSlot()
    def addStepSize(self):
        dialog = TableStepDialog()
        dialog.exec()
        if dialog.result() == dialog.Accepted:
            item = TableStepItem()
            item.setStepSize(dialog.stepSize())
            item.setZLimit(dialog.zLimit())
            item.setStepColor(dialog.stepColor())
            self.stepSizesTreeWidget.addTopLevelItem(item)
            self.stepSizesTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    @QtCore.pyqtSlot()
    def editStepSize(self):
        item = self.stepSizesTreeWidget.currentItem()
        if isinstance(item, TableStepItem):
            dialog = TableStepDialog()
            dialog.setStepSize(item.stepSize())
            dialog.setZLimit(item.zLimit())
            dialog.setStepColor(item.stepColor())
            dialog.exec()
            if dialog.result() == dialog.Accepted:
                item.setStepSize(dialog.stepSize())
                item.setZLimit(dialog.zLimit())
                item.setStepColor(dialog.stepColor())
                self.stepSizesTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    @QtCore.pyqtSlot()
    def removeStepSize(self):
        item = self.stepSizesTreeWidget.currentItem()
        if isinstance(item, TableStepItem):
            if showQuestion(f"Do you want to remove step size {item.stepSize()!r}?"):
                index = self.stepSizesTreeWidget.indexOfTopLevelItem(item)
                self.stepSizesTreeWidget.takeTopLevelItem(index)
                enabled = self.stepSizesTreeWidget.topLevelItemCount() > 0
                self.editStepSizeButton.setEnabled(enabled)
                self.removeStepSizeButton.setEnabled(enabled)
                self.stepSizesTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def readSettings(self):
        table_step_sizes = settings.value("table_step_sizes", [], list)
        self.stepSizesTreeWidget.clear()
        for step_size in table_step_sizes:
            item = TableStepItem()
            item.setStepSize(from_table_unit(step_size.get("step_size")))
            item.setZLimit(from_table_unit(step_size.get("z_limit")))
            item.setStepColor(format(step_size.get("step_color")))
            self.stepSizesTreeWidget.addTopLevelItem(item)
        self.stepSizesTreeWidget.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.zLimitSpinBox.setValue(settings.table_z_limit())
        # Probecard limits
        x, y, z = settings.table_probecard_maximum_limits()
        self.probecardXMaximumSpinBox.setValue(x)
        self.probecardYMaximumSpinBox.setValue(y)
        self.probecardZMaximumSpinBox.setValue(z)
        temporary_z_limit = settings.table_temporary_z_limit()
        self.temporaryZLimitCheckBox.setChecked(temporary_z_limit)
        # Joystick limits
        x, y, z = settings.table_joystick_maximum_limits
        self.joystickXMaximumSpinBox.setValue(x)
        self.joystickYMaximumSpinBox.setValue(y)
        self.joystickZMaximumSpinBox.setValue(z)
        table_contact_delay = settings.value("table_contact_delay", 0, float)
        self.contactDelaySpinBox.setValue(table_contact_delay)
        self.overdriveSpinBox.setValue(settings.retry_contact_overdrive())

    def writeSettings(self):
        table_step_sizes: List[Dict] = []
        for index in range(self.stepSizesTreeWidget.topLevelItemCount()):
            item = self.stepSizesTreeWidget.topLevelItem(index)
            if isinstance(item, TableStepItem):
                table_step_sizes.append({
                    "step_size": to_table_unit(item.stepSize()),
                    "z_limit": to_table_unit(item.zLimit()),
                    "step_color": item.stepColor(),
                })
        settings.setValue("table_step_sizes", table_step_sizes)
        settings.set_table_z_limit(self.zLimitSpinBox.value())
        # Probecard limits
        settings.set_table_probecard_maximum_limits([
            self.probecardXMaximumSpinBox.value(),
            self.probecardYMaximumSpinBox.value(),
            self.probecardZMaximumSpinBox.value(),
        ])
        temporary_z_limit = self.temporaryZLimitCheckBox.isChecked()
        settings.set_table_temporary_z_limit(temporary_z_limit)
        # Joystick limits
        settings.table_joystick_maximum_limits = [
            self.joystickXMaximumSpinBox.value(),
            self.joystickYMaximumSpinBox.value(),
            self.joystickZMaximumSpinBox.value(),
        ]
        table_contact_delay = self.contactDelaySpinBox.value()
        settings.setValue("table_contact_delay", table_contact_delay)
        settings.set_retry_contact_overdrive(self.overdriveSpinBox.value())
