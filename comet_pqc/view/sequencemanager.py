import logging
from typing import Any, Dict, List, Optional

from PyQt5 import QtCore, QtWidgets

from ..core.config import Sequence, load_sequence
from ..settings import settings
from .components import showException, showQuestion
from .sequencetreewidget import load_all_sequences

__all__ = ["SequenceManagerDialog"]

logger = logging.getLogger(__name__)


class SequenceManagerTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, sequence: Sequence, filename: str) -> None:
        super().__init__()
        self.setText(0, sequence.name)
        self.setText(1, filename)
        self.setToolTip(1, filename)
        self._sequence: Sequence = sequence
        self._filename: str = filename

    def sequence(self) -> Sequence:
        return self._sequence

    def filename(self) -> str:
        return self._filename


class SequenceManagerDialog(QtWidgets.QDialog):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sequence Manager")

        self.sequenceTreeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget(self)
        self.sequenceTreeWidget.setHeaderLabels(["Name", "Filename"])
        self.sequenceTreeWidget.setRootIsDecorated(False)

        self.addButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.addButton.setText("&Add")
        self.addButton.clicked.connect(self.addSequence)

        self.removeButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("&Remove")
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.removeSequence)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.sequenceTreeWidget, 0, 0, 3, 1)
        layout.addWidget(self.addButton, 0, 1)
        layout.addWidget(self.removeButton, 1, 1)
        layout.addWidget(self.buttonBox, 4, 0, 1, 2)

    def currentSequence(self) -> Optional[Sequence]:
        """Return selected sequence object or None if nothing selected."""
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SequenceManagerTreeItem):
            return item.sequence()
        return None

    def sequenceFilenames(self) -> List[str]:
        filenames = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            if isinstance(item, SequenceManagerTreeItem):
                filenames.append(item.filename())
        return filenames

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManagerDialog")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not self.restoreGeometry(geometry):
            self.resize(800, 600)
        settings.endGroup()

    def readSequences(self) -> None:
        """Load all built-in and custom sequences from settings."""
        self.sequenceTreeWidget.clear()
        for name, filename in load_all_sequences():
            try:
                sequence = load_sequence(filename)
                item = SequenceManagerTreeItem(sequence, filename)
                self.sequenceTreeWidget.addTopLevelItem(item)
            except Exception as exc:
                logger.error("failed to load sequence: %s", filename)
                logger.exception(exc)
        self.sequenceTreeWidget.resizeColumnToContents(0)
        if self.sequenceTreeWidget.topLevelItemCount():
            self.sequenceTreeWidget.setCurrentItem(self.sequenceTreeWidget.topLevelItem(0))

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManagerDialog")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()
        self.writeSequences()

    def writeSequences(self) -> None:
        """Store custom sequences to settings."""
        sequences: List[str] = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            if isinstance(item, SequenceManagerTreeItem):
                sequences.append(item.filename())
        settings.setValue("custom_sequences", list(set(sequences)))

    @QtCore.pyqtSlot()
    def addSequence(self) -> None:
        filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Open Sequence", "YAML files (*.yml, *.yaml);;All files (*)")
        logging.warning(filenames)
        for filename in filenames:
            try:
                sequence = load_sequence(filename)
            except Exception as exc:
                showException(exc)
                break
            else:
                if filename not in self.sequenceFilenames():
                    item = SequenceManagerTreeItem(sequence, filename)
                    self.sequenceTreeWidget.addTopLevelItem(item)
                    self.sequenceTreeWidget.setCurrentItem(item)

    @QtCore.pyqtSlot()
    def removeSequence(self) -> None:
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SequenceManagerTreeItem):
            if showQuestion(
                title="Remove Sequence",
                text=f"Do yo want to remove sequence {item.sequence().name!r}?",
            ):
                index: int = self.sequenceTreeWidget.indexOfTopLevelItem(item)
                self.sequenceTreeWidget.takeTopLevelItem(index)
                self.removeButton.setEnabled(self.sequenceTreeWidget.topLevelItemCount() != 0)
