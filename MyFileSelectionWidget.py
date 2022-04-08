from datetime import datetime
import sys
import gzip
import json
from enum import Enum
from PyQt5.QtWidgets import QProgressBar,QWidget, QTreeWidget, QTreeWidgetItem, \
    QApplication, QPushButton, QVBoxLayout, QAbstractItemView, QCheckBox, QLabel, \
    QGroupBox, QSizePolicy, QLayout, QHBoxLayout, QMenu, QAction
from PyQt5.QtCore import QDir, QFileInfo, pyqtSignal, Qt, QPoint, QRect, QSize, QThread
from PyQt5.QtGui import QCursor
from loglibPlus import ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine

class ReportLevel(Enum):
    Fatal = 0
    Error = 1
    Warning = 2
    Notice = 3

class FilterLogThread(QThread):
    statusChanged = pyqtSignal(str)
    progressChanged = pyqtSignal(int)
    Ended = pyqtSignal(object)
    def __init__(self, regex:list, dirPath, files, parent = None):
        super(FilterLogThread, self).__init__(parent)
        self.regex = regex
        self.files = files
        self.filteredFile = dirPath +"/fileredLog-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"

    def run(self):
        total = len(self.files)
        num = 0
        with open(self.filteredFile, "a") as newLogFile:
            for file in self.files:
                fileInfo = QFileInfo(file)
                self.statusChanged.emit("Filtering:" + fileInfo.fileName())

                if fileInfo.suffix() == "log":
                    with open(file, "rb") as logFile:
                        content = logFile.readlines()
                else:
                    with gzip.open(file, "rb") as logFile:
                        content = logFile.readlines()

                for line in content:
                    try:
                        line = line.decode("utf-8")
                    except:
                        try:
                            line = line.decode("gbk")
                        except:
                            continue
                    for r in self.regex:
                        if r in line:
                            newLogFile.write(line)
                            break
                num += 1
                self.progressChanged.emit(num / total * 100)

        self.Ended.emit(QFileInfo(self.filteredFile))

