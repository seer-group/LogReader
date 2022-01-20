import sys
from PyQt5 import QtCore, QtWidgets,QtGui

class Win(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(200, 200, 400, 400)
        self.setWindowTitle('选择绘制目标：')
        self.setWindowIcon(QtGui.QIcon('rbk.ico'))

        self.btn1 = QtWidgets.QPushButton(self)
        self.btn1.setText('绘制GoodPos轨迹')
        self.btn1.clicked.connect(self.show1)
        self.btn2 = QtWidgets.QPushButton(self)
        self.btn2.setText('绘制xxx轨迹')
        self.btn2.clicked.connect(self.show2)
        self.btn3 = QtWidgets.QPushButton(self)
        self.btn3.setText('绘制xxx轨迹')
        self.btn3.clicked.connect(self.show3)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.btn1)
        layout.addWidget(self.btn2)
        layout.addWidget(self.btn3)
        self.setLayout(layout)

    def show1(self):
        reply = QtWidgets.QMessageBox.information(self,"请确认：","是否绘制？",QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,QtWidgets.QMessageBox.Yes)
        print(1)
    def show2(self):
        reply = QtWidgets.QMessageBox.information(self,"请确认：","是否绘制？",QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,QtWidgets.QMessageBox.Yes)
        print(2)
    def show3(self):
        reply = QtWidgets.QMessageBox.information(self,"请确认：","是否绘制？",QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,QtWidgets.QMessageBox.Yes)
        print(3)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = Win()
    form.show()
    sys.exit(app.exec_())
