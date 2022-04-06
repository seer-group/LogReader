import re
import math
from datetime import datetime
import codecs
import chardet
import logging
import gzip
from multiprocessing import Pool, Manager
import json
def rbktimetodate(rbktime):
    """ 将rbk的时间戳转化为datatime """
    if len(rbktime) == 17:
        return datetime.strptime(rbktime, '%y%m%d %H%M%S.%f')
    else:
        return datetime.strptime(rbktime, '%Y-%m-%d %H:%M:%S.%f')

def findrange(ts, t1, t2):
    """ 在ts中寻找大于t1小于t2对应的下标 """
    small_ind = -1
    large_ind = len(ts)-1
    for i, data in enumerate(ts):
        large_ind = i
        if(t1 <= data and small_ind < 0):
            small_ind = i
        if(t2 <= data):
            break
    return small_ind, large_ind

def polar2xy(angle, dist):
    """ 将极坐标angle,dist 转化为xy坐标 """
    x , y = [], []
    for a, d in zip(angle, dist):
        x.append(d * math.cos(a))
        y.append(d * math.sin(a))
    return x,y

def sortFunc(ds):
    return ds[0]
class ReadLog:
    """ 读取Log """
    def __init__(self, filenames):
        """ 支持传入多个文件名称"""
        self.filenames = filenames
        self.lines = []
        self.lines_num = 0
        self.thread_num = 4
        self.sum_argv = Manager().list()
        self.argv = []
        self.tmin = None
        self.tmax = None
        self.regex = re.compile("\[(.*?)\].*")
    def _startTime(self, f, file):
        for line in f.readlines(): 
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    line = line.decode('gbk')
                except UnicodeDecodeError:
                    logging.debug("{}: {} {}".format(file, " Skipped due to decoding failure!", line))
                    continue
            out = self.regex.match(line)
            if out:
                return rbktimetodate(out.group(1))
        return None   
    def _readData(self, f, file):
        lines = []
        for line in f.readlines(): 
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    line = line.decode('gbk')
                except UnicodeDecodeError:
                    logging.debug("{}: {} {}".format(file, " Skipped due to decoding failure!", line))
                    continue
            lines.append(line)
        for line in lines:
            out = self.regex.match(line)
            if out:
                t = rbktimetodate(out.group(1))
                if self.tmin is None:
                    self.tmin = t
                elif self.tmin > t:
                    self.tmin = t
                break
        for line in reversed(lines):
            out = self.regex.match(line)
            if out:
                t = rbktimetodate(out.group(1))
                if self.tmax is None:
                    self.tmax = t
                elif self.tmax < t:
                    self.tmax = t
                break
        self.lines.extend(lines)

    def _do(self, lines):
        l0 = lines["l0"]
        for ind, line in enumerate(lines["data"]):
            break_flag = False
            for data in self.argv:
                if type(data).__name__ == 'dict':
                    for k in data.keys():
                        data[k].parsed_flag = True
                        if data[k].parse(line, ind + l0):
                            break_flag = True
                            break
                    if break_flag:
                        break_flag = False
                        break
                elif data.parse(line):
                    break
        self.sum_argv.append((l0,self.argv))

    def _work(self, argv):
        self.lines_num = len(self.lines)
        al = int(self.lines_num/self.thread_num)
        if al < 1000 or self.thread_num <= 1:
            for ind, line in enumerate(self.lines):
                break_flag = False
                for data in argv:
                    if type(data).__name__ == 'dict':
                        for k in data.keys():
                            data[k].parsed_flag = True
                            if data[k].parse(line, ind):
                                break_flag = True
                                break
                        if break_flag:
                            break_flag = False
                            break
                    elif data.parse(line):
                        break     
        else:
            line_caches = []
            print("thread num:", self.thread_num, ' lines_num:', self.lines_num)
            for i in range(self.thread_num):
                if i is self.thread_num -1:
                    tmp = dict()
                    tmp['l0'] = i * al
                    tmp['data'] = self.lines[i*al:]
                    line_caches.append(tmp)
                else:
                    tmp = dict()
                    tmp['l0'] = i * al
                    tmp['data'] = self.lines[i*al:((i+1)*al)]
                    line_caches.append(tmp)
            pool = Pool(self.thread_num)
            self.argv = argv
            pool.map(self._do, line_caches)
            self.sum_argv.sort(key = sortFunc)
            for s in self.sum_argv:
                for (a,b) in zip(argv,s[1]):
                    if type(a) is dict:
                        for k in a.keys():
                            a[k].insert_data(b[k])
                    else:
                        a.insert_data(b)
            self.sum_argv = Manager().list()

    def parse(self,*argv):
        """依据输入的正则进行解析"""
        file_ind = []
        file_stime = []
        for (ind,file) in enumerate(self.filenames):
            if file.endswith(".log"):
                try:
                    with open(file,'rb') as f:
                        st = self._startTime(f, file_ind)
                        if st != None:
                            file_ind.append(ind)
                            file_stime.append(st)
                except:
                    continue
            else:
                try:
                    with gzip.open(file,'rb') as f:
                        st = self._startTime(f, file_ind)
                        if st != None:
                            file_ind.append(ind)
                            file_stime.append(st) 
                except:
                    continue       
        
        max_location =sorted(enumerate(file_stime), key=lambda y:y[1])
        #print(max_location)
        
        new_file_ind = []
        for i in range(len(max_location)):
            new_file_ind.append(file_ind[max_location[i][0]])

        for i in new_file_ind:
            file = self.filenames[i]
            if file.endswith(".log"):
                try:
                    with open(file,'rb') as f:
                        self._readData(f,file)
                except:
                    continue
            else:
                try:
                    with gzip.open(file,'rb') as f:
                        self._readData(f, file)    
                except:
                    continue
        self._work(argv)


