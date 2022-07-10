import json
import re
import sqlite3
from datetime import datetime

from PyQt5.QtGui import QStandardItemModel, QStandardItem, QCursor, QKeyEvent
from PyQt5.QtWidgets import QWidget, QTreeView, QAbstractItemView, QHBoxLayout, QMenu, QAction, QLineEdit, QPushButton, \
    QVBoxLayout
from PyQt5.QtCore import pyqtSignal, QThread, Qt, QModelIndex
from ReadThread import ReadThread


class CreateModelThread(QThread):
    def __init__(self, readThread, parent=None):
        super().__init__(parent)
        self.readThread = readThread
        self.networkLines = []
        self.taskStartLines = []
        self.taskFinishLines = []
        self.otherNode = None
        self.model = QStandardItemModel()
        self.protocol = self._getProtocol()

    def _getLogLines(self):
        for line in self.readThread.reader.lines:
            if "[NP][d] [NetworkJSON]" in line or "[NP][d] [NetworkCmd]" in line or "[NP][d] [NetworkCmdHeader]" in line:
                self.networkLines.append(line)
            elif "[MoveFactory][d] [Text][cnt: 0" in line or "[MF][d] [Text][cnt: 0" in line:
                self.taskStartLines.append(line)
            elif "[MoveFactory][d] [Text][Task finished" in line or "[MF][d] [Text][Task finished" in line:
                self.taskFinishLines.append(line)

    def _addNetworkLines(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Time", "Key", "Value"])
        i = 0
        while i < len(self.networkLines):
            if "[NP][d] [NetworkCmdHeader]" in self.networkLines[i]:
                toolTip = self.networkLines[i]
                header = self.networkLines[i].strip().split("[NP][d] [NetworkCmdHeader]")
                cmd = []
                js = []
                if i + 1 < len(self.networkLines) and "[NP][d] [NetworkCmd]" in self.networkLines[i + 1]:
                    toolTip += self.networkLines[i + 1]
                    cmd = self.networkLines[i + 1].strip().split("[NP][d] [NetworkCmd]")
                    i += 1
                    if i + 1 < len(self.networkLines) and "[NP][d] [NetworkJSON]" in self.networkLines[i + 1]:
                        toolTip += self.networkLines[i + 1]
                        js = self.networkLines[i + 1].strip().split("[NP][d] [NetworkJSON]")
                        i += 1
                headerTime = datetime.strptime(header[0], "[%y%m%d %H%M%S.%f]")
                header = header[-1][1:-1].split("|")
                rootNode = QStandardItem(headerTime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
                rootNode.setToolTip(toolTip)
                rootNodeKey = header[0]
                headerNode = QStandardItem(headerTime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
                rootNode.appendRow((headerNode, QStandardItem("NetworkCmdHeader")))
                for j, v in enumerate(header):
                    headerNode.appendRow((None, QStandardItem(str(j)), QStandardItem(v)))
                if cmd:
                    cmdTime = datetime.strptime(cmd[0], "[%y%m%d %H%M%S.%f]")
                    cmd = cmd[-1][1:-1].split("|")
                    rootNodeKey += " " + cmd[0]
                    nodeCmd = QStandardItem(cmdTime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
                    rootNode.appendRow((nodeCmd, QStandardItem("NetworkCmd")))
                    for j, v in enumerate(cmd):
                        nodeCmd.appendRow((None, QStandardItem(str(j)), QStandardItem(v)))
                if js:
                    jsTime = datetime.strptime(js[0], "[%y%m%d %H%M%S.%f]")
                    js = json.loads(js[-1][1:-1])
                    nodeJs = QStandardItem(jsTime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
                    rootNode.appendRow((nodeJs, QStandardItem("NetworkJSON")))
                    self._addJsonLines(nodeJs, js)
                    rootNode.setData(self._findJsonValue(js, "task_id"), Qt.UserRole + 1)
                v3 = None
                if len(header) > 6:
                    v3 = QStandardItem(f"{header[5]}\t{self.protocol.get(int(header[5]), 'Unknown')}")
                self.model.appendRow((rootNode, QStandardItem(rootNodeKey), v3))
            i += 1

    def _addTaskStartLines(self):
        # 添加节点方法
        def addNode(taskStartTime, taskStartDict, node):
            taskStartTimeNode = QStandardItem(taskStartTime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
            taskStartKeyNode = QStandardItem(
                f"TaskStart\t{taskStartDict.get('source_name')} -> {taskStartDict.get('target_name')}")
            taskValueNode = QStandardItem(taskStartDict.get('task_id'))
            taskStartTimeNode.setData(taskStartDict.get('target_name'), Qt.UserRole + 1)
            for k, v in taskStartDict.items():
                taskStartTimeNode.appendRow((None, QStandardItem(k), QStandardItem(v)))
            node.appendRow((taskStartTimeNode, taskStartKeyNode, taskValueNode))
        if self.model.rowCount():
            for i in range(self.model.rowCount()):
                node = self.model.item(i, 0)
                if node.data(Qt.UserRole + 1):
                    j = 0
                    flag = False
                    while j < len(self.taskStartLines):
                        taskStartTime, taskStartDict = self._parseTaskLine(self.taskStartLines[j])
                        currentTaskId = taskStartDict.get('task_id')
                        if currentTaskId and currentTaskId in node.data(Qt.UserRole + 1):
                            node.setToolTip(node.toolTip() + self.taskStartLines[j])
                            addNode(taskStartTime, taskStartDict, node)
                            self.taskStartLines.pop(j)
                            flag = True
                            continue
                        if flag:
                            if not currentTaskId:
                                node.setToolTip(node.toolTip() + self.taskStartLines[j])
                                addNode(taskStartTime, taskStartDict, node)
                                self.taskStartLines.pop(j)
                                continue
                            else:
                                break
                        j += 1
        for i in self.taskStartLines:
            taskStartTime, taskStartDict = self._parseTaskLine(i)
            if not self.otherNode:
                self.otherNode = QStandardItem("0")
            self.otherNode.setToolTip(self.otherNode.toolTip() + i)
            addNode(taskStartTime, taskStartDict, self.otherNode)

        if self.otherNode:
            self.model.insertRow(0, (self.otherNode, QStandardItem("Other"), QStandardItem("Other")))

    def _addTaskFinishLines(self):
        # 添加节点方法
        def addNode(taskFinishTime, taskFinishDict, node, index):
            taskFinishTimeNode = QStandardItem(taskFinishTime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
            taskFinishKeyNode = QStandardItem(f"TaskFinish\t{taskFinishDict.get('TaskFinished')}")
            for k, v in taskFinishDict.items():
                if k != "TaskFinished":
                    taskFinishTimeNode.appendRow((None, QStandardItem(k), QStandardItem(v)))
            node.insertRow(index, (taskFinishTimeNode, taskFinishKeyNode))
        for node in self._taskStartNodeIter():
            if node.data(Qt.UserRole + 1):
                for line in reversed(self.taskFinishLines):
                    taskFinishTime, taskFinishDict = self._parseTaskLine(line)
                    targetId = taskFinishDict.get('TaskFinished')
                    if targetId and targetId == node.data(Qt.UserRole + 1):
                        node.parent().setToolTip(node.parent().toolTip() + line)
                        addNode(taskFinishTime, taskFinishDict, node.parent(), node.row() + 1)
                        self.taskFinishLines.remove(line)
                        break
        if self.taskFinishLines:
            for line in self.taskFinishLines:
                taskFinishTime, taskFinishDict = self._parseTaskLine(line)
                if not self.otherNode:
                    self.otherNode = QStandardItem("0")
                    self.model.insertRow(0, (self.otherNode, QStandardItem("Other"), QStandardItem("Other")))
                inserted = False
                for i in range(self.otherNode.row()):
                    node = self.otherNode.child(i, 0)
                    if node.data(Qt.UserRole + 1) == taskFinishDict.get('TaskFinished'):
                        self.otherNode.setToolTip(self.otherNode.toolTip() + line)
                        addNode(taskFinishTime, taskFinishDict, self.otherNode, i + 1)
                        inserted = True
                        break
                if not inserted:
                    addNode(taskFinishTime, taskFinishDict, self.otherNode, 0)

    def _taskStartNodeIter(self):
        for i in range(self.model.rowCount() - 1, -1, -1):
            for j in range(self.model.item(i, 0).rowCount() - 1, -1, -1):
                if self.model.item(i, 0).child(j, 0).data(Qt.UserRole + 1):
                    yield self.model.item(i, 0).child(j, 0)

    @staticmethod
    def _parseTaskLine(line):
        taskDict = {}
        reg = re.findall(r"(\w+ {.*?})|(cnt: \d+)|(skill_name: \"[\d|\w]*\")|(Task finished : \d*)", line)
        for g in reg:
            for i, s in enumerate(g):
                if s:
                    if i == 0:
                        s = s.replace("{", "").replace("value:", "").replace("\"", "").replace("}", "")
                        k = s.split()[0]
                        v = s[len(k):].strip()
                        taskDict[k] = v
                        break
                    elif i == 1:
                        taskDict["cnt"] = s.replace("cnt: ", "")
                        break
                    elif i == 2:
                        taskDict["skill_name"] = s.replace("skill_name: ", "").replace("\"", "")
                        break
                    elif i == 3:
                        taskDict["TaskFinished"] = s.replace("Task finished : ", "")
                        break
        return datetime.strptime(line[:19], "[%y%m%d %H%M%S.%f]"), taskDict

    @staticmethod
    def _getProtocol():
        with sqlite3.connect("protocol.db") as conn:
            c = conn.cursor()
            c.execute("SELECT reqValue, reqDescription FROM SCProtocol")
            return {k: v for k, v in c.fetchall()}

    # 找到json的key对应的所有value的值
    def _findJsonValue(self, js, key: str):
        values = []
        if isinstance(js, dict):
            for k, v in js.items():
                if k == key:
                    values.append(v)
                elif isinstance(v, dict) or isinstance(v, list):
                    result = self._findJsonValue(v, key)
                    if result:
                        values.extend(result)
        elif isinstance(js, list):
            for v in js:
                if isinstance(v, dict) or isinstance(v, list):
                    result = self._findJsonValue(v, key)
                    if result:
                        values.extend(result)
        return values

    # 找到json的key所在的所有父节点
    def _findJsonParent(self, js, key: str):
        parents = []
        if isinstance(js, dict):
            for k, v in js.items():
                if k == key:
                    parents.append(js)
                elif isinstance(v, dict) or isinstance(v, list):
                    result = self._findJsonParent(v, key)
                    if result:
                        parents.extend(result)
        elif isinstance(js, list):
            for v in js:
                if isinstance(v, dict) or isinstance(v, list):
                    result = self._findJsonParent(v, key)
                    if result:
                        parents.extend(result)
        return parents

    # 解析json 并加入到node中
    def _addJsonLines(self, node: QStandardItem, value):
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, dict) or isinstance(v, list):
                    currentNode = QStandardItem("object") if isinstance(v, dict) else QStandardItem("array")
                    node.appendRow((currentNode, QStandardItem(k)))
                    self._addJsonLines(currentNode, v)
                else:
                    node.appendRow((None, QStandardItem(k), QStandardItem(str(v))))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, dict) or isinstance(v, list):
                    currentNode = QStandardItem("object") if isinstance(v, dict) else QStandardItem("array")
                    node.appendRow((currentNode, QStandardItem(str(i))))
                    self._addJsonLines(currentNode, v)
                else:
                    node.appendRow((None, QStandardItem(str(i)), QStandardItem(str(v))))

    def run(self):
        self.networkLines = []
        self.taskStartLines = []
        self.taskFinishLines = []
        self.otherNode = None
        self._getLogLines()
        self._addNetworkLines()
        self._addTaskStartLines()
        self._addTaskFinishLines()



class MoveFactoryWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, readThread: ReadThread, paren=None):
        super(MoveFactoryWidget, self).__init__(paren)
        self.createModelThread = CreateModelThread(readThread)
        self.setWindowTitle("Move factory list")
        self.searchLine = QLineEdit()
        self.searchLine.setPlaceholderText("输入搜索内容")
        self.searchLine.hide()
        self.searchButton = QPushButton("Search")
        self.searchButton.hide()
        self.allButton = QPushButton("All")
        self.allButton.hide()
        self.searchLayout = QHBoxLayout()
        self.searchLayout.addWidget(self.searchLine)
        self.searchLayout.addWidget(self.searchButton)
        self.searchLayout.addWidget(self.allButton)
        self.treeView = QTreeView()
        self.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.contextMenu = QMenu()
        self.expandAllAction = QAction("全部展开", self.treeView)
        self.collapseAllAction = QAction("全部折叠", self.treeView)
        self.expandThisAction = QAction("展开当前项", self.treeView)
        self.collapseThisAction = QAction("折叠当前项", self.treeView)
        self.expandThisAndChildAction = QAction("展开当前及所有子项", self.treeView)
        self.collapseThisAndChildAction = QAction("折叠当前及所有子项", self.treeView)
        self.contextMenu.addAction(self.expandAllAction)
        self.contextMenu.addAction(self.collapseAllAction)
        self.contextMenu.addAction(self.expandThisAction)
        self.contextMenu.addAction(self.collapseThisAction)
        self.contextMenu.addAction(self.expandThisAndChildAction)
        self.contextMenu.addAction(self.collapseThisAndChildAction)

        self.setLayout(QVBoxLayout())
        self.layout().addLayout(self.searchLayout)
        self.layout().addWidget(self.treeView)

        self.treeView.setModel(self.createModelThread.model)
        self.searchLine.returnPressed.connect(self._slotSearchButtonClicked)
        self.searchButton.clicked.connect(self._slotSearchButtonClicked)
        self.allButton.clicked.connect(self._slotAllButtonClicked)
        self.treeView.customContextMenuRequested.connect(lambda: self.contextMenu.exec(QCursor.pos()))
        self.treeView.doubleClicked.connect(self._slotDoubleClicked)
        self.expandAllAction.triggered.connect(self.treeView.expandAll)
        self.collapseAllAction.triggered.connect(self.treeView.collapseAll)
        self.expandThisAction.triggered.connect(self._slotExpandThis)
        self.collapseThisAction.triggered.connect(self._slotCollapseThis)
        self.expandThisAndChildAction.triggered.connect(lambda: self._slotExpandThisAndChild(self.treeView.currentIndex()))
        self.collapseThisAndChildAction.triggered.connect(lambda: self._slotCollapseThisAndChild(self.treeView.currentIndex()))

    # 展开当前行
    def _slotExpandThis(self):
        index = self.treeView.currentIndex()
        self.treeView.expand(index.sibling(index.row(), 0))

    # 折叠当前行
    def _slotCollapseThis(self):
        index = self.treeView.currentIndex()
        self.treeView.collapse(index.sibling(index.row(), 0))

    # 展开当前行及其子行
    def _slotExpandThisAndChild(self, index: QModelIndex):
        sibling = index.sibling(index.row(), 0)
        self.treeView.expand(sibling)
        for i in range(self.treeView.model().rowCount(sibling)):
            self._slotExpandThisAndChild(self.treeView.model().index(i, 0, sibling))

    # 折叠当前行及其子行
    def _slotCollapseThisAndChild(self, index: QModelIndex):
        sibling = index.sibling(index.row(), 0)
        self.treeView.collapse(sibling)
        for i in range(self.treeView.model().rowCount(sibling)):
            self._slotCollapseThisAndChild(self.treeView.model().index(i, 0, sibling))

    def _slotDoubleClicked(self, index) -> None:
        print("double click")
        sibling = index.sibling(index.row(), 0)
        if self.treeView.isExpanded(sibling):
            print("collapse")
            self.treeView.collapse(sibling)
        else:
            print("expand")
            self.treeView.expand(sibling)

    # 递归搜索
    def treeViewSearch(self, text: str, index: QModelIndex):
        slibing1 = index.sibling(index.row(), 1)
        slibing2 = index.sibling(index.row(), 2)
        node1 = self.treeView.model().itemFromIndex(index)
        node2 = self.treeView.model().itemFromIndex(slibing1)
        node3 = self.treeView.model().itemFromIndex(slibing2)
        if node1 and text in node1.text().upper() or node2 and text in node2.text().upper() or node3 and text in node3.text().upper():
            return True
        for i in range(self.treeView.model().rowCount(index)):
            if self.treeViewSearch(text, self.treeView.model().index(i, 0, index)):
                return True
        return False

    def _slotSearchButtonClicked(self):
        searchText = self.searchLine.text().upper()
        if searchText:
            flag = False
            model: QStandardItemModel = self.treeView.model()
            for i in range(model.rowCount()):
                if self.treeViewSearch(searchText, model.index(i, 0)):
                    self.treeView.setRowHidden(i, self.treeView.rootIndex(), False)
                else:
                    flag = True
                    self.treeView.setRowHidden(i, self.treeView.rootIndex(), True)
            if flag:
                self.allButton.show()
                self.allButton.setProperty("show", True)

    def _slotAllButtonClicked(self):
        model: QStandardItemModel = self.treeView.model()
        for i in range(model.rowCount()):
            self.treeView.setRowHidden(i, self.treeView.rootIndex(), False)
        self.allButton.hide()
        self.allButton.setProperty("show", False)

    def closeEvent(self, event) -> None:
        self.closed.emit()

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        # ctrl + F 打开搜索框
        if a0.key() == Qt.Key_F and a0.modifiers() == Qt.ControlModifier:
            if self.searchLine.isHidden():
                self.searchLine.show()
                self.searchButton.show()
                self.searchLine.setFocus()
                if self.allButton.property("show"):
                    self.allButton.show()
            else:
                self.searchLine.hide()
                self.searchButton.hide()
                self.allButton.hide()
        elif a0.key() == Qt.Key_Return:
            if self.searchLine.isVisible() and self.searchLine.text():
                self._slotSearchButtonClicked()

    def updateModel(self):
        self.createModelThread.start()