import re

from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QApplication, QTreeView, QAbstractItemView, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, QThread

from ReadThread import ReadThread


class CreateModelThread(QThread):
    def __init__(self, readThread, parent=None):
        super().__init__(parent)
        self.readThread = readThread
        self.model = QStandardItemModel()

    def run(self):
        # 将self.readThread.taskstart.content()和self.readThread.taskfinish.content()合并
        newList = [(t, d) for d, t in zip(*self.readThread.taskstart.content())] + [(t, d) for d, t in
                                                                                    zip(*self.readThread.taskfinish.content())]
        # 按时间排序
        newList.sort(key=lambda x: x[0])
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Time", "Content"])
        for i in newList:
            if "[MF][d] [Text][cnt: 0" in i[1] or "[MoveFactory][d] [Text][cnt: 0" in i[1]:
                self.model.appendRow(QStandardItem(i[0].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
                r: list[str] = re.findall(r"\w+ {.*?}", i[1])
                target_name = ""
                source_name = ""
                for idx, v in enumerate(r):
                    if v.startswith("target_name"):
                        target_name = v.split()[-2].replace("\"", "")
                    elif v.startswith("source_name"):
                        source_name = v.split()[-2].replace("\"", "")
                    s = v.replace("{", "").replace(" value: ", " : ").replace("\"", "").replace("}", "")
                    self.model.item(self.model.rowCount() - 1, 0).setChild(idx, 1, QStandardItem(s))
                self.model.setItem(self.model.rowCount() - 1, 1,
                                   QStandardItem(f'TaskStart : {source_name} -> {target_name}'))
            else:
                self.model.appendRow([QStandardItem(i[0].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
                                      QStandardItem('TaskFinish : {}'.format(i[1].split()[-1].replace("]", "")))])
            self.model.item(self.model.rowCount() - 1, 1).setToolTip(i[1])


class MoveFactoryWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, readThread: ReadThread, paren=None):
        super(MoveFactoryWidget, self).__init__(paren)
        self.createModelThread = CreateModelThread(readThread)
        self.setWindowTitle("Move factory list")
        self.treeView = QTreeView()
        self.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.treeView)

        self.treeView.setModel(self.createModelThread.model)

    def closeEvent(self, event) -> None:
        self.closed.emit()

    def updateModel(self):
        self.createModelThread.start()