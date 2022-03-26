from cv2 import log
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

class TargetPrecision(QtWidgets.QWidget):
    dropped = pyqtSignal('PyQt_PyObject')
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self, data:ReadThread):
        super(QtWidgets.QWidget, self).__init__()
        self.setWindowTitle('TargetPrecision')
        self.log_data = data
        self.targetName = ""
        self.xdata = []
        self.ydata = []
        self.adata = []
        self.tdata = []
        self.draw_size = []
        self.xy_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.px_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.py_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.pa_data = lines.Line2D([],[], marker = '.', linestyle = '', markersize=10)
        self.setupUI()

    def analysis(self):
        self.targetName = "Task finished : "+ self.find_edit.text()
        logging.debug("analysis target: {}".format(self.targetName))
        if not isinstance(self.log_data, ReadThread):
            logging.debug("log_data type is error. {}".format(type(self.log_data)))
            return 
        if 'LocationEachFrame' not in self.log_data.content:
            logging.debug("LocationEachFrame is not in the log")
            return
        data = self.log_data.taskfinish.content()
        locx = self.log_data.content['LocationEachFrame']['x']
        locy = self.log_data.content['LocationEachFrame']['y']
        loca = self.log_data.content['LocationEachFrame']['theta']
        loc_t = np.array(self.log_data.content['LocationEachFrame']['t'])
        last_ind = 0
        xdata = []
        ydata = []
        adata = []
        tdata = []
        for ind, t in enumerate(data[1]):
            if self.targetName in data[0][ind]:
                loc_idx = (np.abs(loc_t - t)).argmin()
                if loc_idx < len(loc_t):
                    loc_idx += 1
                xdata.append(locx[loc_idx])
                ydata.append(locy[loc_idx])
                adata.append(loca[loc_idx])
                tdata.append(loc_t[loc_idx])
        self.xdata = xdata
        self.ydata = ydata
        self.adata = adata
        self.tdata = tdata
        self.xy_data.set_xdata(self.xdata)
        self.xy_data.set_ydata(self.ydata)

        self.px_data.set_xdata(self.tdata)
        self.px_data.set_ydata(self.xdata)
        self.py_data.set_xdata(self.tdata)
        self.py_data.set_ydata(self.ydata)
        self.pa_data.set_xdata(self.tdata)
        self.pa_data.set_ydata(self.adata)


        if len(xdata) < 1:
            logging.debug("cannot find target name: {}".format(self.targetName))
        else:
            xmin, ymin ,amin, tmin = 0.,0.,0.,0.
            xmax, ymax, amax, tmax = 1.,1.,1.,1.
            xrange, yrange, arange = 0., 0., 0.
            xmin = min(xdata)
            xmax = max(xdata)
            xrange = xmax - xmin
            ymin = min(ydata)
            ymax = max(ydata)
            yrange = ymax - ymin
            amin = min(adata)
            amax = max(adata)
            arange = amax - amin
            tmin = min(tdata)
            tmax = max(tdata)
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
        self.ax.add_line(self.xy_data)
        self.ax.grid(True)
        self.ax.axis('auto')
        self.ax.set_xlabel('x (m)')
        self.ax.set_ylabel('y (m)')
        self.ruler = RulerShape()
        self.ruler.add_ruler(self.ax)
        self.toolbar = MyToolBar(self.static_canvas, self, ruler = self.ruler)
        self.toolbar.fig_ratio = 1
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
        self.paxs[0].set_ylabel('x (m)')
        self.paxs[1].add_line(self.py_data)
        self.paxs[1].set_ylabel('y (m)')
        self.paxs[2].add_line(self.pa_data)
        self.paxs[2].set_ylabel('theta (degree)')
        self.pruler = RulerShapeMap()
        for a in self.paxs:
            a.grid(True)
            a.axis('auto')
            self.pruler.add_ruler(a)
        self.ptoolbar = MyToolBar(self.pstatic_canvas, self, ruler = self.pruler)
        self.ptoolbar.fig_ratio = 1
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

        tab = QtWidgets.QTabWidget()
        tab.addTab(w0, "xy chart")
        tab.addTab(w1, "detail chart")
 
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.find_label)
        hbox.addWidget(self.find_edit)
        hbox.addWidget(self.find_up)
        self.fig_layout = QtWidgets.QVBoxLayout(self)
        self.fig_layout.addLayout(hbox)
        self.fig_layout.addWidget(tab)

if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = TargetPrecision(None)
    form.show()
    app.exec_()