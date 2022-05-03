from matplotlib.backend_tools import ToolBase, ToolToggleBase
import matplotlib.lines as lines
import matplotlib.text as text
import math, os
from matplotlib.backends.backend_qt5agg import  FigureCanvas, NavigationToolbar2QT
from PyQt5 import QtGui, QtCore,QtWidgets
from datetime import datetime
from loglibPlus import num2date
from enum import IntEnum
def keepRatio(xmin, xmax, ymin, ymax, fig_ratio, bigger = True):
    ax_ratio = (xmax - xmin)/(ymax - ymin)
    spanx = xmax - xmin 
    xmid = (xmax+xmin)/2
    spany = ymax - ymin
    ymid = (ymax+ymin)/2
    if bigger:
        if ax_ratio > fig_ratio:
            ymax = ymid + spany*ax_ratio/fig_ratio/2
            ymin = ymid - spany*ax_ratio/fig_ratio/2
        elif ax_ratio < fig_ratio:
            xmax = xmid + spanx*fig_ratio/ax_ratio/2
            xmin = xmid - spanx*fig_ratio/ax_ratio/2
    else:
        if ax_ratio < fig_ratio:
            ymax = ymid + spany*ax_ratio/fig_ratio/2
            ymin = ymid - spany*ax_ratio/fig_ratio/2
        elif ax_ratio > fig_ratio:
            xmax = xmid + spanx*fig_ratio/ax_ratio/2
            xmin = xmid - spanx*fig_ratio/ax_ratio/2
    return xmin, xmax, ymin ,ymax

class TriggleFlag(IntEnum):
    ZOOM = 0
    PAN = 1
    RULER = 2
    NONE = 3
class MyToolBar(NavigationToolbar2QT):
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis', 'zoom_to_rect', 'zoom'),
        (None, None, None, None),
      )
    def __init__(self, canvas, parent, ruler, coordinates=True):
        """coordinates: should we show the coordinates on the right?"""
        NavigationToolbar2QT.__init__(self, canvas, parent, False)
        icon = QtGui.QIcon("images/ruler_large.png")
        a = self.addAction(icon,"ruler", self.ruler)
        a.setCheckable(True)
        
        self._actions["ruler"] = a
        self.triggle_mode = TriggleFlag.NONE
        self._idPress = None
        self._idRelease = None
        self._idDrag = None
        self._ruler = ruler
        self._rulerXY = []
        self._has_home_back = False

    def home(self, *args):
        if self._has_home_back:
            return True
        xmax = None
        xmin = None
        for a in self.canvas.figure.get_axes():
            ymax = None
            ymin = None
            lines = a.get_lines()
            for l in lines:
                data = l.get_data()
                if xmax is None and len(data[0]) > 0:
                    xmax = max(data[0])
                else:
                    xmax = max(data[0] + [xmax])
                if xmin is None and len(data[0]) > 0:
                    xmin = min(data[0])
                else:
                    xmin = min(data[0]+[xmin])
                if ymax is None and len(data[1]) > 0:
                    ymax = max(data[1])
                else:
                    ymax = max(data[1]+[ymax])
                if ymin is None and len(data[1]) > 0:
                    ymin = min(data[1])
                else:
                    ymin = min(data[1]+[ymin])
            if ymax != None and ymin != None:
                dy = (ymax - ymin) * 0.05
                a.set_ylim(ymin - dy, ymax + dy)
        if xmax != None and xmin != None:
            dx = (xmax - xmin) * 0.05
            for a in self.canvas.figure.get_axes():
                a.set_xlim(xmin - dx, xmax + dx)
        self.canvas.figure.canvas.draw()


    def update_home_callBack(self, func):
        self._has_home_back = True
        self._actions["home"].triggered.connect(func)


    def my_update_buttons_checked(self):
        if self.triggle_mode != TriggleFlag.RULER:
            if self._idPress is not None:
                self._idPress = self.canvas.mpl_disconnect(self._idPress)
            if self._idRelease is not None:
                self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        elif self.triggle_mode != TriggleFlag.NONE:
            if self._actions['pan'].isChecked():
                super().pan(None)
            if self._actions['zoom'].isChecked():
                super().zoom(None)            
        self._actions['ruler'].setChecked(self.triggle_mode == TriggleFlag.RULER)
        self._actions['zoom'].setChecked(self.triggle_mode == TriggleFlag.ZOOM)
        self._actions['pan'].setChecked(self.triggle_mode == TriggleFlag.PAN)

    def pan(self, *args):
        # print("pan", self.triggle_mode)
        super().pan(*args)
        self.triggle_mode = TriggleFlag.NONE if self.triggle_mode == TriggleFlag.PAN else TriggleFlag.PAN
        self.my_update_buttons_checked()

    def zoom(self, *args):
        # print("zoom", self.triggle_mode)
        super().zoom(*args)
        self.triggle_mode = TriggleFlag.NONE if self.triggle_mode == TriggleFlag.ZOOM else TriggleFlag.ZOOM
        self.my_update_buttons_checked()

    def ruler(self):
        # print("ruler", self.triggle_mode)
        """Activate ruler."""
        self.triggle_mode = TriggleFlag.NONE if self.triggle_mode == TriggleFlag.RULER else TriggleFlag.RULER
        active = self.triggle_mode == TriggleFlag.RULER

        if active:
            self._idPress = self.canvas.mpl_connect('button_press_event',
                                                    self.press_ruler)
            self._idRelease = self.canvas.mpl_connect('button_release_event',
                                                      self.release_ruler)
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)
            self._ruler.hide_all()
            self.canvas.figure.canvas.draw()

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(active)
        self.my_update_buttons_checked()

    def press_ruler(self, event):
        """Callback for mouse button press in Ruler mode."""
        if self.triggle_mode != TriggleFlag.RULER:
            return
        if event.button == 1 and event.inaxes:
            self._button_pressed = 1
        else:
            self._button_pressed = None
            return
        self._rulerXY = [[event.xdata, event.ydata],[event.xdata, event.ydata]]
        if self._idDrag is not None:
            self._idDrag = self.canvas.mpl_disconnect(self._idDrag)
        self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.move_ruler)
        self._ruler.update(event.inaxes, self._rulerXY)
        self._ruler.set_visible(event.inaxes, True)

    def release_ruler(self, event):
        """Callback for mouse button release in Ruler mode."""
        if self.triggle_mode != TriggleFlag.RULER:
            return
        if event.button == 1 and event.inaxes:
            self._button_pressed = 1
        else:
            self._button_pressed = None
            return
        if self._idDrag is not None:
            self._idDrag = self.canvas.mpl_disconnect(self._idDrag)

    def move_ruler(self, event):
        """Callback for mouse button move in Ruler mode."""
        if self.triggle_mode != TriggleFlag.RULER:
            return
        if event.button == 1 and event.inaxes:
            self._button_pressed = 1
        else:
            self._button_pressed = None
            return
        self._rulerXY[1] = [event.xdata, event.ydata]
        self._ruler.update(event.inaxes, self._rulerXY)
        self.canvas.figure.canvas.draw()
    
    def isActive(self):
        for a in self._actions:
            if self._actions[a].isChecked():
                return True
        return False

