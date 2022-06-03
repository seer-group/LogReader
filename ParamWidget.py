import os.path
import sqlite3
import sys

from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QStandardItemModel, QStandardItem, QKeyEvent
from PyQt5.QtWidgets import QWidget, QApplication, QTableView, QPushButton, QVBoxLayout, QFileDialog, \
    QAbstractItemView, QLineEdit, QHBoxLayout
from PyQt5.QtCore import Qt, QStandardPaths, pyqtSignal


class ParamWidget(QWidget):
    closed = pyqtSignal()
    def __init__(self, paren=None):
        super(ParamWidget, self).__init__(paren)
        self.setWindowTitle("查看参数文件")
        self.setAcceptDrops(True)

        self.paramFiles = []

        self.openButton = QPushButton("打开参数文件")
        self.searchLineEdit = QLineEdit()
        self.searchLineEdit.setHidden(True)
        self.searchLineEdit.setPlaceholderText("请输入搜索关键字")
        self.searchLineEdit.setToolTip("仅匹配 参数名 插件名 值")
        self.searchButton = QPushButton("搜索")
        self.searchButton.setHidden(True)
        self.allButton = QPushButton("全部")
        self.allButton.setHidden(True)
        self.searchLayout = QHBoxLayout()
        self.searchLayout.addWidget(self.searchLineEdit)
        self.searchLayout.addWidget(self.searchButton)
        self.searchLayout.addWidget(self.allButton)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(("参数名", "插件名", "值", "所属文件"))
        self.tableView = QTableView()
        self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.setModel(self.model)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.openButton)
        self.layout().addLayout(self.searchLayout)
        self.layout().addWidget(self.tableView)

        self.openButton.clicked.connect(self._openParamFile)
        self.searchButton.clicked.connect(self._search)
        self.allButton.clicked.connect(self._all)

    def _openParamFile(self):
        defaultDir = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]
        self.paramFiles = QFileDialog.getOpenFileNames(self, "选择参数文件", defaultDir, "参数文件(*.param)")[0]
        if self.paramFiles:
            self.readParam()

    def closeEvent(self, event) -> None:
        self.closed.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            self.paramFiles = [file.toLocalFile() for file in mimeData.urls() if
                               file.fileName()[-6:].lower() == ".param"]
            if self.paramFiles:
                self.readParam()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Ctrl+F打开/关闭搜索框
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            if self.searchLineEdit.isHidden():
                self.searchLineEdit.setHidden(False)
                self.searchButton.setHidden(False)
            else:
                self.searchLineEdit.setHidden(True)
                self.searchButton.setHidden(True)

    def readParam(self, files=None):
        if files:
            root = os.path.split(os.path.split(files)[0])[0]
            self.paramFiles = [os.path.join(os.path.join(root, "params"), "robot.param")]
        self.model.removeRows(0, self.model.rowCount())
        for file in self.paramFiles:
            if not os.path.exists(file):
                continue
            conn = sqlite3.connect(file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            for table in cursor.fetchall():
                cursor.execute("SELECT key,value FROM %s" % (table[0]))
                for k, v in cursor.fetchall():
                    row1 = QStandardItem(k)
                    row2 = QStandardItem(table[0])
                    row3 = QStandardItem(v)
                    row4 = QStandardItem(file)
                    self.model.appendRow((row1, row2, row3, row4))
            cursor.close()
            conn.close()

    def _search(self):
        text = self.searchLineEdit.text()
        if not text:
            return
        items = self.model.findItems(text, Qt.MatchContains, column=0)
        items += self.model.findItems(text, Qt.MatchContains, column=1)
        items += self.model.findItems(text, Qt.MatchContains, column=2)
        for i in range(self.model.rowCount()):
            self.tableView.setRowHidden(i, True)
        if items:
            for i in items:
                self.tableView.setRowHidden(i.row(),False)
        self.allButton.setHidden(False)

    def _all(self):
        for i in range(self.model.rowCount()):
            self.tableView.setRowHidden(i, False)
        self.allButton.setHidden(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = ParamWidget()
    w.show()
    app.exec()