class Data:
    def __init__(self, info, key_name:str):
        self.type = key_name
        self.regex = re.compile("\[(.*?)\].*\["+self.type+"\]\[(.*?)\]")
        self.regex2 = re.compile("\[(.*?)\].*\["+self.type+"\|(.*?)\]")
        self.short_regx = "["+self.type
        self.info = info['content']
        self.data = dict()
        self.data['t'] = []
        self.description = dict()
        self.unit = dict()
        self.parse_error = False
        self.parsed_flag = False
        self.line_num = []
        for tmp in self.info:
            self.data[tmp['name']] =  []
            if 'unit' in tmp:
                self.unit[tmp['name']] = tmp['unit']
            else:
                self.unit[tmp['name']] = ""
            if 'description' in tmp:
                if type(tmp['description']) is str:
                    self.description[tmp['name']] = tmp['description'] + " " + self.unit[tmp['name']]
                elif type(tmp['description']) is int:
                    self.description[tmp['name']] = tmp['description']
                else:
                    self.description[tmp['name']] = self.type + '.' + tmp['name'] + " " + self.unit[tmp['name']]
            else:
                self.description[tmp['name']] = self.type + '.' + tmp['name'] + " " + self.unit[tmp['name']]

    def _storeData(self, tmp, ind, values):
        if tmp['type'] == 'double' or tmp['type'] == 'int64' or tmp['type'] == 'int':
            try:
                self.data[tmp['name']].append(float(values[ind]))
            except:
                self.data[tmp['name']].append(0.0)
        elif tmp['type'] == 'mm':
            try:
                self.data[tmp['name']].append(float(values[ind])/1000.0)
            except:
                self.data[tmp['name']].append(0.0)
        elif tmp['type'] == 'cm':
            try:
                self.data[tmp['name']].append(float(values[ind])/100.0)
            except:
                self.data[tmp['name']].append(0.0)
        elif tmp['type'] == 'rad':
            try:
                self.data[tmp['name']].append(float(values[ind])/math.pi * 180.0)
            except:
                self.data[tmp['name']].append(0.0)
        elif tmp['type'] == 'm':
            try:
                self.data[tmp['name']].append(float(values[ind]))
            except:
                self.data[tmp['name']].append(0.0)
        elif tmp['type'] == 'LSB':
            try:
                self.data[tmp['name']].append(float(values[ind])/16.03556)
            except:
                self.data[tmp['name']].append(0.0)                               
        elif tmp['type'] == 'bool':
            try:
                if values[ind] == "true" or values[ind] == "1":
                    self.data[tmp['name']].append(1.0)
                else:
                    self.data[tmp['name']].append(0.0)
            except:
                self.data[tmp['name']].append(0.0)  
        elif tmp['type'] == 'json':
            try:
                self.data[tmp['name']].append(json.loads(values[ind]))
            except:
                self.data[tmp['name']].append(values[ind])   
        elif tmp['type'] == 'str':
            self.data[tmp['name']].append(values[ind])
        else:
            self.data[tmp['name']].append(values[ind])

    def parse(self, line, num):
        if self.short_regx in line:
            out = self.regex.match(line)
            if not out:
                out = self.regex2.match(line)
            if out:
                datas = out.groups()
                values = datas[1].split('|')
                self.data['t'].append(rbktimetodate(datas[0]))
                for tmp in self.info:
                    if 'type' in tmp and 'index' in tmp and 'name' in tmp:
                        if type(self.description[tmp['name']]) is int:
                            if 'description' in tmp:
                                tmp_type = type(tmp['description'])
                                description = ""
                                has_description = False
                                if tmp_type is str:
                                    description = tmp['description']
                                    has_description = True
                                elif tmp_type is int:
                                    if tmp['description'] < len(values) and tmp['index'] < len(values):
                                        description = values[tmp['description']]
                                        has_description = True
                                if has_description:
                                    self.description[tmp['name']] = description + " " + self.unit[tmp['name']]
                                else:
                                    self.description[tmp['name']] = tmp['name']

                        if tmp['index'] < len(values):
                            self._storeData(tmp, int(tmp['index']), values)
                        else:
                            self.data[tmp['name']].append(None)

                    else:
                        if not self.parse_error:
                            logging.error("Error in {} {} ".format(self.type, tmp.keys()))
                            self.parse_error = True
                self.line_num.append(num)
                return True
            return False
        return False
    def parse_now(self, lines):
        if not self.parsed_flag:
            for ind, line in enumerate(lines):
                self.parse(line, ind)
                
    def __getitem__(self,k):
        return self.data[k]
    def __setitem__(self,k,value):
        self.data[k] = value
    def insert_data(self, other):
        for key in other.data.keys():
            if key in self.data.keys():
                self.data[key].extend(other.data[key])
            else:
                self.data[key] = other.data[key]     
        self.line_num.extend(other.line_num)

