import re
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QDateTime, QPoint, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QCursor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtChart import QChartView, QChart, QScatterSeries, QDateTimeAxis


class LoadDataTread(QThread):
    def __init__(self, readThred, parent=None):
        super(LoadDataTread, self).__init__(parent)
        self.readThread = readThred
        self.data = {}
        # self.oriData = []

    def run(self) -> None:
        regex = re.compile("\[.+?\]")
        if not self.readThread:
            return
        for line in self.readThread.reader.lines:
            if not "[NP][d] [ApList]" in line:
                continue
            temp = regex.findall(line)
            # self.oriData.append(line)
            dateTime = QDateTime.fromString(temp[0], "[yyMMdd hhmmss.zzz]").addYears(100).toMSecsSinceEpoch()
            temp = temp[-1][1:-1].split("|")
            index = 0
            while index < len(temp):
                if temp[index] in self.data.keys():
                    self.data[temp[index]].append((dateTime, int(temp[index + 1])))
                else:
                    self.data[temp[index]] = [(dateTime, int(temp[index + 1]))]
                index += 2


class MyChart(QChart):
    def __init__(self):
        super(MyChart, self).__init__()
        # 动画在拖动时会卡顿
        # self.setAnimationOptions(QChart.SeriesAnimations)
        self.valueLabel = QLabel()
        self.valueLabel.setWindowFlags(Qt.ToolTip)
        self.leftButtonPressed = False
        self.pressPos = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.leftButtonPressed = True
            self.pressPos = event.pos()

    def mouseMoveEvent(self, event) -> None:
        if self.leftButtonPressed:
            deltaPos = event.pos() - self.pressPos
            self.scroll(-deltaPos.x(), deltaPos.y())
            self.pressPos = event.pos()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.leftButtonPressed = False

    def wheelEvent(self, event) -> None:
        v = 1.2 if event.delta() > 0 else 0.8
        area:QRectF = self.plotArea()
        centerPoint:QPointF = area.center()
        area.setWidth(area.width()*v)
        area.setHeight(area.height()*v)
        newCenterPoint = QPointF(2*centerPoint-event.pos()-(centerPoint-event.pos())/v)
        area.moveCenter(newCenterPoint)
        self.zoomIn(area)

    def updateSeries(self, data: dict):
        self.removeAllSeries()
        dateAxisX = QDateTimeAxis(self)
        dateAxisX.setFormat("hh:mm:ss")
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

    def _slotHovered(self, point: QPoint, state: bool):
        if state:
            t = datetime.fromtimestamp(point.x()/1000).strftime('%H:%M:%S.%f')[:-3]
            self.valueLabel.setText(f"{t}  {point.y()}")
            p = QCursor.pos()
            self.valueLabel.move(p.x() - (self.valueLabel.width() / 2), p.y() - (self.valueLabel.height() * 1.5))
            self.valueLabel.show()
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
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.chartView)

    def closeEvent(self, event) -> None:
        self.closed.emit()

    def loadData(self):
        self.load = LoadDataTread(self.readThread)
        self.load.finished.connect(lambda: self.chart.updateSeries(self.load.data))
        self.load.start()