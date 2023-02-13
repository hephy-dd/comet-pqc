import logging
import math
import os
import traceback
from typing import Callable, Dict, Iterable, List, Optional, Union

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.position import Position
from ..core.utils import make_path, user_home
from ..settings import settings
from ..utils import format_table_unit, getcal, getrm

__all__ = [
    "stitchPixmaps",
    "createIcon",
    "showQuestion",
    "showWarning",
    "showException",
    "ToggleButton",
    "PositionLabel",
    "CalibrationLabel",
    "CalibrationWidget",
    "DirectoryWidget",
    "PositionsComboBox",
    "ExceptionDialog",
]


def stitchPixmaps(pixmaps: Iterable[QtGui.QPixmap], vertical: bool = True) -> QtGui.QPixmap:
    """Stitch together multiple QPixmaps to a single QPixmap."""
    # Calculate size of stitched image
    if vertical:
        width = max([pixmap.width() for pixmap in pixmaps])
        height = sum([pixmap.height() for pixmap in pixmaps])
    else:
        width = sum([pixmap.width() for pixmap in pixmaps])
        height = max([pixmap.height() for pixmap in pixmaps])
    canvas: QtGui.QPixmap = QtGui.QPixmap(width, height)
    canvas.fill(QtCore.Qt.white)
    painter = QtGui.QPainter(canvas)
    offset = 0
    for pixmap in pixmaps:
        if vertical:
            painter.drawPixmap(0, offset, pixmap)
            offset += pixmap.height()
        else:
            painter.drawPixmap(offset, 0, pixmap)
            offset += pixmap.height()
    painter.end()
    return canvas


def createIcon(size: int, color: str) -> QtGui.QIcon:
    """Return circular colored icon."""
    pixmap: QtGui.QPixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtGui.QColor("transparent"))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setPen(QtGui.QColor(color))
    painter.setBrush(QtGui.QColor(color))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QtGui.QIcon(pixmap)


def showQuestion(text: str, title: Optional[str] = None, parent: Optional[QtWidgets.QWidget] = None) -> bool:
    title = "" if title is None else title
    return QtWidgets.QMessageBox.question(parent, title, text) == QtWidgets.QMessageBox.Yes


def showWarning(text: str, title: Optional[str] = None, parent: Optional[QtWidgets.QWidget] = None) -> bool:
    title = "" if title is None else title
    return QtWidgets.QMessageBox.warning(parent, title, text) == QtWidgets.QMessageBox.Yes


def showException(exc: Exception, parent: Optional[QtWidgets.QWidget] = None) -> None:
    dialog = ExceptionDialog(parent)
    dialog.setException(exc)
    dialog.exec()


def handle_exception(func: Callable) -> Callable:
    def catch_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            tb = traceback.format_exc()
            logging.exception(exc)
            showException(exc)
    return catch_exception_wrapper


