import sys
import re
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib import legend
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout,QHBoxLayout, QSlider, QLabel, QCheckBox
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QCloseEvent

class LoadDataTread(QThread):
    readReady = pyqtSignal()
    def __init__(self, readThred, parent=None):
        super(LoadDataTread, self).__init__(parent)
        self.readThread = readThred
        self.outerData = []
        self.innerData = []
        self.oriData = []
    def run(self) -> None:
        self.outerData = []
        self.innerData = []
        self.oriData = []
        if not self.readThread:
            return
        for line in self.readThread.reader.lines:
            if not "[CPU][d] [ProbeCpu]" in line:
                continue
            self.oriData.append(line)
            temp = re.split(r"\[|\]", line)
            timeStr = temp[1]
            temp = temp[-2].split("|")
            name = ["System", "free", "rbkProc"]
            num = ["", "", ""]
            ratio = [float(temp[0]), 100 - float(temp[0]) - float(temp[1]), float(temp[1])]
            self.outerData.append([timeStr, name, num, ratio])
            name = ["System", "free"]
            num = ["", ""]
            ratio = [float(temp[0]), 100 - float(temp[0]) - float(temp[1])]
            index = 0
            temp = temp[2:]
            while index < len(temp):
                name.append(temp[index])
                num.append(temp[index + 1])
                ratio.append(float(temp[index + 2]))
                index += 3
            name.append("other")
            num.append("")
            ratio.append(self.outerData[-1][-1][-1] - sum(ratio[2:]))
            self.innerData.append([timeStr, name, num, ratio])
        self.readReady.emit()

class CPUPieView(QWidget):
    closed = pyqtSignal()
    def __init__(self,readThread, parent=None):
        super(CPUPieView, self).__init__(parent)
        self.readThread = readThread
        self.setWindowTitle("CPU pie view")
        self.setLayout(QVBoxLayout())
        self.canvas = FigureCanvasQTAgg(Figure())
        self.ax1 = self.canvas.figure.add_subplot(111)
        self.outerHandles = None
        self.innerHandles = None
        self.outerLegend = None
        self.innerLegend = None
        self.ax1.axis("off")
        self.slider = QSlider(Qt.Horizontal, self)
        self.label = QLabel()
        self.label.setFixedHeight(15)
        self.legendCheckBox = QCheckBox("Show Legend")
        self.legendCheckBox.setChecked(True)
        hLayout = QHBoxLayout(self)
        hLayout.addWidget(self.label)
        hLayout.addWidget(self.legendCheckBox)
        self.layout().addWidget(self.canvas)
        self.layout().addLayout(hLayout)
        self.layout().addWidget(self.slider)
        self.load = None
        self.slider.setDisabled(True)

        self.slider.valueChanged.connect(self._slotSliderValueChanged)
        self.legendCheckBox.clicked.connect(self._slotLegendCheckBoxClicked)

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.closed.emit()

    def _slotLegendCheckBoxClicked(self,v):
        if v:
            self._showLegend(self.slider.value())
        else:
            try:
                self.outerLegend.remove()
                self.innerLegend.remove()
            except:
                pass
        self.canvas.draw()
    def _slotSliderValueChanged(self,i):
        self.updateCanvas(i)

    def loadData(self):
        def _slotReadReady():
            self.slider.setMinimum(0)
            self.slider.setMaximum(len(self.load.outerData) - 1)
            self.slider.setDisabled(False)
            self.updateCanvas(0)
        self.load = LoadDataTread(self.readThread)
        self.load.readReady.connect(_slotReadReady)
        self.load.start()

    def updateCanvas(self, index):
        self.ax1.cla()
        try:
            self.outerLegend.remove()
            self.innerLegend.remove()
        except:
            pass
        self.label.setText(f"time:{self.load.outerData[index][0]}\t{index+1}/{len(self.load.outerData)}")
        self.label.setToolTip(self.load.oriData[index])
        self.outerHandles, _, _ = self.ax1.pie(self.load.outerData[index][-1], radius=1.3, autopct='%1.2f%%', pctdistance=1.2, wedgeprops=dict(width=0.3, edgecolor="#FFFFFF"), startangle=90)
        self.innerHandles, _, _ = self.ax1.pie(self.load.innerData[index][-1], radius=1, autopct='%1.2f%%', pctdistance=0.9, wedgeprops=dict(edgecolor="#FFFFFF"), startangle=90)
        if self.legendCheckBox.isChecked():
            self._showLegend(index)
        self.canvas.draw()
        self.canvas.flush_events()
        # ax.axis('equal')

    def _showLegend(self, index):
        outerLabels = [f"{self.load.outerData[index][1][i]}: {self.load.outerData[index][-1][i]}" for i in range(len(self.load.outerData[index][1]))]
        innerLabels = [f"{self.load.innerData[index][1][i]}: {self.load.innerData[index][-1][i]}" for i in range(len(self.load.innerData[index][1]))]
        self.outerLegend = self.canvas.figure.legend(handles=self.outerHandles, title="Outer", labels=outerLabels, loc="upper left")
        n = round(len(self.load.innerData[index][1])/40)+1
        self.innerLegend = self.canvas.figure.legend(handles=self.innerHandles, title="Inner", labels=innerLabels, ncol=n, loc="center right")
        self.outerLegend.set_draggable(state=True)
        self.innerLegend.set_draggable(state=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    c =CPUPieView(None)
    c.show()
    app.exec()
