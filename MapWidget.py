import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.lines as lines
from matplotlib.patches import Circle, Polygon
from PyQt5 import QtGui, QtCore,QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtCore import *
import numpy as np
import json as js
import os
from MyToolBar import MyToolBar, keepRatio, RulerShape
from matplotlib.path import Path
import matplotlib.patches as patches
from matplotlib.textpath import TextPath
import math
import logging
import copy
import time
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from matplotlib.collections import PatchCollection
import zipfile
from ExtendedComboBox import ExtendedComboBox

def GetGlobalPos(p2b, b2g):
    x = p2b[0] * np.cos(b2g[2]) - p2b[1] * np.sin(b2g[2])
    y = p2b[0] * np.sin(b2g[2]) + p2b[1] * np.cos(b2g[2])
    x = x + b2g[0]
    y = y + b2g[1]
    return np.array([x, y])

def Pos2Base(pos2world, base2world):
    pos2base = [0,0,0]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * np.cos(base2world[2]) + y * np.sin(base2world[2])
    pos2base[1] = -x * np.sin(base2world[2]) + y * np.cos(base2world[2])
    pos2base[2] = pos2world[2] - base2world[2]
    return pos2base

def convert2LaserPoints(org_laser_data, org_laser_pos, robot_pos):
    laser_data = GetGlobalPos(org_laser_data, org_laser_pos)
    laser_data = GetGlobalPos(laser_data, robot_pos)
    laser_data = laser_data.T
    laser_pos = GetGlobalPos(org_laser_pos, robot_pos) # n*2
    circle_cs = laser_data
    c = np.zeros(laser_data.shape) + laser_pos
    org_lines = np.concatenate((c,laser_data), axis=1) #水平扩展
    lines = org_lines.reshape(laser_data.shape[0],2,2)
    return lines, circle_cs

def normalize_theta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta


