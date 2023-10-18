from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..sequence import GroupTreeItem

from .panel import BasicPanel

__all__ = ["GroupPanel"]


class GroupPanel(BasicPanel):

    groupChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.groupNameLineEdit = QtWidgets.QLineEdit(self)
        self.groupNameLineEdit.setToolTip("Group name")
        self.groupNameLineEdit.setClearButtonEnabled(True)
        self.groupNameLineEdit.editingFinished.connect(self.updateGroupName)

        self.groupGroupBox = QtWidgets.QGroupBox(self)
        self.groupGroupBox.setTitle("Group")

        self.groupGroupBoxLayout = QtWidgets.QGridLayout(self.groupGroupBox)
        self.groupGroupBoxLayout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        self.groupGroupBoxLayout.addWidget(self.groupNameLineEdit, 0, 1)
        self.groupGroupBoxLayout.setColumnStretch(0, 0)
        self.groupGroupBoxLayout.setColumnStretch(1, 1)

        self.layout().insertWidget(2, self.groupGroupBox)  # type: ignore

    def updateGroupName(self) -> None:
        if isinstance(self.context, GroupTreeItem):
            self.context.setName(self.groupNameLineEdit.text())
            self.setTitle(f"Group &rarr; {self.context.name()}")
            self.groupChanged.emit(self.context)

    def mount(self, context) -> None:
        super().mount(context)
        self.setTitle(f"Group &rarr; {context.name()}")
        self.setDescription("")
        self.groupGroupBox.show()
        self.groupNameLineEdit.setText(context.name())

    def unmount(self) -> None:
        self.groupNameLineEdit.clear()
        self.groupGroupBox.hide()
        super().unmount()