class Laser:
    """  激光雷达的数据
    data[0]: t
    data[1]: ts 激光点的时间戳
    data[2]: angle rad 
    data[3]: dist m
    data[4]: x m
    data[5]: y m
    data[6]: number
    data[7]: rssi
    """
    def __init__(self, max_dist):
        """ max_dist 为激光点的最远距离，大于此距离激光点无效"""
        self.regex = re.compile('\[(.*?)\].*\[Laser:? ?(\d*?)\]\[(.*?)\]')
        self.regexV2 = re.compile('\[(.*?)\].*\[LaserWithRssi:? ?(\d*?)\]\[(.*?)\]')
        self.short_regx = "[Laser"
        #self.data = [[] for _ in range(7)]
        self.datas = dict()
        self.max_dist = max_dist
    def parse(self, line):
        if self.short_regx in line:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                laser_id = 0
                if datas[1] != "":
                    laser_id =  int(datas[1])
                if laser_id not in self.datas:
                    self.datas[laser_id] = [[] for _ in range(8)]
                self.datas[laser_id][0].append(rbktimetodate(datas[0]))
                tmp_datas = datas[2].split('|')
                self.datas[laser_id][1].append(float(tmp_datas[0]))
                angle = [float(tmp)/180.0*math.pi for tmp in tmp_datas[4::2]]
                dist = [float(tmp) for tmp in tmp_datas[5::2]]
                rssi = [0 for i in angle]
                tmp_a, tmp_d = [], []
                for a, d in zip(angle,dist):
                    if d < self.max_dist:
                        tmp_a.append(a)
                        tmp_d.append(d)
                angle = tmp_a 
                dist = tmp_d
                self.datas[laser_id][2].append(angle)
                self.datas[laser_id][3].append(dist)
                x , y = polar2xy(angle, dist)
                self.datas[laser_id][4].append(x)
                self.datas[laser_id][5].append(y)
                self.datas[laser_id][6].append(len(x))
                self.datas[laser_id][7].append(rssi)
                return True
            else:
                out = self.regexV2.match(line)
                if out:
                    datas = out.groups()
                    laser_id = 0
                    if datas[1] != "":
                        laser_id =  int(datas[1])
                    if laser_id not in self.datas:
                        self.datas[laser_id] = [[] for _ in range(8)]
                    self.datas[laser_id][0].append(rbktimetodate(datas[0]))
                    tmp_datas = datas[2].split('|')
                    self.datas[laser_id][1].append(float(tmp_datas[0]))
                    angle = [float(tmp)/180.0*math.pi for tmp in tmp_datas[4::3]]
                    dist = [float(tmp) for tmp in tmp_datas[5::3]]
                    rssi = [float(tmp) for tmp in tmp_datas[6::3]]
                    tmp_a, tmp_d, tmp_r = [], [], []
                    for a, d, r in zip(angle,dist, rssi):
                        if d < self.max_dist and r >= 0:
                            tmp_a.append(a)
                            tmp_d.append(d)
                            tmp_r.append(r)
                    angle = tmp_a 
                    dist = tmp_d
                    self.datas[laser_id][2].append(angle)
                    self.datas[laser_id][3].append(dist)
                    x , y = polar2xy(angle, dist)
                    self.datas[laser_id][4].append(x)
                    self.datas[laser_id][5].append(y)
                    self.datas[laser_id][6].append(len(x))
                    self.datas[laser_id][7].append(tmp_r)
                    return True
            return False
        return False
    def t(self, laser_index):
        return self.datas[laser_index][0]
    def ts(self, laser_index):
        return self.datas[laser_index][1], self.datas[laser_index][0]
    def angle(self, laser_index):
        return self.datas[laser_index][2], self.datas[laser_index][0]
    def dist(self, laser_index):
        return self.datas[laser_index][3], self.datas[laser_index][0]
    def x(self, laser_index):
        return self.datas[laser_index][4], self.datas[laser_index][0]
    def y(self, laser_index):
        return self.datas[laser_index][5], self.datas[laser_index][0]
    def number(self, laser_index):
        return self.datas[laser_index][6], self.datas[laser_index][0]
    def rssi(self, laser_index):
        return self.datas[laser_index][7], self.datas[laser_index][0]
    def insert_data(self, other):
        for key in other.datas.keys():
            if key in self.datas.keys():
                for k in range(len(self.datas[key])):
                    self.datas[key][k].extend(other.datas[key][k])
            else:
                self.datas[key] = other.datas[key]

