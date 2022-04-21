import sys
import time
from datetime import datetime, timedelta
from enum import Enum

from PyQt5.QtWidgets import QApplication, QWidget, QDateTimeEdit, QHBoxLayout, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QLineEdit, QMenu, QAction, QMessageBox
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QTimerEvent, QPoint, QStandardPaths
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QCursor, QCloseEvent
from LogDownloadWidget import LogDownloadWidget
from CmdArgs import CmdArgs
from LogDownloader import LogDownloader


class ExtLogDownloadWidget(LogDownloadWidget):
    def __init__(self, parent=None):
        super(ExtLogDownloadWidget, self).__init__(parent)

        timerLabel = QLabel("Timer")
        timerLabel.setAlignment(Qt.AlignRight)
        self.timerEdit = QDateTimeEdit()
        self.timerEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.timerEdit.setDateTime(datetime.now() + timedelta(minutes=30))

        noteLabel = QLabel("Note")
        noteLabel.setAlignment(Qt.AlignRight)
        self.noteEdit = QLineEdit()

        gridLayout: QGridLayout = self.layout().findChild(QGridLayout)
        gridLayout.addWidget(timerLabel)
        gridLayout.addWidget(self.timerEdit)
        gridLayout.addWidget(noteLabel)
        gridLayout.addWidget(self.noteEdit)

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
        if self.timerEdit.dateTime() <= datetime.now():
            self.timerEdit.setStyleSheet("color: red")
            isOK = False
        else:
            self.timerEdit.setStyleSheet("")

        if isOK:
            tp = (CmdArgs(
                self.startTimeEdit.text(),
                self.endTimeEdit.text(),
                self.downloadDirEdit.text(),
                self.onlyDownloadLogCheckBox.isChecked(),
                self.ipEdit.text()
            ), self.timerEdit.dateTime(), self.noteEdit.text())
            self.createDownloadTasked.emit(tp)

            dir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[
                      0] + "/robokit-Debug-%s" % datetime.now().strftime("%Y%m%d%H%M%S")
            self.downloadDirEdit.setText(dir)
            self.downloadDirEdit.setCursorPosition(0)
            self.downloadDirEdit.setToolTip(dir)


class TimedLogDownloadStatus(Enum):
    Timing = 0
    Downloading = 1
    Error = 2
    Finished = 3


