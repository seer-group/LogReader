from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.lines as lines
from matplotlib.patches import Circle, Polygon
from PyQt5 import QtGui, QtCore,QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import numpy as np
import json as js
import os
from MyToolBar import MyToolBar, keepRatio, RulerShape, RulerShapeMap
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
from ReadThread import ReadThread
import logging
from datetime import timedelta
from loglibPlus import num2date, date2num
class TargetPrecision(QtWidgets.QWidget):
    dropped = pyqtSignal('PyQt_PyObject')
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self, loggui = None):
        super(QtWidgets.QWidget, self).__init__()
        self.setWindowTitle('TargetPrecision')
        self.robot_log = loggui
        self.log_data = None
        if self.robot_log is not None:
            self.log_data = self.robot_log.read_thread
        self.targetName = ""
        self.xdata = []
        self.ydata = []
        self.adata = []
        self.tdata = []
        self.draw_size = []
        self.xy_data_old = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10, color= 'darkblue') # 当前时间线之前的数据
        self.xy_data_new = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10, color= 'skyblue') # 当前时间线之后的数据
        self.map_xy = lines.Line2D([],[], marker = '*', linestyle = '', markersize=10, color='r')
        self.map_x = lines.Line2D([],[], linestyle = '-', markersize=10, color= 'r')
        self.map_y = lines.Line2D([],[], linestyle = '-', markersize=10, color='r')
        self.map_a = lines.Line2D([],[], linestyle = '-', markersize=10, color='r')
        self.mid_xy = lines.Line2D([],[], marker = 'x', linestyle = '', markersize=10, color= 'g')
        self.mid_x = lines.Line2D([],[], linestyle = '-', markersize=10, color= 'g')
        self.mid_y = lines.Line2D([],[], linestyle = '-', markersize=10, color='g')
        self.mid_a = lines.Line2D([],[], linestyle = '-', markersize=10, color='g')
        self.px_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.py_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.pa_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.setupUI()

    def analysis(self):
        self.targetName = "Task finished : "+ self.find_edit.text()
        sleepTime = float(self.st_edit.text())
        logging.debug("Analysis target: {}. Sleep Time {}".format(self.targetName, sleepTime))
        sleepTime = timedelta(seconds=sleepTime)
        if not isinstance(self.log_data, ReadThread):
            logging.debug("log_data type is error. {}".format(type(self.log_data)))
            return 
        if 'LocationEachFrame' not in self.log_data.content:
            logging.debug("LocationEachFrame is not in the log")
            return
        map_x = None
        map_y = None
        map_a = None
        try:
            lm_id = self.find_edit.text()
            self.ax.set_title('')
            if lm_id in self.robot_log.map_widget.read_map.points:
                m_xy = self.robot_log.map_widget.read_map.points[lm_id]
                map_x = [m_xy[0]]
                map_y = [m_xy[1]]
                map_a = [m_xy[2]/math.pi *180.0]
                self.ax.set_title(m_xy[3])
        except:
            pass

        data = self.log_data.taskfinish.content()
        valid = []
        vx = self.log_data.getData('Speed2DSP.vx')[0]
        vy = self.log_data.content['Speed2DSP']['vy']
        vt = np.array(self.log_data.content['Speed2DSP']['t'])
        if self.choose.currentText() == 'Localization':
            locx = self.log_data.content['LocationEachFrame']['x']
            locy = self.log_data.content['LocationEachFrame']['y']
            loca = self.log_data.content['LocationEachFrame']['theta']
            loc_t = np.array(self.log_data.content['LocationEachFrame']['t'])
            valid = [1.0 for _ in loc_t]
        elif self.choose.currentText() == 'pgv0':
            map_x = [0]
            map_y = [0]
            map_a = [0]
            locx = self.log_data.getData('pgv0.tag_x')[0]
            locy = self.log_data.content['pgv0']['tag_y']
            loca = self.log_data.content['pgv0']['tag_angle']
            loc_t = np.array(self.log_data.content['pgv0']['t'])
            valid = self.log_data.content['pgv0']['is_DMT_detected']
        elif self.choose.currentText() == 'pgv1':
            map_x = [0]
            map_y = [0]
            map_a = [0]
            locx = self.log_data.getData('pgv1.tag_x')[0]
            locy = self.log_data.content['pgv1']['tag_y']
            loca = self.log_data.content['pgv1']['tag_angle']
            loc_t = np.array(self.log_data.content['pgv1']['t'])
            valid = self.log_data.content['pgv1']['is_DMT_detected']
        elif self.choose.currentText() == 'SimLocation':
            locx = self.log_data.getData('SimLocation.x')[0]
            locy = self.log_data.content['SimLocation']['y']
            loca = self.log_data.content['SimLocation']['theta']
            loc_t = np.array(self.log_data.content['SimLocation']['t'])
            valid = [1.0 for _ in loc_t]
        else:
            logging.debug("source name is wrong! {}".format(self.choose.currentText()))
        last_ind = 0
        mid_t = self.robot_log.mid_line_t # 中间线的时间
        tmid = None # 对应的序号
        xdata = []
        ydata = []
        adata = []
        tdata = []
        tl, tr = None, None
        drange = self.r.currentText()
        if drange == "View":
            xmin, xmax = self.robot_log.axs[0].get_xlim()
            tl = num2date(xmin)
            tr = num2date(xmax)
        elif drange == "Selection":
            tl = self.robot_log.left_line_t
            tr = self.robot_log.right_line_t
        if tl is not None and tr is not None and tl >= tr:
            # 如果左边大于右边则忽略
            tl = None
            tr = None
        print(len(data[1]), len(data[0]))
        for ind, t in enumerate(data[1]):
            if self.targetName in data[0][ind]:
                t = t + sleepTime
                if tl is not None and tr is not None:
                    if t < tl or t > tr:
                        continue
                if tmid == None and mid_t != None and t > mid_t:
                    tmid = len(xdata) # 中间线的序号
                # 如果到点的速度很大表示，这个是中间点
                v_idx = (np.abs(vt - t)).argmin()
                if v_idx + 1 < len(vt):
                    v_idx += 1
                print(vx[v_idx], vy[v_idx], v_idx)
                if abs(vx[v_idx]) > 0.0001 or abs(vy[v_idx]) > 0.0001:
                    continue
                loc_idx = (np.abs(loc_t - t)).argmin()
                if loc_idx+1 < len(loc_t):
                    loc_idx += 1
                if valid[loc_idx] > 0.1:
                    xdata.append(locx[loc_idx])
                    ydata.append(locy[loc_idx])
                    adata.append(loca[loc_idx])
                    tdata.append(loc_t[loc_idx])
        if len(xdata) < 1:
            title = "cannot find target name: {}".format(lm_id)
            logging.debug("cannot find target name: {}".format(lm_id))
            self.ax.set_title(title)
        else:
            self.ax.set_title(lm_id)
            self.xdata = xdata
            self.ydata = ydata
            self.adata = adata
            self.tdata = tdata
            if tmid == None:
                self.xy_data_old.set_xdata(self.xdata)
                self.xy_data_old.set_ydata(self.ydata)
                self.xy_data_new.set_xdata([])
                self.xy_data_new.set_ydata([])
            else:
                self.xy_data_old.set_xdata(self.xdata[:tmid])
                self.xy_data_old.set_ydata(self.ydata[:tmid])
                self.xy_data_new.set_xdata(self.xdata[tmid:])
                self.xy_data_new.set_ydata(self.ydata[tmid:])
            self.px_data.set_xdata(self.tdata)
            self.px_data.set_ydata(self.xdata)
            self.py_data.set_xdata(self.tdata)
            self.py_data.set_ydata(self.ydata)
            self.pa_data.set_xdata(self.tdata)
            self.pa_data.set_ydata(self.adata)

            mid_x = [sum(self.xdata)*1.0/len(self.xdata)]
            mid_y = [sum(self.ydata)*1.0/len(self.ydata)]
            mid_a = [sum(self.adata)*1.0/len(self.adata)]
            self.mid_xy.set_xdata(mid_x)
            self.mid_xy.set_ydata(mid_y)
            self.mid_x.set_xdata(self.tdata)
            self.mid_x.set_ydata(mid_x*len(self.tdata))
            self.mid_y.set_xdata(self.tdata)
            self.mid_y.set_ydata(mid_y*len(self.tdata))
            self.mid_a.set_xdata(self.tdata)
            self.mid_a.set_ydata(mid_a*len(self.tdata))

            if map_x != None and map_y != None and map_a != None:
                self.map_xy.set_xdata(map_x)
                self.map_xy.set_ydata(map_y)
                self.map_x.set_xdata(self.tdata)
                self.map_x.set_ydata(map_x*len(self.tdata))
                self.map_y.set_xdata(self.tdata)
                self.map_y.set_ydata(map_y*len(self.tdata))
                self.map_a.set_xdata(self.tdata)
                self.map_a.set_ydata(map_a*len(self.tdata))
                tmpx = xdata + map_x
                tmpy = ydata + map_y
                tmpa = adata + map_a
            else:
                tmpx = xdata
                tmpy = ydata
                tmpa = adata              

            xmin, ymin ,amin, tmin = 0.,0.,0.,0.
            xmax, ymax, amax, tmax = 1.,1.,1.,1.
            xrange, yrange, arange = 0., 0., 0.
            xmin = min(tmpx)
            xmax = max(tmpx)
            xrange = xmax - xmin
            if xrange < 1e-6:
                xrange = 1e-6
            ymin = min(tmpy)
            ymax = max(tmpy)
            yrange = ymax - ymin
            if yrange < 1e-6:
                yrange = 1e-6
            amin = min(tmpa)
            amax = max(tmpa)
            arange = amax - amin
            if arange < 1e-6:
                arange = 1e-6
            tmin = min(tdata)
            tmax = max(tdata)
            if tmin == tmax:
                tmax = num2date(date2num(tmin) + 0.0001)
                tmin = num2date(date2num(tmin) - 0.0001)
            xmin = xmin - 0.05 * xrange
            xmax = xmax + 0.05 * xrange
            ymin = ymin - 0.05 * yrange
            ymax = ymax + 0.05 * yrange
            amin = amin - 0.05 * arange
            amax = amax + 0.05 * arange

            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)


            for a in self.paxs:
                a.set_xlim(tmin, tmax)
            self.paxs[0].set_ylim(xmin, xmax)
            self.paxs[1].set_ylim(ymin, ymax)
            self.paxs[2].set_ylim(amin, amax)
        self.static_canvas.figure.canvas.draw()
        self.pstatic_canvas.figure.canvas.draw()

    def setupUI(self):
        self.static_canvas = FigureCanvas(Figure(figsize=(6,6)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.static_canvas.figure.subplots_adjust(left = 0.1, right = 0.95, bottom = 0.1, top = 0.95)
        self.static_canvas.figure.tight_layout()
        self.ax = self.static_canvas.figure.subplots(1, 1)
        self.ax.add_line(self.xy_data_old)
        self.ax.add_line(self.xy_data_new)
        self.ax.add_line(self.map_xy)
        self.ax.add_line(self.mid_xy)
        self.ax.grid(True)
        self.ax.axis('auto')
        self.ax.set_xlabel('x (m)')
        self.ax.set_ylabel('y (m)')
        self.ruler = RulerShape()
        self.ruler.add_ruler(self.ax)
        self.toolbar = MyToolBar(self.static_canvas, self, ruler = self.ruler)
        w0 = QtWidgets.QWidget()
        v0 = QtWidgets.QVBoxLayout()
        v0.addWidget(self.toolbar)
        v0.addWidget(self.static_canvas)
        w0.setLayout(v0)

        self.pstatic_canvas = FigureCanvas(Figure(figsize=(6,6)))
        self.pstatic_canvas.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.pstatic_canvas.figure.subplots_adjust(left = 0.1, right = 0.95, bottom = 0.1, top = 0.95)
        self.pstatic_canvas.figure.tight_layout()
        self.paxs= self.pstatic_canvas.figure.subplots(3, 1, sharex = True)
        self.paxs[0].add_line(self.px_data)
        self.paxs[0].add_line(self.map_x)
        self.paxs[0].add_line(self.mid_x)
        self.paxs[0].set_ylabel('x (m)')
        self.paxs[1].add_line(self.py_data)
        self.paxs[1].add_line(self.map_y)
        self.paxs[1].add_line(self.mid_y)
        self.paxs[1].set_ylabel('y (m)')
        self.paxs[2].add_line(self.pa_data)
        self.paxs[2].add_line(self.map_a)
        self.paxs[2].add_line(self.mid_a)
        self.paxs[2].set_ylabel('theta (degree)')
        self.pruler = RulerShapeMap()
        for a in self.paxs:
            a.grid(True)
            a.axis('auto')
            self.pruler.add_ruler(a)
        self.ptoolbar = MyToolBar(self.pstatic_canvas, self, ruler = self.pruler)
        w1 = QtWidgets.QWidget()
        v1 = QtWidgets.QVBoxLayout()
        v1.addWidget(self.ptoolbar)
        v1.addWidget(self.pstatic_canvas)
        w1.setLayout(v1)


        self.find_label = QtWidgets.QLabel("Target Name:")
        valid = QtGui.QIntValidator()
        self.find_edit = QtWidgets.QLineEdit()
        self.find_edit.setValidator(valid)


        self.find_up = QtWidgets.QPushButton("Analysis")
        self.find_up.clicked.connect(self.analysis)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.find_label)
        hbox.addWidget(self.find_edit)
        hbox.addWidget(self.find_up)

        self.stime_msg = QtWidgets.QLabel("SleepTime:")
        valid = QtGui.QDoubleValidator()
        self.st_edit = QtWidgets.QLineEdit("0.5")
        self.st_edit.setValidator(valid)
        hbox_s = QtWidgets.QFormLayout()
        hbox_s.addRow(self.stime_msg, self.st_edit)

        self.r_msg = QtWidgets.QLabel("Range:")
        self.r = QtWidgets.QComboBox()
        self.r.addItem("All")
        self.r.addItem("Selection")
        self.r.addItem("View")
        hbox_r = QtWidgets.QFormLayout()
        hbox_r.addRow(self.r_msg, self.r)

        hbox_st = QtWidgets.QHBoxLayout()
        hbox_st.addLayout(hbox_s)
        hbox_st.addLayout(hbox_r)


        self.choose_msg = QtWidgets.QLabel("Source:")
        self.choose = QtWidgets.QComboBox()
        self.choose.addItem("Localization")
        self.choose.addItem("pgv0")
        self.choose.addItem("pgv1")
        self.choose.addItem("SimLocation")
        hbox2 = QtWidgets.QFormLayout()
        hbox2.addRow(self.choose_msg, self.choose)

        tab = QtWidgets.QTabWidget()
        tab.addTab(w0, "xy chart")
        tab.addTab(w1, "detail chart")

 


        self.fig_layout = QtWidgets.QVBoxLayout(self)
        self.fig_layout.addLayout(hbox)
        self.fig_layout.addLayout(hbox_st)
        self.fig_layout.addLayout(hbox2)
        self.fig_layout.addWidget(tab)

if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = TargetPrecision(None)
    form.show()
    app.exec_()