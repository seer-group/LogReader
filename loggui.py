import matplotlib
from enum import Enum

from searchWidget import SearchWidget

matplotlib.use('Qt5Agg')
matplotlib.rcParams['font.sans-serif']=['FangSong']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from matplotlib.figure import Figure
from datetime import datetime
from datetime import timedelta
import os, sys
from ExtendedComboBox import ExtendedComboBox
from Widget import Widget
from ReadThread import ReadThread, Fdir2Flink
from loglibPlus import ErrorLine, WarningLine, FatalLine, NoticeLine, TaskStart, TaskFinish, Service
from loglibPlus import date2num, num2date
from MapWidget import MapWidget, Readmap
from LogViewer import LogViewer
from JsonView import JsonView, DataView
from MyToolBar import MyToolBar, RulerShapeMap
import logging
import numpy as np
import traceback
import json
from multiprocessing import freeze_support
from PyQt5.QtCore import pyqtSignal
import MotorRead as mr
from getMotorErr import MotorErrViewer 
from TargetPrecision import TargetPrecision
from CmdArgs import CmdArgs
from LogDownloader import LogDownloader
from MyFileSelectionWidget import MyFileSelectionWidget
from ExtractZipThread import ExtractZipThread
from LogDownloadWidget import LogDownloadWidget
from TimedLogDownloadWidget import TimedLogDownloadWidget
from CPUPieView import CPUPieView
from MapCheckWidget import MapCheckWidget
from ParamWidget import ParamWidget
from APHeatMapWidget import APHeatMapWidget
from MoveFactoryWidget import MoveFactoryWidget

class XYSelection:
    def __init__(self, num = 1):
        self.num = num 
        self.groupBox = QtWidgets.QGroupBox('图片'+str(self.num))
        self.x_label = QtWidgets.QLabel('Time')
        self.y_label = QtWidgets.QLabel('Data')
        self.x_combo = ExtendedComboBox()
        self.y_combo = ExtendedComboBox()
        x_form = QtWidgets.QFormLayout()
        x_form.addRow(self.x_label,self.x_combo)
        y_form = QtWidgets.QFormLayout()
        y_form.addRow(self.y_label,self.y_combo)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(y_form)
        vbox.addLayout(x_form)
        self.groupBox.setLayout(vbox)


