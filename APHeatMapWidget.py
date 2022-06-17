import datetime
import os
import re
import json

from PyQt5.QtGui import QColor, QPainter, QPen, QWheelEvent, QTransform, QRadialGradient, QLinearGradient, QFont
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout, QGraphicsRectItem, QGraphicsItemGroup, \
    QGraphicsEllipseItem, QTabWidget, QCheckBox, QHBoxLayout, QRadioButton, QSpacerItem, QSizePolicy, QGraphicsItem, \
    QBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPointF, QRect
from ApListWidget import ApListWidget


class ReadMapThread(QThread):
    error = pyqtSignal(object)

    def __init__(self, readThread, parent=None):
        super(ReadMapThread, self).__init__(parent)
        self.readThread = readThread
        # 图表点数据
        self.chartPointData = {}
        # apList原始log
        self.oriData = {}
        # log内的地图
        self.mapFile = None
        # 图元信息
        self.graphicsItems = {}
        # 线路颜色
        self.pathPen = QPen(QColor(181, 106, 33, 200), 50)
        # 点颜色透明
        self.pointPen = QPen(QColor(0, 0, 0, 0))

    def run(self) -> None:
        self.chartPointData = {}
        self.oriData = {}
        self.graphicsItems = {}
        self._getApData()
        self._getMapData()
        self._getHeatMapData()

    def _getMapData(self):
        chassises = self.readThread.rstatus.chassis()
        js = json.loads(chassises[0][0])
        self.mapFile = js.get("CURRENT_MAP")
        if self.mapFile is None:
            self.error.emit("未获取到地图文件")
            return
        # 获取地图文件路径
        root = os.path.split(os.path.split(self.readThread.filenames[0])[0])[0]
        mapFile = os.path.join(os.path.join(root, "maps"), f"{self.mapFile}.smap")
        try:
            with open(mapFile, "rb") as mf:
                mapJS: dict = json.load(mf)
        except Exception as e:
            self.error.emit(e)
            return
        map = QGraphicsItemGroup()
        map.setData(0, "map")
        if "header" in mapJS:
            minX = mapJS["header"]["minPos"]["x"]
            minY = mapJS["header"]["minPos"]["y"]
            maxX = mapJS["header"]["maxPos"]["x"]
            maxY = mapJS["header"]["maxPos"]["y"]
            item = QGraphicsRectItem(minX * 1000, minY * 1000, maxX * 1000, maxY * 1000)
            item.setBrush(Qt.white)
            item.setPen(self.pointPen)
            map.addToGroup(item)
        if "normalPosList" in mapJS:
            i = 0
            for point in mapJS["normalPosList"]:
                # 每3个数据采样一次
                if i % 3 == 0:
                    x = point["x"] if "x" in point else 0
                    y = point["y"] if "y" in point else 0
                    item = QGraphicsRectItem(x * 1000, y * 1000, 10, 10)
                    item.setBrush(Qt.black)
                    item.setPen(self.pointPen)
                    map.addToGroup(item)
                i += 1
        if "rssiPosList" in mapJS:
            for point in mapJS["rssiPosList"]:
                x = point["x"] if "x" in point else 0
                y = point["y"] if "y" in point else 0
                item = QGraphicsRectItem(x * 1000, y * 1000, 10, 10)
                item.setBrush(Qt.red)
                item.setPen(self.pointPen)
                map.addToGroup(item)
        # if "advancedCurveList" in mapJS:
        #     for line in mapJS["advancedCurveList"]:
        #         if line["className"] == "BezierPath":
        #             sx = line["startPos"]["pos"]["x"] if "x" in line["startPos"]["pos"] else 0
        #             sy = line["startPos"]["pos"]["y"] if "y" in line["startPos"]["pos"] else 0
        #             ex = line["endPos"]["pos"]["x"] if "x" in line["endPos"]["pos"] else 0
        #             ey = line["endPos"]["pos"]["y"] if "y" in line["endPos"]["pos"] else 0
        #             cx1 = line["controlPos1"]["x"] if "x" in line["controlPos1"] else 0
        #             cy1 = line["controlPos1"]["y"] if "y" in line["controlPos1"] else 0
        #             cx2 = line["controlPos2"]["x"] if "x" in line["controlPos2"] else 0
        #             cy2 = line["controlPos2"]["y"] if "y" in line["controlPos2"] else 0
        #             path = QPainterPath()
        #             path.moveTo(sx * 1000, sy * 1000)
        #             path.cubicTo(cx1 * 1000, cy1 * 1000, cx2 * 1000, cy2 * 1000, ex * 1000, ey * 1000)
        #             item = QGraphicsPathItem(path)
        #             item.setPen(self.pathPen)
        #             map.addToGroup(item)
        #             continue
        #         if line['className'] == 'StraightPath':
        #             sx = line["startPos"]["pos"]["x"] if "x" in line["startPos"]["pos"] else 0
        #             sy = line["startPos"]["pos"]["y"] if "y" in line["startPos"]["pos"] else 0
        #             ex = line["endPos"]["pos"]["x"] if "x" in line["endPos"]["pos"] else 0
        #             ey = line["endPos"]["pos"]["y"] if "y" in line["endPos"]["pos"] else 0
        #             line = QGraphicsLineItem(sx * 1000, sy * 1000, ex * 1000, ey * 1000)
        #             line.setPen(self.pathPen)
        #             map.addToGroup(line)
        #             continue
        self.graphicsItems[self.mapFile] = map

    def _getHeatMapData(self):
        # 获取定位信息的生成器
        def getLocationEachFrame():
            locationEachFrame = self.readThread.content['LocationEachFrame']
            index = 0
            while index < len(locationEachFrame["t"]):
                yield locationEachFrame["t"][index], locationEachFrame["x"][index], locationEachFrame["y"][index]
                index += 1

        # 获取每个信号强度对应的定位信息
        for k, points in self.chartPointData.items():
            self.graphicsItems[k] = QGraphicsItemGroup()
            self.graphicsItems[k].setData(0, "heatmap")
            getLEF = getLocationEachFrame()
            for point in points:
                flag = False
                i = 0
                while True:
                    try:
                        tm, x, y = next(getLEF)
                    except StopIteration:
                        flag = True
                        break
                    if tm.timestamp() * 1000 > point.x():
                        break
                    # point.y()是信号强度dBm
                    strength = point.y()
                    # 每10个数据采样一次
                    if i % 10 == 0:
                        # 将信号强度映射到颜色
                        r, g, b = 0, 0, 0
                        if strength < -90:
                            r = 255
                        elif strength < -75:
                            r = 255
                            g = (strength + 90) / 25 * 255
                        elif strength < -50:
                            r = 255 - (strength + 75) / 25 * 255
                            g = 255
                        else:
                            g = 255
                        brushColor = QColor(r, g, b)
                        # 一个数据点的宽度2m
                        item = QGraphicsEllipseItem(x * 1000 - 500, y * 1000 - 500, 1000, 1000)
                        item.setBrush(brushColor)
                        item.setPen(self.pointPen)
                        # 根据信号强度设置层级
                        item.setZValue(strength)
                        self.graphicsItems[k].addToGroup(item)
                    i += 1
                # 如果迭代器已经结束，则跳过
                if flag:
                    break

    def _getApData(self):
        if not self.readThread:
            return
        regex = re.compile("\[.+?\]")
        for line in self.readThread.reader.lines:
            if not "[NP][d] [ApList]" in line:
                continue
            temp = regex.findall(line)
            # 日志条目时间
            tm = datetime.datetime.strptime(temp[0], '[%y%m%d %H%M%S.%f]')
            # 时间戳
            stamp = tm.timestamp() * 1000
            temp = temp[-1][1:-1].split("|")
            # 这个数据有时为空
            if len(temp) < 2:
                continue
            self.oriData[stamp] = line
            index = 0
            while index < len(temp):
                if temp[index] in self.chartPointData.keys():
                    self.chartPointData[temp[index]].append(QPointF(stamp, int(temp[index + 1])))
                else:
                    self.chartPointData[temp[index]] = [QPointF(stamp, int(temp[index + 1]))]
                index += 2


