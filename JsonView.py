# 2017 by Gregor Engberding , MIT License

import sys

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QAbstractListModel, QMimeData, \
    QDataStream, QByteArray, QJsonDocument, QVariant, QJsonValue, QJsonParseError, \
        pyqtSignal
from PyQt5.QtWidgets import QApplication, QFileDialog, QTreeView
import json
class QJsonTreeItem(object):
    def __init__(self, parent=None):

        self.mParent = parent
        self.mChilds = []
        self.mValue =None

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
       self. mValue = value

    def key(self):
        return self.mKey

    def value(self):
        return self.mValue

    def load(self, value, parent=None):

        rootItem = QJsonTreeItem(parent)
        rootItem.setKey("root")

        try:
            value = value.toVariant()
        except AttributeError:
            pass

        try:
            value = value.toObject()
        except AttributeError:
            pass

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

        with open(fileName,"rb",) as file:
            if file is None:
                return False
            self.loadJson(file.read())

    def loadJson(self, json):
        error = QJsonParseError()
        self.mDocument = QJsonDocument.fromJson(json,error)

        if self.mDocument is not None:
            self.beginResetModel()
            if self.mDocument.isArray():
                self.mRootItem.load( list( self.mDocument.array()))
            else:
                self.mRootItem = self.mRootItem.load( self.mDocument.object())
            self.endResetModel()

            return True

        print("QJsonModel: error loading Json")
        return False

    def data(self, index: QModelIndex, role: int = ...):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()
        col = index.column()

        if role == Qt.DisplayRole:
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

class JsonView(QTreeView):
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent =None):
        super().__init__(parent)
        self.model = QJsonModel()
        self.setModel(self.model)  
        self.resize(520, 435)
        self.setWindowTitle("AGV Status")
    def loadJson(self, bytes_json):
        self.model.loadJson(bytes_json)
    def loadJsonFile(self, fileName):
        self.model.load(fileName)
    def closeEvent(self, event):
        self.hide()
        self.hiddened.emit(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    view = JsonView()

    view.loadJsonFile("test_version.json")
    view.show()
    sys.exit(app.exec_())