class GetReportThread(QThread):
    statusChanged = pyqtSignal(str)
    progressChanged = pyqtSignal(int)
    reported = pyqtSignal(object, str, str)

    def __init__(self, dirPath, files, parent = None):
        super(GetReportThread, self).__init__(parent)
        self.files = files
        self.reportFile = dirPath +"/Report_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt"

    def run(self):
        total = len(self.files)
        num = 0
        with open(self.reportFile, "a") as reportFile:
            for file in self.files:
                fileInfo = QFileInfo(file)
                self.statusChanged.emit("GetReport:" + fileInfo.fileName())

                reportText = ""
                level = None
                log = ReadLog([file])
                log.thread_num = 1
                err = ErrorLine()
                war = WarningLine()
                fat = FatalLine()
                notice = NoticeLine()
                log.parse(err, war, fat, notice)

                if len(err.content()[0]) > 0 or len(fat.content()[0]) > 0 or len(war.content()[0]) > 0 or len(notice.alarmnum()[0]) > 0:
                    reportText += f"{len(fat.content()[0])}  FATALs,  {len(err.content()[0])}  ERRORs,  {len(war.content()[0])}  WARNINGs,  {len(notice.content()[0])}  NOTICEs\n"
                    if len(fat.alarmnum()[0]) > 0:
                        level = ReportLevel.Fatal
                        reportText += "FATAL:\n"
                        for iter in range(0, len(fat.alarmnum()[0])):
                            reportText += f"  {fat.alarmnum()[0][iter]} {fat.alarminfo()[0][iter]}\n"
                    if len(err.alarmnum()[0]) > 0:
                        if not level:
                            level = ReportLevel.Error
                        reportText +="ERRORS:\n"
                        for iter in range(0, len(err.alarmnum()[0])):
                            reportText += f"  {err.alarmnum()[0][iter]} {err.alarminfo()[0][iter]}\n"
                    if len(war.alarmnum()[0]) > 0:
                        if not level:
                            level = ReportLevel.Warning
                        reportText += "WARNING:\n"
                        for iter in range(0, len(war.alarmnum()[0])):
                            reportText += f"  {war.alarmnum()[0][iter]} {war.alarminfo()[0][iter]}\n"
                    if len(notice.alarmnum()[0]) > 0:
                        if not level:
                            level = ReportLevel.Notice
                        reportText += "NOTICE:\n"
                        for iter in range(0, len(notice.alarmnum()[0])):
                            reportText += f"  {notice.alarmnum()[0][iter]} {notice.alarminfo()[0][iter]}\n"

                print("=" * 20, file=reportFile)
                print("Files: ", file, file=reportFile)
                print(len(fat.content()[0]), " FATALs, ", len(err.content()[0]), " ERRORs, ", len(war.content()[0]),
                      " WARNINGs, ", len(notice.content()[0]), " NOTICEs", file=reportFile)
                print("FATALs:", file=reportFile)
                for data in fat.content()[0]:
                    print(data, file=reportFile)
                print("ERRORs:", reportFile)
                for data in err.content()[0]:
                    print(data, reportFile)
                print("WARNINGs:", reportFile)
                for data in war.content()[0]:
                    print(data, file=reportFile)
                print("NOTICEs:", file=reportFile)
                for data in notice.content()[0]:
                    print(data, file=reportFile)

                num += 1
                self.progressChanged.emit(num / total * 100)
                self.reported.emit(level, fileInfo.fileName(), reportText)

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margin, _, _, _ = self.getContentsMargins()

        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton,
                                                                QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton,
                                                                QSizePolicy.PushButton, Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class MyFileSelectionWidget(QWidget):
    submit = pyqtSignal(list)
    def __init__(self, dirParh, parent = None):
        super(MyFileSelectionWidget, self).__init__(parent)
        self.dirPath = dirParh
        self.setWindowTitle("Select Log Files")
        self.setMinimumHeight(500)
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout(self)
        self.buttonLayout = QHBoxLayout(self)

        self.groupBox = QGroupBox("Filter Log")
        self.groupBox.setLayout(FlowLayout(self.groupBox))

        self.statusLabel = QLabel()
        self.statusLabel.setHidden(True)
        self.progressBar = QProgressBar(self)
        self.progressBar.setHidden(True)

        self.filesView = QTreeWidget(self)
        self.filesView.setWordWrap(True)
        self.filesView.setHeaderHidden(True)
        self.filesView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filesView.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.contextMenu = QMenu()
        self.expandAction = QAction("Expand all", self.filesView)
        self.collapseAction = QAction("Collapse all", self.filesView)
        self.contextMenu.addAction(self.expandAction)
        self.contextMenu.addAction(self.collapseAction)

        self.checkBoxes = []

        self.getReportButton = QPushButton(text="GetReport")
        self.filterButton = QPushButton(text="Filter")
        self.openButton = QPushButton(text="Open")

        self.buttonLayout.addWidget(self.getReportButton)
        self.buttonLayout.addWidget(self.filterButton)
        self.buttonLayout.addWidget(self.openButton)

        self.layout.addWidget(self.statusLabel)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.filesView)
        self.layout.addWidget(self.groupBox)
        self.layout.addLayout(self.buttonLayout)

        self._loadFileList()

        self.filesView.itemSelectionChanged.connect(lambda :self.setWindowTitle(f"{len(self.filesView.selectedItems())} Log Files selected "))
        self.filesView.customContextMenuRequested.connect(lambda :self.contextMenu.exec(QCursor.pos()))
        self.expandAction.triggered.connect(self.filesView.expandAll)
        self.collapseAction.triggered.connect(self.filesView.collapseAll)
        self.openButton.clicked.connect(self._slotOpenClicked)
        self.filterButton.clicked.connect(self._slotFilterClicked)
        self.getReportButton.clicked.connect(self._slotGetReportClicked)

        with open("filterCheckBox.json","r") as f:
            for k,v in json.load(f).items():
                cb = QCheckBox(k)
                cb.data = v
                self.checkBoxes.append(cb)
        [self.groupBox.layout().addWidget(i) for i in self.checkBoxes]

    def _slotOpenClicked(self):
        selectedFiles = self._getSelectedFiles()
        if not selectedFiles:
            return
        self.submit.emit(selectedFiles)

    def _slotFilterClicked(self):
        selectedFiles = self._getSelectedFiles()
        if not selectedFiles:
            return
        regex = [i.data for i in self.checkBoxes if i.isChecked()]
        if regex:
            thread = FilterLogThread(regex, self.dirPath, selectedFiles, self)
            thread.started.connect(self._initStatusProgress)
            thread.finished.connect(self._initStatusProgress)
            thread.statusChanged.connect(lambda s: self.statusLabel.setText(s))
            thread.progressChanged.connect(lambda i: self.progressBar.setValue(i))
            thread.Ended.connect(self._addTreeWidgetTopLevelItem)
            thread.start()

    def _slotGetReportClicked(self):
        selectedFiles = self._getSelectedFiles()
        if not selectedFiles:
            return
        thread = GetReportThread(self.dirPath, selectedFiles, self)
        thread.started.connect(self._initStatusProgress)
        thread.finished.connect(self._initStatusProgress)
        thread.statusChanged.connect(lambda s: self.statusLabel.setText(s))
        thread.progressChanged.connect(lambda i: self.progressBar.setValue(i))
        thread.reported.connect(self._addReportText)
        thread.start()

    def _getSelectedFiles(self):
        if not self.filesView.selectedItems():
            return None
        return [self.dirPath + "/" + file.text(0) for file in self.filesView.selectedItems()]

    def _initStatusProgress(self):
        if self.statusLabel.isHidden():
            self.statusLabel.setHidden(False)
            self.statusLabel.setText("")
            self.progressBar.setHidden(False)
            self.progressBar.setValue(0)
            return
        self.statusLabel.setHidden(True)
        self.progressBar.setHidden(True)

    def _loadFileList(self):
        dir = QDir(self.dirPath)
        dir.setNameFilters(["*.gz", "*.log"])
        for file in dir.entryInfoList():
            self._addTreeWidgetTopLevelItem(file)

    def _addTreeWidgetTopLevelItem(self,file):
        twi = QTreeWidgetItem()
        twi.setText(0, file.fileName())
        self.filesView.addTopLevelItem(twi)

    def _addReportText(self,level:ReportLevel, file:str, reportText:str):
        if not level:
            return
        twi:QTreeWidgetItem = self.filesView.findItems(file, Qt.MatchExactly, 0)[0]
        if twi.childCount():
            twi.removeChild(twi.child(0))
        if level == ReportLevel.Fatal or level == ReportLevel.Error:
            twi.setBackground(0,Qt.red)
        elif level == ReportLevel.Warning:
            twi.setBackground(0,Qt.yellow)
        reportTwi = QTreeWidgetItem()
        reportTwi.setDisabled(True)
        reportTwi.setText(0,reportText)
        twi.addChild(reportTwi)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    s = MyFileSelectionWidget("D:/测试文件/AMB800K-2022-03-25_12-01-32")
    s.show()
    app.exec()