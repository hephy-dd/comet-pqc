from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtMultimedia, QtMultimediaWidgets

class CameraDialog(QtWidgets.QDialog):

    def __init__(self, corvus):
        super().__init__()
        self.corvus = corvus
        self.device_info = QtWidgets.QLabel()
        self.device_info.setText(self.corvus.identification)
        #self.media_content = QtMultimedia.QMediaContent(QtCore.QUrl("http://10.0.0.7:23"))
        self.media_player = QtMultimedia.QMediaPlayer()
        #self.media_player.setMedia(self.media_content)
        self.video_widget = QtMultimediaWidgets.QVideoWidget()
        self.video_widget.setFixedSize(640, 480)
        self.video_widget.setStyleSheet("background-color: rgb(85, 85, 255);")
        self.video_widget.setAutoFillBackground(True)
        self.media_player.setVideoOutput(self.video_widget)
        self.step_spinbox = QtWidgets.QDoubleSpinBox()
        self.step_spinbox.setValue(1)
        self.step_spinbox.setSingleStep(0.1)
        self.step_spinbox.setDecimals(3)
        self.step_spinbox.setSuffix(" mm")
        self.left_button = QtWidgets.QPushButton("Left")
        self.left_button.clicked.connect(self.move_left)
        self.front_button = QtWidgets.QPushButton("Front")
        self.front_button.clicked.connect(self.move_front)
        self.back_button = QtWidgets.QPushButton("Back")
        self.back_button.clicked.connect(self.move_back)
        self.right_button = QtWidgets.QPushButton("Right")
        self.right_button.clicked.connect(self.move_right)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.left_button)
        button_layout.addWidget(self.front_button)
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.right_button)
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok |
            QtWidgets.QDialogButtonBox.Cancel
        )
        #button_box.button(QtWidgets.QDialogButtonBox.Ok).setDefault(False)
        button_box.button(QtWidgets.QDialogButtonBox.Ok).setAutoDefault(False)
        #button_box.button(QtWidgets.QDialogButtonBox.Cancel).setDefault(False)
        button_box.button(QtWidgets.QDialogButtonBox.Cancel).setAutoDefault(False)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.device_info)
        layout.addWidget(self.video_widget)
        layout.addWidget(QtWidgets.QLabel("Step size"))
        layout.addWidget(self.step_spinbox)
        layout.addLayout(button_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)
        # Set units to mm
        self.corvus.x.unit = 2
        self.corvus.y.unit = 2
        self.corvus.z.unit = 2

    def move_front(self):
        value = self.step_spinbox.value()
        self.corvus.rmove(0, -value, 0)

    def move_back(self):
        value = self.step_spinbox.value()
        self.corvus.rmove(0, value, 0)

    def move_left(self):
        value = self.step_spinbox.value()
        self.corvus.rmove(-value, 0, 0)

    def move_right(self):
        value = self.step_spinbox.value()
        self.corvus.rmove(value, 0, 0)