class DataSelection(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super(QtWidgets.QWidget, self).__init__()
        self.groupBox = QtWidgets.QGroupBox('增加曲线')
        self.y_label = QtWidgets.QLabel('Data')
        self.y_combo = ExtendedComboBox()
        y_form = QtWidgets.QFormLayout()
        y_form.addRow(self.y_label,self.y_combo)
        self.groupBox.setLayout(y_form)

        vbox = QtWidgets.QVBoxLayout(self)
        self.btn = QtWidgets.QPushButton("Yes") 
        self.btn.clicked.connect(self.getData)
        vbox.addWidget(self.groupBox)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Line Input")
        self.ax = None
    def initForm(self, ax, keys):
        self.ax = ax
        self.y_combo.clear()
        self.y_combo.addItems(keys)
    def getData(self):
        try:
            name = self.y_combo.currentText()
            self.hide()
            self.getdata.emit([self.ax, name])
        except:
            pass

class SelectEnum(Enum):
    NoSelect = 0
    Left = 1
    Right = 2
    Region = 3
    Mid = 4

class SelectRegion:
    def __init__(self, ax, t0, t1, tmid) -> None:
        self.ax = ax
        self.select_region = ax.axvspan(t0, t1, facecolor='r', alpha = 0.3, picker = self.pickfunc) 
        self.select_region.set_zorder(0)
        self.left_line = ax.axvline(t0, linestyle = '--', color = 'y', linewidth = 1, picker = self.pickfunc)
        self.left_line.set_zorder(0)
        self.right_line = ax.axvline(t1, linestyle = '--', color = 'y', linewidth = 1, picker = self.pickfunc)
        self.right_line.set_zorder(0)
        self.mid_line = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = self.pickfunc)
        self.mid_line.set_zorder(10)
        self.t0 = t0
        self.t1 = t1
        self.tmid = tmid
        self.select_type = SelectEnum.NoSelect
        print("init", type(self.tmid), type(self.t0), type(self.t1))

    def getRightT(self, t):
        if isinstance(t, float):
            return t
        elif isinstance(t, datetime):
            return date2num(t)
        else:
            print("getRightT t type error: ", type(t), t)
            return t
    def setRegion(self, t0, t1):
        self.t0 = self.getRightT(t0)
        self.t1 = self.getRightT(t1)              
        self.left_line.set_xdata(self.t0)
        self.right_line.set_xdata(self.t1)
        data = self.select_region.get_xy()
        data[0][0] = data[1][0] = data[4][0] = self.t0
        data[2][0] = data[3][0] = self.t1

    def setMidLine(self, tmid):
        self.tmid = self.getRightT(tmid)
        self.mid_line.set_xdata(self.tmid)

    def addAgain(self, ax):
        if ax is self.ax:
            self.ax.add_artist(self.left_line)
            self.ax.add_artist(self.right_line)
            self.ax.add_artist(self.select_region)
            self.ax.add_artist(self.mid_line)

    def getMidLineX(self):
        return self.mid_line.get_xdata()

    def pickfunc(self, artist, mouseevent):
        if artist is self.select_region or\
            artist is self.left_line or\
                artist is self.right_line or\
                    artist is self.mid_line:
            cur_t = mouseevent.xdata
            if not isinstance(cur_t, float):
                return False, dict()
            dt0 = abs(self.t0 - cur_t)
            dt1 = abs(self.t1 - cur_t)
            dtmid = abs(self.tmid -cur_t)
            ax = mouseevent.inaxes
            xmin,xmax = ax.get_xlim()
            min_step = (xmax - xmin)/40.0
            # print("pickfunc", self.t0, self.t1, self.tmid, cur_t, dt0, dt1, dtmid)
            if dtmid < min_step:
                self.select_type = SelectEnum.Mid
            elif dt0 < min_step:
                self.select_type = SelectEnum.Left
            elif dt1 < min_step:
                self.select_type = SelectEnum.Right
            elif cur_t > self.t0 and cur_t < self.t1:
                self.select_type = SelectEnum.Region
        return False, dict()

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.cmdArgs = CmdArgs.getCmdArgs()
        self.finishReadFlag = False
        self.filenames = []
        self.lines_dict = {"fatal":[],"error":[],"warning":[],"notice":[], "taskstart":[], "taskfinish":[], "service":[]} 
        self.setWindowTitle('Log分析器')
        self.read_thread = ReadThread()
        self.read_thread.signal.connect(self.readFinished)
        self.mid_line_t = None #中间蓝线对应的时间 datetime
        self.select_type = SelectEnum.NoSelect #中间蓝线是否被选择上
        self.left_line_t = None #datetime
        self.right_line_t = None #datetime
        self.select_regions = []
        self.mouse_pressed = False
        self.log_widget = None
        self.sts_widget = None
        self.motor_view_widget = None
        self.dataViews = [] #显示特定数据框
        self.in_close = False
        self.setupUI()
        self.logDownloader = None
        self.logDownload_widget = None
        self.timedLogDownload_widget = None
        self.mapCheckWidget = None
        self.fs_widget = None

        if isinstance(self.cmdArgs, str):
            self.extractZip(self.cmdArgs)
        elif self.cmdArgs.ip:
            self.downloadLog(self.cmdArgs)

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,900)
        self.max_fig_num = 6 
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.openLogFilesDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.num_menu = QtWidgets.QMenu('&Num', self)
        self.menuBar().addMenu(self.num_menu)

        self.fig_menu = QtWidgets.QMenu('&Fig', self)
        group = QtWidgets.QActionGroup(self.fig_menu)
        texts = [str(i) for i in range(2,self.max_fig_num+1)]
        cur_id = 1
        cur_fig_num = int(texts[cur_id])
        for text in texts:
            action = QtWidgets.QAction(text, self.fig_menu, checkable=True, checked=text==texts[cur_id])
            self.fig_menu.addAction(action)
            group.addAction(action)
        group.setExclusive(True)
        group.triggered.connect(self.fignum_changed)
        self.num_menu.addMenu(self.fig_menu)

        self.cpu_menu = QtWidgets.QMenu('&CPU', self)
        group = QtWidgets.QActionGroup(self.cpu_menu)
        texts = [str(i) for i in range(1, 9)]
        cur_id = 3
        cur_cpu_num = int(texts[cur_id])
        self.read_thread.cpu_num = cur_cpu_num
        for text in texts:
            action = QtWidgets.QAction(text, self.cpu_menu, checkable=True, checked=text==texts[cur_id])
            self.cpu_menu.addAction(action)
            group.addAction(action)
        group.setExclusive(True)
        group.triggered.connect(self.cpunum_changed)
        self.num_menu.addMenu(self.cpu_menu)

        self.tools_menu = QtWidgets.QMenu('&Tools', self)
        self.menuBar().addMenu(self.tools_menu)
        self.map_action = QtWidgets.QAction('&Open Map', self.tools_menu, checkable = True)
        self.map_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_M)
        self.map_action.triggered.connect(self.openMap)
        self.tools_menu.addAction(self.map_action)

        self.view_action = QtWidgets.QAction('&Open Log', self.tools_menu, checkable = True)
        self.view_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_L)
        self.view_action.triggered.connect(self.openViewer)
        self.tools_menu.addAction(self.view_action)

        self.json_action = QtWidgets.QAction('&Open Status', self.tools_menu, checkable = True)
        self.json_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_J)
        self.json_action.triggered.connect(self.openJsonView)
        self.tools_menu.addAction(self.json_action)

        self.motor_err_action = QtWidgets.QAction('&View Motor Err', self.tools_menu, checkable = True)
        self.motor_err_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_R)
        self.motor_err_action.triggered.connect(self.viewMotorErr)
        self.tools_menu.addAction(self.motor_err_action)

        self.data_action = QtWidgets.QAction('&Open Data', self.tools_menu, checkable = True)
        self.data_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_D)
        self.data_action.setChecked(True)
        self.data_action.triggered.connect(self.openDataView)
        self.tools_menu.addAction(self.data_action)

        self.motor_follow_action = QtWidgets.QAction('&View Motor Follow Cure', self.tools_menu, checkable = True)
        self.motor_follow_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_K)
        self.motor_follow_action.triggered.connect(self.drawMotorFollow)
        self.tools_menu.addAction(self.motor_follow_action)

        self.precision = QtWidgets.QAction('&TargetPrecision', self.tools_menu, checkable = True)
        self.precision.triggered.connect(self.openPrecision)
        self.tools_menu.addAction(self.precision)

        self.moveFactory_action = QtWidgets.QAction('&MoveFactoryList', self.tools_menu, checkable = True)
        self.moveFactory_action.triggered.connect(self.openMoveFactoryWidget)
        self.tools_menu.addAction(self.moveFactory_action)

        self.cpuPie_action = QtWidgets.QAction("&CPU饼图", self.tools_menu, checkable=True)
        self.cpuPie_action.triggered.connect(self.openCPUPie)
        self.tools_menu.addAction(self.cpuPie_action)

        self.heatMap_action = QtWidgets.QAction("&网络信号热力图", self.tools_menu, checkable=True)
        self.heatMap_action.triggered.connect(self.openHeatMapWidget)
        self.tools_menu.addAction(self.heatMap_action)

        self.param_action = QtWidgets.QAction("&查看param文件",self.tools_menu, checkable=True)
        self.param_action.triggered.connect(self.openParamWidget)
        self.tools_menu.addAction(self.param_action)

        self.logdownload_action = QtWidgets.QAction("&Log下载", self.tools_menu)
        self.logdownload_action.triggered.connect(self.openLogDownloadWidget)
        self.tools_menu.addAction(self.logdownload_action)

        self.logdownload_action2 = QtWidgets.QAction("&批量定时log下载", self.tools_menu)
        self.logdownload_action2.triggered.connect(self.openTimedLogDownloadWidget)
        self.tools_menu.addAction(self.logdownload_action2)

        self.mapCheck_action = QtWidgets.QAction("&地图检查", self.tools_menu)
        self.mapCheck_action.triggered.connect(self.openMapCheckWidget)
        self.tools_menu.addAction(self.mapCheck_action)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)
        self.menuBar().addMenu(self.help_menu)

        self._main = Widget()
        self._main.dropped.connect(self.dragFiles)
        self.setCentralWidget(self._main)
        self.layout = QtWidgets.QVBoxLayout(self._main)
        self.searchWidget = SearchWidget(self.read_thread, self._main)
        self.searchWidget.hide()
        def moveTo(i):
            self.info.setText(self.get_content(i))
            self.resetMidLineProperty(i)
            self.updateMap()
        self.searchWidget.nextMove.connect(moveTo)
        self.layout.addWidget(self.searchWidget)
        #Add ComboBox
        self.xys = []
        self.xy_hbox = QtWidgets.QHBoxLayout()
        for i in range(0,cur_fig_num):
            selection = XYSelection(i+1)
            selection.y_combo.activated.connect(self.ycombo_onActivated)
            selection.x_combo.activated.connect(self.xcombo_onActivated)
            self.xys.append(selection)
            self.xy_hbox.addWidget(selection.groupBox)
        self.layout.addLayout(self.xy_hbox)

        #消息框
        # self.label_info = QtWidgets.QLabel("",self)
        # self.label_info.setStyleSheet("background-color: white;")
        # self.label_info.setWordWrap(True)
        self.info = QtWidgets.QTextBrowser(self)
        self.info.setReadOnly(True)
        self.info.setMinimumHeight(5)
        # self.layout.addWidget(self.info)

        #图形化结构
        self.fig_height = 2.0
        self.static_canvas = FigureCanvas(Figure(figsize=(14,self.fig_height*cur_fig_num)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.static_canvas_ORG_resizeEvent = self.static_canvas.resizeEvent
        self.static_canvas.resizeEvent = self.static_canvas_resizeEvent
        self.fig_widget = Widget()
        self.fig_layout = QtWidgets.QVBoxLayout(self.fig_widget)
        self.fig_layout.addWidget(self.static_canvas)
        self.scroll = QtWidgets.QScrollArea(self.fig_widget)
        self.scroll.setWidget(self.static_canvas)
        self.scroll.setWidgetResizable(True)
        self.scroll.keyPressEvent = self.keyPressEvent
        # self.scroll.keyReleaseEvent = self.keyReleaseEvent
        self.is_keypressed = False
        self.key_loc_idx = -1   # 按键盘更新mid_line时，用于记住当前定位的位置
        self.key_laser_idx = -1 # 按键盘更新时，用于记住当前激光的信息
        self.key_laser_channel = -1 # 按键盘更新时， 用于记住当前激光的信息
        # self.layout.addWidget(self.scroll)
        self.ruler = RulerShapeMap()
        self.toolBar = MyToolBar(self.static_canvas, self._main, self.ruler)
        self.toolBar.update_home_callBack(self.new_home)
        self.addToolBar(self.toolBar)
        # self.static_canvas.figure.subplots_adjust(left = 0.2/cur_fig_num, right = 0.99, bottom = 0.05, top = 0.99, hspace = 0.1)
        self.axs= self.static_canvas.figure.subplots(cur_fig_num, 1, sharex = True)
        self.axs[0].tick_params(axis='x', labeltop=True, top = True)
        for ax in self.axs:
            self.ruler.add_ruler(ax)
        #鼠标移动消息
        self.static_canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.static_canvas.mpl_connect('button_press_event', self.mouse_press)
        self.static_canvas.mpl_connect('button_release_event', self.mouse_release)
        self.static_canvas.mpl_connect('axes_leave_event', self.leave_axes)

        #Log
        self.log_info = QtWidgets.QTextBrowser(self)
        self.log_info.setReadOnly(True)
        self.log_info.setMinimumHeight(10)
        self.log_info.setOpenLinks(False)
        self.log_info.anchorClicked.connect(self.openFileUrl)
        # self.layout.addWidget(self.log_info)

        #消息框，绘图，Log窗口尺寸可变
        splitter1 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter1.addWidget(self.info)
        splitter1.addWidget(self.scroll)
        splitter1.setSizes([1,100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.log_info)
        splitter2.setSizes([100,0])
        self.layout.addWidget(splitter2)

        #选择消息框
        self.hbox = QtWidgets.QHBoxLayout()
        self.check_all = QtWidgets.QCheckBox('ALL',self)
        self.check_fatal = QtWidgets.QCheckBox('FATAL',self)
        self.check_err = QtWidgets.QCheckBox('ERROR',self)
        self.check_war = QtWidgets.QCheckBox('WARNING',self)
        self.check_notice = QtWidgets.QCheckBox('NOTICE',self)
        self.check_tstart = QtWidgets.QCheckBox('TASK START',self)
        self.check_tfinish = QtWidgets.QCheckBox('TASK FINISHED',self)
        self.check_service = QtWidgets.QCheckBox('SERVICE',self)
        self.hbox.addWidget(self.check_all)
        self.hbox.addWidget(self.check_fatal)
        self.hbox.addWidget(self.check_err)
        self.hbox.addWidget(self.check_war)
        self.hbox.addWidget(self.check_notice)
        self.hbox.addWidget(self.check_tstart)
        self.hbox.addWidget(self.check_tfinish)
        self.hbox.addWidget(self.check_service)
        self.hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.addLayout(self.hbox)
        self.check_fatal.stateChanged.connect(self.changeCheckBox)
        self.check_err.stateChanged.connect(self.changeCheckBox)
        self.check_war.stateChanged.connect(self.changeCheckBox)
        self.check_notice.stateChanged.connect(self.changeCheckBox)
        self.check_tstart.stateChanged.connect(self.changeCheckBox)
        self.check_tfinish.stateChanged.connect(self.changeCheckBox)
        self.check_service.stateChanged.connect(self.changeCheckBox)
        self.check_all.stateChanged.connect(self.changeCheckBoxAll)
        self.check_all.setChecked(True)

        self.dataSelection = DataSelection()
        self.dataSelection.getdata.connect(self.addNewData)
        self.dataSelection.hide()

        self.map_widget = MapWidget(self)
        self.map_widget.setWindowIcon(QtGui.QIcon('rds.ico'))
        self.map_widget.hiddened.connect(self.mapClosed)
        self.map_widget.keyPressEvent = self.keyPressEvent

        self.targetPrecision = TargetPrecision(self)
        self.targetPrecision.hide()

        self.moveFactoryWidget = MoveFactoryWidget(self.read_thread)
        self.moveFactoryWidget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.moveFactoryWidget.closed.connect(lambda: self.moveFactory_action.setChecked(False))
        self.moveFactoryWidget.hide()

        self.cpuPieView = CPUPieView(self.read_thread)
        self.cpuPieView.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.cpuPieView.closed.connect(lambda : self.cpuPie_action.setChecked(False))
        self.cpuPieView.hide()

        self.heatMapWidget = APHeatMapWidget(self.read_thread)
        self.heatMapWidget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.heatMapWidget.closed.connect(lambda: self.heatMap_action.setChecked(False))
        self.heatMapWidget.hide()

        self.paramWidget = ParamWidget()
        self.paramWidget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.paramWidget.closed.connect(lambda: self.param_action.setChecked(False))
        self.paramWidget.hide()
        # dataView相关的初始化
        self.dataViewNewOne(None)


    def static_canvas_resizeEvent(self, event):
        self.static_canvas_ORG_resizeEvent(event)
        w = event.size().width()
        font_width = 100.0
        self.static_canvas.figure.subplots_adjust(left = (font_width/(w*1.0)), right = 0.99, bottom = 0.05, top = 0.95, hspace = 0.1)

    def get_content(self, mouse_time):
        content = ""
        dt_min = 1e10
        if self.read_thread.fatal.t() and self.check_fatal.isChecked():
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
            dt_min = min(vdt)
        if self.read_thread.err.t() and self.check_err.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.war.t() and self.check_war.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.notice.t() and self.check_notice.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.taskstart.t() and self.check_tstart.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskstart.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.taskfinish.t() and self.check_tfinish.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskfinish.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt
        if self.read_thread.service.t() and self.check_service.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.service.t()]
            tmp_dt = min(vdt)
            if tmp_dt < dt_min:
                dt_min = tmp_dt

        if dt_min < 10:
            contents = []
            if self.read_thread.fatal.t() and self.check_fatal.isChecked():
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.fatal.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.err.t() and self.check_err.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.err.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.war.t() and self.check_war.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.war.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.notice.t() and self.check_notice.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.notice.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.taskstart.t() and self.check_tstart.isChecked():
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskstart.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.taskstart.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.taskfinish.t() and self.check_tfinish.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.taskfinish.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.taskfinish.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.service.t() and self.check_service.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.service.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.service.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            content = '\n'.join(contents)
        return content

    def updateMap(self):
        self.updateMapSelectLine()
        self.updateLogView()
        self.updateJsonView()
        self.updateDataViews()

    def updateJsonView(self):
        map_name = None
        if len(self.read_thread.rstatus.chassis()[1]) > 0:
            ts = np.array(self.read_thread.rstatus.chassis()[1])
            idx = (np.abs(ts - self.mid_line_t)).argmin()
            j = json.loads(self.read_thread.rstatus.chassis()[0][idx])   
            map_name = j.get("CURRENT_MAP",None)
            if map_name:
                map_name = map_name + ".smap"
            if self.sts_widget:
                if idx < len(self.read_thread.rstatus.version()[0]):
                    j["ROBOKIT_VERSION_REDISTRIBUTE"] = "{}.{}".format(self.read_thread.rstatus.version()[0][idx],
                                                                        j["ROBOKIT_VERSION_REDISTRIBUTE"])
                if idx < len(self.read_thread.rstatus.fatalNum()[0]):
                    j["fatalNums"] = self.read_thread.rstatus.fatalNum()[0][idx]
                if idx < len(self.read_thread.rstatus.fatals()[0]):
                    try:
                        j["fatals"] = json.loads(self.read_thread.rstatus.fatals()[0][idx])
                    except:
                        j["fatals"] = self.read_thread.rstatus.fatals()[0][idx]
                if idx < len(self.read_thread.rstatus.errorNum()[0]):
                    j["errorNums"] = self.read_thread.rstatus.errorNum()[0][idx]
                if idx < len(self.read_thread.rstatus.errors()[0]):
                    try:
                        j["errors"] = json.loads(self.read_thread.rstatus.errors()[0][idx])
                    except:
                        j["errors"] = self.read_thread.rstatus.errors()[0][idx]
                if idx < len(self.read_thread.rstatus.warningNum()[0]):
                    j["warningNum"] = self.read_thread.rstatus.warningNum()[0][idx]
                if idx < len(self.read_thread.rstatus.warnings()[0]):
                    try:
                        j["warnings"] = json.loads(self.read_thread.rstatus.warnings()[0][idx])
                    except:
                        j["warnings"] = self.read_thread.rstatus.warnings()[0][idx]
                if idx < len(self.read_thread.rstatus.noticeNum()[0]):
                    j["noticeNum"] = self.read_thread.rstatus.noticeNum()[0][idx]
                if idx < len(self.read_thread.rstatus.notices()[0]):
                    try:
                        j["notices"] = json.loads(self.read_thread.rstatus.notices()[0][idx])
                    except:
                        j["notices"] = self.read_thread.rstatus.notices()[0][idx]
                self.sts_widget.loadJson(j)    

    def updateSelection(self):
        self.select_type = SelectEnum.NoSelect
        if self.toolBar.isActive():
            return
        for s in self.select_regions:
            if s.select_type is not SelectEnum.NoSelect:
                self.select_type = s.select_type
                break

    def mouse_press(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = num2date(event.xdata)
            if event.button == 1:
                self.updateSelection()
                print("select_type:", self.select_type)
                if self.select_type is not SelectEnum.NoSelect:
                    self.mouse_pressed = True
                content = 't, '  + event.inaxes.get_ylabel() + ' : ' + str(mouse_time) + ',' +str(event.ydata)
                self.log_info.append(content)
            elif event.button == 3:
                if not self.toolBar.isActive():
                    self.popMenu = QtWidgets.QMenu(self)
                    self.popMenu.addAction('&Save All Data',lambda:self.saveAllData(event.inaxes))
                    self.popMenu.addAction('&Save View Data',lambda:self.saveViewData(event.inaxes))
                    self.popMenu.addAction('&Save Region Data',lambda:self.saveSelectData(event.inaxes))
                    self.popMenu.addAction('&Move Here',lambda:self.moveHere(event.xdata))
                    self.popMenu.addAction('&resize Region',lambda:self.resizeRegion())
                    self.popMenu.addAction('&reset Data', lambda:self.resetData(event.inaxes))
                    self.popMenu.addAction('&Diff Time', lambda:self.diffData(event.inaxes))
                    self.popMenu.addAction('&- Data', lambda:self.negData(event.inaxes))
                    self.popMenu.addAction('&Add Data', lambda:self.addData(event.inaxes))
                    cursor = QtGui.QCursor()
                    self.popMenu.exec_(cursor.pos())
                # show info
                content = self.get_content(mouse_time)
                if content != "":
                    self.log_info.append(content[:-1])

    def mouse_move(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = num2date(event.xdata)
            content = self.get_content(mouse_time)
            self.info.setText(content)
            if self.mouse_pressed:
                if self.select_type == SelectEnum.Mid:
                    self.resetMidLineProperty(mouse_time)
                    self.updateMap()
                elif self.select_type == SelectEnum.Left:
                    self.setSelectLeft(mouse_time)
                elif self.select_type == SelectEnum.Right:
                    self.setSelectRight(mouse_time)
                elif self.select_type == SelectEnum.Region:
                    self.setSelectRegion(event.xdata)
        elif not self.finishReadFlag:
            self.info.setText("")

    def mouse_release(self, event):
        self.mouse_pressed = False
        self.select_type = SelectEnum.NoSelect
        for s in self.select_regions:
            s.select_type = SelectEnum.NoSelect

    def leave_axes(self, event):
        self.mouse_pressed = False
        self.select_type = SelectEnum.NoSelect
        for s in self.select_regions:
            s.select_type = SelectEnum.NoSelect

    def moveHere(self, mtime):
        mouse_time = mtime
        if type(mouse_time) is not datetime:
            mouse_time = num2date(mtime)
        self.resetMidLineProperty(mouse_time)
        self.updateMap()

    def resizeRegion(self):
        (xmin,xmax) = self.axs[0].get_xlim()
        tmid = (xmin+xmax)/2.0
        dx = xmax - xmin
        self.setSelectLeft(num2date(xmin + dx * 0.1))
        self.setSelectRight(num2date(xmax - dx * 0.1))     

    def setSelectLeft(self, t):
        if t < self.right_line_t:
            self.left_line_t = t
            for s in self.select_regions:
                s.setRegion(self.left_line_t, self.right_line_t)
            self.static_canvas.figure.canvas.draw()

    def setSelectRight(self,t):
        if t > self.left_line_t:
            self.right_line_t = t
            for s in self.select_regions:
                s.setRegion(self.left_line_t, self.right_line_t)
            self.static_canvas.figure.canvas.draw()

    def setSelectRegion(self, midx):

        lt = date2num(self.left_line_t)
        rt = date2num(self.right_line_t)
        dt = midx - (lt + rt)/2.0
        lt += dt
        rt += dt
        self.left_line_t = num2date(lt)
        self.right_line_t = num2date(rt)
        for s in self.select_regions:
            s.setRegion(lt, rt)
        self.static_canvas.figure.canvas.draw()

    def saveAllData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        # print(xmin, xmax, time0, time1)
        xy = self.xys[indx]
        group_name = xy.y_combo.currentText().split('.')[0]
        tmpdata = []

        # 获取数据
        if xy.x_combo.currentText() == 't':
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        elif xy.x_combo.currentText() == 'timestamp':
            org_t = self.read_thread.getData(group_name + '.timestamp')[0]
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], t)
        self.savePlotData(cur_ax, tmpdata[1][0], tmpdata[1][-1])

    def saveViewData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xmin,xmax = cur_ax.get_xlim()
        time0 = num2date(xmin)
        time1 = num2date(xmax)
        self.savePlotData(cur_ax, time0, time1)

    def saveSelectData(self, cur_ax):
        self.savePlotData(cur_ax, self.left_line_t, self.right_line_t)

    def savePlotData(self, cur_ax, time0, time1):
        indx = self.axs.tolist().index(cur_ax)
        # print(xmin, xmax, time0, time1)
        xy = self.xys[indx]
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self,"选取log文件", "","CSV Files (*.csv);;PY Files (*.py)")
        subffix = os.path.splitext(fname)[1]
        isPy = subffix == ".py"
        logging.debug('Save ' + xy.y_combo.currentText() + ' and ' + xy.x_combo.currentText() + ' in ' + fname)
        group_name = xy.y_combo.currentText().split('.')[0]
        tmpdata = []

        # 获取数据
        if xy.x_combo.currentText() == 't':
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        elif xy.x_combo.currentText() == 'timestamp':
            org_t = self.read_thread.getData(group_name + '.timestamp')[0]
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], t)        

        outdata = []
        # 对数据存之前进行处理
        if isPy:
            ind1 = (np.abs(np.array(tmpdata[1])-time0)).argmin()
            ind2 = (np.abs(np.array(tmpdata[1][ind1::])-time1)).argmin() + ind1
            x,y = [],[]
            for i in range(len(tmpdata[1])):
                if i >= ind1 and i < ind2:
                    x.append(datetime.timestamp(tmpdata[1][i]))
                    y.append(tmpdata[0][i])
            xdata = 't='+str(x)
            ydata = 'x='+str(y)
            outdata.append(xdata)
            outdata.append(ydata)
        else:
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
            tmpdata[1].sort()
            ind1 = (np.abs(np.array(tmpdata[1])-time0)).argmin()
            ind2 = (np.abs(np.array(tmpdata[1][ind1::])-time1)).argmin() + ind1
            list_tmpdata.sort(key=lambda d: d[0])
            for (ind, data) in enumerate(list_tmpdata):
                if ind >= ind1 and ind <= ind2:
                    outdata.append("{},{}".format(data[0].strftime('%Y-%m-%d %H:%M:%S.%f'), data[1]))
        # 写数据
        if fname:
            try:
                with open(fname, 'w') as fn:
                    for d in outdata:
                        fn.write(d+'\n')
            except:
                pass

    def resetData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        org_t = self.read_thread.getData(group_name + '.timestamp')[0]
        if len(org_t) > 0:
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
            tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], t]
            self.drawdata(cur_ax, tmpdata, self.read_thread.ylabel[xy.y_combo.currentText()], False)
        else:
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
            self.drawdata(cur_ax, tmpdata,  self.read_thread.ylabel[xy.y_combo.currentText()], False)

    def diffData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        list_tmpdata = []
        org_t = self.read_thread.getData(group_name + '.timestamp')[0]
        if len(org_t) > 0:
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
            tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], t)
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        else:
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
            list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        if len(list_tmpdata) < 2:
            return
        list_tmpdata.sort(key=lambda d: d[0])
        dts = [(a[0]-b[0]).total_seconds() for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        dvs = [a[1]-b[1] for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        try:
            dv_dt = [a/b if abs(b) > 1e-12 else np.nan for a, b in zip(dvs, dts)]
            self.drawdata(cur_ax, (dv_dt, list_tmpdata[1::]), 'diff_'+self.read_thread.ylabel[xy.y_combo.currentText()], False)
        except ZeroDivisionError:
            pass

    def negData(self, cur_ax):
        indx = self.axs.tolist().index(cur_ax)
        xy = self.xys[indx]        
        group_name = xy.y_combo.currentText().split('.')[0]
        org_t = self.read_thread.getData(group_name + '.timestamp')[0]
        if len(org_t) > 0:
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
            tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], t]
            tmpdata[0] = [-a for a in tmpdata[0]]
            self.drawdata(cur_ax, (tmpdata[0], tmpdata[1]), '-'+self.read_thread.ylabel[xy.y_combo.currentText()], False)
        else:
            tmpdata = self.read_thread.getData(xy.y_combo.currentText())
            data = [-a for a in tmpdata[0]]
            self.drawdata(cur_ax, (data, tmpdata[1]), '-'+self.read_thread.ylabel[xy.y_combo.currentText()], False)

    def addData(self, cur_ax):
        keys = list(self.read_thread.data.keys())
        self.dataSelection.initForm(cur_ax, keys)
        self.dataSelection.show()
    
    def addNewData(self, event):
        cur_ax = event[0]
        current_text = event[1]
        tmpdata = self.read_thread.getData(current_text)
        self.drawdata(cur_ax, tmpdata, self.read_thread.ylabel[current_text], False, False)
        

    def keyPressEvent(self,event):
        if len(self.select_regions) < 1:
            return
        if event.key() == QtCore.Qt.Key_F and event.modifiers() == QtCore.Qt.ControlModifier:
            if self.searchWidget.isVisible():
                self.searchWidget.hide()
            else:
                self.searchWidget.show()
        try:
            if (event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D
                or event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_Right):
                cur_t = self.select_regions[0].getMidLineX()
                if type(cur_t) is not datetime:
                    cur_t = num2date(cur_t)
                if event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D:
                    self.key_laser_idx = -1
                    self.key_laser_channel = -1
                    t = np.array(self.read_thread.content['LocationEachFrame']['t'])
                    if self.key_loc_idx < 0:
                        self.key_loc_idx = (np.abs(t-cur_t)).argmin()
                    if event.key() == QtCore.Qt.Key_A:
                        if self.key_loc_idx > 0:
                            self.key_loc_idx = self.key_loc_idx - 1
                    if event.key() ==  QtCore.Qt.Key_D:
                        if self.key_loc_idx < (len(t) -1 ):
                            self.key_loc_idx = self.key_loc_idx + 1
                    cur_t = t[self.key_loc_idx]
                else:
                    self.key_loc_idx = -1
                    if self.key_laser_idx < 0 \
                    or self.key_laser_channel < 0:
                        min_laser_channel = -1
                        laser_idx = -1
                        min_dt = None
                        for index in self.read_thread.laser.datas.keys():
                            t = np.array(self.read_thread.laser.t(index))
                            if len(t) < 1:
                                continue
                            tmp_laser_idx = (np.abs(t-cur_t)).argmin()
                            tmp_dt = np.min(np.abs(t-cur_t))
                            if min_dt == None or tmp_dt < min_dt:
                                min_laser_channel = index
                                laser_idx = tmp_laser_idx
                                min_dt = tmp_dt
                        self.key_laser_idx = laser_idx
                        self.key_laser_channel = min_laser_channel
                        t = self.read_thread.laser.t(min_laser_channel)
                        cur_t = t[laser_idx]
                    if event.key() == QtCore.Qt.Key_Left:
                        self.key_laser_idx = self.key_laser_idx -1
                        t = self.read_thread.laser.t(self.key_laser_channel)
                        if self.key_laser_idx < 0:
                            self.key_laser_idx = len(t) - 1
                        cur_t = t[self.key_laser_idx]
                    if event.key() == QtCore.Qt.Key_Right:
                        self.key_laser_idx = self.key_laser_idx + 1
                        t = self.read_thread.laser.t(self.key_laser_channel)
                        if self.key_laser_idx >= len(t):
                            self.key_laser_idx = 0
                        cur_t = t[self.key_laser_idx]
                self.mid_line_t = cur_t
                self.updateMap()
        except Exception as e:
            logging.warning(e)

    def new_home(self, *args, **kwargs):
        for ax, xy in zip(self.axs, self.xys):
            text = xy.y_combo.currentText()
            if text in self.read_thread.data:
                data = self.read_thread.getData(text)[0]
                if data:
                    tmpd = np.array(data)
                    tmpd = tmpd[~np.isnan(tmpd)]
                    if len(tmpd) > 0:
                        max_range = max(max(tmpd) - min(tmpd), 1e-6)
                        ax.set_ylim(min(tmpd) - 0.05 * max_range, max(tmpd)  + 0.05 * max_range)
                        ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        self.static_canvas.figure.canvas.draw()

    def new_forward(self, *args, **kwargs):
        xmin,xmax =  self.axs[0].get_xlim()
        range = xmax - xmin
        xmin = xmin + range /10.0
        xmax = xmax + range /10.0
        for ax in self.axs:
            ax.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def new_back(self, *args, **kwargs):
        xmin,xmax =  self.axs[0].get_xlim()
        range = xmax - xmin
        xmin = xmin - range /10.0
        xmax = xmax - range /10.0
        for ax in self.axs:
            ax.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def openFileUrl(self, flink):
        QtGui.QDesktopServices.openUrl(flink)

    def openLogFilesDialog(self):
        # self.setGeometry(50,50,640,480)
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log | *.gz);;All Files (*)", options=options)
        if self.filenames:
            self.finishReadFlag = False
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading ' + str(len(self.filenames)) + ' Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1)+':'+f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def openModelFilesDialog(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.model_name, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取model文件", "","model Files (*.model);;All Files (*)", options=options)
        if self.model_name:
            return self.model_name[0]
        else:
            return None

    def dragFiles(self, files):
        flag_first_in = True
        for file in files:
            if os.path.exists(file):
                subffix = os.path.splitext(file)[1]
                if subffix == ".log" or subffix == ".gz":
                    if flag_first_in:
                        self.filenames = []
                        flag_first_in = False
                    self.filenames.append(file)
                elif os.path.splitext(file)[1] == ".json":
                    logging.debug('Update log_config.json')
                    self.read_thread.log_config = file
                else: 
                    logging.debug('fail to load {}'.format(file))
                    return
        if self.filenames:
            self.finishReadFlag = False
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading' + str(len(self.filenames)) + 'Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1) + ':' + f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def readFinished(self, result):
        for tmps in self.read_thread.log:
            self.log_info.append(tmps)
        logging.debug('read Finished')
        self.log_info.append('Finished')
        max_line = 1000
        if len(self.read_thread.fatal.t()) > max_line:
            logging.warning("FATALs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.fatal.t())))
            self.log_info.append("FATALs are too much to be ploted. Max Number is "+ str(max_line) + ". Current Number is " + str(len(self.read_thread.fatal.t())))
            self.read_thread.fatal = FatalLine()
        if len(self.read_thread.err.t()) > max_line:
            logging.warning("ERRORs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.err.t())))
            self.log_info.append("ERRORs are too much to be ploted. Max Number is " + str(max_line)+". Current Number is "+str(len(self.read_thread.err.t())))
            # self.read_thread.err = ErrorLine()
            # 这里改为超过1000条就只取前1000条
            self.read_thread.err.data[0] = self.read_thread.err.data[0][:max_line]
        if len(self.read_thread.war.t()) > max_line:
            logging.warning("WARNINGs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.war.t())))
            self.log_info.append("WARNINGs are too much to be ploted. Max Number is " + str(max_line) +  ". Current Number is " + str(len(self.read_thread.war.t())))
            self.read_thread.war = WarningLine()
        if len(self.read_thread.notice.t()) > max_line:
            logging.warning("NOTICEs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.notice.t())))
            self.log_info.append("NOTICEs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.notice.t())))
            self.read_thread.notice = NoticeLine()
        if len(self.read_thread.taskstart.t()) > max_line:
            logging.warning("TASKSTART are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskstart.t())))
            self.log_info.append("TASKSTART are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskstart.t())))
            self.read_thread.taskstart = TaskStart()
        if len(self.read_thread.taskfinish.t()) > max_line:
            logging.warning("TASKFINISH are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskfinish.t())))
            self.log_info.append("TASKFINISH are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.taskfinish.t())))
            self.read_thread.taskfinish = TaskFinish()
        if len(self.read_thread.service.t()) > max_line:
            logging.warning("SERVICE are too much to be ploted. Max Number is " + str(max_line) +". Current Number is " + str(len(self.read_thread.service.t())))
            self.log_info.append("SERVICE are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.service.t())))
            self.read_thread.service = Service()
        self.finishReadFlag = True
        self.setWindowTitle('Log分析器: {0}'.format([f.split('/')[-1] for f in self.filenames]))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            keys = list(self.read_thread.data.keys())
            for ax, xy in zip(self.axs, self.xys):
                last_combo_ind = xy.y_combo.currentIndex()
                xy.y_combo.clear()
                xy.y_combo.addItems(keys) 
                xy.x_combo.clear()
                xy.x_combo.addItems(['t']) 
                if last_combo_ind >= 0:
                    xy.y_combo.setCurrentIndex(last_combo_ind)
                group_name = xy.y_combo.currentText().split('.')[0]
                if group_name in self.read_thread.content:
                    if 'timestamp' in self.read_thread.content[group_name].data:
                        xy.x_combo.addItems(['timestamp'])
                self.drawdata(ax, self.read_thread.getData(xy.y_combo.currentText()),
                                self.read_thread.ylabel[xy.y_combo.currentText()], True)
            for d in self.dataViews:
                self.initDataView(d)
            self.key_laser_channel = -1
            self.key_laser_idx = -1
            self.key_loc_idx = -1
            self.resetSelect()
            self.openMap(self.map_action.isChecked())
            self.openViewer(self.view_action.isChecked())
            self.openJsonView(self.json_action.isChecked())
            self.openDataView(self.data_action.isChecked())
            self.updateMap()
            self.cpuPieView.loadData()
            self.heatMapWidget.loadMap()
            self.paramWidget.readParam(self.filenames[0])
            self.moveFactoryWidget.updateModel()


    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer cd.1.5.1""")

    def ycombo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (ind, xy) in enumerate(self.xys):
            if xy.y_combo == curcombo:
                index = ind
                break
        text = curcombo.currentText()
        current_x_index = self.xys[index].x_combo.currentIndex()
        self.xys[index].x_combo.clear()
        self.xys[index].x_combo.addItems(['t'])
        group_name = text.split('.')[0]
        if group_name in self.read_thread.content:
            if 'timestamp' in self.read_thread.content[group_name].data:
                self.xys[index].x_combo.addItems(['timestamp'])

        ax = self.axs[index]
        if self.xys[index].x_combo.count() == 1 or current_x_index == 0:
            logging.info('Fig.' + str(index+1) + ' : ' + text + ' ' + 't')
            self.drawdata(ax, self.read_thread.getData(text), self.read_thread.ylabel[text], False)
        else:
            logging.info('Fig.' + str(index+1) + ' : ' + text + ' ' + 'timestamp')
            org_t = self.read_thread.getData(group_name + '.timestamp')[0]
            t = []
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(text)[1][0] + tmp for tmp in dt]
            self.drawdata(ax, (self.read_thread.getData(text)[0], t), self.read_thread.ylabel[text], False)


    def xcombo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (ind, xy) in enumerate(self.xys):
            if xy.x_combo == curcombo:
                index = ind
                break; 
        text = curcombo.currentText()
        ax = self.axs[index]
        y_label = self.xys[index].y_combo.currentText()
        logging.info('Fig.' + str(index+1) + ' : ' + y_label + ' ' + text)
        if text == 't':
            self.drawdata(ax, self.read_thread.getData(y_label), self.read_thread.ylabel[y_label], False)
        elif text == 'timestamp':
            group_name = y_label.split('.')[0]
            org_t = self.read_thread.getData(group_name + '.timestamp')[0]
            t = []
            dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
            t = [self.read_thread.getData(y_label)[1][0] + tmp for tmp in dt]
            self.drawdata(ax, (self.read_thread.getData(y_label)[0], t), self.read_thread.ylabel[y_label], False)

    def cpunum_changed(self, action):
        self.read_thread.cpu_num = int(action.text())

    def fignum_changed(self,action):
        new_fig_num = int(action.text())
        logging.info('fignum_changed to '+str(new_fig_num))
        xmin, xmax = self.axs[0].get_xlim()
        for ax in self.axs:
            self.static_canvas.figure.delaxes(ax)

        # self.static_canvas.figure.subplots_adjust(left = 0.2/new_fig_num, right = 0.99, bottom = 0.05, top = 0.99, hspace = 0.1)
        self.static_canvas.figure.set_figheight(new_fig_num*self.fig_height)
        self.axs= self.static_canvas.figure.subplots(new_fig_num, 1, sharex = True)
        self.axs[0].tick_params(axis='x', labeltop=True, top = True)
        self.ruler.clear_rulers()
        for ax in self.axs:
            self.ruler.add_ruler(ax)
        self.scroll.setWidgetResizable(True)
        for i in range(0, self.xy_hbox.count()): 
            self.xy_hbox.itemAt(i).widget().deleteLater()
        combo_y_ind = [] 
        combo_x_ind = [] 
        for xy in self.xys:
            combo_y_ind.append(xy.y_combo.currentIndex())
            combo_x_ind.append(xy.x_combo.currentIndex())
        self.xys = []
        for i in range(0,new_fig_num):
            selection = XYSelection(i+1)
            selection.y_combo.activated.connect(self.ycombo_onActivated)
            selection.x_combo.activated.connect(self.xcombo_onActivated)
            self.xys.append(selection)
            self.xy_hbox.addWidget(selection.groupBox)
        if self.finishReadFlag:
            if self.read_thread.filenames:
                keys = list(self.read_thread.data.keys())
                count = 0
                for ax, xy in zip(self.axs, self.xys):
                    xy.y_combo.addItems(keys)
                    if count < len(combo_y_ind):
                        xy.y_combo.setCurrentIndex(combo_y_ind[count])
                    xy.x_combo.addItems(['t'])
                    group_name = xy.y_combo.currentText().split('.')[0]
                    if group_name in self.read_thread.content:
                        if 'timestamp' in self.read_thread.content[group_name].data:
                            xy.x_combo.addItems(['timestamp'])
                    if count < len(combo_x_ind):
                        xy.x_combo.setCurrentIndex(combo_x_ind[count])
                    count = count + 1
                    ax.set_xlim(xmin, xmax)
                    #TO DO
                    if xy.x_combo.currentText() == 't':
                        self.drawdata(ax, self.read_thread.getData(xy.y_combo.currentText()),
                                   self.read_thread.ylabel[xy.y_combo.currentText()], False)
                    elif xy.x_combo.currentText() == 'timestamp':
                        org_t = self.read_thread.getData(group_name + '.timestamp')[0]
                        t = []
                        dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
                        t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
                        data = (self.read_thread.getData(xy.y_combo.currentText())[0], t)
                        self.drawdata(ax, data,
                                    self.read_thread.ylabel[xy.y_combo.currentText()], False)
                self.resetSelect()
        self.static_canvas.figure.canvas.draw()


    def drawdata(self, ax, data, ylabel, resize = False, replot = True):
        xmin,xmax =  ax.get_xlim()
        if replot:
            ax.cla()
            self.drawFEWN(ax)
            if data[1] and data[0]:
                ax.plot(data[1], data[0], '.', url = ylabel)
                if isinstance(data[0][0], float):
                    tmpd = np.array(data[0], dtype=float)
                    tmpd = tmpd[~np.isnan(tmpd)]
                    if len(tmpd) > 0:
                        max_range = max(max(tmpd) - min(tmpd), 1.0)
                        ax.set_ylim(min(tmpd) - 0.05 * max_range, max(tmpd) + 0.05 * max_range)
            if resize:
                ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
            else:
                ax.set_xlim(xmin, xmax)
            ax.set_ylabel(ylabel)
            ax.grid()
            ind = np.where(self.axs == ax)[0][0]
            for s in self.select_regions:
                s.addAgain(ax)
            self.ruler.add_ruler(ax)
        else:
            if data[1] and data[0]:
                ax.plot(data[1], data[0], '.', url = ylabel)
                #用于遍历绘制的数据的特定artist
                art_list = [[],[]]
                for art in ax.get_children():
                    if art.get_url() is not None:
                        art_list[0].append(art)
                        art_list[1].append(art.get_url())
                ax.legend(art_list[0], art_list[1], loc='upper right')
        self.static_canvas.figure.canvas.draw()

    def drawFEWN(self,ax):
        """ 绘制 Fatal, Error, Warning在坐标轴上"""
        fl, el, wl,nl = None, None, None, None
        self.lines_dict = dict()
        line_num = 0
        legend_info = []
        fnum, ernum, wnum, nnum = [], [], [], [] 
        tsnum, tfnum, tsenum = [],[], []
        tsl, tfl, tse = None, None, None
        lw = 1.5
        ap = 0.8
        for tmp in self.read_thread.taskstart.t():
            tsl = ax.axvline(tmp, linestyle = '-', color = 'b', linewidth = lw, alpha = ap)
            tsnum.append(line_num)
            line_num = line_num + 1
        if tsl:
            legend_info.append(tsl)
            legend_info.append('task start')
        for tmp in self.read_thread.taskfinish.t():
            tfl = ax.axvline(tmp, linestyle = '--', color = 'b', linewidth = lw, alpha = ap)
            tfnum.append(line_num)
            line_num = line_num + 1
        if tfl:
            legend_info.append(tfl)
            legend_info.append('task finish')
        for tmp in self.read_thread.service.t():
            tse = ax.axvline(tmp, linestyle = '-', color = 'k', linewidth = lw, alpha = ap)
            tsenum.append(line_num)
            line_num = line_num + 1
        if tse:
            legend_info.append(tse)
            legend_info.append('service')
        for tmp in self.read_thread.fatal.t():
            fl= ax.axvline(tmp, linestyle='-',color = 'm', linewidth = lw, alpha = ap)
            fnum.append(line_num)
            line_num = line_num + 1
        if fl:
            legend_info.append(fl)
            legend_info.append('fatal')
        for tmp in self.read_thread.err.t():
            el= ax.axvline(tmp, linestyle = '-.', color='r', linewidth = lw, alpha = ap)
            ernum.append(line_num)
            line_num = line_num + 1
        if el:
            legend_info.append(el)
            legend_info.append('error')
        for tmp in self.read_thread.war.t():
            wl = ax.axvline(tmp, linestyle = '--', color = 'y', linewidth = lw, alpha = ap)
            wnum.append(line_num)
            line_num = line_num + 1
        if wl:
            legend_info.append(wl)
            legend_info.append('warning')
        for tmp in self.read_thread.notice.t():
            nl = ax.axvline(tmp, linestyle = ':', color = 'g', linewidth = lw, alpha = ap)
            nnum.append(line_num)
            line_num = line_num + 1
        if nl:
            legend_info.append(nl)
            legend_info.append('notice')
        if legend_info:
            ax.legend(legend_info[0::2], legend_info[1::2], loc='upper right')
        self.lines_dict['fatal'] = fnum
        self.lines_dict['error'] = ernum
        self.lines_dict['warning'] = wnum
        self.lines_dict['notice'] = nnum
        self.lines_dict['taskstart'] = tsnum
        self.lines_dict['taskfinish'] = tfnum
        self.lines_dict['service'] = tsenum
        lines = ax.get_lines()
        for n in fnum:
            lines[n].set_visible(self.check_fatal.isChecked())
        for n in ernum:
            lines[n].set_visible(self.check_err.isChecked())
        for n in wnum:
            lines[n].set_visible(self.check_war.isChecked())
        for n in nnum:
            lines[n].set_visible(self.check_notice.isChecked())
        for n in tsnum:
            lines[n].set_visible(self.check_tstart.isChecked())
        for n in tfnum:
            lines[n].set_visible(self.check_tfinish.isChecked())
        for n in tsenum:
            lines[n].set_visible(self.check_service.isChecked())
        
    def updateCheckInfoLine(self,key):
        for ax in self.axs:
            lines = ax.get_lines()
            for num in self.lines_dict[key]:
                vis = not lines[num].get_visible()
                lines[num].set_visible(vis)
        self.static_canvas.figure.canvas.draw()


    def changeCheckBox(self):
        if self.check_err.isChecked() and self.check_fatal.isChecked() and self.check_notice.isChecked() and \
        self.check_war.isChecked() and self.check_tstart.isChecked() and self.check_tfinish.isChecked() and \
        self.check_service.isChecked():
            self.check_all.setCheckState(QtCore.Qt.Checked)
        elif self.check_err.isChecked() or self.check_fatal.isChecked() or self.check_notice.isChecked() or \
        self.check_war.isChecked() or self.check_tstart.isChecked() and self.check_tfinish.isChecked() or \
        self.check_service.isChecked():
            self.check_all.setTristate()
            self.check_all.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            self.check_all.setTristate(False)
            self.check_all.setCheckState(QtCore.Qt.Unchecked)

        cur_check = self.sender()
        if cur_check is self.check_fatal:
            self.updateCheckInfoLine('fatal')
        elif cur_check is self.check_err:
            self.updateCheckInfoLine('error')
        elif cur_check is self.check_war:
            self.updateCheckInfoLine('warning')
        elif cur_check is self.check_notice:
            self.updateCheckInfoLine('notice')
        elif cur_check is self.check_tstart:
            self.updateCheckInfoLine('taskstart')
        elif cur_check is self.check_tfinish:
            self.updateCheckInfoLine('taskfinish')
        elif cur_check is self.check_service:
            self.updateCheckInfoLine('service')

    def changeCheckBoxAll(self):
        if self.check_all.checkState() == QtCore.Qt.Checked:
            self.check_fatal.setChecked(True)
            self.check_err.setChecked(True)
            self.check_war.setChecked(True)
            self.check_notice.setChecked(True)
            self.check_tstart.setChecked(True)
            self.check_tfinish.setChecked(True)
            self.check_service.setChecked(True)
        elif self.check_all.checkState() == QtCore.Qt.Unchecked:
            self.check_fatal.setChecked(False)
            self.check_err.setChecked(False)
            self.check_war.setChecked(False)
            self.check_notice.setChecked(False)
            self.check_tstart.setChecked(False)
            self.check_tfinish.setChecked(False)
            self.check_service.setChecked(False)

    def openMap(self, checked):
        if checked:
            self.map_widget.show()
        else:
            self.map_widget.hide()
        self.static_canvas.figure.canvas.draw()
    
    def viewMotorErr(self, checked):
        if checked:
            if not self.motor_view_widget:
                self.motor_view_widget = MotorErrViewer()
                self.motor_view_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.motor_view_widget.hiddened.connect(self.motorErrViewerClosed)
                self.motor_view_widget.moveHereSignal.connect(self.moveHere)
                dir_name, _ = os.path.split(self.filenames[0])
                pdir_name, _ = os.path.split(dir_name)
                model_dir = os.path.join(pdir_name,"models")
                model_name = os.path.join(model_dir,"robot.model")
                if not os.path.exists(model_name):
                    model_dir = dir_name
                    model_name = os.path.join(model_dir,"robot.model")
                    if not os.path.exists(model_name):
                        model_dir = os.path.join(dir_name,"models")
                        model_name = os.path.join(model_dir,"robot.model")
                        if not os.path.exists(model_name):
                            model_name = None
                if not model_name:
                    model_name = self.openModelFilesDialog()
                if model_name:
                    self.motor_view_widget.setModelPath(model_name)
                    self.motor_view_widget.setReportPath(self.read_thread.getReportFileAddr())
                    self.motor_view_widget.listMotorErr()
            self.motor_view_widget.show()
            (xmin,xmax) = self.axs[0].get_xlim()
            tmid = (xmin+xmax)/2.0 
            # if len(self.mid_select_lines) > 1:
            #     for ln in self.mid_select_lines:
            #         ln.set_visible(True)
            #     cur_t = self.mid_select_lines[0].get_xdata()[0]
            #     if type(cur_t) is not datetime:
            #         cur_t = cur_t * 86400 - 62135712000
            #         cur_t = datetime.fromtimestamp(cur_t)
            #     self.updateMap(cur_t, self.key_loc_idx, self.key_laser_idx, self.key_laser_channel)
            # else:
            #     for ax in self.axs:
            #         wl = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = 10)
            #         self.mid_select_lines.append(wl) 
            #         mouse_time = tmid * 86400 - 62135712000
            #         if mouse_time > 1e6:
            #             mouse_time = datetime.fromtimestamp(mouse_time)
            #             self.updateMap(mouse_time, -1, -1, -1)
        else:
            if self.motor_view_widget:
                self.motor_view_widget.clearPlainText()
                self.motor_view_widget.hide() 

    def openViewer(self, checked):
        if checked:
            if not self.log_widget:
                self.log_widget = LogViewer()
                self.log_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.log_widget.hiddened.connect(self.viewerClosed)
                self.log_widget.moveHereSignal.connect(self.moveHere)
            if self.read_thread.reader:
                self.log_widget.setText(self.read_thread.reader.lines)
            self.log_widget.show()
            self.updateLogView()
        else:
            if self.log_widget:
                self.log_widget.hide()      
    
    def updateLogView(self):
        if self.log_widget is not None \
            and self.mid_line_t is not None \
                and self.read_thread.reader is not None:
            if self.key_loc_idx < 0:
                t = np.array(self.read_thread.content['LocationEachFrame']['t'])
                self.key_loc_idx = (np.abs(t-self.mid_line_t)).argmin()
            label = ''
            if 'LocationEachFrame' in self.read_thread.content:
                label = 'LocationEachFrame'
            elif 'Location' in self.read_thread.content:
                label = 'Location'
            if label != '':
                idx = self.read_thread.content[label].line_num[self.key_loc_idx]
                dt1 = (self.mid_line_t - self.read_thread.reader.tmin).total_seconds()
                dt2 = (self.read_thread.content[label]['t'][self.key_loc_idx] - self.read_thread.reader.tmin).total_seconds()
                ratio = dt1/ dt2
                idx = idx * ratio
                if idx > self.read_thread.reader.lines_num:
                    idx = self.read_thread.reader.lines_num
                if idx < 0:
                    idx = 0
                self.log_widget.setLineNum(idx)

    def openDataView(self, flag):
        if flag:
            if len(self.dataViews) < 1:
                self.dataViewNewOne(None)
        else:
            if len(self.dataViews) > 0:
                self.data_action.setChecked(True)

    def openJsonView(self, checked):
        if checked:
            if not self.sts_widget:
                self.sts_widget = JsonView()
                self.sts_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
                self.sts_widget.hiddened.connect(self.jsonViewerClosed)
            self.sts_widget.show()
            self.updateJsonView()
        else:
            if self.sts_widget:
                self.sts_widget.hide()           

    def openPrecision(self, checked):
        if checked:
            self.targetPrecision.show()
        else:
            self.targetPrecision.hide()

    def openMoveFactoryWidget(self, checked):
        if checked:
            self.moveFactoryWidget.show()
        else:
            self.moveFactoryWidget.hide()

    def openCPUPie(self,checked):
        if checked:
            self.cpuPieView.show()
        else:
            self.cpuPieView.hide()

    def openHeatMapWidget(self,checked):
        if checked:
            self.heatMapWidget.show()
        else:
            self.heatMapWidget.hide()

    def openParamWidget(self,checked):
        if checked:
            self.paramWidget.show()
        else:
            self.paramWidget.hide()


    def openLogDownloadWidget(self):
        if self.logDownload_widget:
            return
        def func():
            self.logDownload_widget = None
        self.logDownload_widget = LogDownloadWidget()
        self.logDownload_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.logDownload_widget.createDownloadTasked.connect(self.downloadLog)
        self.logDownload_widget.createDownloadTasked.connect(func)
        self.logDownload_widget.closed.connect(func)
        self.logDownload_widget.show()

    def openTimedLogDownloadWidget(self):
        if self.timedLogDownload_widget:
            return
        def func():
            self.timedLogDownload_widget = None
        self.timedLogDownload_widget = TimedLogDownloadWidget()
        self.timedLogDownload_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.timedLogDownload_widget.filesReady.connect(self.openFSWidget)
        self.timedLogDownload_widget.closed.connect(func)
        self.timedLogDownload_widget.show()

    def openMapCheckWidget(self):
        self.mapCheckWidget = MapCheckWidget()
        self.mapCheckWidget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.mapCheckWidget.show()

    # 画电机跟随曲线
    def drawMotorFollow(self, checked):
        dir_name, _ = os.path.split(self.filenames[0])
        pdir_name, _ = os.path.split(dir_name)
        model_dir = os.path.join(pdir_name,"models")
        model_name = os.path.join(model_dir,"robot.model")
        if not os.path.exists(model_name):
            model_dir = dir_name
            model_name = os.path.join(model_dir,"robot.model")
            if not os.path.exists(model_name):
                model_dir = os.path.join(dir_name,"models")
                model_name = os.path.join(model_dir,"robot.model")
                if not os.path.exists(model_name):
                    model_name = None
        if not model_name:
            model_name = self.openModelFilesDialog()
        if model_name:
            motor_name_list = mr.getMotorNames(model_name)
            motor_num = len(motor_name_list)
            num = QtWidgets.QLabel(str(motor_num))
            self.fignum_changed(num)
            try:
                name_motorinfo = mr.getNameMotorInfoDict(self.filenames[0], motor_name_list)
                name_motorcmd = mr.getNameMotorCmdDict(self.filenames[0], motor_name_list)
                name_type = mr.getMotorNameTypeDict(model_name)
                for i, name in enumerate(motor_name_list):
                    key1 = "MotorCmd." + name_motorcmd[name]
                    if name_type[name] == "steer":
                        key2 = name_motorinfo[name] + ".postion"
                    else:
                        key2 = name_motorinfo[name] + ".speed"
                    if i < self.max_fig_num:
                        self.drawdata(self.axs[i], self.read_thread.getData(key1),
                                        self.read_thread.ylabel[key1], True)
                        self.drawdata(self.axs[i], self.read_thread.getData(key2), 
                                        self.read_thread.ylabel[key2], False, False)
            except Exception as e:
                if KeyError in e.args:
                    self.log_info.append("Please choose the true model matched with log!!!")
            self.motor_follow_action.setChecked(False)
        else:
            self.log_info.append("Please choose the true model matched with log!!!")

    def resetMidLineProperty(self, t):
        self.mid_line_t = t
        self.key_laser_channel = -1
        self.key_laser_idx = -1
        self.key_loc_idx = -1

    def resetSelect(self):
        (xmin,xmax) = self.axs[0].get_xlim()
        tmid = (xmin+xmax)/2.0 
        self.select_regions = []

        self.mid_line_t = num2date(tmid)
        for ax in self.axs:
            dx = xmax - xmin
            self.left_line_t = num2date(xmin + dx * 0.1)
            self.right_line_t = num2date(xmax - dx * 0.1)
            s = SelectRegion(ax, xmin + dx * 0.1, xmax - dx * 0.1, tmid)
            self.select_regions.append(s)

    def updateMapSelectLine(self):
        for s in self.select_regions:
            if self.mid_line_t is not None:
                s.setMidLine(self.mid_line_t)
        self.static_canvas.figure.canvas.draw()

    def mapClosed(self,info):
        self.map_widget.hide()
        self.map_action.setChecked(False)
        self.openMap(False)

    def viewerClosed(self):
        self.view_action.setChecked(False)
        self.openViewer(False)

    def jsonViewerClosed(self, event):
        self.json_action.setChecked(False)
        self.openJsonView(False)

    def motorErrViewerClosed(self):
        self.motor_err_action.setChecked(False)
        self.viewMotorErr(False)

    def closeEvent(self, event):
        self.in_close = True
        if self.map_widget:
            self.map_widget.close()
        if self.log_widget:
            self.log_widget.close()
        if self.sts_widget:
            self.sts_widget.close()
        if self.motor_view_widget:
            self.motor_view_widget.close()
        if self.fs_widget:
            self.fs_widget.close()
        if self.logDownload_widget:
            self.logDownload_widget.close()
        if self.timedLogDownload_widget:
            self.timedLogDownload_widget.close()
        if self.mapCheckWidget:
            self.mapCheckWidget.close()
        for d in self.dataViews:
            d.close()
        self.moveFactoryWidget.close()
        self.cpuPieView.close()
        self.heatMapWidget.close()
        self.paramWidget.close()
        self.targetPrecision.close()
        self.close()

    def updateDataView(self, d:DataView):
        first_k = d.selection.y_combo.currentText()
        t = None
        if first_k in self.read_thread.content:
            for name in self.read_thread.content[first_k].data.keys():
                if name != 't':
                    k = first_k+'.'+name
                    t = self.read_thread.getData(k)[1]
                    break
        if t is None or len(t) < 1:
            j = dict()
            j[first_k] = "No Valid Data"
            d.loadJson(j)
            return
        ts = np.array(t)
        idx = (np.abs(ts - self.mid_line_t)).argmin()
        j = dict()
        for k in self.read_thread.content[first_k].data.keys():
            if k[0] == '_':
                continue
            data_name = k
            tmp_k = first_k+'.'+k
            if tmp_k in self.read_thread.ylabel:
                data_name = self.read_thread.ylabel[tmp_k]
                if tmp_k in data_name:
                    data_name = k
            j[data_name] = self.read_thread.content[first_k].data[k][idx]
        d.loadJson(j)

    def updateDataViews(self):
        for d in self.dataViews:
            self.updateDataView(d)

    def dataViewClosed(self, other):
        if not self.in_close:
            self.dataViews.remove(other)
            if len(self.dataViews) < 1:
                self.data_action.setChecked(False)
    
    def dataViewNewOne(self, other):
        dataView = DataView()
        dataView.setWindowIcon(QtGui.QIcon('rbk.ico'))
        dataView.closeMsg.connect(self.dataViewClosed)
        dataView.newOneMsg.connect(self.dataViewNewOne)
        dataView.dataViewMsg.connect(self.updateDataView)
        dataView.setGeometry(850,50,400,900)
        dataView.show()
        self.initDataView(dataView)
        self.dataViews.append(dataView)  
        self.updateDataView(dataView) 

    def initDataView(self, d:DataView):
        d.setSelectionItems(list(self.read_thread.content.keys())) 

    def downloadLog(self, cmdArgs):
        def release(*args):
            # self.setStatusBar(None)
            self.statusBar().deleteLater()
            #创建新的下载时析构
            self.logDownloader.deleteLater()
            #立即析构
            # self.logDownloader = None

        progressBar = QtWidgets.QProgressBar(self)
        progressBar.setMaximumHeight(15)
        statusLabel1 = QtWidgets.QLabel()
        statusLabel1.setAlignment(QtCore.Qt.AlignBottom)
        statusLabel2 = QtWidgets.QLabel()
        statusLabel2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        statusBar = QtWidgets.QStatusBar(self)
        statusBar.addWidget(progressBar, 3)
        statusBar.addWidget(statusLabel1, 5)
        statusBar.addPermanentWidget(statusLabel2, 2)
        self.setStatusBar(statusBar)

        self.logDownloader = LogDownloader(cmdArgs)
        self.logDownloader.downloadProgressChanged.connect(progressBar.setValue)
        self.logDownloader.downloadStatusChanged.connect(statusLabel1.setText)
        self.logDownloader.connectionChanged.connect(statusLabel2.setText)
        self.logDownloader.reqOrResInfoChanged.connect(statusBar.setToolTip)
        self.logDownloader.filesReady.connect(self.openFSWidget)
        self.logDownloader.filesReady.connect(release)
        self.logDownloader.error.connect(lambda msg: QtWidgets.QMessageBox.critical(self, "Error", msg))
        self.logDownloader.error.connect(release)
        self.logDownloader.run()

    def extractZip(self, zipFile):

        progressBar = QtWidgets.QProgressBar(self)
        progressBar.setMaximumHeight(15)
        statusLabel1 = QtWidgets.QLabel()
        statusLabel1.setAlignment(QtCore.Qt.AlignBottom)
        statusBar = QtWidgets.QStatusBar(self)
        statusBar.addWidget(progressBar, 3)
        statusBar.addWidget(statusLabel1, 7)
        self.setStatusBar(statusBar)

        thread = ExtractZipThread(zipFile, self)
        thread.extractFileChanged.connect(statusLabel1.setText)
        thread.extractProgressChanged.connect(progressBar.setValue)
        thread.error.connect(lambda msg: QtWidgets.QMessageBox.critical(self, "Error", msg))
        thread.error.connect(lambda msg: self.statusBar().deleteLater())
        thread.filesReady.connect(self.openFSWidget)
        thread.filesReady.connect(lambda dir: self.statusBar().deleteLater())
        thread.start()

    def openFSWidget(self, dirPath):
        self.fs_widget = MyFileSelectionWidget(dirPath)
        self.fs_widget.setWindowIcon(QtGui.QIcon('rbk.ico'))
        self.fs_widget.submit.connect(self.dragFiles)
        self.fs_widget.show()


if __name__ == "__main__":
    freeze_support()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not os.path.exists('log'):
        os.mkdir('log')
    log_name = "log\\loggui_" + str(ts).replace(':','-').replace(' ','_') + ".log"
    logging.basicConfig(filename = log_name,format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d][%(funcName)s] %(message)s', level=logging.DEBUG)

    def excepthook(type_, value, traceback_):
        # Print the error and traceback
        traceback.print_exception(type_, value, traceback_) 
        logging.error(traceback.format_exception(type_, value, traceback_))
        QtCore.qFatal('')
    sys.excepthook = excepthook

    try:
        qapp = QtWidgets.QApplication(sys.argv)
        app = ApplicationWindow()
        app.setWindowIcon(QtGui.QIcon('rbk.ico'))
        app.show()
        sys.exit(qapp.exec_())
    except:
        logging.error(traceback.format_exc())