class Readcp (QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.cp_name = ''
        self.js = dict()
        self.laser = []
    # run method gets called when we start the thread
    def run(self):
        time.sleep(1.0)
        fid = open(self.cp_name, encoding= 'UTF-8')
        self.js = js.load(fid)
        fid.close()
        self.laser = dict()
        x, y, r = 0, 0, 0
        try:
            if 'deviceTypes' in self.js:
                for device in self.js['deviceTypes']:
                    if device['name'] == 'laser':
                        for laser in device['devices']:
                            for param in laser['deviceParams']:
                                if param['key'] == 'basic':
                                    for p in param['arrayParam']['params']:
                                        if p['key'] == 'x':
                                            x = p['doubleValue']
                                        elif p['key'] == 'y':
                                            y = p['doubleValue']
                                        elif p['key'] == 'yaw':
                                            r = p['doubleValue']
                            self.laser[laser['name']] = [float(x), float(y), np.deg2rad(r)]
                        break
        except:
            logging.error('Cannot Open robot.cp: ' + self.cp_name)
        self.signal.emit(self.cp_name)

class Readmodel(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.model_name = ''
        self.js = dict()
        self.head = None
        self.tail = None 
        self.width = None
        self.loc_laser_ind = 0
        self.laser = dict() #x,y,r
        self.laser_id2name = dict()
    # run method gets called when we start the thread
    def run(self):
        with open(self.model_name, 'r',encoding= 'UTF-8') as fid:
            try:
                self.js = js.load(fid)
            except:
                logging.error("robot model file cannot read!!!")
            # fid.close()
            self.head = None
            self.tail = None 
            self.width = None
            self.laser = dict() #x,y,r
            if 'chassis' in self.js:
                self.head = float(self.js['chassis']['head'])
                self.tail = float(self.js['chassis']['tail'])
                self.width = float(self.js['chassis']['width'])
                laser0 = self.js['laser']['index'][0]
                self.laser[0] = [float(laser0['x']),float(laser0['y']),np.deg2rad(float(laser0['r']))]
            elif 'deviceTypes' in self.js:
                for device in self.js['deviceTypes']:
                    if device['name'] == 'chassis':
                        for param in device['devices'][0]['deviceParams']:
                            if param['key'] == 'shape':
                                for childparam in param['comboParam']['childParams']:
                                    if childparam['key'] == 'rectangle':
                                        if param['comboParam']['childKey'] == childparam['key']:
                                            for p in childparam['params']:
                                                if p['key'] == 'width':
                                                    self.width = p['doubleValue']
                                                elif p['key'] == 'head':
                                                    self.head = p['doubleValue']
                                                elif p['key'] == 'tail':
                                                    self.tail = p['doubleValue']
                                    elif childparam['key'] == 'circle':
                                        if param['comboParam']['childKey'] == childparam['key']:
                                            for p in childparam['params']:
                                                if p['key'] == 'radius':
                                                    self.width = p['doubleValue']
                                                    self.head = self.width
                                                    self.tail = self.width
                    elif device['name'] == 'laser':
                        x, y, r, idx = 0, 0, 0, 0
                        for laser in device['devices']:
                            for param in laser['deviceParams']:
                                if param['key'] == 'basic':
                                    for p in param['arrayParam']['params']:
                                        if p['key'] == 'x':
                                            x = p['doubleValue']
                                        elif p['key'] == 'y':
                                            y = p['doubleValue']
                                        elif p['key'] == 'yaw':
                                            r = p['doubleValue']
                                        elif p['key'] == 'id':
                                            idx = p['uint32Value']
                                        elif p['key'] == 'useForLocalization':
                                            if p['boolValue'] == True:
                                                self.loc_laser_ind = idx
                            self.laser[idx] = [float(x),float(y),np.deg2rad(r)]
                            self.laser_id2name[idx] = laser['name']
            else:
                logging.error('Cannot Open robot.model: ' + self.model_name)
            self.signal.emit(self.model_name)

class Readmap(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.map_name = ''
        self.js = dict()
        self.map_x = []
        self.map_y = []
        self.lines = []
        self.circles = []
        self.points = dict()
        self.p_names = dict()
        self.bin = dict()
        self.straights = []
        self.bezier_codes = [ 
            Path.MOVETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            ]
        self.straight_codes = [
            Path.MOVETO,
            Path.LINETO ,
        ]
    # run method gets called when we start the thread
    def run(self):
        print("map_name: ", self.map_name)
        try:
            with open(self.map_name, encoding= 'UTF-8') as fid:
                self.js = js.load(fid)
        except UnicodeDecodeError as e:
            logging.warn("readMap {} in utf-8 error. {}".format(self.map_name, e))
            try:
                with open(self.map_name, encoding='gbk') as fid:
                    self.js = js.load(fid)
            except UnicodeDecodeError as e:
                logging.warn("readMap {} in gbk error. {}".format(self.map_name, e))
                try:
                    fz = zipfile.ZipFile(self.map_name, 'r')
                    full_map_name = os.path.splitext(self.map_name)[0]
                    map_name = ""
                    for file in fz.namelist():
                        fz.extract(file, full_map_name)    
                        if os.path.splitext(file)[1] == ".smap":
                            map_name = os.path.join(full_map_name, file)
                    logging.debug("mapWidget|readMap|{}|{}".format(full_map_name, map_name))
                    with open(map_name, encoding= 'UTF-8') as fid:
                        self.js = js.load(fid)
                except Exception as e:
                    print(e)
                    logging.error("readMap error: {}. {}".format(self.map_name, e))
        self.map_x = []
        self.map_y = []
        self.lines = []
        self.circles = []
        self.straights = []
        self.points = dict()
        self.p_names = dict()
        self.bin = dict()
        # print(self.js.keys())
        def addStr(startPos, endPos):
            x1 = 0
            y1 = 0
            x2 = 0
            y2 = 0
            if 'x' in startPos:
                x1 = startPos['x']
            if 'y' in startPos:
                y1 = startPos['y']
            if 'x' in endPos:
                x2 = endPos['x']
            if 'y' in endPos:
                y2 = endPos['y']
            self.straights.append([(x1,y1),(x2,y2)])            
        for pos in self.js.get('normalPosList', []):
            if 'x' in pos:
                self.map_x.append(float(pos['x']))
            else:
                self.map_x.append(0.0)
            if 'y' in pos:
                self.map_y.append(float(pos['y']))
            else:
                self.map_y.append(0.0)
        def f3order(p0, p1, p2, p3):
            dt = 0.001
            t = 0
            v = []
            while(t < 1.0):
                s = 1 - t
                x = (p0 * s * s * s
                        + 3.0 * p1 * s * s * t
                        + 3.0 * p2 * s * t * t
                        + p3 * t * t * t)
                v.append(x)
                t = t + dt
            return v 
        def f5order(p0, p1, p2, p3, p4, p5):
            dt = 0.001
            t = 0
            v = []
            while(t < 1.0):
                s = 1 - t
                x = (p0 * s * s * s * s * s 
                        + 5.0 * p1 * s * s * s * s * t
                        + 10.0 * p2 * s * s * s * t * t
                        + 10.0 * p3 * s * s * t * t * t
                        + 5.0 * p4 * s * t *t * t * t
                        + p5 * t * t * t * t * t)
                v.append(x)
                t = t + dt
            return v 
        if 'advancedCurveList' in self.js:
            for line in self.js['advancedCurveList']:
                if line['className'] == 'BezierPath' \
                    or line['className'] == 'DegenerateBezier':
                    x0 = 0
                    y0 = 0
                    x1 = 0
                    y1 = 0
                    x2 = 0
                    y2 = 0
                    x3 = 0
                    y3 = 0
                    ok = False
                    if 'controlPos1' in line and 'controlPos2' in line:
                        ok = True
                    if ok == False:
                        continue
                    if 'x' in line['startPos']['pos']:
                        x0 = line['startPos']['pos']['x']
                    if 'y' in line['startPos']['pos']:
                        y0 = line['startPos']['pos']['y']
                    if 'x' in line['controlPos1']:
                        x1 = line['controlPos1']['x']
                    if 'y' in line['controlPos1']:
                        y1 = line['controlPos1']['y']
                    if 'x' in line['controlPos2']:
                        x2 = line['controlPos2']['x']
                    if 'y' in line['controlPos2']:
                        y2 = line['controlPos2']['y']
                    if 'x' in line['endPos']['pos']:
                        x3 = line['endPos']['pos']['x']
                    if 'y' in line['endPos']['pos']:
                        y3 = line['endPos']['pos']['y']
                    xs = np.array([])
                    ys = np.array([])
                    if line['className'] == 'BezierPath':
                        xs = np.array(f3order(x0, x1, x2, x3))
                        ys = np.array(f3order(y0, y1, y2, y3))
                    elif line['className'] == 'DegenerateBezier':
                        xs = np.array(f5order(x0, x1, x1, x2, x2, x3))
                        ys = np.array(f5order(y0, y1, y1, y2, y2, y3))
                    points = np.vstack((xs,ys))  
                    self.lines.append(points.T)
                elif line['className'] == 'ArcPath':
                    x1 = 0
                    y1 = 0
                    x2 = 0
                    y2 = 0
                    x3 = 0
                    y3 = 0
                    if 'x' in line['startPos']['pos']:
                        x1 = line['startPos']['pos']['x']
                    if 'y' in line['startPos']['pos']:
                        y1 = line['startPos']['pos']['y']
                    if 'x' in line['controlPos1']:
                        x2 = line['controlPos1']['x']
                    if 'y' in line['controlPos1']:
                        y2 = line['controlPos1']['y']
                    if 'x' in line['endPos']['pos']:
                        x3 = line['endPos']['pos']['x']
                    if 'y' in line['endPos']['pos']:
                        y3 = line['endPos']['pos']['y']
                    A = x1*(y2-y3) - y1*(x2-x3)+x2*y3-x3*y2
                    B = (x1*x1 + y1*y1)*(y3-y2)+(x2*x2+y2*y2)*(y1-y3)+(x3*x3+y3*y3)*(y2-y1)
                    C = (x1*x1 + y1*y1)*(x2-x3)+(x2*x2+y2*y2)*(x3-x1)+(x3*x3+y3*y3)*(x1-x2)
                    D = (x1*x1 + y1*y1)*(x3*y2-x2*y3)+(x2*x2+y2*y2)*(x1*y3-x3*y1)+(x3*x3+y3*y3)*(x2*y1-x1*y2)
                    if abs(A) > 1e-12:
                        x = -B/2/A
                        y = -C/2/A
                        r = math.sqrt((B*B+C*C-4*A*D)/(4*A*A))
                        theta1 = math.atan2(y1-y,x1-x)
                        theta3 = math.atan2(y3-y,x3-x)
                        v1 = np.array([x2-x1,y2-y1])
                        v2 = np.array([x3-x2,y3-y2])
                        flag = float(np.cross(v1,v2))
                        if flag >= 0:
                            self.circles.append([x, y, r, np.rad2deg(theta1), np.rad2deg(theta3)])
                        else:
                            self.circles.append([x, y, r, np.rad2deg(theta3), np.rad2deg(theta1)])
                    else:
                        self.straights.append([(x1,y1),(x3,y3)])
                elif line['className'] == 'StraightPath':
                    addStr(line['startPos']['pos'],line['endPos']['pos'])
        if 'primitiveList' in self.js:
            for line in self.js['primitiveList']:
                if line['className'] == 'RoundLine':
                    cL = line['controlPosList']
                    critical_dist = math.hypot(cL[1]['x'] - cL[3]['x'], cL[1]['y'] - cL[3]['y'])
                    angle1 = math.atan2(cL[0]['y'] - cL[1]['y'], cL[0]['x'] - cL[1]['x'])
                    angle2 = math.atan2(cL[3]['y'] - cL[1]['y'], cL[3]['x'] - cL[1]['x'])
                    angle3 = math.atan2(cL[2]['y'] - cL[1]['y'], cL[2]['x'] - cL[1]['x'])
                    delta_angle = normalize_theta(angle2 - angle1)
                    delta_angle2 = normalize_theta(angle3 - angle2)
                    if critical_dist < 0.0001 or math.fabs(math.fabs(delta_angle) - math.fabs(delta_angle2) > 0.1):
                        addStr(line['startPos']['pos'],line['endPos']['pos'])                     
                    else:
                        addStr(line['startPos']['pos'],cL[0])
                        addStr(cL[2],line['endPos']['pos'])
                        r0 = math.hypot(cL[1]['x'] - cL[0]['x'], cL[1]['y'] - cL[0]['y'])
                        r1 = math.hypot(cL[1]['x'] - cL[2]['x'], cL[1]['y'] - cL[2]['y'])
                        r = (r0 + r1)/2.0
                        if angle1 < angle3:
                            self.circles.append([cL[1]['x'], cL[1]['y'], r, np.rad2deg(angle1), np.rad2deg(angle3)])
                        else:
                            self.circles.append([cL[1]['x'], cL[1]['y'], r, np.rad2deg(angle3), np.rad2deg(angle1)])
        if 'advancedPointList' in self.js:
            for pt in self.js['advancedPointList']:
                x0 = 0
                y0 = 0 
                theta = 0
                if 'x' in pt['pos']:
                    x0 = pt['pos']['x']
                if 'y' in pt['pos']:
                    y0 = pt['pos']['y']
                if 'dir' in pt:
                    theta = pt['dir']
                if  'ignoreDir' in pt:
                    if pt['ignoreDir'] == True:
                        theta = None
                self.points[pt['instanceName'][2::]] = [x0,y0,theta, pt['instanceName']]
                self.p_names[pt['instanceName']] = pt['instanceName'][2::]
        if 'binLocationsList' in self.js:
            for bs in self.js['binLocationsList']:
                for b in bs['binLocationList']:
                    if 'pointName' in b and 'instanceName' in b:
                        self.bin[b['instanceName']] = b['pointName']
        self.signal.emit(self.map_name)

class PointWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.x_label = QtWidgets.QLabel('x(m)')
        self.y_label = QtWidgets.QLabel('y(m)')
        valid = QtGui.QDoubleValidator()
        self.x_edit = QtWidgets.QLineEdit()
        self.x_edit.setValidator(valid)
        self.y_edit = QtWidgets.QLineEdit()
        self.y_edit.setValidator(valid)
        self.x_input = QtWidgets.QFormLayout()
        self.x_input.addRow(self.x_label,self.x_edit)
        self.y_input = QtWidgets.QFormLayout()
        self.y_input.addRow(self.y_label,self.y_edit)
        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addLayout(self.x_input)
        vbox.addLayout(self.y_input)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Point Input")

    def getData(self):
        try:
            x = float(self.x_edit.text())
            y = float(self.y_edit.text())
            self.hide()
            self.getdata.emit([x,y])
        except:
            pass

class RobotWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.x_label = QtWidgets.QLabel('x(m)')
        self.y_label = QtWidgets.QLabel('y(m)')
        self.theta_label = QtWidgets.QLabel('theta(deg)')
        valid = QtGui.QDoubleValidator()
        self.x_edit = QtWidgets.QLineEdit()
        self.x_edit.setValidator(valid)
        self.y_edit = QtWidgets.QLineEdit()
        self.y_edit.setValidator(valid)
        self.theta_edit = QtWidgets.QLineEdit()
        self.theta_edit.setValidator(valid)        
        self.x_input = QtWidgets.QFormLayout()
        self.x_input.addRow(self.x_label,self.x_edit)
        self.y_input = QtWidgets.QFormLayout()
        self.y_input.addRow(self.y_label,self.y_edit)
        self.theta_input = QtWidgets.QFormLayout()
        self.theta_input.addRow(self.theta_label,self.theta_edit)

        self.c_msg = QtWidgets.QLabel("color:")
        self.c = QtWidgets.QComboBox(self)
        self.c.addItems(["b", "g", "r", "c", "m", "y"])
        hbox2 = QtWidgets.QFormLayout()
        hbox2.addRow(self.c_msg, self.c)

        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addLayout(self.x_input)
        vbox.addLayout(self.y_input)
        vbox.addLayout(self.theta_input)
        vbox.addLayout(hbox2)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Robot Input")

    def getData(self):
        try:
            x = float(self.x_edit.text())
            y = float(self.y_edit.text())
            theta = float(self.theta_edit.text())
            self.hide()
            self.getdata.emit([x,y,theta, self.c.currentText()])
        except:
            pass

class LineWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.groupBox1 = QtWidgets.QGroupBox('P1')
        x_label = QtWidgets.QLabel('x(m)')
        y_label = QtWidgets.QLabel('y(m)')
        valid = QtGui.QDoubleValidator()
        self.x_edit1 = QtWidgets.QLineEdit()
        self.x_edit1.setValidator(valid)
        self.y_edit1 = QtWidgets.QLineEdit()
        self.y_edit1.setValidator(valid)
        x_input = QtWidgets.QFormLayout()
        x_input.addRow(x_label,self.x_edit1)
        y_input = QtWidgets.QFormLayout()
        y_input.addRow(y_label,self.y_edit1)
        vbox1 = QtWidgets.QVBoxLayout()
        vbox1.addLayout(x_input)
        vbox1.addLayout(y_input)
        self.groupBox1.setLayout(vbox1)
        
        self.groupBox2 = QtWidgets.QGroupBox('P2')
        x_label = QtWidgets.QLabel('x(m)')
        y_label = QtWidgets.QLabel('y(m)')
        valid = QtGui.QDoubleValidator()
        self.x_edit2 = QtWidgets.QLineEdit()
        self.x_edit2.setValidator(valid)
        self.y_edit2 = QtWidgets.QLineEdit()
        self.y_edit2.setValidator(valid)
        x_input = QtWidgets.QFormLayout()
        x_input.addRow(x_label,self.x_edit2)
        y_input = QtWidgets.QFormLayout()
        y_input.addRow(y_label,self.y_edit2)
        vbox2 = QtWidgets.QVBoxLayout()
        vbox2.addLayout(x_input)
        vbox2.addLayout(y_input)
        self.groupBox2.setLayout(vbox2)

        vbox = QtWidgets.QVBoxLayout(self)
        self.btn = QtWidgets.QPushButton("Yes") 
        self.btn.clicked.connect(self.getData)
        vbox.addWidget(self.groupBox1)
        vbox.addWidget(self.groupBox2)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Line Input")

    def getData(self):
        try:
            x1 = float(self.x_edit1.text())
            y1 = float(self.y_edit1.text())
            x2 = float(self.x_edit2.text())
            y2 = float(self.y_edit2.text())
            self.hide()
            self.getdata.emit([[x1,y1],[x2,y2]])
        except:
            pass

class CurveWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.data_label = QtWidgets.QLabel('Script: x,y,linestype,marker,markersize,color:')
        self.data_edit = QtWidgets.QTextEdit()
        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.data_label)
        vbox.addWidget(self.data_edit)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Curve Input")

    def getData(self):
        code = self.data_edit.toPlainText()
        try:
            l = locals()
            exec(code,globals(),l)
            self.hide()
            self.getdata.emit([l['x'],l['y'],
            l.get('linestyle','--'),
            l.get('marker','.'), 
            l.get('markersize',6),
            l.get('color','r')])
        except Exception as err:
            print(err.args)
            pass
class DataWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Data Input")
        self.choose_msg = QtWidgets.QLabel("Data:")
        self.choose = QtWidgets.QComboBox(self)
        self.choose.addItems(["SimLocation", "LocationEachFrame", "LocalPos", "robot2world", "code2robot"])
        hbox0 = QtWidgets.QFormLayout()
        hbox0.addRow(self.choose_msg, self.choose)

        self.ls_msg = QtWidgets.QLabel("linestyle:")
        self.ls = QtWidgets.QComboBox(self)
        self.ls.addItems(["solid", "dotted", "dashed", "dashdot"])
        hbox1 = QtWidgets.QFormLayout()
        hbox1.addRow(self.ls_msg, self.ls)

        self.c_msg = QtWidgets.QLabel("color:")
        self.c = QtWidgets.QComboBox(self)
        self.c.addItems(["b", "g", "r", "c", "m", "y"])
        hbox2 = QtWidgets.QFormLayout()
        hbox2.addRow(self.c_msg, self.c)

        self.m_msg = QtWidgets.QLabel("marker:")
        self.m = QtWidgets.QComboBox(self)
        self.m.addItems([".", ",", "o", "v", "^", "<", ">", "1", "2", "3", "4"])
        hbox3 = QtWidgets.QFormLayout()
        hbox3.addRow(self.m_msg, self.m)

        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addLayout(hbox0)
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)
        vbox.addWidget(self.btn)

    def getData(self):
        self.getdata.emit([self.choose.currentText(),
        self.ls.currentText(),
        self.c.currentText(),
        self.m.currentText()])

class FindElement(QtWidgets.QWidget):
    """查找图元的对话窗口

    Args:
        QtWidgets (_type_): _description_
    """
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent = None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.car_combo = ExtendedComboBox()
        self.car_label = QtWidgets.QLabel('Element')
        car_form = QtWidgets.QFormLayout()
        car_form.addRow(self.car_label,self.car_combo)
        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addLayout(car_form)
        vbox.addWidget(self.btn)
        self.setWindowTitle("FindElement")
        self.resize(300, 40)
    def addItems(self,names):
        self.car_combo.addItems(names)
    def getData(self):
        """
        """
        try:
            text = self.car_combo.currentText()
            self.hide()
            self.getdata.emit([text])
        except Exception as err:
            print(err.args)
            pass

class MapWidget(QtWidgets.QWidget):
    dropped = pyqtSignal('PyQt_PyObject')
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self, loggui):
        super(QtWidgets.QWidget, self).__init__()
        self.setWindowTitle('MapViewer')
        self.robot_log = loggui
        self.map_name = None
        self.model_name = None
        self.cp_name = None
        self.readingModelFlag = False
        self.draw_size = [] #xmin xmax ymin ymax
        self.map_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize = 1.0,color="gray")
        self.map_data.set_zorder(12)
        self.laser_data = LineCollection([], linewidths=3, linestyle='solid')
        self.laser_data_points = PatchCollection([])
        self.org_laser_data = [] # 激光的原始数据，用于提取出来保存
        self.laser_org_color = np.array([1,0,0,0.2])
        self.laser_color = self.laser_org_color[:]
        self.laser_point_org_color = np.array([1,0,0,0.5])
        self.laser_point_color = self.laser_point_org_color[:]
        self.laser_data.set_color(self.laser_org_color)
        self.laser_data.set_zorder(11)
        self.laser_data_points.set_color(self.laser_org_color)
        self.laser_data_points.set_linestyle('-')
        self.laser_data_points.set_edgecolor('r')
        self.laser_data_points.set_linewidth(2.0)
        self.laser_data_points.set_zorder(10)
        self.robot_data = lines.Line2D([],[], linestyle = '-', color='k')
        self.robot_data.set_zorder(21)
        self.robot_data_c0 = lines.Line2D([],[], linestyle = '-', linewidth = 2, color='k')
        self.robot_data_c0.set_zorder(21)
        self.robot_loc_data = lines.Line2D([],[], linestyle = '--', color='gray')
        self.robot_loc_data.set_zorder(21)
        self.robot_loc_data_c0 = lines.Line2D([],[], linestyle = '--', linewidth = 2, color='gray')
        self.robot_loc_data_c0.set_zorder(21)
        self.obs_points = lines.Line2D([],[], linestyle = '', marker = '*', markersize = 8.0, color='k')
        self.obs_points.set_zorder(40)
        self.depthCamera_hole_points = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 4.0, color='black')
        self.depthCamera_obs_points = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 4.0, color='gray')
        self.particle_points = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 4.0, color='b')
        self.particle_points.set_zorder(20)
        self.trajectory = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='m')
        self.trajectory.set_zorder(20)
        self.trajectory_next = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='mediumpurple')
        self.trajectory_next.set_zorder(20)
        self.odo = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='green')
        self.odo.set_zorder(20)
        self.odo_next = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='lightgreen')
        self.odo_next.set_zorder(20)
        self.cur_arrow = patches.FancyArrow(0, 0, 0.5, 0,
                                            length_includes_head=True,# 增加的长度包含箭头部分
                                            width=0.05,
                                            head_width=0.1, head_length=0.16, fc='r', ec='b')
        self.cur_arrow.set_zorder(20)
        self.org_arrow_xy = self.cur_arrow.get_xy().copy()

        self.robot_pos = [0., 0., 0.]
        self.robot_loc_pos = []
        self.laser_pos = dict()
        self.laser_org_data = np.array([])
        self.laser_index = -1
        self.check_draw_flag = False
        self.fig_ratio = 1.0
        self.setAcceptDrops(True)
        self.dropped.connect(self.dragFiles)
        self.read_map = Readmap()
        self.read_map.signal.connect(self.readMapFinished)
        self.read_model = Readmodel()
        self.read_model.signal.connect(self.readModelFinished)
        self.read_cp = Readcp()
        self.read_cp.signal.connect(self.readCPFinished)
        self.setupUI()
        self.pointLists = dict()
        self.lineLists = dict()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateRobotData)
        self.timer.start(1000)
        self.mid_line_t = None
        self.left_line_t = None
        self.right_line_t = None
        self.left_idx = None
        self.right_idx = None

    def setupUI(self):
        self.static_canvas = FigureCanvas(Figure(figsize=(5,5)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.static_canvas.figure.subplots_adjust(left = 0.0, right = 1.0, bottom = 0.0, top = 1.0)
        self.static_canvas.figure.tight_layout()
        self.ax, self.color_ax = self.static_canvas.figure.subplots(1, 2, 
        gridspec_kw={'width_ratios': [100, 1], 'wspace':0.01})
        self.cm = matplotlib.cm.jet
        norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
        self.static_canvas.figure.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=self.cm),
             cax=self.color_ax)
        self.ax.add_line(self.map_data)
        self.ax.add_patch(self.cur_arrow)
        self.ax.add_line(self.robot_data)
        self.ax.add_line(self.robot_data_c0)
        self.ax.add_line(self.robot_loc_data)
        self.ax.add_line(self.robot_loc_data_c0)
        self.ax.add_collection(self.laser_data)
        self.ax.add_collection(self.laser_data_points)
        self.ax.add_line(self.obs_points)
        self.ax.add_line(self.depthCamera_hole_points)
        self.ax.add_line(self.depthCamera_obs_points)
        self.ax.add_line(self.particle_points)
        self.ax.add_line(self.trajectory)
        self.ax.add_line(self.trajectory_next)
        self.ax.add_line(self.odo)
        self.ax.add_line(self.odo_next)
        self.ruler = RulerShape()
        self.ruler.add_ruler(self.ax)
        self.toolbar = MyToolBar(self.static_canvas, self, self.ruler)
        self.toolbar.update_home_callBack(self.toolbarHome)
        self.toolbar.fig_ratio = 1
        self.userToolbar = QtWidgets.QToolBar(self)
        self.autoMap = QtWidgets.QAction("AUTO", self.userToolbar)
        self.autoMap.setCheckable(True)
        self.autoMap.toggled.connect(self.changeAutoMap)
        self.smap_action = QtWidgets.QAction("SMAP", self.userToolbar)
        self.smap_action.triggered.connect(self.openMap)
        self.model_action = QtWidgets.QAction("MODEL", self.userToolbar)
        self.model_action.triggered.connect(self.openModel)
        self.cp_action = QtWidgets.QAction("CP", self.userToolbar)
        self.cp_action.triggered.connect(self.openCP)
        self.draw_point = QtWidgets.QAction("POINT", self.userToolbar)
        self.draw_point.triggered.connect(self.addPoint)
        self.draw_line = QtWidgets.QAction("LINE", self.userToolbar)
        self.draw_line.triggered.connect(self.addLine)
        self.draw_rpos = QtWidgets.QAction("ROBOT", self.userToolbar)
        self.draw_rpos.triggered.connect(self.addRobotPos)
        self.draw_curve = QtWidgets.QAction("CURVE", self.userToolbar)
        self.draw_curve.triggered.connect(self.addCurve)
        self.draw_data = QtWidgets.QAction("DATA", self.userToolbar) # 依据selection参数的XY
        self.draw_data.triggered.connect(self.addDATAXY)
        self.draw_clear = QtWidgets.QAction("CLEAR", self.userToolbar)
        self.draw_clear.triggered.connect(self.drawClear)
        self.draw_center = QtWidgets.QAction("CENTER", self.userToolbar)
        self.draw_center.triggered.connect(self.drawCenter)
        self.draw_center.setCheckable(True)
        self.draw_center.setChecked(False)
        self.userToolbar.addActions([self.autoMap, self.smap_action, self.model_action, self.cp_action])
        self.userToolbar.addSeparator()
        self.userToolbar.addActions([self.draw_point, self.draw_rpos, self.draw_line, self.draw_curve, self.draw_data, self.draw_clear])
        self.userToolbar.addSeparator()
        self.find_element_bar = QtWidgets.QAction("FindElement", self.userToolbar)
        self.find_element_bar.triggered.connect(self.findElement)
        self.userToolbar.addActions([self.draw_center, self.find_element_bar])

        self.find_element = FindElement(self)
        self.find_element.getdata.connect(self.getElement)
        self.find_element.hide()
        self.find_element.setWindowFlags(Qt.Window)

        self.getPoint = PointWidget()
        self.getPoint.getdata.connect(self.getPointData)
        self.getPoint.hide()
        self.getLine = LineWidget()
        self.getLine.getdata.connect(self.getLineData)
        self.getLine.hide()
        self.getRobot = RobotWidget()
        self.getRobot.getdata.connect(self.getRobotPosData)
        self.getRobot.hide()
        self.getCurve = CurveWidget()
        self.getCurve.getdata.connect(self.getCurveData)
        self.getCurve.hide()
        self.getDataXY = DataWidget()
        self.getDataXY.getdata.connect(self.getDataXYData)
        self.autoMap.setChecked(True)
        self.fig_layout = QtWidgets.QVBoxLayout(self)
        self.timestamp_lable = QtWidgets.QLabel(self)
        self.timestamp_lable.setText('当前激光时刻定位（实框）: ')
        self.timestamp_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.timestamp_lable.setFixedHeight(16)
        self.logt_lable = QtWidgets.QLabel(self)
        self.logt_lable.setText('当前时刻定位(虚框): ')
        self.logt_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.logt_lable.setFixedHeight(16)
        self.obs_lable = QtWidgets.QLabel(self)
        self.obs_lable.setText('')
        self.obs_lable.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.obs_lable.setFixedHeight(16)
        self.fig_layout.addWidget(self.toolbar)
        self.fig_layout.addWidget(self.userToolbar)
        self.fig_layout.addWidget(self.timestamp_lable)
        self.fig_layout.addWidget(self.logt_lable)
        self.fig_layout.addWidget(self.obs_lable)
        self.fig_layout.addWidget(self.static_canvas)
        self.static_canvas.mpl_connect('resize_event', self.resize_fig)

                #选择消息框
        self.hbox = QtWidgets.QHBoxLayout()
        self.check_all = QtWidgets.QCheckBox('ALL',self)
        self.check_all.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_map = QtWidgets.QCheckBox('MAP',self)
        self.check_map.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_robot = QtWidgets.QCheckBox('ROBOT',self)
        self.check_robot.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_partical = QtWidgets.QCheckBox('Paritical',self)
        self.check_partical.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_3dHole = QtWidgets.QCheckBox('3DHole',self)
        self.check_3dHole.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_3dObs = QtWidgets.QCheckBox('3DObs',self)
        self.check_3dObs.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_traj = QtWidgets.QCheckBox('TRAJ',self)
        self.check_traj.setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_odo = QtWidgets.QCheckBox('ODO',self)
        self.check_odo.setFocusPolicy(QtCore.Qt.NoFocus)
        self.hbox.addWidget(self.check_all)
        self.hbox.addWidget(self.check_map)
        self.hbox.addWidget(self.check_robot)
        self.hbox.addWidget(self.check_partical)
        self.hbox.addWidget(self.check_3dHole)
        self.hbox.addWidget(self.check_3dObs)
        self.hbox.addWidget(self.check_traj)
        self.hbox.addWidget(self.check_odo)
        self.check_all.stateChanged.connect(self.changeCheckBoxAll)
        self.check_map.stateChanged.connect(self.changeCheckBox)
        self.check_robot.stateChanged.connect(self.changeCheckBox)
        self.check_partical.stateChanged.connect(self.changeCheckBox)
        self.check_3dHole.stateChanged.connect(self.changeCheckBox)
        self.check_3dObs.stateChanged.connect(self.changeCheckBox)
        self.check_traj.stateChanged.connect(self.changeCheckBox)
        self.check_odo.stateChanged.connect(self.changeCheckBox)
        self.check_lasers = dict()
        self.hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.fig_layout.addLayout(self.hbox)
        self.check_all.setChecked(True)
        self.check_partical.setChecked(False)
        self.check_odo.setChecked(False)
        self.static_canvas.mpl_connect('button_press_event', self.mouse_press)
        
    def mouse_press(self, event):
        if event.button == 3:
            if not self.toolbar.isActive():
                self.popMenu = QtWidgets.QMenu(self)
                self.popMenu.addAction('&Save Laser Data',lambda:self.saveLaserData(event.inaxes))
                cursor = QtGui.QCursor()
                self.popMenu.exec_(cursor.pos())
    
    def saveLaserData(self, event):
        if len(self.org_laser_data) < 1:
            return
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self,"选取log文件", "","CSV Files (*.csv);;PY Files (*.py)")
        subffix = os.path.splitext(fname)[1]
        isPy = subffix == ".py"

        outdata = []
        # 对数据存之前进行处理
        if isPy:
            x,y = [],[]
            for c in self.org_laser_data:
                x.append(c[0])
                y.append(c[1])
            xdata = 'x='+str(x)
            ydata = 'y='+str(y)
            outdata.append(xdata)
            outdata.append(ydata)
        else:
            for c in self.org_laser_data:
                outdata.append("{},{}".format(c[0], c[1]))
        # 写数据
        if fname:
            try:
                with open(fname, 'w') as fn:
                    for d in outdata:
                        fn.write(d+'\n')
            except:
                pass        

    def changeAutoMap(self):
        flag =  not self.autoMap.isChecked()
        self.smap_action.setEnabled(flag)
        self.model_action.setEnabled(flag)
        self.cp_action.setEnabled(flag)

    def openMap(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,"选取smap文件", "","smap Files (*.smap);;All Files (*)", options=options)
        if filename:
            self.map_name = filename
            self.read_map.map_name = self.map_name
            self.read_map.start()

    def openModel(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,"选取model文件", "","model Files (*.model);;All Files (*)", options=options)
        if filename:
            self.model_name = filename
            self.read_model.model_name = self.model_name
            self.read_model.start()

    def openCP(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,"选取cp文件", "","cp Files (*.cp);;All Files (*)", options=options)
        if filename:
            self.cp_name = filename
            self.read_cp.cp_name = self.cp_name
            self.read_cp.start()

    def addPoint(self):
        self.getPoint.hide()
        self.getPoint.show()

    def addLine(self):
        self.getLine.hide()
        self.getLine.show()
    
    def addRobotPos(self):
        self.getRobot.hide()
        self.getRobot.show()

    def addCurve(self):
        self.getCurve.hide()
        self.getCurve.show()

    def addDATAXY(self):
        self.getDataXY.hide()
        self.getDataXY.show()

    def findElement(self):
        self.find_element.show()

    def getElement(self, event:list):
        """ 回调函数，查找图元所在位置

        Args:
            event (list): 消息，第一个为图元名称
        """
        name = event[0] # 点位名称或者库位名称
        point = []
        if name in self.read_map.bin:
            name = self.read_map.bin[name]
        
        if name in self.read_map.p_names:
            p = self.read_map.points[self.read_map.p_names[name]]
            point.append(p[0])
            point.append(p[1])
        # 设置查看的范围
        if len(point) == 2:
            x0 = p[0]
            y0 = p[1]
            xmax = x0 + 1
            xmin = x0 - 1
            ymax = y0 + 1
            ymin = y0 - 1
            self.draw_size = [xmin,xmax, ymin, ymax]
            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)
            self.static_canvas.figure.canvas.draw()

    def getPointData(self, event):
        point = lines.Line2D([],[], linestyle = '', marker = 'x', markersize = 8.0, color='r')
        point.set_xdata(event[0])
        point.set_ydata(event[1])
        point.set_zorder(30)
        id = str(int(round(time.time()*1000)))
        if id not in self.pointLists or self.pointLists[id] is None:
            self.pointLists[id] = point
            self.ax.add_line(self.pointLists[id])
            self.static_canvas.figure.canvas.draw() 

    def getRobotPosData(self, event):
        """回调函数，绘制机器人形状

        Args:
            event (_type_): [x,y,theta,color]
        """
        if len(event) != 4:
            return
        robot_pos = [event[0], event[1], event[2]/180.0*math.pi]
        if self.read_model.tail and self.read_model.head and self.read_model.width:
            xdata = [-self.read_model.tail,   -self.read_model.tail,     self.read_model.head,  
                     self.read_model.head, -self.read_model.tail, self.read_model.head, 
                     0.0,self.read_model.head,0.0,self.read_model.head,
                     self.read_model.head, -self.read_model.tail]
            ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, 
                     0.0, 0.0, 0.0, 
                     -self.read_model.width/2, 0.0,self.read_model.width/2,0.0,
                     self.read_model.width/2, self.read_model.width/2]
            robot_shape = np.array([xdata, ydata])

            robot_shape = GetGlobalPos(robot_shape,robot_pos)
            l = lines.Line2D([],[], linestyle = '--', marker = '.', markersize = 6.0, color=event[3])
            l.set_xdata(robot_shape[0])
            l.set_ydata(robot_shape[1])
            l.set_zorder(30)
            id = str(int(round(time.time()*1000)))
            if id not in self.lineLists or self.lineLists[id] is None:
                self.lineLists[id] = l
                self.ax.add_line(self.lineLists[id])
                self.static_canvas.figure.canvas.draw()         

    def getLineData(self, event):
        l = lines.Line2D([],[], linestyle = '--', marker = '.', markersize = 6.0, color='r')
        l.set_xdata([event[0][0],event[1][0]])
        l.set_ydata([event[0][1],event[1][1]])
        l.set_zorder(30)
        id = str(int(round(time.time()*1000)))
        if id not in self.lineLists or self.lineLists[id] is None:
            self.lineLists[id] = l
            self.ax.add_line(self.lineLists[id])
            self.static_canvas.figure.canvas.draw() 
    

    def getCurveData(self, event):
        l = lines.Line2D([],[], linestyle = event[2], marker = event[3], markersize = event[4], color=event[5])
        l.set_xdata(event[0])
        l.set_ydata(event[1])     
        l.set_zorder(30)
        id = str(int(round(time.time()*1000)))
        if id not in self.lineLists or self.lineLists[id] is None:
            self.lineLists[id] = l
            self.ax.add_line(self.lineLists[id])
            self.static_canvas.figure.canvas.draw()

    def getDataXYData(self, event):
        datax = event[0] + ".x"
        datay = event[0] + ".y"
        print("getDataXYData", event, datax, datay)
        datax = self.robot_log.read_thread.getData(datax)
        datay = self.robot_log.read_thread.getData(datay)
        ts = np.array(datax[1])
        if len(ts) < 1:
            return
        left_idx = (np.abs(ts - self.left_line_t)).argmin()  
        right_idx = (np.abs(ts[left_idx::] - self.right_line_t)).argmin()   + left_idx
        if left_idx >= right_idx:
            return
        x = datax[0][left_idx:right_idx]
        y = datay[0][left_idx:right_idx]
        id = str(int(round(time.time()*1000)))
        l = lines.Line2D(x, y, linestyle = event[1], marker =event[3], markersize = 6, color= event[2])
        l.set_zorder(100.)
        if id not in self.lineLists or self.lineLists[id] is None:
            self.lineLists[id] = l
            self.ax.add_line(self.lineLists[id])
            self.static_canvas.figure.canvas.draw()

    def drawClear(self):
        for p in self.pointLists:
            if self.pointLists[p] is not None:
                self.pointLists[p].remove()
                self.pointLists[p] = None
        for l in self.lineLists:
            if self.lineLists[l] is not None:
                self.lineLists[l].remove()
                self.lineLists[l] = None
        self.static_canvas.figure.canvas.draw()    

    def drawCenter(self):
        if self.draw_center.isChecked():
            (xmin, xmax) = self.ax.get_xlim()
            (ymin, ymax) = self.ax.get_ylim()
            x0 = (xmin + xmax)/2.0
            y0 = (ymin + ymax)/2.0
            dx = self.robot_pos[0] - x0
            dy = self.robot_pos[1] - y0
            self.ax.set_xlim(xmin + dx, xmax + dx)
            self.ax.set_ylim(ymin + dy, ymax + dy)      
            self.redraw()
  
    def add_laser_check(self, index):
        self.check_lasers[index] = QtWidgets.QCheckBox('Laser'+str(index),self)
        self.check_lasers[index].setFocusPolicy(QtCore.Qt.NoFocus)
        self.check_lasers[index].stateChanged.connect(self.changeCheckBox)
        self.hbox.addWidget(self.check_lasers[index])

    def changeCheckBoxAll(self):
        if self.check_all.checkState() == QtCore.Qt.Checked:
            self.check_map.setChecked(True)
            self.check_robot.setChecked(True)
            self.check_partical.setChecked(True)
            self.check_3dHole.setChecked(True)
            self.check_3dObs.setChecked(True)
            self.check_traj.setChecked(True)
            self.check_odo.setChecked(True)
            for k in self.check_lasers.keys():
                self.check_lasers[k].setChecked(True)
        elif self.check_all.checkState() == QtCore.Qt.Unchecked:
            self.check_map.setChecked(False)
            self.check_robot.setChecked(False)
            self.check_partical.setChecked(False)
            self.check_3dHole.setChecked(False)
            self.check_3dObs.setChecked(False)
            self.check_traj.setChecked(False)
            self.check_odo.setChecked(False)
            for k in self.check_lasers.keys():
                self.check_lasers[k].setChecked(False)

    def changeCheckBox(self):
        all_laser_check = True
        part_laser_check = False
        for k in self.check_lasers.keys():
            if self.check_lasers[k].isChecked:
                part_laser_check = True
            else:
                all_laser_check = False
        if self.check_map.isChecked() and self.check_robot.isChecked() and all_laser_check\
            and self.check_partical.isChecked()\
                and self.check_3dHole.isChecked()\
                    and self.check_3dObs.isChecked()\
                        and self.check_traj.isChecked()\
                            and self.check_odo.isChecked():
            self.check_all.setCheckState(QtCore.Qt.Checked)
        elif self.check_map.isChecked() or self.check_robot.isChecked() or part_laser_check\
            or self.check_partical.isChecked()\
                or self.check_3dObs.isChecked()\
                    or self.check_3dHole.isChecked()\
                        or self.check_traj.isChecked()\
                            or self.check_odo.isChecked():
            self.check_all.setTristate()
            self.check_all.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            self.check_all.setTristate(False)
            self.check_all.setCheckState(QtCore.Qt.Unchecked)

        cur_check = self.sender()
        if cur_check is self.check_robot:
            self.robot_data.set_visible(cur_check.isChecked())
            self.cur_arrow.set_visible(cur_check.isChecked())
            self.cur_arrow.set_visible(cur_check.isChecked())
        elif cur_check is self.check_map:
            self.map_data.set_visible(cur_check.isChecked())
        elif cur_check is self.check_partical:
            self.particle_points.set_visible(cur_check.isChecked())
        elif cur_check is self.check_3dObs:
            self.depthCamera_obs_points.set_visible(cur_check.isChecked())
        elif cur_check is self.check_3dHole:
            self.depthCamera_hole_points.set_visible(cur_check.isChecked())
        elif cur_check is self.check_traj:
            self.trajectory.set_visible(cur_check.isChecked())
            self.trajectory_next.set_visible(cur_check.isChecked())
        elif cur_check is self.check_odo:
            print(self.odo.get_visible(), cur_check.isChecked(), self.readingModelFlag)
            if self.odo.get_visible() == False and cur_check.isChecked() and self.readingModelFlag == False:
                print("update odo")
                self.readtrajectory()
            self.odo.set_visible(cur_check.isChecked())
            self.odo_next.set_visible(cur_check.isChecked())        
        else:
            for k in self.check_lasers.keys():
                if cur_check is self.check_lasers[k]:
                    if self.laser_index is k:
                        self.laser_data.set_visible(cur_check.isChecked())
                        self.laser_data_points.set_visible(cur_check.isChecked())
                    self.mid_line_t = None
                       
        self.static_canvas.figure.canvas.draw() 

    def closeEvent(self,event):
        if self.robot_log is not None and self.robot_log.in_close:
            self.getLine.close()
            self.getCurve.close()
            self.getPoint.close()
            self.getDataXY.close()
        else:
            self.getLine.hide()
            self.getCurve.hide()
            self.getPoint.hide()
            self.getDataXY.hide()
            self.hide()
            self.hiddened.emit(True)

    def toolbarHome(self, *args, **kwargs):
        if len(self.draw_size) == 4:
            xmin, xmax, ymin ,ymax = keepRatio(self.draw_size[0], self.draw_size[1], self.draw_size[2], self.draw_size[3], self.fig_ratio)
            self.ax.set_xlim(xmin,xmax)
            self.ax.set_ylim(ymin,ymax)
            self.static_canvas.figure.canvas.draw()

    def resize_fig(self, event):
        ratio = event.width/event.height
        self.fig_ratio = ratio
        self.toolbar.fig_ratio = ratio
        (xmin, xmax) = self.ax.get_xlim()
        (ymin, ymax) = self.ax.get_ylim()
        bigger = True
        if len(self.draw_size) == 4:
            factor = 1.5
            if not(xmin > self.draw_size[0]*factor or xmax < self.draw_size[1]*factor or ymin > self.draw_size[2]*factor or ymax < self.draw_size[3]*factor):
                bigger = False
        xmin, xmax, ymin ,ymax = keepRatio(xmin, xmax, ymin, ymax, ratio, bigger)
        self.ax.set_xlim(xmin,xmax)
        self.ax.set_ylim(ymin,ymax)
        self.static_canvas.figure.canvas.draw()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.dropped.emit(links)
        else:
            event.ignore()

    def dragFiles(self,files):
        new_map = False
        new_model = False
        new_cp = False
        for file in files:
            if file and os.path.exists(file):
                if self.smap_action.isEnabled() and os.path.splitext(file)[1] == ".smap":
                    self.map_name = file
                    new_map = True
                elif self.model_action.isEnabled() and os.path.splitext(file)[1] == ".model":
                    self.model_name = file
                    new_model = True
                elif self.cp_action.isEnabled() and os.path.splitext(file)[1] == ".cp":
                    self.cp_name = file
                    new_cp = True
        if new_map and self.map_name:
            self.read_map.map_name = self.map_name
            self.read_map.start()
        if new_model and self.model_name:
            self.read_model.model_name = self.model_name
            self.read_model.start()
        if new_cp and self.cp_name:
            self.read_cp.cp_name = self.cp_name
            self.read_cp.start()

    def readFiles(self,files):
        new_map = False
        new_model = False
        new_cp = False
        for file in files:
            if file and os.path.exists(file):
                if not self.smap_action.isEnabled() and os.path.splitext(file)[1] == ".smap":
                    self.map_name = file
                    new_map = True
                elif not self.model_action.isEnabled() and os.path.splitext(file)[1] == ".model":
                    self.model_name = file
                    new_model = True
                elif not self.cp_action.isEnabled() and os.path.splitext(file)[1] == ".cp":
                    self.cp_name = file
                    new_cp = True
            elif file:
                try:
                    if os.path.splitext(file)[1] == ".smap":
                        self.smap_action.setEnabled(True)
                    if os.path.splitext(file)[1] == ".model":
                        self.model_action.setEnabled(True)
                    if os.path.splitext(file)[1] == ".cp":
                        self.cp_action.setEnabled(True)
                except:
                    self.autoMap.setChecked(False)
        if new_map and self.map_name:
            self.read_map.map_name = self.map_name
            self.read_map.start()
        if new_model and self.model_name:
            font = QtGui.QFont()
            font.setBold(False)
            self.cp_action.setFont(font)
            self.read_model.model_name = self.model_name
            self.read_model.start()
        if new_cp and self.cp_name:
            font = QtGui.QFont()
            font.setBold(False)
            self.cp_action.setFont(font)
            self.read_cp.cp_name = self.cp_name
            self.read_cp.start()

    def readMapFinished(self, result):
        if len(self.read_map.map_x) > 0:
            self.map_data.set_xdata(self.read_map.map_x)
            self.map_data.set_ydata(self.read_map.map_y)
            self.ax.grid(True)
            self.ax.axis('auto')
            xmin = min(self.read_map.map_x)
            xmax = max(self.read_map.map_x)
            ymin = min(self.read_map.map_y)
            ymax = max(self.read_map.map_y)
            if xmax - xmin > ymax - ymin:
                ymax = ymin + xmax - xmin
            else:
                xmax = xmin + ymax - ymin
            self.draw_size = [xmin, xmax, ymin ,ymax]
            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)
            [p.remove() for p in reversed(self.ax.patches)]
            [p.remove() for p in reversed(self.ax.texts)]
            self.ax.add_patch(self.cur_arrow) #add robot arrow again
            for line in self.read_map.lines:
                path = Polygon(line, closed=False, facecolor='none', edgecolor='orange', lw=1)
                path.set_zorder(19)
                self.ax.add_patch(path)
            for circle in self.read_map.circles:
                wedge = patches.Arc([circle[0], circle[1]], circle[2]*2, circle[2]*2, 0, circle[3], circle[4], facecolor = 'none', ec="orange", lw = 1)
                wedge.set_zorder(19)
                self.ax.add_patch(wedge)
            for vert in self.read_map.straights:
                path = Path(vert, self.read_map.straight_codes)
                patch = patches.PathPatch(path, facecolor='none', edgecolor='orange', lw=2)
                patch.set_zorder(19)
                self.ax.add_patch(patch)
            pr = 0.25
            for k in self.read_map.points:
                pt = self.read_map.points[k][0:3]
                name = self.read_map.points[k][-1]
                circle = patches.Circle((pt[0], pt[1]), pr, facecolor='orange',
                edgecolor=(0, 0.8, 0.8), linewidth=3, alpha=0.5)
                circle.set_zorder(19)
                self.ax.add_patch(circle)
                text_path = TextPath((pt[0],pt[1]), name, size = 0.2)
                text_path = patches.PathPatch(text_path, ec="none", lw=3, fc="k")
                text_path.set_zorder(19)
                self.ax.add_patch(text_path)
                if pt[2] != None:
                    arrow = patches.Arrow(pt[0],pt[1], pr * np.cos(pt[2]), pr*np.sin(pt[2]), pr)
                    arrow.set_zorder(19)
                    self.ax.add_patch(arrow)
            self.ruler.add_ruler(self.ax)
            self.setWindowTitle("{} : {}".format('MapViewer', os.path.split(self.map_name)[1]))
            font = QtGui.QFont()
            font.setBold(True)
            self.smap_action.setFont(font)
            self.mid_line_t = None
            elements = list(self.read_map.p_names.keys())
            elements.extend(list(self.read_map.bin.keys()))
            self.find_element.addItems(set(elements))

    def readModelFinished(self, result):
        self.readingModelFlag = True
        if self.read_model.head and self.read_model.tail and self.read_model.width:
            if self.laser_index == -1:
                if len(self.read_model.laser) > 0:
                    self.laser_index = list(self.read_model.laser.keys())[0]
            if self.laser_index in self.read_model.laser.keys():
                for i in range(0, self.hbox.count()): 
                    self.hbox.itemAt(i).widget().deleteLater()
                self.check_all = QtWidgets.QCheckBox('ALL',self)
                self.check_all.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_map = QtWidgets.QCheckBox('MAP',self)
                self.check_map.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_robot = QtWidgets.QCheckBox('ROBOT',self)
                self.check_robot.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_partical = QtWidgets.QCheckBox('Paritical',self)
                self.check_partical.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_3dHole = QtWidgets.QCheckBox('3DHole',self)
                self.check_3dHole.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_3dObs = QtWidgets.QCheckBox('3DObs',self)
                self.check_3dObs.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_traj = QtWidgets.QCheckBox('TRAJ',self)
                self.check_traj.setFocusPolicy(QtCore.Qt.NoFocus)
                self.check_odo = QtWidgets.QCheckBox('ODO',self)
                self.check_odo.setFocusPolicy(QtCore.Qt.NoFocus)
                self.hbox.addWidget(self.check_all)
                self.hbox.addWidget(self.check_map)
                self.hbox.addWidget(self.check_robot)
                self.hbox.addWidget(self.check_partical)
                self.hbox.addWidget(self.check_3dHole)
                self.hbox.addWidget(self.check_3dObs)
                self.hbox.addWidget(self.check_traj)
                self.hbox.addWidget(self.check_odo)
                
                self.check_all.stateChanged.connect(self.changeCheckBoxAll)
                self.check_map.stateChanged.connect(self.changeCheckBox)
                self.check_robot.stateChanged.connect(self.changeCheckBox)
                self.check_partical.stateChanged.connect(self.changeCheckBox)
                self.check_3dHole.stateChanged.connect(self.changeCheckBox)
                self.check_3dObs.stateChanged.connect(self.changeCheckBox)
                self.check_traj.stateChanged.connect(self.changeCheckBox)
                self.check_odo.stateChanged.connect(self.changeCheckBox)
                self.check_lasers = dict()
                for k in self.read_model.laser.keys():
                    self.add_laser_check(k)
                self.check_all.setChecked(True)
                self.check_partical.setChecked(False)
                self.check_odo.setChecked(False)


                xdata = [-self.read_model.tail, -self.read_model.tail, self.read_model.head, self.read_model.head, -self.read_model.tail]
                ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, self.read_model.width/2, self.read_model.width/2]
                robot_shape = np.array([xdata, ydata])
                xxdata = [-0.05, 0.05, 0.0, 0.0, 0.0]
                xydata = [0.0, 0.0, 0.0, 0.05, -0.05]
                cross_shape = np.array([xxdata,xydata])
                self.laser_pos = copy.deepcopy(self.read_model.laser)
                # laser_data = [[self.laser_pos[self.laser_index][0], self.laser_pos[self.laser_index][1]]]
                self.updateRobotData()

                if len(self.draw_size) != 4:
                    xmax = self.robot_pos[0] + 10
                    xmin = self.robot_pos[0] - 10
                    ymax = self.robot_pos[1] + 10
                    ymin = self.robot_pos[1] - 10
                    self.draw_size = [xmin,xmax, ymin, ymax]
                    self.ax.set_xlim(xmin, xmax)
                    self.ax.set_ylim(ymin, ymax)
                font = QtGui.QFont()
                font.setBold(True)
                self.model_action.setFont(font)
                font = QtGui.QFont()
                font.setBold(False)
                self.cp_action.setFont(font)
                self.static_canvas.figure.canvas.draw()
            else:
                print("read laser error! laser_index: ", self.laser_index, "; laser index in model: ", self.read_model.laser.keys())
                logging.debug("read laser error! laser_index: " + str(self.laser_index) +" "+ str(self.read_model.laser.keys()))
        else:
            print("readModel error!")
            logging.debug("readModel error!")
        self.readingModelFlag = False
        self.mid_line_t = None

    def readCPFinished(self, result):
        if self.read_model.laser:
            if self.read_cp.laser:
                for key in self.read_model.laser.keys():
                    self.laser_pos[key] = [0,0,0]
                    laser_name = self.read_model.laser_id2name[key]
                    if laser_name in self.read_cp.laser.keys():
                        self.laser_pos[key][0] = self.read_model.laser[key][0] + self.read_cp.laser[laser_name][0]
                        self.laser_pos[key][1] = self.read_model.laser[key][1] + self.read_cp.laser[laser_name][1]
                        self.laser_pos[key][2] = self.read_model.laser[key][2] + self.read_cp.laser[laser_name][2]
                    else:
                        self.laser_pos[key][0] = self.read_model.laser[key][0]
                        self.laser_pos[key][1] = self.read_model.laser[key][1]
                        self.laser_pos[key][2] = self.read_model.laser[key][2]
                    laser_data = [self.laser_pos[key][0], self.laser_pos[key][1]]
                    font = QtGui.QFont()
                    font.setBold(True)
                    self.cp_action.setFont(font)
                    if self.laser_org_data.any() and self.laser_index == key:
                        lines, cs = convert2LaserPoints(self.laser_org_data, self.laser_pos[self.laser_index], self.robot_pos)
                        self.laser_data.set_segments(lines)
                        self.laser_data.set_color(self.laser_color)
                        patches = []
                        self.org_laser_data = cs
                        for c in cs:
                            circle = Circle((c[0], c[1]), 0.01)
                            patches.append(circle)
                        self.laser_data_points.set_paths(patches)
                        self.laser_data_points.set_color(self.laser_point_color)
                        self.mid_line_t = None

    def updateObs(self):
        if self.robot_log is None:
            return
        if self.robot_log.mid_line_t is None:
            return
        mid_line_t = self.robot_log.mid_line_t
        content = self.robot_log.read_thread.content
        obs_pos = []
        obs_info = ''
        if 'StopPoints' in content:
            stoppts = content['StopPoints']
            stop_ts = np.array(stoppts['t'])
            if len(stop_ts) > 0:
                stop_idx = (np.abs(stop_ts - mid_line_t)).argmin()
                dt = (stop_ts[stop_idx] - mid_line_t).total_seconds()
                if abs(dt) < 0.5:
                    obs_pos = [stoppts['x'][stop_idx], stoppts['y'][stop_idx]]
                    stop_type = ["Ultrasonic", "Laser", "Fallingdown", "CollisionBar" ,"Infrared",
                    "VirtualPoint", "APIObstacle", "ReservedPoint", "DiUltrasonic", "DepthCamera", 
                    "ReservedDepthCamera", "DistanceNode"]
                    cur_type = "unknown"
                    tmp_id = (int)(stoppts['category'][stop_idx])
                    if tmp_id >= 0 and tmp_id < len(stop_type):
                        cur_type = stop_type[(int)(stoppts['category'][stop_idx])]
                    obs_info = "x: {} y: {} 类型: {} id:{} 距离: {}".format(stoppts['x'][stop_idx],
                        stoppts['y'][stop_idx],cur_type,(int)(stoppts['ultra_id'][stop_idx]), stoppts['dist'][stop_idx])

        if obs_info != '':
            self.obs_lable.setText('障碍物信息: ' + obs_info)
            self.obs_lable.show()
        else:
            self.obs_lable.setText('')
        if obs_pos:
            self.obs_points.set_xdata([obs_pos[0]])
            self.obs_points.set_ydata([obs_pos[1]])
        else:
            self.obs_points.set_xdata([])
            self.obs_points.set_ydata([])
    
    def updateDepth(self):
        if self.robot_log is None:
            return
        if self.robot_log.mid_line_t is None:
            return
        mid_line_t = self.robot_log.mid_line_t      
        depthCamera_idx = 0
        depth = self.robot_log.read_thread.depthcamera
        depth_t = np.array(depth.t())
        depth_pos = []
        if len(depth_t) > 0:
            depthCamera_idx = (np.abs(depth_t- mid_line_t)).argmin()
            dt = (depth_t[depthCamera_idx] - mid_line_t).total_seconds()
            if abs(dt) < 0.5:
                pos_x = depth.x()[0][depthCamera_idx]
                pos_y = depth.y()[0][depthCamera_idx]
                pos_z = depth.z()[0][depthCamera_idx]
                depth_pos = np.array([pos_x, pos_y, pos_z])

        if len(depth_pos) > 0:
            hole_points = [[],[]]
            obs_points = [[],[]]
            for ind, val in enumerate(depth_pos[2]):
                if val < 0:
                    hole_points[0].append(depth_pos[0][ind])
                    hole_points[1].append(depth_pos[1][ind])
                else:
                    obs_points[0].append(depth_pos[0][ind])
                    obs_points[1].append(depth_pos[1][ind])
            self.depthCamera_hole_points.set_xdata([hole_points[0]])
            self.depthCamera_hole_points.set_ydata([hole_points[1]])
            self.depthCamera_obs_points.set_xdata([obs_points[0]])
            self.depthCamera_obs_points.set_ydata([obs_points[1]])
        else:
            self.depthCamera_hole_points.set_xdata([])
            self.depthCamera_hole_points.set_ydata([])
            self.depthCamera_obs_points.set_xdata([])
            self.depthCamera_obs_points.set_ydata([])

    def updateParticle(self):
        if self.robot_log is None:
            return
        if self.robot_log.mid_line_t is None:
            return
        mid_line_t = self.robot_log.mid_line_t
        particle = self.robot_log.read_thread.particle
        particle_idx = 0
        pt = np.array(particle.t())
        particle_pos = []
        if len(pt) > 0:
            particle_idx = (np.abs(pt- mid_line_t)).argmin()
            dt = (pt[particle_idx] - mid_line_t).total_seconds()
            if abs(dt) < 0.5:
                pos_x = particle.x()[0][particle_idx]
                pos_y = particle.y()[0][particle_idx]
                theta = particle.theta()[0][particle_idx]
                particle_pos = np.array([pos_x, pos_y, theta])
        if len(particle_pos) > 0:
            points = [[],[]]
            for ind, val in enumerate(particle_pos[2]):
                points[0].append(particle_pos[0][ind])
                points[1].append(particle_pos[1][ind])
            self.particle_points.set_xdata([points[0]])
            self.particle_points.set_ydata([points[1]])
        else:
            self.particle_points.set_xdata([])
            self.particle_points.set_ydata([])
    
    def updateLoc(self):
        if self.robot_log is None:
            return
        if self.robot_log.mid_line_t is None:
            return
        mid_line_t = self.robot_log.mid_line_t
        content = self.robot_log.read_thread.content
        if 'LocationEachFrame' not in content:
            return
        loc = content['LocationEachFrame']  
        if len(loc['x']) < 1:
            return
        if len(loc['timestamp']) < 1:
            return
        loc_idx = self.robot_log.key_loc_idx
        if loc_idx < 0:
            loc_ts = np.array(loc['t'])
            loc_idx = (np.abs(loc_ts - mid_line_t)).argmin()
        if loc_idx < 1:
            loc_idx = 1
        self.robot_log.key_loc_idx = loc_idx

        self.robot_loc_pos = [loc['x'][loc_idx],loc['y'][loc_idx],np.deg2rad(loc['theta'][loc_idx])]
        loc_info = "{},{},{},{},{}".format(loc['t'][loc_idx], (int)(loc['timestamp'][loc_idx]), 
            loc['x'][loc_idx], loc['y'][loc_idx], loc['theta'][loc_idx])
        self.logt_lable.setText('当前时刻定位(虚框): '+ loc_info)

        if self.laser_index in self.laser_pos.keys() \
         and self.read_model.tail and self.read_model.head and self.read_model.width:
            xdata = [-self.read_model.tail, -self.read_model.tail, self.read_model.head, self.read_model.head, -self.read_model.tail]
            ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, self.read_model.width/2, self.read_model.width/2]
            robot_shape = np.array([xdata, ydata])
            xxdata = [-0.05, 0.05, 0.0, 0.0, 0.0]
            xydata = [0.0, 0.0, 0.0, 0.05, -0.05]
            cross_shape = np.array([xxdata,xydata])


            cross_shape = GetGlobalPos(cross_shape,self.robot_loc_pos)
            robot_shape = GetGlobalPos(robot_shape,self.robot_loc_pos)
            self.robot_loc_data_c0.set_xdata(cross_shape[0])
            self.robot_loc_data_c0.set_ydata(cross_shape[1])
            self.robot_loc_data.set_xdata(robot_shape[0])
            self.robot_loc_data.set_ydata(robot_shape[1])
        
        self.updateLaser()

    def updateLaser(self):
        if self.robot_log is None:
            return
        if self.robot_log.mid_line_t is None:
            return
        mid_line_t = self.robot_log.mid_line_t
        content = self.robot_log.read_thread.content
        if 'LocationEachFrame' not in content:
            return
        loc = content['LocationEachFrame']      
        if len(loc['x']) < 1:
            return
        if len(loc['timestamp']) < 1:
            return
        laser_data = self.robot_log.read_thread.laser
        if len(laser_data.datas) < 1:
            return
        loc_idx = self.robot_log.key_loc_idx
        if loc_idx < 0:
            return
        laser_idx = self.robot_log.key_laser_idx
        min_laser_channel = self.robot_log.key_laser_channel
        if laser_idx < 0 or min_laser_channel < 0:
            if min_laser_channel < 0: 
                min_laser_channel = list(laser_data.datas.keys())[0]
            if laser_idx < 0:
                laser_idx = 0
            min_dt = None
            for index in laser_data.datas.keys():
                t = np.array(laser_data.t(index))
                if len(t) < 1:
                    continue
                ischecked = False
                if index in self.check_lasers:
                    if self.check_lasers[index].isChecked():
                        ischecked = True
                if not ischecked:
                    continue
                tmp_laser_idx = (np.abs(t - mid_line_t)).argmin()
                tmp_dt = np.min(np.abs(t - mid_line_t))
                if min_dt == None or tmp_dt < min_dt:
                    min_laser_channel = index
                    laser_idx = tmp_laser_idx
                    min_dt = tmp_dt
        self.robot_log.key_laser_idx = laser_idx
        self.key_laser_channel = min_laser_channel

        print("min_laser_channel", min_laser_channel, laser_idx)
        laser_x = laser_data.x(min_laser_channel)[0][laser_idx]
        laser_y = laser_data.y(min_laser_channel)[0][laser_idx]
        laser_points = np.array([laser_x, laser_y])
        rssi = np.array(laser_data.rssi(min_laser_channel)[0][laser_idx])
        #在一个区间内差找最小值
        ts = laser_data.ts(min_laser_channel)[0][laser_idx]

        loc_min_ind = loc_idx - 200
        loc_max_ind = loc_idx + 200
        if loc_min_ind < 0:
            loc_min_ind = 0
        if loc_max_ind >= len(loc['timestamp']):
            loc_max_ind = len(loc['timestamp']) - 1
            if loc_max_ind < 0:
                loc_max_ind = 0
        pos_ts = np.array(loc['timestamp'][loc_min_ind:loc_max_ind])
        pos_idx = (np.abs(pos_ts - ts)).argmin()
        pos_idx = loc_min_ind + pos_idx
        self.robot_pos = [loc['x'][pos_idx], loc['y'][pos_idx], np.deg2rad(loc['theta'][pos_idx])]
        laser_info = "{},{},{},{},{}".format(loc['t'][pos_idx], (int)(loc['timestamp'][pos_idx]), 
            loc['x'][pos_idx], loc['y'][pos_idx], loc['theta'][pos_idx])
        self.timestamp_lable.setText('当前激光时刻定位（实框）: '+ laser_info)

        self.laser_org_data = laser_points
        laser_rssi = rssi
        if len(laser_rssi) == len(self.laser_org_data.T) and len(laser_rssi) > 0:
            color = self.cm(laser_rssi/255.) # 将透过率变成颜色变化
            self.laser_point_color = self.cm(laser_rssi/255.)
            self.laser_point_color[:,3] = self.laser_point_color[:,3]*0.5
            color[:,3] = color[:,3] * 0.2 # 改变透明度
            self.laser_color = color
        else:
            self.laser_color = self.laser_org_color[:]
            self.laser_point_color = self.laser_point_org_color[:]
        self.laser_index = min_laser_channel

        if self.laser_index in self.laser_pos.keys() \
         and self.read_model.tail and self.read_model.head and self.read_model.width:
            xdata = [-self.read_model.tail, -self.read_model.tail, self.read_model.head, self.read_model.head, -self.read_model.tail]
            ydata = [self.read_model.width/2, -self.read_model.width/2, -self.read_model.width/2, self.read_model.width/2, self.read_model.width/2]
            robot_shape = np.array([xdata, ydata])
            xxdata = [-0.05, 0.05, 0.0, 0.0, 0.0]
            xydata = [0.0, 0.0, 0.0, 0.05, -0.05]
            cross_shape = np.array([xxdata,xydata])

            robot_shape = GetGlobalPos(robot_shape,self.robot_pos)
            self.robot_data.set_xdata(robot_shape[0])
            self.robot_data.set_ydata(robot_shape[1])
            cross_shape = GetGlobalPos(cross_shape,self.robot_pos)
            self.robot_data_c0.set_xdata(cross_shape[0])
            self.robot_data_c0.set_ydata(cross_shape[1])
            if self.laser_index in self.check_lasers:
                self.laser_data.set_visible(self.check_lasers[self.laser_index].isChecked())
                self.laser_data_points.set_visible(self.check_lasers[self.laser_index].isChecked())
            if self.laser_index not in self.laser_pos:
                print(" no laser_index", self.laser_index, self.laser_pos)
                return
            if len(self.laser_org_data) < 1:
                print(" len(self.laser_org_data)", len(self.laser_org_data))
                return
            lines, cs = convert2LaserPoints(self.laser_org_data, self.laser_pos[self.laser_index], self.robot_pos)
            self.laser_data.set_segments(lines)
            self.laser_data.set_color(self.laser_color)
            patches = []
            self.org_laser_data = cs
            for c in cs:
                circle = Circle((c[0], c[1]), 0.01)
                patches.append(circle)
            self.laser_data_points.set_paths(patches)
            self.laser_data_points.set_color(self.laser_point_color)
            self.laser_data_points.set_edgecolor('r')

    def updateMapAndShape(self):
        map_name = None
        rstatus = self.robot_log.read_thread.rstatus
        if len(rstatus.chassis()[1]) > 0:
            ts = np.array(rstatus.chassis()[1])
            idx = (np.abs(ts - self.mid_line_t)).argmin()
            j = js.loads(rstatus.chassis()[0][idx])   
            map_name = j.get("CURRENT_MAP",None)
            if map_name == None:
                map_name = j.get("debug:current_map",None)
            if map_name:
                map_name = map_name + ".smap"
        fs = self.robot_log.filenames
        if fs:
            full_map_name = None
            dir_name, _ = os.path.split(fs[0])
            pdir_name, _ = os.path.split(dir_name)
            if map_name:
                map_dir = os.path.join(pdir_name,"maps")
                full_map_name = os.path.join(map_dir,map_name)
                if not os.path.exists(full_map_name):
                    map_dir = dir_name
                    full_map_name = os.path.join(map_dir,map_name)
                    if not os.path.exists(full_map_name):
                        map_dir = os.path.join(dir_name,"maps")
                        full_map_name = os.path.join(map_dir,map_name)
                        if not os.path.exists(full_map_name):
                            full_map_name = None
                if full_map_name == self.map_name:
                    full_map_name = None

            model_dir = os.path.join(pdir_name,"models")
            model_name = os.path.join(model_dir,"robot.model")
            cp_name = os.path.join(model_dir,"robot.cp")
            if not os.path.exists(model_name):
                model_dir = dir_name
                model_name = os.path.join(model_dir,"robot.model")
                cp_name = os.path.join(model_dir,"robot.cp")
                if not os.path.exists(model_name):
                    model_dir = os.path.join(dir_name,"models")
                    model_name = os.path.join(model_dir,"robot.model")
                    cp_name = os.path.join(model_dir,"robot.cp")
                    if not os.path.exists(model_name):
                        model_name = None      
            if model_name == self.model_name:
                model_name = None
            if cp_name == self.cp_name:
                cp_name = None
            self.readFiles([full_map_name, model_name, cp_name]) 
        else:
            self.readFiles([None, None, None])     

    def readtrajectory(self):
        if self.robot_log is None:
            return
        if self.robot_log.mid_line_t is None:
            return
        mid_line_t = self.robot_log.mid_line_t
        content = self.robot_log.read_thread.content
        if 'LocationEachFrame' not in content:
            return
        loc = content['LocationEachFrame']  
        if len(loc['x']) < 1:
            return
        if len(loc['timestamp']) < 1:
            return
        loc_idx = self.robot_log.key_loc_idx
        if loc_idx < 0:
            return
        if loc_idx < 1:
            loc_idx = 1
        if self.left_line_t != self.robot_log.left_line_t:
            self.left_line_t = self.robot_log.left_line_t
            loc_ts = np.array(loc['t'])
            self.left_idx = (np.abs(loc_ts - self.left_line_t)).argmin()
        if self.right_line_t != self.robot_log.right_line_t:
            self.right_line_t = self.robot_log.right_line_t
            loc_ts = np.array(loc['t'][self.left_idx::])
            self.right_idx = (np.abs(loc_ts - self.right_line_t)).argmin() + self.left_idx            
        x,y,xn,yn = [],[],[],[]
        print("idx: ", loc_idx, self.left_idx, self.right_idx)
        if self.left_idx >= self.right_idx:
            logging.debug("readtrajectory left_idx larger than right_idx{} {}".format(self.left_idx, self.right_idx))
            self.left_idx = 0
            self.right_idx = len(loc['x'])
        if loc_idx <= self.left_idx:
            xn = loc['x'][self.left_idx:self.right_idx]
            yn = loc['y'][self.left_idx:self.right_idx]
        elif loc_idx > self.left_idx and loc_idx <= self.right_idx:
            x = loc['x'][self.left_idx:loc_idx]
            y = loc['y'][self.left_idx:loc_idx]
            xn = loc['x'][loc_idx:self.right_idx]
            yn = loc['y'][loc_idx:self.right_idx]
        elif loc_idx >= self.right_idx:
                x = loc['x'][self.left_idx:self.right_idx]
                y = loc['y'][self.left_idx:self.right_idx]      

        x0 = loc['x'][loc_idx]
        y0 = loc['y'][loc_idx]
        r0 = np.deg2rad(loc['theta'][loc_idx])

        self.trajectory.set_xdata(x)
        self.trajectory.set_ydata(y)
        self.trajectory_next.set_xdata(xn)
        self.trajectory_next.set_ydata(yn)

        data = self.org_arrow_xy.copy()
        tmp_data = data.copy()
        data[:,0]= tmp_data[:,0] * np.cos(r0) - tmp_data[:,1] * np.sin(r0)
        data[:,1] = tmp_data[:,0] * np.sin(r0) + tmp_data[:,1] * np.cos(r0)
        data = data + [x0, y0]
        self.cur_arrow.set_xy(data)

        if len(self.draw_size) != 4 and len(x) > 0 and len(y) > 0:
                xmax = max(x) + 10 
                xmin = min(x) - 10
                ymax = max(y) + 10
                ymin = min(y) - 10
                self.draw_size = [xmin,xmax, ymin, ymax]
                self.ax.set_xlim(xmin, xmax)
                self.ax.set_ylim(ymin, ymax)

        if not self.check_odo.isChecked():
            return
        if 'Odometer' not in content:
            return
        odox = self.robot_log.read_thread.getData('Odometer.x')[0]
        if len(odox) < 1:
            print("odox is less than 1")
            x,y,xn,yn = [],[],[],[]
            self.odo.set_xdata(x)
            self.odo.set_ydata(y)
            self.odo_next.set_xdata(xn)
            self.odo_next.set_ydata(yn)
            return
        odo = content["Odometer"]
        odo_ts = np.array(odo['t'])
        odo_mid_idx = (np.abs(odo_ts - self.mid_line_t)).argmin()  
        odo_left_idx = (np.abs(odo_ts - self.left_line_t)).argmin()  
        odo_right_idx = (np.abs(odo_ts[odo_left_idx::] - self.right_line_t)).argmin() + odo_left_idx
        if odo_left_idx >= odo_right_idx:
            return
        ox = np.array(odo['x'][odo_left_idx:odo_right_idx])
        oy = np.array(odo['y'][odo_left_idx:odo_right_idx])
        otheta = np.deg2rad(odo['theta'][odo_left_idx:odo_right_idx])
        x0 = loc['x'][self.left_idx]
        y0 = loc['y'][self.left_idx]
        theta0 = np.deg2rad(loc['theta'][self.left_idx])
        o0 = [ox[0],oy[0],otheta[0]]
        l0 = [x0,y0,theta0]
        oPos2o0 = Pos2Base([ox, oy, otheta], o0) # coordinator transform
        oPos = GetGlobalPos(oPos2o0, l0)
        print("oPos", oPos[0][0], oPos[1][0], l0[0], l0[1])
        odo_mid_idx = odo_mid_idx - odo_left_idx
        odo_right_idx = odo_right_idx - odo_left_idx
        odo_left_idx = 0
        x,y,xn,yn = [],[],[],[]
        # print("idx: ", odo_mid_idx, odo_left_idx, odo_right_idx)
        if odo_mid_idx <= odo_left_idx:
            xn = oPos[0][odo_left_idx:odo_right_idx]
            yn = oPos[1][odo_left_idx:odo_right_idx]
        elif odo_mid_idx > odo_left_idx and odo_mid_idx <= odo_right_idx:
            x = oPos[0][odo_left_idx:odo_mid_idx]
            y = oPos[1][odo_left_idx:odo_mid_idx]
            xn = oPos[0][odo_mid_idx:odo_right_idx]
            yn = oPos[1][odo_mid_idx:odo_right_idx]
        elif odo_mid_idx >= odo_right_idx:
            x = oPos[0][odo_left_idx:odo_right_idx]
            y = oPos[1][odo_left_idx:odo_right_idx] 
        self.odo.set_xdata(x)
        self.odo.set_ydata(y)
        self.odo_next.set_xdata(xn)
        self.odo_next.set_ydata(yn)

    def updateRobotData(self):
        if self.robot_log is not None and not self.isHidden():
            if self.mid_line_t != self.robot_log.mid_line_t:
                self.mid_line_t = self.robot_log.mid_line_t
                self.updateMapAndShape()
                self.updateObs()
                self.updateDepth()
                self.updateParticle()
                self.updateLoc()
                self.readtrajectory()
                if self.draw_center.isChecked():
                    (xmin, xmax) = self.ax.get_xlim()
                    (ymin, ymax) = self.ax.get_ylim()
                    x0 = (xmin + xmax)/2.0
                    y0 = (ymin + ymax)/2.0
                    dx = self.robot_loc_pos[0] - x0
                    dy = self.robot_loc_pos[1] - y0
                    self.ax.set_xlim(xmin + dx, xmax + dx)
                    self.ax.set_ylim(ymin + dy, ymax + dy)
                self.redraw()
            elif self.left_line_t != self.robot_log.left_line_t \
                or self.right_line_t != self.robot_log.right_line_t:
                self.readtrajectory()
                self.redraw()

    def redraw(self):
        self.static_canvas.figure.canvas.draw()


if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = MapWidget(None)
    form.show()
    app.exec_()