class DepthCamera:
    """ 深度摄像头的数据
    data[0]: t
    data[1]: x m
    data[2]: y m
    data[3]: z m
    data[4]: number
    data[5]: ts
    """
    def __init__(self):
        """ max_dist 为激光点的最远距离，大于此距离激光点无效"""
        self.regex = re.compile('\[(.*?)\].* \[DepthCamera\d*?\]\[(.*?)\]')
        self.short_regx = "[DepthCamera"
        #self.data = [[] for _ in range(7)]
        self.datas =  [[] for _ in range(6)]
    def parse(self, line):
        if self.short_regx in line:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                tmp_datas = datas[1].split('|')
                if(len(tmp_datas) < 2):
                    return True
                self.datas[0].append(rbktimetodate(datas[0]))
                ts = 0
                if len(tmp_datas[1:]) %3 == 0:
                    dx = [float(tmp) for tmp in tmp_datas[1::3]]
                    dy = [float(tmp) for tmp in tmp_datas[2::3]]
                    dz = [float(tmp) for tmp in tmp_datas[3::3]]
                    ts = float(tmp_datas[0])
                elif len(tmp_datas)%2 == 0:
                    dx = [float(tmp) for tmp in tmp_datas[0::2]]
                    dy = [float(tmp) for tmp in tmp_datas[1::2]]
                    dz = [0 for tmp in dx]
                else:
                    dx = [float(tmp) for tmp in tmp_datas[1::2]]
                    dy = [float(tmp) for tmp in tmp_datas[2::2]]
                    dz = [0 for tmp in dx]
                    ts = float(tmp_datas[0])
                self.datas[1].append(dx)
                self.datas[2].append(dy)
                self.datas[3].append(dz)
                self.datas[4].append(len(tmp_datas))
                self.datas[5].append(ts)
                return True
            return False
        return False
    def t(self):
        return self.datas[0]
    def x(self):
        return self.datas[1], self.datas[0]
    def y(self):
        return self.datas[2], self.datas[0]
    def z(self):
        return self.datas[3], self.datas[0]
    def number(self):
        return self.datas[4], self.datas[0]
    def ts(self):
        return self.datas[5], self.datas[0]
    def insert_data(self, other):
        for i in range(len(self.datas)):
            self.datas[i].extend(other.datas[i])