class RulerShape:
    def __init__(self):
        self._lines = []
        self._texts = []
        self._axs = []
    
    def clear_rulers(self):
        self._lines = []
        self._texts = []
        self._axs = []

    def add_ruler(self,ax):
        ruler_t = text.Text(0, 0, '')
        ruler_t.set_bbox(dict(facecolor='white', alpha=0.5))
        ruler_l = lines.Line2D([],[], marker = '+', linestyle = '-', color = 'black', markersize = 10.0)
        ruler_t.set_visible(False)
        ruler_l.set_visible(False)
        ruler_l.set_zorder(101)
        ruler_t.set_zorder(100)
        ax.add_line(ruler_l)
        ax.add_artist(ruler_t)
        if ax not in self._axs:
            self._lines.append(ruler_l)
            self._texts.append(ruler_t)
            self._axs.append(ax)
        else:
            indx = self._axs.index(ax)
            self._lines[indx] = ruler_l
            self._texts[indx] = ruler_t
        
    def update(self, ax, data):
        indx = self._axs.index(ax)
        self._lines[indx].set_xdata([data[0][0],data[1][0]])
        self._lines[indx].set_ydata([data[0][1],data[1][1]])
        (xmin, xmax) = ax.get_xlim()
        (ymin, ymax) = ax.get_ylim()
        xmid = (xmin + xmax)/2.0
        ymid = (ymin + ymax)/2.0
        text_x = (data[1][0]+data[0][0])/2.0
        text_y = (data[1][1]+data[0][1])/2.0
        if ymid < text_y:
            self._texts[indx].set_verticalalignment("top")
        else:
            self._texts[indx].set_verticalalignment("bottom")
        if xmid < text_x:
            self._texts[indx].set_horizontalalignment("right")
        else:
            self._texts[indx].set_horizontalalignment("left")
        self._texts[indx].set_x(text_x)
        self._texts[indx].set_y(text_y)        
        dx = data[1][0] - data[0][0]
        dy = data[1][1] - data[0][1]
        ds = math.sqrt(dx * dx + dy * dy)
        degree = math.atan2(dy, dx) * 180.0 /math.pi
        self._texts[indx].set_text('X:{:.3f} m\nY:{:.3f} m\nD:{:.3f} m\nA:{:.3f}$\degree$'.format(dx, dy, ds, degree))

    def set_visible(self, ax, value):
        indx = self._axs.index(ax)
        self._texts[indx].set_visible(value)
        self._lines[indx].set_visible(value)

    def hide_all(self):
        for t,l in zip(self._texts, self._lines):
            t.set_visible(False)
            l.set_visible(False)

class RulerShapeMap(RulerShape):
    def __init__(self):
        super(RulerShapeMap, self).__init__()

    def update(self, ax, data):
        indx = self._axs.index(ax)
        self._lines[indx].set_xdata([data[0][0],data[1][0]])
        self._lines[indx].set_ydata([data[0][1],data[1][1]])
        (xmin, xmax) = ax.get_xlim()
        (ymin, ymax) = ax.get_ylim()
        xmid = (xmin + xmax)/2.0
        ymid = (ymin + ymax)/2.0
        text_x = (data[1][0]+data[0][0])/2.0
        text_y = (data[1][1]+data[0][1])/2.0
        if ymid < text_y:
            self._texts[indx].set_verticalalignment("top")
        else:
            self._texts[indx].set_verticalalignment("bottom")
        if xmid < text_x:
            self._texts[indx].set_horizontalalignment("right")
        else:
            self._texts[indx].set_horizontalalignment("left")
        self._texts[indx].set_x(text_x)
        self._texts[indx].set_y(text_y)  
        dt = data[1][0] - data[0][0]
        try:
            t1 = num2date(data[1][0])
            t0 = num2date(data[0][0])
            dt = (t1 - t0).total_seconds()
        except:
            pass 
        dy = data[1][1] - data[0][1]
        dydt = 0
        if abs(dt) > 1e-9:
            dydt = dy/dt
        self._texts[indx].set_text('dY:{:.3e}\ndT:{:.3e} s\n dY/dT:{:.3e}'.format(dy, dt, dydt))