class TimedLogDownloadWidget(QWidget):
    filesReady = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super(TimedLogDownloadWidget, self).__init__(parent)

        self.pTimer = None
        self.setWindowTitle("Timed log download")
        self.logDownloadWidget = ExtLogDownloadWidget(self)
        self.logDownloadWidget.setMaximumWidth(330)
        self.treeView = QTreeView(self)
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.treeView.setMinimumWidth(500)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(("Time", "Status", "Note", "Progress"))
        self.treeView.setModel(self.model)
        self.treeView.setColumnWidth(0, 200)
        self.treeView.setColumnWidth(1, 150)
        self.treeView.setColumnWidth(2, 150)
        self.treeView.setColumnWidth(3, 100)

        self.contextMenu = QMenu(self.treeView)
        self.deleteItem = QAction("Delete", self.treeView)
        self.openfs = QAction("Open", self.treeView)
        self.contextMenu.addAction(self.openfs)
        self.contextMenu.addAction(self.deleteItem)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.logDownloadWidget)
        self.layout().addWidget(self.treeView)

        self.logDownloadWidget.createDownloadTasked.connect(self._slotCreateDownloadTasked)
        self.treeView.customContextMenuRequested.connect(self._slotContextMenuRequested)
        self.treeView.doubleClicked.connect(self._slotOpenFileSelection)
        self.deleteItem.triggered.connect(self._slotDeleteItem)
        self.openfs.triggered.connect(self._slotOpenFileSelection)

    def closeEvent(self, e: QCloseEvent):
        if self.model.rowCount():
            s = QMessageBox.information(self, "Tooltip", "Are you sure?", QMessageBox.Yes | QMessageBox.No)
            if s == QMessageBox.Yes:
                e.accept()
                self.closed.emit()
            else:
                e.ignore()
        else:
            self.closed.emit()

    def timerEvent(self, e: QTimerEvent):
        print(time.time())
        needKill = True
        for row in range(self.model.rowCount()):
            if self.model.item(row, 0).data() > QDateTime.currentDateTime():
                needKill = False
                time_t = self.model.item(row, 0).data().toTime_t() - QDateTime.currentDateTime().toTime_t()
                self.model.item(row, 0).setText(str(timedelta(seconds=time_t)))
            elif self.model.item(row, 1).text() == TimedLogDownloadStatus.Timing.name:
                self.model.item(row, 0).setText("Done")
                self.model.item(row, 1).setText(TimedLogDownloadStatus.Downloading.name)
                self._logDownload(row)

        if needKill:
            self.killTimer(self.pTimer)
            self.pTimer = None

    def _slotDeleteItem(self, *args):
        row = self.treeView.currentIndex().row()
        if self.model.item(row, 1).text() == TimedLogDownloadStatus.Downloading.name:
            self.model.item(row, 3).downloader.deleteLater()
        self.model.removeRow(row)

    def _slotContextMenuRequested(self, v):
        row = self.treeView.indexAt(v).row()
        if row >= 0 and row <= self.model.rowCount():
            if self.model.item(row, 1).text() == TimedLogDownloadStatus.Finished.name:
                self.openfs.setVisible(True)
            else:
                self.openfs.setVisible(False)
            self.contextMenu.exec(QCursor.pos())

    def _slotOpenFileSelection(self, v):
        if isinstance(v, QPoint):
            row = self.treeView.indexAt(v).row()
            self.filesReady.emit(self.model.item(row, 3).dir)
        elif self.model.item(v.row(), 1).text() == TimedLogDownloadStatus.Finished.name:
            self.filesReady.emit(self.model.item(v.row(), 3).dir)

    def _slotCreateDownloadTasked(self, tp: tuple):
        c0 = QStandardItem()
        c0.setData(tp[1])
        c0.setToolTip(tp[1].toString("yyyy-MM-dd HH:mm:ss"))
        c1 = QStandardItem(TimedLogDownloadStatus.Timing.name)
        c2 = QStandardItem(tp[2])
        info = f"Start time: {tp[0].startTime}\nEnd time: {tp[0].endTime}\nIP: {tp[0].ip}\nDirectory: {tp[0].dirName}\nOnly Robokit logs: {tp[0].onlyLog}"
        c2.setToolTip(info)
        c3 = QStandardItem()
        c3.setData(tp[0])
        self.model.appendRow((c0, c1, c2, c3))

        if not self.pTimer:
            self.pTimer = self.startTimer(1000)

    def _logDownload(self, row):
        def func(dir):
            ProgressItem.dir = dir

        ProgressItem: QStandardItem = self.model.item(row, 3)
        timeItem: QStandardItem = self.model.item(row, 1)
        ProgressItem.downloader = LogDownloader(ProgressItem.data(), self)
        ProgressItem.downloader.downloadProgressChanged.connect(lambda v: ProgressItem.setText(f"{v}%"))
        ProgressItem.downloader.downloadStatusChanged.connect(ProgressItem.setToolTip)
        ProgressItem.downloader.connectionChanged.connect(timeItem.setToolTip)
        # currentItem.downloader.reqOrResInfoChanged.connect()
        ProgressItem.downloader.error.connect(lambda v: timeItem.setText(TimedLogDownloadStatus.Error.name))
        ProgressItem.downloader.error.connect(timeItem.setToolTip)
        ProgressItem.downloader.error.connect(lambda v: ProgressItem.downloader.deleteLater())
        ProgressItem.downloader.filesReady.connect(lambda v: timeItem.setText(TimedLogDownloadStatus.Finished.name))
        ProgressItem.downloader.filesReady.connect(func)
        ProgressItem.downloader.filesReady.connect(lambda v: ProgressItem.downloader.deleteLater())
        ProgressItem.downloader.run()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    t = TimedLogDownloadWidget()
    t.show()
    app.exec()