class ParticleState:
    """ 粒子滤波数据
    data[0]: t
    data[1]: x m
    data[2]: y m
    data[3]: theta m
    data[4]: number
    data[5]: ts
    """
    def __init__(self):
        
        self.regex = re.compile('\[(.*?)\].* \[Particle State: \]\[(.*?)\]')
        self.short_regx = "[Particle State:"
        #self.data = [[] for _ in range(7)]
        self.datas =  [[] for _ in range(6)]
    def parse(self, line):
        if self.short_regx in line:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                tmp_datas = datas[1].split('|')
                if(len(tmp_datas) < 2):
                    return True
                dx, dy, dz, ts = [], [], [], 0
                if len(tmp_datas[1:]) %3 == 0:
                    dx = [float(tmp) for tmp in tmp_datas[1::3]]
                    dy = [float(tmp) for tmp in tmp_datas[2::3]]
                    dz = [float(tmp) for tmp in tmp_datas[3::3]]
                    ts = float(tmp_datas[0])
                else:
                    return True
                self.datas[0].append(rbktimetodate(datas[0]))
                self.datas[1].append(dx)
                self.datas[2].append(dy)
                self.datas[3].append(dz)
                self.datas[4].append(len(dx))
                self.datas[5].append(ts)
                return True
            return False
        return False
    def t(self):
        return self.datas[0]
    def x(self):
        return self.datas[1], self.datas[0]
    def y(self):
        return self.datas[2], self.datas[0]
    def theta(self):
        return self.datas[3], self.datas[0]
    def number(self):
        return self.datas[4], self.datas[0]
    def ts(self):
        return self.datas[5], self.datas[0]
    def insert_data(self, other):
        for i in range(len(self.datas)):
            self.datas[i].extend(other.datas[i])