class ToggleButton(QtWidgets.QPushButton):
    """Colored checkable button."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.stateIcons: Dict[bool, QtGui.QIcon] = {
            False: createIcon(12, "grey"),
            True: createIcon(12, "green"),
        }
        self.setCheckable(True)
        self.toggleIcon(self.isChecked())
        self.toggled.connect(self.toggleIcon)

    @QtCore.pyqtSlot(bool)
    def toggleIcon(self, state: bool) -> None:
        self.setIcon(self.stateIcons.get(state) or QtGui.QIcon())


class FocusComboBox(QtWidgets.QComboBox):

    focusIn = QtCore.pyqtSignal()
    focusOut = QtCore.pyqtSignal()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        self.focusIn.emit()
        super().focusInEvent(event)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self.focusOut.emit()
        super().focusOutEvent(event)


class PositionLabel(QtWidgets.QLabel):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setValue(None)
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def value(self):
        return self.property("value")

    def setValue(self, value: Optional[float]) -> None:
        self.setProperty("value", value)
        if value is None:
            self.setText(format(float("nan")))
        else:
            self.setText(format_table_unit(value))  # TODO too explicit


class PositionWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Position")

        self.xLabel: QtWidgets.QLabel = QtWidgets.QLabel("X", self)
        self.xLabel.setToolTip("X axis position")

        self.yLabel: QtWidgets.QLabel = QtWidgets.QLabel("Y", self)
        self.yLabel.setToolTip("Y axis position")

        self.zLabel: QtWidgets.QLabel = QtWidgets.QLabel("Z", self)
        self.zLabel.setToolTip("Z axis position")

        self.xPositionLabel: PositionLabel = PositionLabel(self)
        self.yPositionLabel: PositionLabel = PositionLabel(self)
        self.zPositionLabel: PositionLabel = PositionLabel(self)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.xLabel, 0, 0)
        layout.addWidget(self.yLabel, 1, 0)
        layout.addWidget(self.zLabel, 2, 0)
        layout.addWidget(self.xPositionLabel, 0, 1)
        layout.addWidget(self.yPositionLabel, 1, 1)
        layout.addWidget(self.zPositionLabel, 2, 1)

    def setPosition(self, position: Position) -> None:
        x, y, z = position
        self.xPositionLabel.setValue(x)
        self.yPositionLabel.setValue(y)
        self.zPositionLabel.setValue(z)


class CalibrationLabel(QtWidgets.QLabel):

    def __init__(self, prefix: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setPrefix(prefix)
        self.setValue(None)

    def setPrefix(self, prefix: str) -> None:
        self._prefix = prefix

    def value(self) -> float:
        return self._value

    def setValue(self, value: Optional[float]) -> None:
        self._value = value if value is not None else float("nan")
        self.setText(f"{self._prefix} {self._value}")
        if math.isnan(self._value) or not self._value:
            self.setStyleSheet("QLabel:enabled{color:red}")
        else:
            self.setStyleSheet("QLabel:enabled{color:green}")


class CalibrationWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Calibration")

        self.xLabel: QtWidgets.QLabel = QtWidgets.QLabel("X", self)
        self.xLabel.setToolTip("X axis calibration state")

        self.yLabel: QtWidgets.QLabel = QtWidgets.QLabel("Y", self)
        self.yLabel.setToolTip("Y axis calibration state")

        self.zLabel: QtWidgets.QLabel = QtWidgets.QLabel("Z", self)
        self.zLabel.setToolTip("Z axis calibration state")

        self.xCalLabel: CalibrationLabel = CalibrationLabel("cal", self)
        self.yCalLabel: CalibrationLabel = CalibrationLabel("cal", self)
        self.zCalLabel: CalibrationLabel = CalibrationLabel("cal", self)

        self.xRmLabel: CalibrationLabel = CalibrationLabel("rm", self)
        self.yRmLabel: CalibrationLabel = CalibrationLabel("rm", self)
        self.zRmLabel: CalibrationLabel = CalibrationLabel("rm", self)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.xLabel, 0, 0)
        layout.addWidget(self.yLabel, 1, 0)
        layout.addWidget(self.zLabel, 2, 0)
        layout.addWidget(self.xCalLabel, 0, 1)
        layout.addWidget(self.yCalLabel, 1, 1)
        layout.addWidget(self.zCalLabel, 2, 1)
        layout.addWidget(self.xRmLabel, 0, 2)
        layout.addWidget(self.yRmLabel, 1, 2)
        layout.addWidget(self.zRmLabel, 2, 2)

    def reset(self) -> None:
        self.setCalibration(Position())

    def setCalibration(self, position: Position) -> None:
        self.xCalLabel.setValue(getcal(position.x))
        self.yCalLabel.setValue(getcal(position.y))
        self.zCalLabel.setValue(getcal(position.z))
        self.xRmLabel.setValue(getrm(position.x))
        self.yRmLabel.setValue(getrm(position.y))
        self.zRmLabel.setValue(getrm(position.z))


class DirectoryWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Working Directory")

        self.locationComboBox: QtWidgets.QComboBox = FocusComboBox(self)
        self.locationComboBox.setDuplicatesEnabled(False)
        self.locationComboBox.setEditable(True)
        self.locationComboBox.focusOut.connect(self.updateLocations)
        self.locationComboBox.currentIndexChanged.connect(self.updateInputs)

        self.selectButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.selectButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "search.svg")))
        self.selectButton.setToolTip("Select a directory")
        self.selectButton.clicked.connect(self.selectDirectory)

        self.removeButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.removeButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeButton.setToolTip("Remove directory from list")
        self.removeButton.clicked.connect(self.removeCurrentDirectory)

        layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.locationComboBox)
        layout.addWidget(self.selectButton)
        layout.addWidget(self.removeButton)

    def currentLocation(self) -> str:
        return self.locationComboBox.currentText().strip()

    def locations(self) -> List[str]:
        locations: List[str] = []
        self.updateLocations()
        for index in range(self.locationComboBox.count()):
            location = self.locationComboBox.itemText(index).strip()
            locations.append(self.locationComboBox.itemText(index).strip())
        return locations

    def clear_locations(self):
        with QtCore.QSignalBlocker(self.locationComboBox):
            self.locationComboBox.clear()
            self.updateLocations()

    def addLocation(self, path: str) -> None:
        self.locationComboBox.addItem(path)

    @QtCore.pyqtSlot()
    def updateInputs(self) -> None:
        self.removeButton.setEnabled(self.locationComboBox.count() > 1)

    @QtCore.pyqtSlot()
    def selectDirectory(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select directory", self.currentLocation())
        if path:
            for i in range(self.locationComboBox.count()):
                location = self.locationComboBox.itemText(i).strip()
                if location == path:
                    self.locationComboBox.setCurrentIndex(i)
                    return
            self.updateLocations()
            self.locationComboBox.insertItem(0, path)
            self.locationComboBox.setCurrentIndex(0)

    @QtCore.pyqtSlot()
    def removeCurrentDirectory(self) -> None:
        self.updateLocations()
        if self.locationComboBox.count() > 1:
            index = self.locationComboBox.currentIndex()
            if index >= 0:
                if showQuestion(
                    title="Remove directory",
                    text=f"Do you want to remove directory {self.locationComboBox.currentText()!r} from the list?"
                ):
                    self.locationComboBox.removeItem(index)

    @QtCore.pyqtSlot()
    def updateLocations(self) -> None:
        self.removeButton.setEnabled(self.locationComboBox.count() > 1)
        current_text = self.locationComboBox.currentText().strip()
        for i in range(self.locationComboBox.count()):
            if self.locationComboBox.itemText(i).strip() == current_text:
                return
        if current_text:
            self.locationComboBox.insertItem(0, current_text)
            self.locationComboBox.setCurrentIndex(0)


class WorkingDirectoryWidget(DirectoryWidget):

    def readSettings(self) -> None:
        self.clear_locations()
        locations = settings.outputPaths()
        if not locations:
            locations = [os.path.join(user_home(), "PQC")]
        for location in locations:
            self.addLocation(location)
        self.locationComboBox.setCurrentIndex(settings.currentOutputPath())
        self.updateLocations()

    def writeSettings(self) -> None:
        self.updateLocations()
        settings.setOutputPaths(self.locations())
        settings.setCurrentOutputPath(self.locationComboBox.currentIndex())


class OperatorWidget(QtWidgets.QGroupBox):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Operator")

        self.operatorComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox(self)
        self.operatorComboBox.setDuplicatesEnabled(False)

        self.addButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.addButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "add.svg")))
        self.addButton.setToolTip("Add new operator.")
        self.addButton.clicked.connect(self.addOperator)

        self.removeButton: QtWidgets.QToolButton = QtWidgets.QToolButton(self)
        self.removeButton.setIcon(QtGui.QIcon(make_path("assets", "icons", "delete.svg")))
        self.removeButton.setToolTip("Remove current operator from list.")
        self.removeButton.clicked.connect(self.removeOperator)

        layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.operatorComboBox)
        layout.addWidget(self.addButton)
        layout.addWidget(self.removeButton)

    def operator(self) -> str:
        return self.operatorComboBox.currentText().strip()

    def operators(self) -> List[str]:
        names = []
        for index in range(self.operatorComboBox.count()):
            name = self.operatorComboBox.itemText(index).strip()
            names.append(name)
        return names

    @QtCore.pyqtSlot()
    def addOperator(self) -> None:
        operator, success = QtWidgets.QInputDialog.getText(self, "Add operator", "Enter name of operator")
        if success:
            operator = operator.strip()
            if operator not in self.operators():
                self.operatorComboBox.addItem(operator)
            self.operatorComboBox.setCurrentIndex(self.operatorComboBox.findText(operator))

    @QtCore.pyqtSlot()
    def removeOperator(self) -> None:
        index = self.operatorComboBox.currentIndex()
        if index >= 0:
            if showQuestion(
                title="Remove operator",
                text=f"Do you want to remove operator {self.operatorComboBox.currentText()!r} from the list?"
            ):
                self.operatorComboBox.removeItem(index)

    def readSettings(self) -> None:
        self.operatorComboBox.clear()
        self.operatorComboBox.addItems(settings.operators())
        self.operatorComboBox.setCurrentIndex(settings.currentOperator())

    def writeSettings(self) -> None:
        index = self.operatorComboBox.currentIndex()
        settings.setCurrentOperator(index)
        settings.setOperators(self.operators())


class PositionsComboBox(QtWidgets.QComboBox):

    def readSettings(self) -> None:  # TODO
        self.clear()
        for position in settings.table_positions():
            self.addItem(f"{position} ({position.x:.3f}, {position.y:.3f}, {position.z:.3f})")
        index: int = settings.value("current_table_position", 0, int)
        self.setCurrentIndex(index)

    def writeSettings(self) -> None:  # TODO
        index: int = self.currentIndex()
        settings.setValue("current_table_position", index)


class ExceptionDialog(QtWidgets.QMessageBox):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exception")
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.setDefaultButton(QtWidgets.QMessageBox.Ok)

    def setException(self, exc: Exception) -> None:
        details: str = "".join(traceback.format_tb(exc.__traceback__))
        self.setText(format(exc))
        self.setDetailedText(details)
        # Fix message box width after setting text!
        spacer = QtWidgets.QSpacerItem(480, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        layout = self.layout()
        if isinstance(layout, QtWidgets.QGridLayout):
            layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())


class CheckableItemMixin:

    def isCheckable(self) -> bool:
        return self.flags() & QtCore.Qt.ItemIsUserCheckable != 0  # type: ignore

    def setCheckable(self, enabled: bool) -> None:
        flags = self.flags()  # type: ignore
        if enabled:
            flags |= QtCore.Qt.ItemIsUserCheckable
        else:
            flags &= ~QtCore.Qt.ItemIsUserCheckable
        self.setFlags(flags)  # type: ignore


class SelectableItemMixin:

    def isSelectable(self) -> bool:
        return self.flags() & QtCore.Qt.ItemIsSelectable != 0  # type: ignore

    def setSelectable(self, enabled: bool) -> None:
        flags = self.flags()  # type: ignore
        if enabled:
            flags |= QtCore.Qt.ItemIsSelectable
        else:
            flags &= ~QtCore.Qt.ItemIsSelectable
        self.setFlags(flags)  # type: ignore


class CheckedItemMixin:

    def isChecked(self) -> bool:
        return self.checkState(0) == QtCore.Qt.Checked  # type: ignore

    def setChecked(self, state: bool) -> None:
        self.setCheckState(0, QtCore.Qt.Checked if state else QtCore.Qt.Unchecked)  # type: ignore
