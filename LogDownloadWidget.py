from datetime import datetime, timedelta
import sys
from PyQt5.QtWidgets import QWidget, QApplication, QGridLayout,QLabel, QLineEdit, QDateTimeEdit, QToolButton,\
    QPushButton, QCheckBox, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QFileDialog
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp, Qt, QStandardPaths, pyqtSignal

class LogDownloadWidget(QWidget):
    createDownloadTasked = pyqtSignal(tuple)
    def __init__(self,parent = None):
        super(LogDownloadWidget, self).__init__(parent)
        self.setWindowTitle("Log download")
        gridLayout = QGridLayout()

        self.startTimeLabel = QLabel("Start time")
        self.startTimeLabel.setAlignment(Qt.AlignRight)
        self.startTimeEdit = QDateTimeEdit()
        self.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.endTimeLabel = QLabel("End time")
        self.endTimeLabel.setAlignment(Qt.AlignRight)
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.ipLabel = QLabel("IP")
        self.ipLabel.setAlignment(Qt.AlignRight)
        self.ipEdit = QLineEdit()
        self.regExp = QRegExp("\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b")
        self.ipEdit.setValidator(QRegExpValidator(self.regExp))

        self.downloaDirLabel = QLabel("Directory")
        self.downloaDirLabel.setAlignment(Qt.AlignRight)
        self.downloaDirEdit = QLineEdit()
        self.downloaDirEdit.setReadOnly(True)
        self.openDirButton = QToolButton(text = "...")

        self.onlyDownloadLogCheckBox = QCheckBox("Only Robokit logs")
        self.createDownloadTaskButton = QPushButton("Create")

        hBoxLayout1 = QHBoxLayout()
        hBoxLayout1.addWidget(self.downloaDirLabel)
        hBoxLayout1.addWidget(self.downloaDirEdit)
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

    def dataInit(self):
        self.startTimeEdit.setDateTime(datetime.now() - timedelta(minutes=30))
        self.endTimeEdit.setDateTime(datetime.now())
        self.ipEdit.setText("192.168.192.5")
        dir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0] + "/robokit-Debug-%s" % datetime.now().strftime("%Y%m%d%H%M%S")
        self.downloaDirEdit.setText(dir)
        self.downloaDirEdit.setCursorPosition(0)
        self.downloaDirEdit.setToolTip(dir)

    def _slotOpenDirClicked(self):
        defaultDir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]
        dir = QFileDialog.getExistingDirectory(self, "Select directory", defaultDir)
        if dir:
            self.downloaDirEdit.setText(dir)
            self.downloaDirEdit.setCursorPosition(0)
            self.downloaDirEdit.setToolTip(dir)

    def _slotCreateDownloadTaskClicked(self):
        if self.regExp.exactMatch(self.ipEdit.text()):
            tp = (self.startTimeEdit.text(),
                  self.endTimeEdit.text(),
                  self.ipEdit.text(),
                  self.downloaDirEdit.text(),
                  self.onlyDownloadLogCheckBox.isChecked())
            self.createDownloadTasked.emit(tp)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    l = LogDownloadWidget()
    l.show()
    app.exec()