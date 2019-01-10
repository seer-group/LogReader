import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.figure import Figure
from loglib import MCLoc, IMU, Odometer, Battery, Controller, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
from loglib import findrange
from datetime import datetime, timedelta
import sys
from numpy import searchsorted



def decide_old_imu(gx,gy,gz):
    for v in gx:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gy:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gz:
        if abs(round(v) - v) > 1e-5:
            return True
    return False

class ReadThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filenames = []
        self.run()

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        self.mcl = MCLoc()
        self.imu = IMU()
        self.odo = Odometer()
        self.battery = Battery()
        self.controller = Controller()
        self.odo = Odometer()
        self.send = Send()
        self.get = Get()
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.tlist = []
        if self.filenames:
            log = ReadLog(self.filenames)
            log.parse(self.mcl, self.imu, self.odo, self.battery, self.controller, self.send, self.get, self.laser, self.err, self.war, self.fatal, self.notice)
            #analyze data
            old_imu_flag = decide_old_imu(self.imu.gx()[0], self.imu.gy()[0], self.imu.gz()[0])
            if old_imu_flag:
                self.imu.old2newGyro()
                print('The unit of gx, gy, gz in file is rad/s.')
            else:
                print('The org unit of gx, gy, gz in IMU is LSB/s.')
            tmax = max(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            tmin = min(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            dt = tmax - tmin
            self.tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]
            #save Error
            fid = open("Report.txt", "w") 
            print("="*20, file = fid)
            print("Files: ", self.filenames, file = fid)
            print(len(self.fatal.content()[0]), " FATALs, ", len(self.err.content()[0]), " ERRORs, ", 
                    len(self.war.content()[0]), " WARNINGs, ", len(self.notice.content()[0]), " NOTICEs", file = fid)
            print("FATALs:", file = fid)
            for data in self.fatal.content()[0]:
                print(data, file = fid)
            print("ERRORs:", file = fid)
            for data in self.err.content()[0]:
                print(data,file = fid)
            print("WARNINGs:", file = fid)
            for data in self.war.content()[0]:
                print(data, file = fid)
            print("NOTICEs:", file = fid)
            for data in self.notice.content()[0]:
                print(data, file = fid)
            fid.close()
        #creat dic
        self.data = {"mcl.x":self.mcl.x(),"mcl.y":self.mcl.y(),"mcl.theta":self.mcl.theta(), "mcl.confidence":self.mcl.confidence(),
                     "imu.yaw":self.imu.yaw(),"imu.pitch": self.imu.pitch(), "imu.roll": self.imu.roll(), 
                     "imu.ax":self.imu.ax(),"imu.ay":self.imu.ay(),"imu.az":self.imu.az(),
                     "imu.gx":self.imu.gx(),"imu.gy":self.imu.gy(),"imu.gz":self.imu.gz(),
                     "imu.offx":self.imu.offx(),"imu.offy":self.imu.offy(),"imu.offz":self.imu.offz(),
                     "imu.org_gx":([i+j for (i,j) in zip(self.imu.gx()[0],self.imu.offx()[0])], self.imu.gx()[1]),
                     "imu.org_gy":([i+j for (i,j) in zip(self.imu.gy()[0],self.imu.offy()[0])], self.imu.gy()[1]),
                     "imu.org_gz":([i+j for (i,j) in zip(self.imu.gz()[0],self.imu.offz()[0])], self.imu.gz()[1]),
                     "odo.x":self.odo.x(),"odo.y":self.odo.y(),"odo.theta":self.odo.theta(),"odo.stop":self.odo.stop(),
                     "odo.vx":self.odo.vx(),"odo.vy":self.odo.vy(),"odo.vw":self.odo.vw(),"odo.steer_angle":self.odo.steer_angle(),
                     "send.vx":self.send.vx(),"send.vy":self.send.vy(),"send.vw":self.send.vw(),"send.steer_angle":self.send.steer_angle(),
                     "send.max_vx":self.send.max_vx(),"send.max_vw":self.send.max_vw(),
                     "get.vx":self.get.vx(),"get.vy":self.get.vy(),"get.vw":self.get.vw(),
                     "get.max_vx":self.get.max_vx(),"get.max_vw":self.get.max_vw(),
                     "battery.percentage": self.battery.percentage(), "battery.current": self.battery.current(), "battery.voltage": self.battery.voltage(),
                     "battery.ischarging": self.battery.ischarging(), "battery.temperature": self.battery.temperature(), "battery.cycle": self.battery.cycle(),
                     "controller.temp": self.controller.temp(), "controller.humi": self.controller.humi(), "controller.voltage":self.controller.voltage(),
                     "controller.emc": self.controller.emc(),"controller.brake":self.controller.brake(),"controller.driveremc":self.controller.driveremc(),
                     "controller.manualcharge": self.controller.manualcharge(),"controller.autocharge": self.controller.autocharge(), "controller.electric": self.controller.electric()}
        self.signal.emit(self.filenames)

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Log分析器')
        self.finishReadFlag = False
        self.read_thread = ReadThread()
        self.openLogFilesDialog()
        self.setupUI()

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,800)
        self.max_fig_num = 6 
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.openLogFilesDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.fig_menu = QtWidgets.QMenu('&Numer', self)
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
        self.menuBar().addMenu(self.fig_menu)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)
        self.menuBar().addMenu(self.help_menu)

        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        #Add ComboBox
        self.layout = QtWidgets.QVBoxLayout(self._main)
        self.grid = QtWidgets.QGridLayout()
        for i in range(0, cur_fig_num):
            self.grid.setColumnMinimumWidth(i*2,40)
            self.grid.setColumnStretch(i*2+1,1)
        self.labels = []
        self.combos = []
        for i in range(0,cur_fig_num):
            label = QtWidgets.QLabel("图片"+str(i+1),self)
            label.adjustSize()
            combo = QtWidgets.QComboBox(self)
            combo.resize(10,10)
            combo.activated.connect(self.combo_onActivated)
            self.labels.append(label)
            self.combos.append(combo)
            self.grid.addWidget(label,1,i*2)
            self.grid.addWidget(combo,1,i*2+1)
        self.label_info = QtWidgets.QLabel("",self)
        self.label_info.setStyleSheet("background-color: white;")
        self.grid.addWidget(self.label_info,2,0,1,50)
        self.layout.addLayout(self.grid)

        #图形化结构
        self.static_canvas = FigureCanvas(Figure(figsize=(100,100)))
        self.layout.addWidget(self.static_canvas)
        self.old_home = NavigationToolbar.home
        self.old_forward = NavigationToolbar.forward
        self.old_back = NavigationToolbar.back
        NavigationToolbar.home = self.new_home
        NavigationToolbar.forward = self.new_forward
        NavigationToolbar.back = self.new_back
        self.addToolBar(NavigationToolbar(self.static_canvas, self))
        self.axs= self.static_canvas.figure.subplots(cur_fig_num, 1, sharex = True)

        #鼠标移动消息
        self.static_canvas.mpl_connect('motion_notify_event', self.mouse_move)

    def mouse_move(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = event.xdata * 86400 - 62135712000
            if mouse_time > 1e6:
                mouse_time = datetime.fromtimestamp(mouse_time)
                content = []
                dt_min = 1e10
                if self.read_thread.fatal.t():
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
                    dt_min = min(vdt)
                    content = self.read_thread.fatal.content()[0][vdt.index(dt_min)]
                if self.read_thread.err.t(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        content = self.read_thread.err.content()[0][vdt.index(tmp_dt)]
                if self.read_thread.war.t(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        content = self.read_thread.war.content()[0][vdt.index(tmp_dt)]
                if self.read_thread.notice.t(): 
                    vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
                    tmp_dt = min(vdt)
                    if tmp_dt < dt_min:
                        dt_min = tmp_dt
                        content = self.read_thread.notice.content()[0][vdt.index(tmp_dt)]
                if dt_min < 1:
                    self.label_info.setText(content)
                else:
                    self.label_info.setText("")
            else:
                self.label_info.setText("")
        else:
            self.label_info.setText("")


    def new_home(self, *args, **kwargs):
        for ax, combo in zip(self.axs, self.combos):
            text = combo.currentText()
            data = self.read_thread.data[text][0]
            if data:
                max_range = max(max(data) - min(data), 1e-6)
                ax.set_ylim(min(data) - 0.05 * max_range, max(data)  + 0.05 * max_range)
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

    def openLogFilesDialog(self):
        # self.setGeometry(50,50,640,480)
        self.read_thread.signal.connect(self.readFinished)
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log);;All Files (*)", options=options)
        if self.filenames:
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            self.statusBar().showMessage('Loading......: {0}'.format([f.split('/')[-1] for f in self.filenames]))

    def readFinished(self, result):
        print("Current: {0}.".format(result))  # Show the output to the user
        self.statusBar().showMessage('Finished')
        self.finishReadFlag = True
        self.setWindowTitle('Log分析器: {0}'.format([f.split('/')[-1] for f in self.filenames]))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            keys = list(self.read_thread.data.keys())
            for ax, combo in zip(self.axs, self.combos):
                combo.addItems(keys)
                self.drawdata(ax, self.read_thread.data[combo.currentText()],combo.currentText(), True)

    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer""")

    def combo_onActivated(self):
        # print("combo1: ",text)
        curcombo = self.sender()
        index = self.combos.index(curcombo)
        text = curcombo.currentText()
        # print("index:", index, "sender:", self.sender()," text:", text)
        ax = self.axs[index]
        self.drawdata(ax, self.read_thread.data[text], text, False)

    def fignum_changed(self,action):
        new_fig_num = int(action.text())
        xmin, xmax = self.axs[0].get_xlim()
        for ax in self.axs:
            self.static_canvas.figure.delaxes(ax)
        self.axs= self.static_canvas.figure.subplots(new_fig_num, 1, sharex = True)
        self.static_canvas.figure.canvas.draw()
        for i in reversed(range(2, self.grid.count())): 
            self.grid.itemAt(i).widget().deleteLater()
        for i in range(0, new_fig_num):
            self.grid.setColumnMinimumWidth(i*2,40)
            self.grid.setColumnStretch(i*2+1,1)
        combo_ind = [] 
        for combo in self.combos:
            combo_ind.append(combo.currentIndex())
        self.labels = []
        self.combos = []
        for i in range(0,new_fig_num):
            label = QtWidgets.QLabel("图片"+str(i+1),self)
            label.adjustSize()
            combo = QtWidgets.QComboBox(self)
            combo.resize(10,10)
            combo.activated.connect(self.combo_onActivated)
            self.labels.append(label)
            self.combos.append(combo)
            self.grid.addWidget(label,1,i*2)
            self.grid.addWidget(combo,1,i*2+1)
        self.label_info = QtWidgets.QLabel("",self)
        self.label_info.setStyleSheet("background-color: white;")
        self.grid.addWidget(self.label_info,2,0,1,50)
        if self.finishReadFlag:
            if self.read_thread.filenames:
                keys = list(self.read_thread.data.keys())
                count = 0
                for ax, combo in zip(self.axs, self.combos):
                    combo.addItems(keys)
                    if count < len(combo_ind):
                        combo.setCurrentIndex(combo_ind[count])
                    count = count + 1
                    ax.set_xlim(xmin, xmax)
                    self.drawdata(ax, self.read_thread.data[combo.currentText()],combo.currentText(), False)

    def drawdata(self, ax, data, ylabel, resize = False):
        xmin,xmax =  ax.get_xlim()
        ax.cla()
        self.drawFEWN(ax)
        if data[1] and data[0]:
            ax.plot(data[1], data[0], '.')
            max_range = max(max(data[0]) - min(data[0]), 1e-6)
            ax.set_ylim(min(data[0]) - 0.05 * max_range, max(data[0]) + 0.05 * max_range)
        if resize:
            ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        else:
            ax.set_xlim(xmin, xmax)
        ax.set_ylabel(ylabel)
        ax.grid()
        self.static_canvas.figure.canvas.draw()

    def drawFEWN(self,ax):
        """ 绘制 Fatal, Error, Warning在坐标轴上"""
        fl, el, wl,nl = None, None, None, None
        legend_info = []
        for tmp in self.read_thread.fatal.t():
            fl, = ax.plot((tmp,tmp),[-1e10, 1e10],'m-')
        if fl:
            legend_info.append(fl)
            legend_info.append('fatal')
        for tmp in self.read_thread.err.t():
            el, = ax.plot((tmp,tmp),[-1e10, 1e10],'r-.')
        if el:
            legend_info.append(el)
            legend_info.append('error')
        for tmp in self.read_thread.war.t():
            wl, = ax.plot((tmp,tmp),[-1e10, 1e10],'y--')
        if wl:
            legend_info.append(wl)
            legend_info.append('warning')
        for tmp in self.read_thread.notice.t():
            nl, = ax.plot((tmp,tmp),[-1e10, 1e10],'g:')
        if nl:
            legend_info.append(nl)
            legend_info.append('notice')
        if legend_info:
            ax.legend(legend_info[0::2], legend_info[1::2], loc='upper right')


if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    app.show()
    qapp.exec_()