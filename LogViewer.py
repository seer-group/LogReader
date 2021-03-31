from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPlainTextEdit, QVBoxLayout
from PyQt5 import QtGui, QtCore,QtWidgets
import gzip

class LogViewer(QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super().__init__()
        self.lines = []
        self.title = "LogViewer"
        self.InitWindow()

    def InitWindow(self):
        self.setWindowTitle(self.title)
        vbox = QVBoxLayout()
        self.plainText = QPlainTextEdit()
        self.plainText.setPlaceholderText("This is LogViewer")
        self.plainText.setReadOnly(True)
        self.plainText.setUndoRedoEnabled(False)
        self.plainText.setCenterOnScroll(True)
        self.plainText.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.plainText.setBackgroundVisible(False)
        vbox.addWidget(self.plainText)
        self.setLayout(vbox)
    def setText(self, lines):
        self.plainText.setPlainText(''.join(lines))     
    def setLineNum(self, ln):
        cursor = QtGui.QTextCursor(self.plainText.document().findBlockByLineNumber(ln))
        # print(self.plainText.document().findBlockByLineNumber(ln).text(), "\n", self.plainText.document().blockCount())
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
                    print(file, "Skipped due to decoding failure!", " ", line)
                    continue
            self.lines.append(line)        

if __name__ == "__main__":
    import sys
    import os
    app = QApplication(sys.argv)
    view = LogViewer()
    filenames = ["14.log","15.log","16.log","17.log","18.log"]
    view.readFilies(filenames)
    view.show()
    app.exec_()

