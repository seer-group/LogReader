import re
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QDateTime, QPoint, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QCursor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtChart import QChartView, QChart, QScatterSeries, QDateTimeAxis, QValueAxis


class LoadDataTread(QThread):
    def __init__(self, readThred, parent=None):
        super(LoadDataTread, self).__init__(parent)
        self.readThread = readThred
        self.data = {}
        self.oriData = {}

    def run(self) -> None:
        regex = re.compile("\[.+?\]")
        if not self.readThread:
            return
        for line in self.readThread.reader.lines:
            if not "[NP][d] [ApList]" in line:
                continue
            temp = regex.findall(line)
            dateTime = QDateTime.fromString(temp[0], "[yyMMdd hhmmss.zzz]").addYears(100).toMSecsSinceEpoch()
            temp = temp[-1][1:-1].split("|")
            # 这个数据有时为空
            if len(temp) < 2:
                continue
            self.oriData[dateTime] = line
            index = 0
            while index < len(temp):
                if temp[index] in self.data.keys():
                    self.data[temp[index]].append((dateTime, int(temp[index + 1])))
                else:
                    self.data[temp[index]] = [(dateTime, int(temp[index + 1]))]
                index += 2


class MyChart(QChart):
    dataHovered = pyqtSignal(object)

    def __init__(self):
        super(MyChart, self).__init__()
        # 动画在拖动时看上去卡顿
        # self.setAnimationOptions(QChart.SeriesAnimations)
        self.valueLabel = QLabel()
        self.valueLabel.setWindowFlags(Qt.ToolTip)
        self.isLBPressed = False
        self.oPos = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.isLBPressed = True
            self.oPos = event.pos()

    def mouseMoveEvent(self, event) -> None:
        if self.isLBPressed:
            deltaPos = event.pos() - self.oPos
            self.scroll(-deltaPos.x(), deltaPos.y())
            self.oPos = event.pos()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.isLBPressed = False

    def wheelEvent(self, event) -> None:
        v = 0.8 if event.delta() > 0 else 1.2
        area = self.plotArea()
        centerPoint = area.center()
        area.setWidth(area.width() * v)
        area.setHeight(area.height() * v)
        newCenterPoint = QPointF(2 * centerPoint - event.pos() - (centerPoint - event.pos()) / v)
        area.moveCenter(newCenterPoint)
        self.zoomIn(area)

    def updateSeries(self, data: dict):
        self.removeAllSeries()
        if len(data) < 1:
            return
        dateAxisX = QDateTimeAxis(self)
        dateAxisX.setFormat("dd hh:mm:ss")
        for k, v in data.items():
            scatterSeries = QScatterSeries(self)
            scatterSeries.setMarkerSize(8)
            scatterSeries.setBorderColor(QColor(0, 0, 0, 0))
            scatterSeries.setName(k)
            scatterSeries.hovered.connect(self._slotHovered)
            for point in v:
                scatterSeries.append(*point)
            self.addSeries(scatterSeries)
        self.createDefaultAxes()
        self.setAxisX(dateAxisX, scatterSeries)
        self.axisX(scatterSeries).setTitleText("时间")
        self.axisY(scatterSeries).setTitleText("信号强度(dBm)")

    def _slotHovered(self, point, state: bool):
        if state:
            t = datetime.fromtimestamp(point.x() / 1000).strftime('%H:%M:%S.%f')[:-3]
            self.valueLabel.setText(f"{t}  {point.y()}")
            p = QCursor.pos()
            self.valueLabel.move(p.x() - (self.valueLabel.width() / 2), p.y() - (self.valueLabel.height() * 1.5))
            self.valueLabel.show()
            self.dataHovered.emit(point.x())

        else:
            self.valueLabel.hide()


class ApListWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, readThread, parent=None):
        super(ApListWidget, self).__init__(parent)
        self.readThread = readThread
        self.load = None
        self.setWindowTitle("AP信号强度")
        self.chart = MyChart()
        self.chartView = QChartView(self.chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)
        self.logLineLabel = QLabel()
        self.resetButton = QPushButton("Reset")
        self.hBoxLayout = QHBoxLayout()
        self.hBoxLayout.addWidget(self.logLineLabel)
        self.hBoxLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.hBoxLayout.addWidget(self.resetButton)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.chartView)
        self.layout().addLayout(self.hBoxLayout)

        self.resetButton.clicked.connect(self.resetButtonClicked)
        self.chart.dataHovered.connect(lambda v: self.logLineLabel.setText(self.load.oriData[v]))

    def closeEvent(self, event) -> None:
        self.closed.emit()

    def loadData(self):
        self.load = LoadDataTread(self.readThread)
        self.load.finished.connect(lambda: self.chart.updateSeries(self.load.data))
        self.load.start()

    def resetButtonClicked(self):
        # 通过记录坐标轴数据恢复有时会有Bug数据正确但是显示不正确,改为重绘
        if self.load and self.load.isFinished():
            self.chart.updateSeries(self.load.data)
