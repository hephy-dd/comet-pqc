import webbrowser

from PyQt5 import QtCore, QtWidgets

from comet import ui, ProcessMixin
from comet.ui.preferences import PreferencesDialog

from .preferences import OptionsTab, TableTab

__all__ = ["MainWindow"]

APP_TITLE = "PQC"
APP_COPY = "Copyright &copy; 2020-2022 HEPHY"
APP_LICENSE = "This software is licensed under the GNU General Public License v3.0"
APP_DECRIPTION = """Process Quality Control (PQC) for CMS Tracker."""


class MainWindow(QtWidgets.QMainWindow, ProcessMixin):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Actions

        self.quit_action = QtWidgets.QAction(self)
        self.quit_action.setText("&Quit")
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)

        self.preferences_action = QtWidgets.QAction(self)
        self.preferences_action.setText("Prefere&nces")
        self.preferences_action.triggered.connect(self.show_preferences)

        self.contents_action = QtWidgets.QAction(self)
        self.contents_action.setText("&Contents")
        self.contents_action.setShortcut("F1")
        self.contents_action.triggered.connect(self.show_contents)

        self.github_action = QtWidgets.QAction(self)
        self.github_action.setText("&GitHub")
        self.github_action.triggered.connect(self.show_github)

        self.about_qt_action = QtWidgets.QAction(self)
        self.about_qt_action.setText("About Qt")
        self.about_qt_action.triggered.connect(self.show_about_qt)

        self.about_action = QtWidgets.QAction(self)
        self.about_action.setText("&About")
        self.about_action.triggered.connect(self.show_about)

        # Menus
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.quit_action)

        self.edit_menu = self.menuBar().addMenu("&Edit")
        self.edit_menu.addAction(self.preferences_action)

        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.addAction(self.contents_action)
        self.help_menu.addAction(self.github_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_qt_action)
        self.help_menu.addAction(self.about_action)

        # Setup status bar widgets
        self.message_label = QtWidgets.QLabel(self)
        self.statusBar().addPermanentWidget(self.message_label)
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setFixedWidth(600)
        self.statusBar().addPermanentWidget(self.progress_bar)

        # Dialogs
        self.preferences_dialog = PreferencesDialog()
        self.preferences_dialog.hide()

        table_tab = TableTab()
        self.preferences_dialog.tab_widget.append(table_tab)
        self.preferences_dialog.table_tab = table_tab

        options_tab = OptionsTab()
        self.preferences_dialog.tab_widget.append(options_tab)
        self.preferences_dialog.options_tab = options_tab

        # Events
        self.hide_message()
        self.hide_progress()

    def show_preferences(self):
        """Show modal preferences dialog."""
        self.preferences_dialog.run()

    def show_contents(self):
        """Open local webbrowser with contents URL."""
        contents_url = QtWidgets.QApplication.instance().property("contentsUrl")
        if isinstance(contents_url, str):
            webbrowser.open(contents_url)

    def show_github(self):
        """Open local webbrowser with GitHub URL."""
        github_url = QtWidgets.QApplication.instance().property("githubUrl")
        if isinstance(github_url, str):
            webbrowser.open(github_url)

    def show_about_qt(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self, "About Qt")

    def show_about(self) -> None:
        version = QtWidgets.QApplication.applicationVersion()
        QtWidgets.QMessageBox.about(self, "About", f"<h1>{APP_TITLE}</h1><p>Version {version}</p><p>{APP_DECRIPTION}</p><p>{APP_COPY}</p><p>{APP_LICENSE}</p>")

    def show_message(self, message):
        """Show status message."""
        self.message_label.setText(message)
        self.message_label.show()

    def hide_message(self):
        """Hide status message."""
        self.message_label.clear()
        self.message_label.hide()

    def show_progress(self, value, maximum):
        """Show progress bar."""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
        self.progress_bar.show()

    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

    def show_exception(self, exception, tb=None):
        """Raise message box showing exception information."""
        ui.show_exception(exception, tb)
        self.show_message("Error")
        self.hide_progress()

    def pages(self) -> list:
        widgets = []
        for index in range(self.dashboard.tab_widget.qt.count()):
            widgets.append(elf.dashboard.tab_widget.qt.widget(index))
        return widgets

    def addPage(self, widget: QtWidgets.QWidget, label: str) -> None:
        self.dashboard.tab_widget.qt.addTab(widget, label)

    def removePage(self, widget: QtWidgets.QWidget) -> None:
        index = self.dashboard.tab_widget.qt.indexOf(widget)
        self.dashboard.tab_widget.qt.removeTab(index)

    def closeEvent(self, event):
        result = QtWidgets.QMessageBox.question(self, "", "Quit application?")
        if result == QtWidgets.QMessageBox.Yes:
            if self.processes:
                dialog = ProcessDialog(self)
                dialog.exec()
            event.accept()
        else:
            event.ignore()


class ProcessDialog(QtWidgets.QProgressDialog, ProcessMixin):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 0)
        self.setValue(0)
        self.setCancelButton(None)
        self.setLabelText("Stopping active threads...")

    def close(self):
        self.processes.stop()
        self.processes.join()
        super().close()

    def exec(self):
        QtCore.QTimer.singleShot(250, self.close)
        return super().exec()