class ColorMap(QWidget):
    def __init__(self):
        super().__init__()

    def paintEvent(self, event):
        p = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, Qt.green)
        gradient.setColorAt(0.5, Qt.yellow)
        gradient.setColorAt(1, Qt.red)
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawRect(25, 0, self.width(), self.height())
        p.setPen(Qt.gray)
        p.setFont(QFont("Times", 8, QFont.Bold))
        p.drawText(0, 15, "-50")
        p.drawText(0, int(self.height()/2)+10, "-75")
        p.drawText(0, int(self.height()), "-90")

class MapView(QGraphicsView):
    def __init__(self, scene=None, parent=None):
        super(MapView, self).__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def wheelEvent(self, event: QWheelEvent) -> None:
        wheelDeltaValue = event.angleDelta().y()
        if wheelDeltaValue > 0 and self.transform().m11() >= 1.5:
            return
        if wheelDeltaValue > 0:
            self.scale(1.2, 1.2)
        else:
            self.scale(1 / 1.2, 1 / 1.2)
        self.update()


class APHeatMapWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, readThread, parent=None):
        super(APHeatMapWidget, self).__init__(parent)
        self.setWindowTitle("网络信号热力图")
        self.readMapThread = ReadMapThread(readThread, self)
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor("#F4F4F4"))
        # self.scene.setBackgroundBrush(Qt.white)
        self.view = MapView(self.scene, self)
        self.view.setTransform(QTransform(1, 0, 0, -1, 0, 0))
        self.view.setRenderHint(QPainter.Antialiasing)
        # openGL
        # self.view.setViewport(QOpenGLWidget(self))
        self.colorMap = ColorMap()
        self.colorMap.setFixedWidth(30)
        self.colorMapLayout = QHBoxLayout()
        self.colorMapLayout.setContentsMargins(0, 0, 10, 0)
        self.colorMapLayout.addItem(QSpacerItem(0, 0,  QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.colorMapLayout.addWidget(self.colorMap)
        self.hBoxLayout = QHBoxLayout()
        self.hBoxLayout.setContentsMargins(0, 0, 0, 10)
        self.view.setLayout(QVBoxLayout())
        self.view.layout().addLayout(self.colorMapLayout)
        self.view.layout().addLayout(self.hBoxLayout)
        self.apListWidget = ApListWidget(self.readMapThread, self)
        self.tabWidget = QTabWidget(self)
        self.tabWidget.addTab(self.view, "热力图")
        self.tabWidget.addTab(self.apListWidget, "信号强度")
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.tabWidget)
        self.readMapThread.finished.connect(self._slotReadFinished)

    def _slotReadFinished(self):
        self.updateMap()
        self.apListWidget.updateSeries()

    def closeEvent(self, event) -> None:
        self.closed.emit()

    def loadMap(self):
        self.readMapThread.start()

    def updateMap(self):
        # 删除scene中的所有item
        self.scene.clear()
        # 删除hBoxLayout中的所有控件
        while self.hBoxLayout.count():
            item = self.hBoxLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def radioButtonClicked(state):
            for v in self.readMapThread.graphicsItems.values():
                if v.data(0) == "heatmap":
                    v.hide()
            self.readMapThread.graphicsItems[self.sender().text()].show()

        # 添加graphicsItems到scene
        i = 0
        for k, v in self.readMapThread.graphicsItems.items():
            if v.data(0) == "map":
                q = QCheckBox(k)
                q.clicked.connect(v.setVisible)
            elif v.data(0) == "heatmap":
                q = QRadioButton(k)
                q.clicked.connect(radioButtonClicked)
            self.hBoxLayout.addWidget(q)
            if i > 1:
                v.hide()
            else:
                q.setChecked(True)
            self.scene.addItem(v)
            i += 1
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)


if __name__ == '__main__':
    pass
