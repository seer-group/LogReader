from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider,RadioButtons
import sys
mcl = MCLoc()
imu = IMU()
odo = Odometer()
send = Send()
get = Get()
laser = Laser(1000.0)
err = ErrorLine()
war = WarningLine()
fat = FatalLine()
notice = NoticeLine()
print(sys.argv[1:])
log = ReadLog(sys.argv[1:])
log.parse(mcl, imu, odo, send, get, laser, err, war, fat, notice)

f = open("Report.txt", "w", encoding='utf-8') 
print(len(err.content()), " ERRORs, ", len(war.content()), " WARNINGs, ", len(fat.content()), " FATALs, ", len(notice.content()), " NOTICEs", file = f)
print("ERRORs:", file = f)
for data in err.content():
    print(data,file = f)
print("WARNINGs:", file = f)
for data in war.content():
    print(data, file = f)
print("FATALs:", file = f)
for data in fat.content():
    print(data, file = f)
print("NOTICEs:", file = f)
for data in notice.content():
    print(data, file = f)
f.close()

plt.figure(1)
plt.subplot(4,1,1)
plt.title('MCLoc')
plt.plot(mcl.t(), mcl.x(),'.', label = 'x')
plt.legend()
plt.subplot(4,1,2)
plt.plot(mcl.t(), mcl.y(),'.', label = 'y')
plt.legend()
plt.subplot(4,1,3)
plt.plot(mcl.t(), mcl.theta(),'.', label = 'theta')
plt.legend()
plt.subplot(4,1,4)
plt.plot(mcl.t(), mcl.confidence(),'.', label = 'confidence')
plt.legend()

plt.figure(21)
plt.title('IMU Yaw')
plt.plot(imu.t(), imu.yaw(),'.')
plt.figure(2)
plt.subplot(3,3,1)
plt.title('IMU')
plt.plot(imu.t(), imu.ax(),'.', label = 'ax')
plt.legend()
plt.subplot(3,3,2)
plt.plot(imu.t(), imu.ay(),'.', label = 'ay')
plt.legend()
plt.subplot(3,3,3)
plt.plot(imu.t(), imu.az(),'.', label = 'az')
plt.legend()
plt.subplot(3,3,4)
plt.plot(imu.t(), imu.gx(),'.', label = 'gx')
plt.legend()
plt.subplot(3,3,5)
plt.plot(imu.t(), imu.gy(),'.', label = 'gy')
plt.legend()
plt.subplot(3,3,6)
plt.plot(imu.t(), imu.gz(),'.', label = 'gz')
plt.legend()
plt.subplot(3,3,7)
plt.plot(imu.t(), imu.offx(),'.', label = 'offx')
plt.legend()
plt.subplot(3,3,8)
plt.plot(imu.t(), imu.offy(),'.', label = 'offy')
plt.legend()
plt.subplot(3,3,9)
plt.plot(imu.t(), imu.offz(),'.', label = 'offz')
plt.legend()

plt.figure(3)
plt.subplot(2,3,1)
plt.title('Odometer')
plt.plot(odo.t(), odo.x(),'.', label = 'x')
plt.legend()
plt.subplot(2,3,2)
plt.plot(odo.t(), odo.y(),'.', label = 'y')
plt.legend()
plt.subplot(2,3,3)
plt.plot(odo.t(), odo.theta(),'.', label = 'theta')
plt.legend()
plt.subplot(2,3,4)
plt.plot(odo.t(), odo.vx(),'.', label = 'vx')
plt.legend()
plt.subplot(2,3,5)
plt.plot(odo.t(), odo.vy(),'.', label = 'vy')
plt.legend()
plt.subplot(2,3,6)
plt.plot(odo.t(), odo.vw(),'.', label = 'vw')
plt.legend()

plt.figure(4)
plt.subplot(2,2,1)
plt.title('Send And Get Velocity')
plt.plot(send.t(), send.vx(), 'o', label= 'send vx')
plt.plot(get.t(), get.vx(), '.', label= 'get vx')
plt.plot(send.t(), send.max_vx(), 'o', label= 'send max vx')
plt.plot(get.t(), get.max_vx(), '.', label= 'get max vx')
plt.legend()
plt.subplot(2,2,2)
plt.plot(send.t(), send.vy(), 'o', label= 'send vy')
plt.plot(get.t(), get.vy(), '.', label= 'get vy')
plt.legend()
plt.subplot(2,2,3)
plt.plot(send.t(), send.vw(), 'o', label= 'send vw')
plt.plot(get.t(), get.vw(), '.', label= 'get vw')
plt.plot(send.t(), send.max_vw(), 'o', label= 'send max vw')
plt.plot(get.t(), get.max_vw(), '.', label= 'get max vw')
plt.legend()
plt.subplot(2,2,4)
plt.plot(send.t(), send.steer_angle(), 'o', label= 'send steer_angle')
plt.plot(get.t(), get.steer_angle(), '.', label= 'get steer_angle')
plt.legend()

if len(laser.x()) > 0:
    plt.figure(5)
    plt.subplot(2,1,1)
    plt.title("Laser")
    plt.subplots_adjust(bottom=0.2,left=0.1) 
    l1, = plt.plot(laser.x()[1], laser.y()[1], '.')
    plt.axis('equal')
    plt.grid()
    plt.subplot(2,1,2,projection = 'polar')
    plt.subplots_adjust(bottom=0.2,left=0.1) 
    l2, = plt.plot(laser.angle()[1], laser.dist()[1], '.')
    axcolor = 'lightgoldenrodyellow'  # slider的颜色
    om1= plt.axes([0.1, 0.08, 0.8, 0.02], facecolor=axcolor) # 第一slider的位置
    som1 = Slider(om1, r'Time', 0, len(laser.ts())-1, valinit=0, valfmt='%i') #产生第二slider
    def update(val):
        s1 = int(som1.val)
        l1.set_xdata(laser.x()[s1])
        l1.set_ydata(laser.y()[s1])
        l2.set_xdata(laser.angle()[s1])
        l2.set_ydata(laser.dist()[s1])
    som1.on_changed(update)
plt.show()