import re
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QDateTime, QPointF, QRect
from PyQt5.QtGui import QPainter, QColor, QCursor, QResizeEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QCheckBox, \
    QTextBrowser, QSplitter
from PyQt5.QtChart import QChartView, QChart, QScatterSeries, QDateTimeAxis, QLineSeries


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
        self.isLineEnabled = False

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
            scatterSeries.append(v)
            if self.isLineEnabled:
                lineSeries = QLineSeries(self)
                lineSeries.setName(k)
                lineSeries.append(v)
                self.addSeries(lineSeries)
                scatterSeries.setColor(lineSeries.color())
            self.addSeries(scatterSeries)
        if self.isLineEnabled:
            # 把折线图例隐藏
            for i, marker in enumerate(self.legend().markers()):
                if not i % 2:
                    marker.setVisible(False)
        self.createDefaultAxes()
        self.setAxisX(dateAxisX, scatterSeries)
        self.axisX(scatterSeries).setTitleText("时间")
        self.axisY(scatterSeries).setTitleText("信号强度(dBm)")

    def _slotHovered(self, point, state: bool):
        if state:
            currentSeries = self.sender()
            for s in self.series():
                if s.name() != currentSeries.name():
                    s.hide()
            t = datetime.fromtimestamp(point.x() / 1000).strftime('%H:%M:%S.%f')[:-3]
            self.valueLabel.setText(f"{t}  {point.y()}")
            p = QCursor.pos()
            self.valueLabel.move(p.x() - (self.valueLabel.width() / 2), p.y() - (self.valueLabel.height() * 1.5))
            self.valueLabel.show()
            self.dataHovered.emit(point.x())
        else:
            [s.show() for s in self.series()]
            if self.isLineEnabled:
                # 把折线图例隐藏
                for i, marker in enumerate(self.legend().markers()):
                    if not i % 2:
                        marker.setVisible(False)
            self.valueLabel.hide()


class ApListWidget(QWidget):

    def __init__(self, readThread, parent=None):
        super(ApListWidget, self).__init__(parent)
        self.readThread = readThread
        self.chart = MyChart()
        self.chartView = QChartView(self.chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)
        self.logLineLabel = QTextBrowser()
        self.logLineLabel.setMinimumHeight(20)
        self.logLineLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.lineCheckBox = QCheckBox("折线")
        self.resetButton = QPushButton("Reset")
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.logLineLabel)
        hBoxLayout.addWidget(self.lineCheckBox)
        hBoxLayout.addWidget(self.resetButton)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.chartView)
        self.layout().addLayout(hBoxLayout)

        self.resetButton.clicked.connect(self.updateSeries)
        self.chart.dataHovered.connect(lambda v: self.logLineLabel.setText(self.readThread.oriData[v]))
        self.lineCheckBox.clicked.connect(self._slotLineCheckBoxClicked)

    def updateSeries(self):
        # 通过记录坐标轴数据恢复有时会有Bug数据正确但是显示不正确,改为重绘
        if self.readThread and self.readThread.isFinished():
            self.chart.updateSeries(self.readThread.chartPointData)

    def _slotLineCheckBoxClicked(self,checked:bool):
        self.chart.isLineEnabled = checked
        self.updateSeries()