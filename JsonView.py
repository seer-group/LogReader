# 2017 by Gregor Engberding , MIT License

import sys

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt , QItemSelectionModel, \
    QDataStream, QByteArray, QJsonDocument, QVariant, QJsonValue, QJsonParseError, \
        pyqtSignal 
from PyQt5.QtWidgets import QApplication, QTreeView, QStyledItemDelegate, QAbstractItemView
import json
from PyQt5 import QtCore, QtWidgets,QtGui
from ExtendedComboBox import ExtendedComboBox

class SelectOnlyDelegate(QStyledItemDelegate):
    def __init__(self, parent) -> None:
        super().__init__(parent)
    def createEditor(self, parent, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex):
        editor = super().createEditor(parent, option, index)
        editor.setReadOnly(True)
        return editor

class QJsonTreeItem(object):
    def __init__(self, parent=None):

        self.mParent = parent
        self.mChilds = []
        self.mValue = None
        self.mKey = None

    def appendChild(self, item):
        self.mChilds.append(item)

    def child(self, row:int):
        return self.mChilds[row]

    def parent(self):
        return self.mParent

    def childCount(self):
        return len(self.mChilds)

    def row(self):
        if self.mParent is not None:
            return self.mParent.mChilds.index(self)
        return 0

    def setKey(self, key:str):
        self.mKey = key

    def setValue(self, value:str):
       self.mValue = value

    def key(self):
        return self.mKey

    def value(self):
        return self.mValue

    def load(self, value, parent=None):

        rootItem = QJsonTreeItem(parent)
        rootItem.setKey("root")

        if isinstance(value, dict):
            # process the key/value pairs
            rootItem.setValue("")
            for key in value:
                v = value[key]
                child = self.load(v, rootItem)
                child.setKey(key)
                rootItem.appendChild(child)

        elif isinstance(value, list):
            # process the values in the list
            rootItem.setValue("")
            for i, v in enumerate(value):
                child = self.load(v, rootItem)
                child.setKey(str(i))
                if child.value() == "" or child.value() == None:
                    child.setValue(str(v))
                rootItem.appendChild(child)

        else:
            # value is processed
            rootItem.setValue(value)
        return rootItem


class QJsonModel(QAbstractItemModel):
    def __init__(self, parent =None):
        super().__init__(parent)
        self.mRootItem = QJsonTreeItem()
        self.mHeaders = ["key","value"]

    def load(self,fileName):
        if fileName is None or fileName is False:
            return False
        with open(fileName, 'r',encoding= 'UTF-8') as fid:
            try:
                j = json.load(fid)
                self.loadJson(j)
            except:
                print("load json file {} error".format(fileName))

    def loadJson(self, json):
        error = QJsonParseError()
        self.mDocument = json

        if self.mDocument is not None:
            self.beginResetModel()
            if isinstance(self.mDocument, list):
                self.mRootItem.load(self.mDocument)
            else:
                self.mRootItem = self.mRootItem.load(self.mDocument)
            self.endResetModel()

            return True

        print("QJsonModel: error loading Json")
        return False

    def data(self, index: QModelIndex, role: int = ...):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()
        col = index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0:
                return str(item.key())
            elif col == 1:
                return str(item.value())

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.DisplayRole:
            return QVariant()

        if orientation == Qt.Horizontal:
            return self.mHeaders[section]

        return QVariant()

    def index(self, row: int, column: int, parent: QModelIndex = ...):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.mRootItem
        else:
            parentItem = parent.internalPointer()
        try:
            childItem = parentItem.child(row)
            return self.createIndex(row, column, childItem)
        except IndexError:
            return QModelIndex()

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.mRootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(),0, parentItem)

    def rowCount(self, parent: QModelIndex = ...):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parentItem = self.mRootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def columnCount(self, parent: QModelIndex = ...):
        return 2

    def flags(self, index: QModelIndex):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable


class JsonView(QTreeView):
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent =None):
        super().__init__(parent)
        self.model = QJsonModel()
        self.setModel(self.model)  
        self.resize(520, 435)
        self.setWindowTitle("Status")
        self.setItemDelegate(SelectOnlyDelegate(self))
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
    # TODO plot the select key
    #     self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    #     self.customContextMenuRequested.connect(self.showContextMenu)

    # def showContextMenu(self, point):
    #     ix = self.indexAt(point)
    #     if ix.column() == 1:
    #         menu = QtWidgets.QMenu()
    #         menu.addAction("Plot")
    #         action = menu.exec_(self.mapToGlobal(point))
    #         if action:
    #             if action.text() == "Plot":
    #                 self.edit(ix)

    def loadJson(self, bytes_json):
        self.model.loadJson(bytes_json)
    def loadJsonFile(self, fileName):
        self.model.load(fileName)
    def closeEvent(self, event):
        self.hide()
        self.hiddened.emit(True)


class DataSelection:
    def __init__(self):
        self.y_label = QtWidgets.QLabel('Data')
        self.y_combo = ExtendedComboBox()
        y_form = QtWidgets.QFormLayout()
        y_form.addRow(self.y_label,self.y_combo)
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addLayout(y_form)

class DataView(QtWidgets.QMainWindow):
    closeMsg = pyqtSignal('PyQt_PyObject')
    newOneMsg = pyqtSignal('PyQt_PyObject')
    dataViewMsg = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent =None):
        self.parent = parent
        super().__init__(parent)
        self.setWindowTitle("DataView")
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        self.layout = QtWidgets.QVBoxLayout(self._main)
        self.newbtn = QtWidgets.QPushButton("new",self._main)
        self.newbtn.clicked.connect(self.newOne)
        self.layout.addWidget(self.newbtn)
        self.selection = DataSelection()
        self.layout.addLayout(self.selection.vbox)
        self.jsonView = JsonView()
        self.layout.addWidget(self.jsonView)
        self.selection.y_combo.activated.connect(self.dataViewUpdate)

    def loadJson(self, data):
        self.jsonView.loadJson(data)
        self.jsonView.expandToDepth(1)

    def loadJsonFile(self, fileName):
        self.jsonView.loadJsonFile(fileName)
        self.jsonView.expandToDepth(1)    

    def setSelectionItems(self, data):
        self.selection.y_combo.addItems(data)
        first_k = self.selection.y_combo.currentText()
        if first_k != "":
            self.setWindowTitle(first_k)  

    def newOne(self):
        self.newOneMsg.emit(self)

    def dataViewUpdate(self):
        first_k = self.selection.y_combo.currentText()
        if first_k != "":
            self.setWindowTitle(first_k)
        self.dataViewMsg.emit(self)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.closeMsg.emit(self)
        return super().closeEvent(a0)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    view = DataView()
    view.loadJsonFile("log_config.json")
    view.show()
    sys.exit(app.exec_())