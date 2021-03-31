from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout
from PyQt5 import QtGui, QtCore,QtWidgets
import gzip

class LogViewer(QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super().__init__()
        self.lines = []
        self.title = "LogViewer"
        self.InitWindow()
        self.resize(600,800)

    def InitWindow(self):
        self.setWindowTitle(self.title)
        vbox = QVBoxLayout()
        self.plainText = QPlainTextEdit()
        self.plainText.setPlaceholderText("This is LogViewer")
        self.plainText.setReadOnly(True)
        self.plainText.setUndoRedoEnabled(False)
        self.plainText.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.plainText.setBackgroundVisible(True)
        self.plainText.ensureCursorVisible()
        
        hbox = QHBoxLayout()
        self.find_edit = QtWidgets.QLineEdit()
        self.find_up = QtWidgets.QPushButton("Up")
        self.find_up.clicked.connect(self.findUp)
        self.find_down = QtWidgets.QPushButton("Down")
        self.find_down.clicked.connect(self.findDown)
        hbox.addWidget(self.find_edit)
        hbox.addWidget(self.find_up)
        hbox.addWidget(self.find_down)
        vbox.addWidget(self.plainText)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.find_cursor = None
        self.find_set_cursor = None
        self.highlightFormat = QtGui.QTextCharFormat()
        self.highlightFormat.setForeground(QtGui.QColor("red"))
        self.plainText.cursorPositionChanged.connect(self.cursorChanged)
        self.last_cursor = None
    def setText(self, lines):
        self.plainText.setPlainText(''.join(lines))     
    def setLineNum(self, ln):
        cursor = QtGui.QTextCursor(self.plainText.document().findBlockByLineNumber(ln))
        self.plainText.setTextCursor(cursor)
    def closeEvent(self,event):
        self.hide()
        self.hiddened.emit(True)    
    def readFilies(self,files):
        for file in files:
            if os.path.exists(file):
                if file.endswith(".log"):
                    with open(file,'rb') as f:
                        self.readData(f,file)
                else:
                    with gzip.open(file,'rb') as f:
                        self.readData(f, file) 
        self.setText(self.lines)  
        
    def readData(self, f, file):
        for line in f.readlines(): 
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    line = line.decode('gbk')
                except UnicodeDecodeError:
                    print("{} {}:{}".format(file,"Skipped due to decoding failure!", line))
                    continue
            self.lines.append(line)        

    def findUp(self):
        searchStr = self.find_edit.text()
        if searchStr is not "":
            doc = self.plainText.document()
            cur_highlightCursor = self.plainText.textCursor()
            if self.find_cursor:
                if self.find_set_cursor and \
                    self.find_set_cursor.position() == cur_highlightCursor.position():
                    cur_highlightCursor = QtGui.QTextCursor(self.find_cursor)
                    cur_highlightCursor.setPosition(cur_highlightCursor.anchor())                   
                
            cur_highlightCursor = doc.find(searchStr, cur_highlightCursor, QtGui.QTextDocument.FindBackward)
            if cur_highlightCursor.position() >= 0:
                if self.find_cursor:
                    fmt = QtGui.QTextCharFormat()
                    self.find_cursor.setCharFormat(fmt)
                cur_highlightCursor.movePosition(QtGui.QTextCursor.NoMove,QtGui.QTextCursor.KeepAnchor)
                cur_highlightCursor.mergeCharFormat(self.highlightFormat)
                self.find_cursor = QtGui.QTextCursor(cur_highlightCursor)
                cur_highlightCursor.setPosition(cur_highlightCursor.anchor())
                self.find_set_cursor = cur_highlightCursor
                self.plainText.setTextCursor(cur_highlightCursor)

    def findDown(self):
        searchStr = self.find_edit.text()
        if searchStr is not "":
            doc = self.plainText.document()
            cur_highlightCursor = self.plainText.textCursor()
            if self.find_cursor:
                if self.find_set_cursor and \
                    cur_highlightCursor.position() == self.find_set_cursor.position():
                    cur_highlightCursor = QtGui.QTextCursor(self.find_cursor)
                    cur_highlightCursor.clearSelection()

            cur_highlightCursor = doc.find(searchStr, cur_highlightCursor)
            if cur_highlightCursor.position()>=0:
                if self.find_cursor:
                    fmt = QtGui.QTextCharFormat()
                    self.find_cursor.setCharFormat(fmt)
                cur_highlightCursor.movePosition(QtGui.QTextCursor.NoMove,QtGui.QTextCursor.KeepAnchor)
                cur_highlightCursor.setCharFormat(self.highlightFormat)
                self.find_cursor = QtGui.QTextCursor(cur_highlightCursor)
                cur_highlightCursor.clearSelection()
                self.find_set_cursor = cur_highlightCursor
                self.plainText.setTextCursor(cur_highlightCursor)
                
    def cursorChanged(self):

        fmt= QtGui.QTextBlockFormat()
        fmt.setBackground(QtGui.QColor("light blue"))
        cur_cursor = self.plainText.textCursor()
        cur_cursor.select(QtGui.QTextCursor.LineUnderCursor)
        cur_cursor.setBlockFormat(fmt)
        if self.last_cursor:
            if cur_cursor.blockNumber() != self.last_cursor.blockNumber():
                fmt = QtGui.QTextBlockFormat()
                self.last_cursor.select(QtGui.QTextCursor.LineUnderCursor)
                self.last_cursor.setBlockFormat(fmt)          
        self.last_cursor = self.plainText.textCursor()

if __name__ == "__main__":
    import sys
    import os
    app = QApplication(sys.argv)
    view = LogViewer()
    filenames = ["14.log"]
    view.readFilies(filenames)
    view.show()
    app.exec_()

