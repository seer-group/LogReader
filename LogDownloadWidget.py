from datetime import datetime, timedelta
import sys
from PyQt5.QtWidgets import QWidget, QApplication, QGridLayout, QLabel, QLineEdit, QDateTimeEdit, QToolButton, \
    QPushButton, QCheckBox, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QFileDialog, QGroupBox
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp, Qt, QStandardPaths, pyqtSignal
from CmdArgs import CmdArgs


class LogDownloadWidget(QWidget):
    createDownloadTasked = pyqtSignal(object)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super(LogDownloadWidget, self).__init__(parent)
        self.setWindowTitle("Log下载")
        gridLayout = QGridLayout()

        self.startTimeLabel = QLabel("起始时间")
        self.startTimeLabel.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.startTimeEdit = QDateTimeEdit()
        self.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.endTimeLabel = QLabel("结束时间")
        self.endTimeLabel.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.ipLabel = QLabel("IP")
        self.ipLabel.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.ipEdit = QLineEdit()
        self.regExp = QRegExp(
            "\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b")
        self.ipEdit.setValidator(QRegExpValidator(self.regExp))

        self.downloadDirLabel = QLabel("下载目录")
        self.downloadDirLabel.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.downloadDirEdit = QLineEdit()
        self.downloadDirEdit.setReadOnly(True)
        self.openDirButton = QToolButton(text="...")

        self.onlyDownloadLogCheckBox = QCheckBox("仅下载log")
        self.createDownloadTaskButton = QPushButton("创建")

        hBoxLayout1 = QHBoxLayout()
        hBoxLayout1.addWidget(self.downloadDirLabel)
        hBoxLayout1.addWidget(self.downloadDirEdit)
        hBoxLayout1.addWidget(self.openDirButton)

        hBoxLayout2 = QHBoxLayout()
        hBoxLayout2.addWidget(self.onlyDownloadLogCheckBox)
        hBoxLayout2.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        hBoxLayout2.addWidget(self.createDownloadTaskButton)

        gridLayout.addWidget(self.startTimeLabel, 0, 0)
        gridLayout.addWidget(self.startTimeEdit, 0, 1)
        gridLayout.addWidget(self.endTimeLabel, 1, 0)
        gridLayout.addWidget(self.endTimeEdit, 1, 1)
        gridLayout.addWidget(self.ipLabel, 2, 0)
        gridLayout.addWidget(self.ipEdit, 2, 1)

        self.setLayout(QVBoxLayout())
        self.layout().addLayout(gridLayout)
        self.layout().addLayout(hBoxLayout1)
        self.layout().addLayout(hBoxLayout2)
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.dataInit()

        self.openDirButton.clicked.connect(self._slotOpenDirClicked)
        self.createDownloadTaskButton.clicked.connect(self._slotCreateDownloadTaskClicked)

    def closeEvent(self, QCloseEvent):
        self.closed.emit()

    def dataInit(self):
        self.startTimeEdit.setDateTime(datetime.now() - timedelta(minutes=30))
        self.endTimeEdit.setDateTime(datetime.now())
        self.ipEdit.setText("192.168.192.5")
        dir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[
                  0] + "/robokit-Debug-%s" % datetime.now().strftime("%Y%m%d%H%M%S")
        self.downloadDirEdit.setText(dir)
        self.downloadDirEdit.setCursorPosition(0)
        self.downloadDirEdit.setToolTip(dir)

    def _slotOpenDirClicked(self):
        defaultDir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]
        dir = QFileDialog.getExistingDirectory(self, "选择下载目录", defaultDir)
        if dir:
            self.downloadDirEdit.setText(dir)
            self.downloadDirEdit.setCursorPosition(0)
            self.downloadDirEdit.setToolTip(dir)

    def _slotCreateDownloadTaskClicked(self):
        isOK = True
        if not self.regExp.exactMatch(self.ipEdit.text()):
            self.ipEdit.setStyleSheet("color: red")
            isOK = False
        else:
            self.ipEdit.setStyleSheet("")
        if self.startTimeEdit.dateTime() >= self.endTimeEdit.dateTime():
            self.endTimeEdit.setStyleSheet("color: red")
            isOK = False
        else:
            self.endTimeEdit.setStyleSheet("")

        if isOK:
            tp = CmdArgs(
                    self.startTimeEdit.text(),
                    self.endTimeEdit.text(),
                    self.downloadDirEdit.text(),
                    self.onlyDownloadLogCheckBox.isChecked(),
                    self.ipEdit.text()
                )
            self.createDownloadTasked.emit(tp)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    l = LogDownloadWidget()
    l.createDownloadTasked.connect(print)
    l.show()
    app.exec()
