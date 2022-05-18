import json
import sys
from PyQt5.QtCore import QStandardPaths, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QPushButton, QTextBrowser, QFileDialog
from PyQt5.QtGui import QDropEvent, QDragEnterEvent


class CheckThread(QThread):
    msg = pyqtSignal(str)

    def __init__(self, parent=None):
        super(CheckThread, self).__init__(parent)
        self.mapFiles = []

    def run(self) -> None:
        self._check()

    def _check(self):
        index = 1
        for mf in self.mapFiles:
            self.msg.emit(f"<p><strong>{index:<3}{mf}</strong></p>")
            index += 1
            error = False
            try:
                with open(mf, "rb") as f:
                    map: dict = json.load(f)
                    if "binLocationsList" in map.keys():
                        for i in map["binLocationsList"]:
                            instanceName = i["binLocationList"][0]["instanceName"]
                            if " " in instanceName:
                                self.msg.emit(
                                    f"<p style='color: red'> ---> [{instanceName}] 含有空格</p>")
                                error = True
            except Exception as e:
                self.msg.emit(
                    f"<p style='color:red'> ---> {type(e).__name__}</p><p style='color:red'> ---> {e}</p>")
                continue
            if not error:
                self.msg.emit(f"<p style='color: green'> ---> OK</p>")


class MapCheckWidget(QWidget):
    def __init__(self, parent=None):
        super(MapCheckWidget, self).__init__(parent)
        self.checkThread = CheckThread(self)
        self.setWindowTitle("地图检查")
        self.setAcceptDrops(True)
        self.openButton = QPushButton("打开地图文件")
        self.report = QTextBrowser()

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.openButton)
        self.layout().addWidget(self.report)

        self.openButton.clicked.connect(self._openMapFile)
        self.checkThread.msg.connect(self.report.append)

    def _openMapFile(self):
        defaultDir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]
        self.checkThread.mapFiles = QFileDialog.getOpenFileNames(self, "选择地图文件", defaultDir, "地图文件(*.smap)")[0]
        if self.checkThread.mapFiles:
            self.report.clear()
            self.checkThread.start()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            self.checkThread.mapFiles = [file.toLocalFile() for file in mimeData.urls() if
                                         file.fileName()[-5:].lower() == ".smap"]
            if self.checkThread.mapFiles:
                self.report.clear()
                self.checkThread.start()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    wd = MapCheckWidget()
    wd.show()
    app.exec()
