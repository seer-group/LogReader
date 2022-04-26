import datetime
import re
from PyQt5.QtChart import QPieSeries, QPieSlice, QChartView, QChart
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QCheckBox, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QCloseEvent, QBrush, QColor, QFont


class LoadDataTread(QThread):
    readReady = pyqtSignal()

    def __init__(self, readThred, parent=None):
        super(LoadDataTread, self).__init__(parent)
        self.readThread = readThred
        self.generalData = []
        self.detailedData = []
        self.oriData = []

    def run(self) -> None:
        self.generalData = []
        self.detailedData = []
        self.oriData = []
        if not self.readThread:
            return
        for line in self.readThread.reader.lines:
            if not "[CPU][d] [ProbeCpu]" in line:
                continue
            self.oriData.append(line)
            temp = re.split(r"\[|\]", line)
            dateTime = datetime.datetime.strptime(temp[1], '%y%m%d %H%M%S.%f')
            temp = temp[-2].split("|")
            name = ["System", "free", "rbkProc"]
            num = ["", "", ""]
            ratio = [float(temp[0]), 100 - float(temp[0]) - float(temp[1]), float(temp[1])]
            self.generalData.append([dateTime, name, num, ratio])
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
            ratio.append(self.generalData[-1][-1][-1] - sum(ratio[2:]))
            self.detailedData.append([dateTime, name, num, ratio])
        self.readReady.emit()


class MyChart(QChart):
    def __init__(self):
        super(MyChart, self).__init__()
        self.legend().setAlignment(Qt.AlignRight)
        self.legend().setBackgroundVisible(True)
        self.legend().setBrush(QBrush(QColor(128, 128, 128, 128)))
        self.innerSliceLabelVisible = True
        self.outerSliceLabelVisible = True
        self.innerSliceLabelPosition = QPieSlice.LabelInsideNormal
        self.outerSliceLabelPosition = QPieSlice.LabelOutside

    def _slotPieSeriesHovered(self, slice: QPieSlice, state: bool):
        currentSeries: QPieSeries = slice.parent()
        if state:
            [s.setVisible(False) for s in self.series() if s != currentSeries]
            [s.setLabelVisible(False) for s in currentSeries.slices() if s != slice]
            slice.setExplodeDistanceFactor(0.03)
            slice.setExploded(state)
        else:
            [s.setVisible(True) for s in self.series()]
            if (currentSeries.holeSize() and self.outerSliceLabelVisible) or \
                    (not currentSeries.holeSize() and self.innerSliceLabelVisible):
                [s.setLabelVisible(True) for s in currentSeries.slices()]
            slice.setExploded(state)

    def updateSeries(self, d1, d2):
        self.removeAllSeries()
        pieSeries1 = QPieSeries()
        pieSeries2 = QPieSeries()
        pieSeries1.setPieSize(0.75)
        pieSeries1.setHoleSize(0.6)
        pieSeries2.setPieSize(0.6)
        for l, v in d1:
            temp = QPieSlice("%s:%.2f%%" % (l, v), v)
            temp.setBorderColor(Qt.gray)
            temp.setBorderWidth(2)
            if self.outerSliceLabelVisible and v:
                temp.setLabelVisible()
                temp.setLabelPosition(self.outerSliceLabelPosition)
            pieSeries1.append(temp)
        for l, v in d2:
            temp = QPieSlice("%s:%.2f%%" % (l, v), v)
            temp.setBorderColor(Qt.gray)
            temp.setBorderWidth(2)
            if self.innerSliceLabelVisible and v:
                temp.setLabelVisible()
                temp.setLabelPosition(self.innerSliceLabelPosition)
                temp.setLabelColor(Qt.white)
            pieSeries2.append(temp)
        self.addSeries(pieSeries1)
        self.addSeries(pieSeries2)

        pieSeries1.hovered.connect(self._slotPieSeriesHovered)
        pieSeries2.hovered.connect(self._slotPieSeriesHovered)


class CPUPieView(QWidget):
    closed = pyqtSignal()

    def __init__(self, readThread, parent=None):
        super(CPUPieView, self).__init__(parent)
        self.readThread = readThread
        self.setWindowTitle("CPU pie view")
        self.setLayout(QVBoxLayout())
        self.chart = MyChart()
        self.chartView = QChartView(self)
        self.chartView.setChart(self.chart)
        self.slider = QSlider(Qt.Horizontal, self)
        self.label = QLabel()
        self.label.setFixedHeight(15)
        self.legendCheckBox = QCheckBox("Legend")
        self.legendCheckBox.setChecked(True)
        self.innerLabelCheckBox = QCheckBox("Inner Slice label")
        self.innerLabelCheckBox.setChecked(True)
        self.outerLabelCheckBox = QCheckBox("Outer Slice label")
        self.outerLabelCheckBox.setChecked(True)
        hLayout = QHBoxLayout(self)
        hLayout.addWidget(self.label)
        hLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        hLayout.addWidget(self.legendCheckBox)
        hLayout.addWidget(self.innerLabelCheckBox)
        hLayout.addWidget(self.outerLabelCheckBox)
        self.layout().addWidget(self.chartView)
        self.layout().addLayout(hLayout)
        self.layout().addWidget(self.slider)
        self.load = None
        self.slider.setDisabled(True)

        self.slider.valueChanged.connect(self.updateChart)
        self.legendCheckBox.clicked.connect(self.chart.legend().setVisible)
        self.innerLabelCheckBox.clicked.connect(self._slotInnerLabelCheckBoxClicked)
        self.outerLabelCheckBox.clicked.connect(self._slotOuterLabelCheckBoxClicked)

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.closed.emit()

    def _slotInnerLabelCheckBoxClicked(self, v):
        self.chart.innerSliceLabelVisible = v
        self.updateChart(self.slider.value())

    def _slotOuterLabelCheckBoxClicked(self, v):
        self.chart.outerSliceLabelVisible = v
        self.updateChart(self.slider.value())

    def loadData(self):
        def _slotReadReady():
            if self.load.oriData:
                self.slider.setMinimum(0)
                self.slider.setMaximum(len(self.load.generalData) - 1)
                self.slider.setDisabled(False)
                self.slider.setValue(0)
                self.updateChart(0)
            else:
                self.removeSeries()
                self.slider.setDisabled(True)

        self.load = LoadDataTread(self.readThread)
        self.load.readReady.connect(_slotReadReady)
        self.load.start()

    def removeSeries(self):
        self.chart.removeAllSeries()

    def updateChart(self, index):
        d1 = zip(self.load.detailedData[index][1], self.load.detailedData[index][-1])
        d2 = zip(self.load.generalData[index][1], self.load.generalData[index][-1])
        self.chart.updateSeries(d1, d2)

        self.label.setText(f"time: {self.load.generalData[index][0]}\t{index + 1}/{len(self.load.generalData)}")
        self.label.setToolTip(self.load.oriData[index])
