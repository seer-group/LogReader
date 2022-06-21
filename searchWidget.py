from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QApplication, QMessageBox


class SearchWidget(QWidget):
    nextMove = pyqtSignal(object)

    def __init__(self, readThread, parent=None):
        super(SearchWidget, self).__init__(parent)
        self.readThread = readThread
        self.setLayout(QHBoxLayout())
        self.lineEdit = QLineEdit()
        self.lineEdit.setPlaceholderText("Input error code")
        self.code = ""
        self.layout().addWidget(self.lineEdit)
        self.button = QPushButton("Search")
        self.layout().addWidget(self.button)
        self.button.clicked.connect(self.search)

    def search(self):
        if self.lineEdit.text() == "":
            return
        if self.code != self.lineEdit.text():
            self.code = self.lineEdit.text()
            # 创建一个生成器对象
            self.iter = self.getNextMove(self.code)
        try:
            self.nextMove.emit(next(self.iter))
        except StopIteration:
            self.code = ""
            QMessageBox.information(self, "提示", "已是最后一条记录，再次点击重新搜索！")

    def getNextMove(self, code):
        for v, t in zip(*self.readThread.err.content()):
            if code in v:
                yield t
        for v, t in zip(*self.readThread.war.content()):
            if code in v:
                yield t
        for v, t in zip(*self.readThread.fatal.content()):
            if code in v:
                yield t
        for v, t in zip(*self.readThread.notice.content()):
            if code in v:
                yield t