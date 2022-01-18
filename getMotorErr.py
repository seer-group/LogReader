import MotorRead as mr
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout
from PyQt5 import QtGui, QtCore,QtWidgets
import re,json
from loglibPlus import rbktimetodate

class MotorErrViewer(QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    moveHereSignal = QtCore.pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super().__init__()
        self.lines = []
        self.title = "MotorErr"
        self.InitWindow()
        self.resize(1200,800)
        self.moveHere_flag = False
        self.report_path = ""
        self.mode_path = ""

    def InitWindow(self):
        self.setWindowTitle(self.title)
        vbox = QVBoxLayout()
        self.plainText = QPlainTextEdit()
        self.plainText.setPlaceholderText("This is MotorErr")
        self.plainText.setReadOnly(True)
        self.plainText.setUndoRedoEnabled(False)
        self.plainText.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.plainText.setBackgroundVisible(True)
        self.plainText.ensureCursorVisible()
        self.plainText.contextMenuEvent = self.contextMenuEvent
        
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
        self.cursor_finish = False

    def setModelPath(self, path):
        self.mode_path = path
    
    def setReportPath(self, path):
        self.report_path = path

    def clearPlainText(self):
        self.plainText.appendPlainText("")
    
    def listMotorErr(self):
        if self.mode_path != "" and self.report_path != "":
            reg = re.compile("(.[a-zA-Z0-9]*-0x[a-zA-Z0-9]*)")
            model_m_b_dict = mr.getMotorNameBrandDict(self.mode_path)
            fid = open(self.report_path,"rb")
            for line in fid.readlines(): 
                    try:
                        line = line.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            line = line.decode('gbk')
                        except UnicodeDecodeError:
                            line = ""
                    if "52135|Motor Error:" in line and "|0]" not in line:
                            self.plainText.appendPlainText(line.replace('\n', '').replace('\r', ''))
                            motor_code_str = reg.findall(line)
                            cnt = 1
                            for pair in motor_code_str:
                                motor_code_list = re.split("\W", pair)
                                motor_name = motor_code_list[1]
                                motor_code = motor_code_list[2]
                                motor_code2num = int(motor_code, 16)
                                motor_brand = model_m_b_dict[motor_name]
                                index = str(cnt) + "名字:"
                                cnt = cnt + 1
                                self.plainText.appendPlainText("电机"+index+motor_name+" 品牌:"+motor_brand+" 错误码:"+motor_code)
                                with open("ErrTab.json", "r", encoding='utf-8') as f:
                                    err_tab = json.loads(f.read())
                                    all_err_in_brand = err_tab[motor_brand]
                                    cnt2 = 1
                                    if all_err_in_brand["match_bit"]:
                                        for key, err_info in all_err_in_brand.items():
                                            if key != "match_bit":
                                                key2num = int(key, 16)
                                                if key2num & motor_code2num:
                                                    index2 = "对应错误"+str(cnt2)+":"
                                                    cnt2 = cnt2 + 1
                                                    self.plainText.appendPlainText("    "+index2+ key + " ")
                                                    self.plainText.appendPlainText("        错误描述:" + err_info["des"])
                                                    self.plainText.appendPlainText("        错误原因:" + err_info["reason"])
                                                    self.plainText.appendPlainText("        解决方法:" + err_info["method"])
                                    else:
                                        for key, err_info in all_err_in_brand.items():
                                            if key != "match_bit":
                                                key2num = int(key, 16)
                                                if key2num == motor_code2num:
                                                    index2 = "对应错误"+str(cnt2)+":"
                                                    cnt2 = cnt2 + 1
                                                    self.plainText.appendPlainText("    "+index2+ key + " ")
                                                    self.plainText.appendPlainText("        错误描述:" + err_info["des"])
                                                    self.plainText.appendPlainText("        错误原因:" + err_info["reason"])
                                                    self.plainText.appendPlainText("        解决方法:" + err_info["method"])
                                f.close()
                                self.plainText.appendPlainText("")
            fid.close()
            self.cursor_finish = True
        else:
            self.plainText.setPlainText(''.join("The model should be add!"))
                
    def setLineNum(self, ln):
        if not self.moveHere_flag:
            cursor = QtGui.QTextCursor(self.plainText.document().findBlockByLineNumber(ln))
            self.plainText.setTextCursor(cursor)
        else:
            self.moveHere_flag = False

    def closeEvent(self,event):
        self.plainText.appendPlainText("")
        self.hide()
        self.hiddened.emit(True)    
    
    def contextMenuEvent(self, event):
        popMenu = self.plainText.createStandardContextMenu()
        popMenu.addAction('&Move Here',self.moveHere)
        cursor = QtGui.QCursor()
        popMenu.exec_(cursor.pos()) 

    def moveHere(self):
        cur_cursor = self.plainText.textCursor()
        cur_cursor.select(QtGui.QTextCursor.LineUnderCursor)
        line = cur_cursor.selectedText()
        regex = re.compile("\[(.*?)\].*")
        out = regex.match(line)
        if out:
            self.moveHere_flag = True
            mtime = rbktimetodate(out.group(1))
            self.moveHereSignal.emit(mtime)  

    def findUp(self):
        searchStr = self.find_edit.text()
        if searchStr != "":
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
        if searchStr != "":
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
        if self.cursor_finish:
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
    view = MotorErrViewer()
    filenames = ["test1.log"]
    view.readFilies(filenames)
    view.show()
    app.exec_()

