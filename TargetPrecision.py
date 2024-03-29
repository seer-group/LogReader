from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.lines as lines
from matplotlib.patches import Circle, Polygon
from PyQt5 import QtGui, QtCore,QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot,Qt
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
from MapWidget import normalize_theta_deg, Pos2Base, GetGlobalPos, P2G
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

    def mouse_press(self, event):
        if not event.inaxes:
            return
        if event.button == 3:
            self.popMenu = QtWidgets.QMenu(self)
            self.popMenu.addAction('&Save Data',lambda:self.saveData())
            cursor = QtGui.QCursor()
            self.popMenu.exec_(cursor.pos())

    def saveData(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self,"选取log文件", "","PY Files (*.py)")
        # 获取数据
        outdata = []
        xdata = 'x='+str(self.xdata)
        ydata = 'y='+str(self.ydata)
        adata = "a="+str(self.adata)
        outdata.append(xdata)
        outdata.append(ydata)
        outdata.append(adata)
        # 写数据
        if fname:
            try:
                with open(fname, 'w') as fn:
                    for d in outdata:
                        fn.write(d+'\n')
            except:
                pass

    def analysis(self):
        self.targetName = "Task finished : "+ self.find_edit.text()+"]"
        sleepTime = float(self.st_edit.text())
        logging.debug("Analysis target: {}. Sleep Time {}".format(self.targetName, sleepTime))
        sleepTime = timedelta(seconds=sleepTime)
        if not isinstance(self.log_data, ReadThread):
            logging.debug("log_data type is error. {}".format(type(self.log_data)))
            return 
        if 'LocationEachFrame' not in self.log_data.content:
            logging.debug("LocationEachFrame is not in the log")
            return
        map_x = None # 地图点的坐标
        map_y = None
        map_a = None
        try:
            lm_id = self.find_edit.text()
            lm_name = ""
            self.ax.set_title('')
            if lm_id in self.robot_log.map_widget.read_map.p_names:
                lm_id = self.robot_log.map_widget.read_map.p_names[lm_id]
            if lm_id in self.robot_log.map_widget.read_map.points:
                m_xy = self.robot_log.map_widget.read_map.points[lm_id]
                map_x = [m_xy[0]]
                map_y = [m_xy[1]]
                map_a = [m_xy[2]/math.pi *180.0]
                print("map_a", map_a)
                lm_name = m_xy[3]
                self.ax.set_title(lm_name)
        except:
            pass
        data = self.log_data.taskfinish.content()
        print("map_a", map_a, "finish data ", len(data[1]))
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
        elif self.choose.currentText() == 'OptLocation':
            locx = self.log_data.getData('OptLocation.x')[0]
            locy = self.log_data.content['OptLocation']['y']
            loca = self.log_data.content['OptLocation']['theta']
            loc_t = np.array(self.log_data.content['OptLocation']['t'])
            valid = [1.0 for _ in loc_t]            
        else:
            logging.debug("source name is wrong! {}".format(self.choose.currentText()))
        if len(loc_t) < 1:
            logging.debug("data time is emtpy {}".format(self.choose.currentText()))
            return
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
        goal_pos = None  # 地图点的坐标
        if map_a != None and map_x != None and map_y != None:
            goal_pos = [copy.deepcopy(map_x[0]), copy.deepcopy(map_y[0]), copy.deepcopy(map_a[0])/180.0*math.pi]
            map_x[0] = 0
            map_y[0] = 0
            map_a[0] = 0
        regex = None
        if self.s_edit.text() != "":
            regex = self.s_edit.text()+"]"
        for ind, t in enumerate(data[1]):
            if self.targetName in data[0][ind]:
                ok_ind = False
                if regex == None:
                    ok_ind = True
                else:
                    if ind > 0:
                        if regex in data[0][ind-1].split(" ")[-1]:
                            ok_ind = True
                if not ok_ind:
                    continue
                t = t + sleepTime

                if tl is not None and tr is not None:
                    if t < tl or t > tr:
                        continue
                if tmid == None and mid_t != None and t > mid_t:
                    tmid = len(xdata) # 中间线的序号
                # 如果到点的速度很大表示，这个是中间点
                if len(vt) > 0:
                    v_idx = (np.abs(vt - t)).argmin()
                    vl_idx = v_idx
                    vr_idx = v_idx
                    if vr_idx + 1 < len(vt):
                        vr_idx += 1
                    if vl_idx - 1 >= 0:
                        vl_idx -= 1
                    if (abs(vx[vl_idx]) > 0.0001 or abs(vy[vl_idx]) > 0.0001) \
                        and (abs(vx[vr_idx]) > 0.0001 or abs(vy[vr_idx]) > 0.0001) \
                            and (abs(vx[v_idx]) > 0.0001 or abs(vy[v_idx]) > 0.0001):
                        continue
                loc_idx = (np.abs(loc_t - t)).argmin()
                if loc_idx+1 < len(loc_t):
                    loc_idx += 1
                if valid[loc_idx] > 0.1:
                    if goal_pos != None:
                        tmp_pos = [locx[loc_idx],locy[loc_idx],loca[loc_idx]/180.0*math.pi]

                        pos2goal = Pos2Base(tmp_pos, goal_pos)  # 转换成地图点坐标系
                        xdata.append(pos2goal[0])
                        ydata.append(pos2goal[1])
                        adata.append(pos2goal[2]/math.pi*180.0)
                    else:
                        xdata.append(locx[loc_idx])
                        ydata.append(locy[loc_idx])
                        adata.append(loca[loc_idx])
                    tdata.append(loc_t[loc_idx])
        if len(xdata) < 1 or len(ydata) < 1 or len(adata) < 1:
            title = "cannot find target name: {}".format(lm_id)
            logging.debug("cannot find target name: {}".format(lm_id))
            self.ax.set_title(title)
        else:
            mx = float(self.mx_edit.text())
            my = float(self.my_edit.text())
            new_xdata = []
            new_ydata = []
            for it in range(len(xdata)):
                new_d = GetGlobalPos([mx, my], [xdata[it], ydata[it], adata[it]/180.0*math.pi])
                new_xdata.append(new_d[0])
                new_ydata.append(new_d[1])
            org_xdata = xdata
            org_ydata = ydata
            xdata = new_xdata
            ydata = new_ydata
            out_xmin = min(xdata)
            out_xmax = max(xdata)
            out_xrange = (out_xmax - out_xmin) *1000
            out_xmid = 0
            if len(org_xdata) > 0:
                out_xmid = sum(org_xdata)/len(org_xdata)
            out_x_off = 0
            if map_x != None:
                out_x_off = (map_x[0] - out_xmid)*1000
            print("x", out_xmid, out_x_off, map_x[0])

            out_ymin = min(ydata)
            out_ymax = max(ydata)
            out_yrange = (out_ymax-out_ymin)*1000
            out_ymid = 0
            if len(org_ydata) > 0:
                out_ymid = sum(org_ydata)/len(org_ydata)
            out_y_off = 0
            if map_y != None:
                out_y_off = (map_y[0] - out_ymid)*1000
            print("y",out_ymid, out_y_off, map_y[0])

            out_amax = adata[0]
            out_amin = adata[0]
            for i, a in enumerate(adata):
                if i > 0:
                    dtheta_max = normalize_theta_deg(out_amax - a)
                    if dtheta_max < 0:
                        out_amax = a
                    else:
                        dtheta_min = normalize_theta_deg(out_amin- a)
                        if dtheta_min > 0:
                            out_amin = a
            out_arange = normalize_theta_deg(out_amax - out_amin)
            out_amid = 0
            suma = adata[0]
            last_a = adata[0]
            for i, a in enumerate(adata):
                if i > 0:
                    dtheta = normalize_theta_deg(a - last_a)
                    last_a = dtheta + last_a
                    suma += last_a
            out_amid = suma /(len(adata) * 1.0)
            out_a_off = 0
            if map_a != None:
                out_a_off = normalize_theta_deg((map_a[0] - out_amid))
                print("a",out_amid, out_a_off, map_a[0])
            result_str = "{}次到点{}\n".format(len(xdata), lm_name)
            result_str += "重复到点误差 x = {:4.1f} mm, y= {:4.1f} mm, theta = {:4.1f} ° \n".format( out_xrange, out_yrange, out_arange)
            result_str += "绝对到点误差 x = {:4.1f} mm, y= {:4.1f} mm, theta = {:4.1f} ° \n".format(out_x_off, out_y_off, out_a_off)
            if goal_pos != None:
                pos2map = P2G([out_xmid, out_ymid, out_amid/180.0*math.pi], goal_pos)  # 转换成地图点坐标系
                result_str += "平均坐标 {:4.3f}, {:4.3f}, {:4.3f} °".format(pos2map[0], pos2map[1], pos2map[2]/math.pi*180.0)
            else:
                result_str += "平均坐标 {:4.3f}, {:4.3f}, {:4.3f} °".format(out_xmid, out_ymid, out_amid)
            self.result_label.setText(result_str)

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
        self.static_canvas = FigureCanvas(Figure(figsize=(4,4)))
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
        self.choose.addItem("OptLocation")
        hbox2 = QtWidgets.QFormLayout()
        hbox2.addRow(self.choose_msg, self.choose)

        self.result_label = QtWidgets.QLabel()
        self.result_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.result_label.setWordWrap(True)  # 自动折叠文字，使文字全部显示
        self.result_label.setAlignment(Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.result_label.setFont(font)

        tab = QtWidgets.QTabWidget()
        tab.addTab(w0, "xy chart")
        tab.addTab(w1, "detail chart")


        self.s_label = QtWidgets.QLabel("PreTarget Name:")
        self.s_edit = QtWidgets.QLineEdit()
        sbox = QtWidgets.QHBoxLayout()
        sbox.addWidget(self.s_label)
        sbox.addWidget(self.s_edit)

        self.mx_label = QtWidgets.QLabel("MeasurePoint x:")
        self.mx_edit = QtWidgets.QLineEdit("0.0")
        valid = QtGui.QDoubleValidator()
        self.mx_edit.setValidator(valid)
        mxbox = QtWidgets.QHBoxLayout()
        mxbox.addWidget(self.mx_label)
        mxbox.addWidget(self.mx_edit)
        self.my_label = QtWidgets.QLabel("y:")
        self.my_edit = QtWidgets.QLineEdit("0.0")
        self.my_edit.setValidator(valid)
        mxbox.addWidget(self.my_label)
        mxbox.addWidget(self.my_edit)

        self.fig_layout = QtWidgets.QVBoxLayout(self)
        self.fig_layout.addLayout(hbox)
        self.fig_layout.addLayout(hbox_st)
        self.fig_layout.addLayout(hbox2)
        self.fig_layout.addLayout(sbox)
        self.fig_layout.addLayout(mxbox)
        self.fig_layout.addWidget(self.result_label)
        self.fig_layout.addWidget(tab)
        self.static_canvas.mpl_connect('button_press_event', self.mouse_press)

if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = TargetPrecision(None)
    form.show()
    app.exec_()