class ErrorLine:
    """  错误信息
    data[0]: t
    data[1]: 错误信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Alarm\]\[Error\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[Alarm][Error"
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:       
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            else:
                pass
                # out = self.general_regex.match(line)
                # if out:
                #     self.data[0].append(rbktimetodate(out.group(1)))
                #     self.data[1].append(out.group(0))
                #     new_num = '00000'
                #     if not new_num in self.data[2]:
                #         self.data[2].append(new_num)                
                #         self.data[3].append('unKnown Error')
                #     return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class WarningLine:
    """  报警信息
    data[0]: t
    data[1]: 报警信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*?\[Alarm\]\[Warning\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[Alarm][Warning"
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:              
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class FatalLine:
    """  错误信息
    data[0]: t
    data[1]: 报警信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[f.*?\].*\[Alarm\]\[Fatal\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[Alarm][Fatal"       
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:                   
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class NoticeLine:
    """  注意信息
    data[0]: t
    data[1]: 注意信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Alarm\]\[Notice\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[Alarm][Notice"
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:              
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class TaskStart:
    """  任务开始信息
    data[0]: t
    data[1]: 开始信息内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Text\]\[cnt:.*")
        self.short_regx = "Text][cnt"
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        if self.short_regx in line:                      
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class TaskFinish:
    """  任务结束信息
    data[0]: t
    data[1]: 结束信息内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Text\]\[Task finished.*")
        self.short_regx = "Text][Task finished" 
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        if self.short_regx in line:               
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class Service:
    """  服务信息
    data[0]: t
    data[1]: 服务内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Service\].*")
        self.short_regx = "[Service"         
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        if self.short_regx in line:               
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class Memory:
    """  内存信息
    t[0]: 
    t[1]:
    t[2]:
    t[3]:
    t[4]:
    t[5]:
    data[0]: used_sys
    data[1]: free_sys
    data[2]: rbk_phy
    data[3]: rbk_vir
    data[4]: rbk_max_phy
    data[5]: rbk_max_vir
    data[6]: cpu_usage
    """
    def __init__(self):
        self.regex = [re.compile("\[(.*?)\].*\[Text\]\[Used system memory *: *(.*?) *([MG])B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Free system memory *: *(.*?) *([MG])B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit physical memory usage *: *(.*?) *([GM])B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit virtual memory usage *: *(.*?) *([GM])B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit Max physical memory usage *: *(.*?) *([GM])B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit Max virtual memory usage *: *(.*?) *([GM])B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit CPU usage *: *(.*?)%\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[System CPU usage *: *(.*?)%\]")]
        self.short_regx =  ["Used system",
                            "Free system",
                            "Robokit physical memory",
                            "Robokit physical memory",
                            "Max physical memory",
                            "Max virtual memory",
                            "Robokit CPU usage",
                            "System CPU usage"]
        self.time = [[] for _ in range(8)]
        self.data = [[] for _ in range(8)]

    def parse(self, line):
        for iter in range(0,8):
            if self.short_regx[iter] in line:
                out = self.regex[iter].match(line)
                if out:
                    self.time[iter].append(rbktimetodate(out.group(1)))
                    if iter == 6 or iter == 7:
                        self.data[iter].append(float(out.group(2)))
                    else:
                        if out.group(3) == "G":
                            self.data[iter].append(float(out.group(2)) * 1024.0)
                        else:
                            self.data[iter].append(float(out.group(2)))
                    return True
                return False
        return False

    def t(self):
        return self.time[0]
    def used_sys(self):
        return self.data[0], self.time[0]
    def free_sys(self):
        return self.data[1], self.time[1]
    def rbk_phy(self):
        return self.data[2], self.time[2]
    def rbk_vir(self):
        return self.data[3], self.time[3]
    def rbk_max_phy(self):
        return self.data[4], self.time[4]
    def rbk_max_vir(self):
        return self.data[5], self.time[5]
    def rbk_cpu(self):
        return self.data[6], self.time[6]
    def sys_cpu(self):
        return self.data[7], self.time[7]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])
        for i in range(len(self.time)):
            self.time[i].extend(other.time[i])
    
class RobotStatus:
    """  内存信息
    t[0]: 
    t[1]:
    data[0]: version
    data[1]: chassis
    data[2]: fatal num
    data[3]: fatal
    data[4]: error num
    data[5]: erros
    data[6]: warning num
    data[7]: warning nums
    data[8]: notice num
    data[9]: notices    
    """
    def __init__(self):
        self.regex = [re.compile("\[(.*?)\].*\[Text\]\[Robokit version: *(.*?)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Chassis Info: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[FatalNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Fatals: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[ErrorNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Errors: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[WarningNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Warnings: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[NoticeNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Notices: (.*)\]")]
        self.short_regx = ["Robokit version:",
                           "Chassis Info:",
                           "FatalNum:",
                           "Fatals:",
                           "ErrorNum:",
                           "Errors:",
                           "WarningNum:",
                           "Warnings:",
                           "NoticeNum:",
                           "Notices"]
        self.time = [[] for _ in range(10)]
        self.data = [[] for _ in range(10)]
    def parse(self, line):
        for iter in range(0,10):
            if self.short_regx[iter] in line:
                out = self.regex[iter].match(line)
                if out:
                    self.time[iter].append(rbktimetodate(out.group(1)))
                    self.data[iter].append(out.group(2))
                    return True
                return False
        return False
    def t(self):
        return self.time[0]
    def version(self):
        return self.data[0], self.time[0]
    def chassis(self):
        return self.data[1], self.time[1]
    def fatalNum(self):
        return self.data[2], self.time[1]
    def fatals(self):
        return self.data[3], self.time[1]
    def errorNum(self):
        return self.data[4], self.time[1]
    def errors(self):
        return self.data[5], self.time[1]
    def warningNum(self):
        return self.data[6], self.time[1]
    def warnings(self):
        return self.data[7], self.time[1]
    def noticeNum(self):
        return self.data[8], self.time[1]
    def notices(self):
        return self.data[9], self.time[1]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])
        for i in range(len(self.time)):
            self.time[i].extend(other.time[i])    