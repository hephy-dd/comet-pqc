import logging
import os
from typing import Optional

import yaml
from PyQt5 import QtCore, QtWidgets

from ..settings import settings as config
from .sequence import load_sequence

__all__ = ["load_all_sequences", "SequenceManagerDialog"]

logger = logging.getLogger(__name__)


def load_all_sequences(config):
    configs = []
    for filename in config.sequence_filenames:
        if os.path.exists(filename):
            try:
                sequence = load_sequence(filename)
            except Exception:
                ...
            else:
                configs.append((sequence.name, filename))
    return configs


class SequenceItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, sequence, filename: str) -> None:
        super().__init__([sequence.name, filename])
        self._sequence = sequence
        self._filename: str = filename
        self.setToolTip(1, filename)

    def sequence(self):
        return self._sequence

    def filename(self) -> str:
        return self._filename


class SequenceManagerDialog(QtWidgets.QDialog):
    """Dialog for managing custom sequence configuration files."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sequence Manager")
        self.resize(640, 480)

        self.sequenceTreeWidget = QtWidgets.QTreeWidget(self)
        self.sequenceTreeWidget.setHeaderLabels(["Name", "Filename"])
        self.sequenceTreeWidget.setRootIsDecorated(False)
        self.sequenceTreeWidget.currentItemChanged.connect(self.loadPreview)

        self.addButton = QtWidgets.QPushButton(self)
        self.addButton.setText("&Add")
        self.addButton.clicked.connect(self.addSequence)

        self.moveUpButton = QtWidgets.QPushButton(self)
        self.moveUpButton.setText("&Up")
        self.moveUpButton.setEnabled(False)
        self.moveUpButton.clicked.connect(self.moveSequenceUp)

        self.moveDownButton = QtWidgets.QPushButton(self)
        self.moveDownButton.setText("&Down")
        self.moveDownButton.setEnabled(False)
        self.moveDownButton.clicked.connect(self.moveSequenceDown)

        self.removeButton = QtWidgets.QPushButton(self)
        self.removeButton.setText("&Remove")
        self.removeButton.setEnabled(False)
        self.removeButton.clicked.connect(self.removeSequence)

        self.previewTreeWidget = QtWidgets.QTreeWidget(self)
        self.previewTreeWidget.setHeaderLabels(["Key", "Value"])

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.addWidget(self.sequenceTreeWidget)
        leftLayout.addWidget(self.previewTreeWidget)

        rightLayout = QtWidgets.QVBoxLayout()
        rightLayout.addWidget(self.addButton)
        rightLayout.addWidget(self.moveUpButton)
        rightLayout.addWidget(self.moveDownButton)
        rightLayout.addWidget(self.removeButton)
        rightLayout.addStretch()

        layout = QtWidgets.QGridLayout(self)
        layout.addLayout(leftLayout, 0, 0)
        layout.addLayout(rightLayout, 0, 1)
        layout.addWidget(self.buttonBox, 1, 0, 1, 2)

    def currentSequence(self):
        """Return selected sequence object or None if nothing selected."""
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SequenceItem):
            return item.sequence()  # TODO
        return None

    def sequenceFilenames(self) -> list:
        filenames: list = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            if isinstance(item, SequenceItem):
                filenames.append(item.filename())
        return filenames

    # Settings

    def readSettings(self) -> None:
        self.readDialogSettings()
        self.load_settings_sequences()

    def readDialogSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManager")
        geometry = settings.value("geometry", QtCore.QByteArray(), QtCore.QByteArray)
        self.restoreGeometry(geometry)
        settings.endGroup()

    def load_settings_sequences(self):
        """Load all sequences from settings."""
        progress = QtWidgets.QProgressDialog(self)
        progress.setLabelText("Loading sequences...")
        progress.setCancelButton(None)

        def callback():
            try:
                self.sequenceTreeWidget.clear()
                all_sequences = load_all_sequences(config)
                progress.setMaximum(len(all_sequences))
                for name, filename in all_sequences:
                    progress.setValue(progress.value() + 1)
                    try:
                        sequence = load_sequence(filename)
                        item = SequenceItem(sequence, filename)
                        self.sequenceTreeWidget.addTopLevelItem(item)
                    except Exception as exc:
                        logger.exception(exc)
                        logger.error("failed to load sequence: %s", filename)
                self.sequenceTreeWidget.resizeColumnToContents(0)
                self.sequenceTreeWidget.resizeColumnToContents(1)
                if self.sequenceTreeWidget.topLevelItemCount():
                    item = self.sequenceTreeWidget.topLevelItem(0)
                    self.sequenceTreeWidget.setCurrentItem(item)
            finally:
                progress.close()

        QtCore.QTimer.singleShot(200, callback)
        progress.exec()

    def writeSettings(self) -> None:
        self.writeDialogSettings()
        self.store_settings_sequences()

    def writeDialogSettings(self) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("SequenceManager")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()

    def store_settings_sequences(self):
        """Store custom sequences to settings."""
        filenames = []
        for index in range(self.sequenceTreeWidget.topLevelItemCount()):
            item = self.sequenceTreeWidget.topLevelItem(index)
            if isinstance(item, SequenceItem):
                filenames.append(item.filename())
        config.sequence_filenames = filenames

    # Callbacks

    def loadPreview(self, current, previous) -> None:
        """Load sequence config preview."""
        self.moveUpButton.setEnabled(False)
        self.moveDownButton.setEnabled(False)
        self.removeButton.setEnabled(False)
        self.previewTreeWidget.clear()
        item = current
        if item is not None:
            self.moveUpButton.setEnabled(True)
            self.moveDownButton.setEnabled(True)
            self.removeButton.setEnabled(True)
            if os.path.exists(item.filename()):
                with open(item.filename()) as f:
                    data = yaml.safe_load(f)

                    def append(item, key, value):
                        """Recursively append items."""
                        if isinstance(value, dict):
                            child = QtWidgets.QTreeWidgetItem()
                            child.setText(0, format(key))
                            item.addChild(child)
                            for key, value in value.items():
                                append(child, key, value)
                        elif isinstance(value, list):
                            child = QtWidgets.QTreeWidgetItem()
                            child.setText(0, format(key))
                            item.addChild(child)
                            for i, obj in enumerate(value):
                                if isinstance(obj, dict):
                                    for key, value in obj.items():
                                        append(child, key, value)
                                else:
                                    append(child, f"[{i}]", obj)
                            child.setExpanded(True)
                        else:
                            child = QtWidgets.QTreeWidgetItem()
                            child.setText(0, format(key))
                            child.setText(1, format(value))
                            item.addChild(child)
                            child.setExpanded(True)

                    for key, value in data.items():
                        append(self.previewTreeWidget.invisibleRootItem(), key, value)

                    self.previewTreeWidget.resizeColumnToContents(0)
                    self.previewTreeWidget.resizeColumnToContents(1)

    def addSequence(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "", os.path.expanduser("~"), "YAML files (*.yml, *.yaml);;All files (*)")
        if filename:
            sequence = load_sequence(filename)
            if filename not in self.sequenceFilenames():
                item = SequenceItem(sequence, filename)
                self.sequenceTreeWidget.addTopLevelItem(item)
                self.sequenceTreeWidget.indexOfTopLevelItem(item)
                self.sequenceTreeWidget.setCurrentItem(item)

    def removeSequence(self) -> None:
        item = self.sequenceTreeWidget.currentItem()
        if isinstance(item, SequenceItem):
            message = f"Do yo want to remove sequence {item.sequence().name!r}?"
            result = QtWidgets.QMessageBox.question(self, "Remove Sequence", message)
            if result == QtWidgets.QMessageBox.Yes:
                index = self.sequenceTreeWidget.indexOfTopLevelItem(item)
                self.sequenceTreeWidget.takeTopLevelItem(index)
                enabled = self.sequenceTreeWidget.topLevelItemCount() != 0
                self.moveUpButton.setEnabled(enabled)
                self.moveDownButton.setEnabled(enabled)
                self.removeButton.setEnabled(enabled)

    def moveSequenceUp(self) -> None:
        self.moveSequenceItem(-1)

    def moveSequenceDown(self) -> None:
        self.moveSequenceItem(+1)

    def moveSequenceItem(self, offset: int) -> None:
        """Moves a top-level item item up/down by offset."""
        item = self.sequenceTreeWidget.currentItem()
        # Make sure it is a top-level item
        if item and not item.parent():
            index = self.sequenceTreeWidget.indexOfTopLevelItem(item)
            if 0 <= index + offset < self.sequenceTreeWidget.topLevelItemCount():
                self.sequenceTreeWidget.takeTopLevelItem(index)
                self.sequenceTreeWidget.insertTopLevelItem(index + offset, item)
                self.sequenceTreeWidget.setCurrentItem(item)
