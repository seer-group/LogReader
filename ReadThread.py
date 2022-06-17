from tokenize import Double
from PyQt5.QtCore import QThread, pyqtSignal
from loglibPlus import Data, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, TaskStart, TaskFinish, Service, ParticleState
from loglibPlus import Memory, DepthCamera, RobotStatus
from datetime import timedelta
from datetime import datetime
import os
import json as js
import logging
import math
import time

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

def rad2LSB(data):
    new_data = [v/math.pi*180.0*16.4 for v in data]
    return new_data

def Fdir2Flink(f):
    flink = " <a href='file:///" + f + "'>"+f+"</a>"
    return flink

def printData(data, fid):
    try:
        print(data, file= fid)
    except UnicodeEncodeError:
        data = data.encode(errors='ignore')  
        print(data, file= fid)
    return

class ReadThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filenames = []
        self.log_config = "log_config.json"
        self.js = dict()
        self.content = dict()
        self.data = dict()
        self.data_org_key = dict()
        self.ylabel = dict()
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.taskstart = TaskStart()
        self.taskfinish = TaskFinish()
        self.service = Service()
        self.memory = Memory()
        self.depthcamera = DepthCamera()
        self.particle = ParticleState()
        self.rstatus = RobotStatus()
        self.log =  []
        self.tlist = []
        self.cpu_num = 4
        self.reader = None
        try:
            f = open('log_config.json',encoding= 'UTF-8')
            self.js = js.load(f)
        except FileNotFoundError:
            logging.error('Failed to open log_config.json')
            self.log.append('Failed to open log_config.json')

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        try:
            f = open(self.log_config,encoding= 'UTF-8')
            self.js = js.load(f)
            f.close()
            logging.error("Load {}".format(self.log_config))
            self.log.append("Load {}".format(self.log_config))
        except FileNotFoundError:
            logging.error("Failed to open {}".format(self.log_config))
            self.log.append("Failed to open {}".format(self.log_config))
        self.content = dict()
        content_delay = dict()
        ###############################################################################
        # 修改对应IO的解析方式
        # 读取模型文件
        root = os.path.split(os.path.split(self.filenames[0])[0])[0]
        modelFile = os.path.join(os.path.join(root, "models"), "robot.model")
        if os.path.exists(modelFile):
            try:
                with open(modelFile, "rb") as f:
                    mjs = js.load(f)
                for item in mjs["deviceTypes"]:
                    if item["name"] == "DI":
                        diNames = [di["deviceParams"][0]["arrayParam"]["params"][0]["uint32Value"] for di in item["devices"] if di["isEnabled"]]
                        # 对diNames进行排序
                        diNames.sort()
                        for i, diName in enumerate(diNames):
                            self.js["DI"]["content"][i]["name"] = f"id{diName}"
                            self.js["DI"]["content"][i]["description"] = f"DI.id{diName} 状态"
                        # 保留真实存在的与模型文件中一致的DI
                        self.js["DI"]["content"] = self.js["DI"]["content"][:len(diNames)]
                    elif item["name"] == "DO":
                        doNames = [do["deviceParams"][0]["arrayParam"]["params"][0]["uint32Value"] for do in item["devices"] if do["isEnabled"]]
                        # 对doNames进行排序
                        doNames.sort()
                        for i, doName in enumerate(doNames):
                            self.js["DO"]["content"][i]["name"] = f"id{doName}"
                            self.js["DO"]["content"][i]["description"] = f"DO.id{doName} 状态"
                        # 保留真实存在的与模型文件中一致的DO
                        self.js["DO"]["content"] = self.js["DO"]["content"][:len(doNames)]
            except Exception as e:
                print(e)
                logging.warning("Failed to load model file: {}".format(e))
        ###############################################################################
        for k in self.js:
            if "type" in self.js[k] and "content" in self.js[k]:
                if k == "LocationEachFrame" or k == "StopPoints":
                    self.content[self.js[k]["type"]] = Data(self.js[k], self.js[k]["type"])
                else:
                    if isinstance(self.js[k]['type'], list):
                        for type in self.js[k]["type"]:
                            content_delay[type] = Data(self.js[k], type)
                    elif isinstance(self.js[k]['type'], str):
                        content_delay[self.js[k]['type']] = Data(self.js[k], self.js[k]['type'])
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.taskstart = TaskStart()
        self.taskfinish = TaskFinish()
        self.service = Service()
        self.memory = Memory()
        self.depthcamera = DepthCamera()
        self.particle = ParticleState()
        self.rstatus = RobotStatus()
        self.tlist = []
        self.log =  []
        self.data = {}
        self.output_fname = ""
        if self.filenames:
            self.reader = ReadLog(self.filenames)
            self.reader.thread_num = self.cpu_num
            time_start=time.time()
            self.reader.parse(self.content, self.laser, self.err, 
                              self.war, self.fatal, self.notice, 
                              self.taskstart, self.taskfinish, self.service, 
                              self.memory, self.depthcamera, self.particle,
                              self.rstatus)
            time_end=time.time()
            self.log.append('read time cost: ' + str(time_end-time_start))
            self.content.update(content_delay)
            #analyze content
            # old_imu_flag = False
            # if 'IMU' in self.js:
            #     old_imu_flag = decide_old_imu(self.content['IMU']['gx'], self.content['IMU']['gy'], self.content['IMU']['gz'])
            # if old_imu_flag:
            #     self.content['IMU']['gx'] = rad2LSB(self.content['IMU']['gx'])
            #     self.content['IMU']['gy'] = rad2LSB(self.content['IMU']['gy'])
            #     self.content['IMU']['gz'] = rad2LSB(self.content['IMU']['gz'])
            #     logging.info('The unit of gx, gy, gz in file is rad/s.')
            #     self.log.append('The unit of gx, gy, gz in file is rad/s.') 
            # else:
            #     logging.info('The org unit of gx, gy, gz in IMU is LSB/s.')
            #     self.log.append('The org unit of gx, gy, gz in IMU is LSB/s.')
            tmp_tlist = self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t()
            tmax, tmin = None, None
            if len(tmp_tlist) > 0:
                tmax = max(self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t())
                tmin = min(self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t())
            if tmax != None:
                tmax = max(tmax, self.reader.tmax)
            else:
                tmax = self.reader.tmax
            if tmin != None:
                tmin = min(tmin, self.reader.tmin)
            else:
                tmin = self.reader.tmin
            dt = tmax - tmin
            self.tlist = [tmin, tmax]
            #save Error
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.output_fname = "Report_" + str(ts).replace(':','-').replace(' ','_') + ".txt"
            path = os.path.dirname(self.filenames[0])
            self.output_fname = path + "/" + self.output_fname
            self.log.append("Report File:" + Fdir2Flink(self.output_fname))
            fid = open(self.output_fname,"w") 
            print("="*20, file = fid)
            print("Files: ", self.filenames, file = fid)
            print(len(self.fatal.content()[0]), " FATALs, ", len(self.err.content()[0]), " ERRORs, ", 
                    len(self.war.content()[0]), " WARNINGs, ", len(self.notice.content()[0]), " NOTICEs", file = fid)
            self.log.append(str(len(self.fatal.content()[0])) + " FATALs, " + str(len(self.err.content()[0])) + 
                " ERRORs, " + str(len(self.war.content()[0])) + " WARNINGs, " + str(len(self.notice.content()[0])) + " NOTICEs")
            print("FATALs:", file = fid)
            for data in self.fatal.content()[0]:
                printData(data, fid)
            print("ERRORs:", file = fid)
            for data in self.err.content()[0]:
                printData(data, fid)
            print("WARNINGs:", file = fid)
            for data in self.war.content()[0]:
                printData(data, fid)
            print("NOTICEs:", file = fid)
            for data in self.notice.content()[0]:
                printData(data, fid)
            fid.close()
        #creat dic
        for k in self.content.keys():
            for name in self.content[k].data.keys():
                if name != 't':
                    self.data[k+'.'+name] = (self.content[k][name], self.content[k]['t'])
                    self.ylabel[k+'.'+name] = self.content[k].description[name]
                    self.data_org_key[k+'.'+name] = k
        if 'IMU' in self.js:
            self.data["IMU.org_gx"] = ([i+j for (i,j) in zip(self.content['IMU']['gx'],self.content['IMU']['offx'])], self.content['IMU']['t'])
            self.data["IMU.org_gy"] = ([i+j for (i,j) in zip(self.content['IMU']['gy'],self.content['IMU']['offy'])], self.content['IMU']['t'])
            self.data["IMU.org_gz"] = ([i+j for (i,j) in zip(self.content['IMU']['gz'],self.content['IMU']['offz'])], self.content['IMU']['t'])
            self.ylabel["IMU.org_gx"] = "原始的gx degree/s"
            self.ylabel["IMU.org_gy"] = "原始的gy degree/s"
            self.ylabel["IMU.org_gz"] = "原始的gz degree/s"
            self.data_org_key["IMU.org_gx"] = "IMU"
            self.data_org_key["IMU.org_gy"] = "IMU"
            self.data_org_key["IMU.org_gz"] = "IMU"

        self.data.update({"memory.used_sys":self.memory.used_sys(), "memory.free_sys":self.memory.free_sys(), "memory.rbk_phy": self.memory.rbk_phy(),
                     "memory.rbk_vir":self.memory.rbk_vir(),"memory.rbk_max_phy":self.memory.rbk_max_phy(),"memory.rbk_max_vir":self.memory.rbk_max_vir(),
                     "memory.cpu":self.memory.rbk_cpu(),"memory.sys_cpu":self.memory.sys_cpu()})
        self.ylabel.update({"memory.used_sys": "used_sys MB", "memory.free_sys":"free_sys MB", "memory.rbk_phy": "rbk_phy MB",
                     "memory.rbk_vir":"rbk_vir MB","memory.rbk_max_phy":"rbk_max_phy MB","memory.rbk_max_vir":"rbk_max_vir MB",
                     "memory.cpu":"cpu %", "memory.sys_cpu":"sys_cpu %"})

        for k in self.laser.datas.keys():
            self.data["laser"+str(k)+'.'+"ts"] = self.laser.ts(k)
            self.data["laser"+str(k)+'.'+"number"] = self.laser.number(k)
            self.ylabel["laser"+str(k)+'.'+"ts"] = "激光的时间戳"
            self.ylabel["laser"+str(k)+'.'+"number"] = "激光的id"

        self.data["depthcamera.number"] = self.depthcamera.number()
        self.data["depthcamera.ts"] = self.depthcamera.ts()
        self.ylabel["depthcamera.number"] = "深度摄像头id"
        self.ylabel["depthcamera.ts"] = "深度摄像头时间戳"
        
        self.data["particle.number"] = self.particle.number()
        self.data["particle.ts"] = self.particle.ts()
        self.ylabel["particle.number"] = "粒子数目"
        self.ylabel["particle.ts"] = "粒子时间戳"

        self.signal.emit(self.filenames)

    def getData(self, vkey):
        if vkey in self.data:
            if not self.data[vkey][0]:
                if vkey in self.data_org_key:
                    org_key = self.data_org_key[vkey]
                    if not self.content[org_key].parsed_flag:
                        # time_start=time.time()
                        self.content[org_key].parse_now(self.reader.lines)
                        for name in self.content[org_key].data.keys():
                            if name != 't':
                                self.ylabel[org_key+'.'+name] = self.content[org_key].description[name]                    
                        # time_end=time.time()
                        # print('real read time cost: ' + str(time_end-time_start))
                    tmp = vkey.split(".")
                    k = tmp[0]
                    name = tmp[1]
                    if k == "IMU" and "org" in name:
                        if len(name) == 6:
                            g = name[4::]  #org_gx, org_gy, org_gz
                            off = "off" + name[-1] #offx, offy, offz
                            self.data[vkey] = ([i+j for (i,j) in zip(self.content[k][g],self.content[k][off])], self.content[k]['t'])   
                        else:
                            self.data[vkey] = ([], [])              
                    else:
                        self.data[vkey] = (self.content[k][name], self.content[k]['t'])
            return self.data[vkey]
        else:
            return [[],[]]

    def getReportFileAddr(self):
        return self.output_fname


