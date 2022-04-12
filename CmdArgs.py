import argparse
from datetime import datetime, timedelta
from PyQt5.QtCore import QStandardPaths
import re

class CmdArgs():
    def __init__(self):
        self.startTime, self.endTime, self.dirName, self.onlyLog, self.ip, self.zip = self.__GetCmdArgs()

    def __str__(self):
        return f"({self.startTime}, {self.endTime}, {self.dirName}, {self.onlyLog}, {self.ip}, {self.zip})"

    def __GetCmdArgs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-s", "--start", metavar="", dest="startTime",
                            help="Start time for downloading logs",
                            default=(datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"))
        parser.add_argument("-e", "--end", metavar="", dest="endTime",
                            help="End time for downloading logs",
                            default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        parser.add_argument("-d", "--dir", metavar="", dest="dirName",
                            help="Download directory",default=QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]+"/robokit-Debug-%s"% datetime.now().strftime("%Y%m%d%H%M%S"))
        parser.add_argument("-o", "--only", dest="onlyLog",
                            help="Whether to download logs only", action="store_true")
        parser.add_argument("-i", "--ip", metavar="", dest="ip",
                            help="Robot IP")
        parser.add_argument("-z", "--zip", metavar="", dest="zip",
                            help="Debug zip file")
        args = parser.parse_args()
        try:
            if args.ip and not re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",args.ip):
                raise ValueError("IP error")
            if datetime.strptime(args.startTime,"%Y-%m-%d %H:%M:%S") > datetime.strptime(args.endTime, "%Y-%m-%d %H:%M:%S"):
                raise ValueError("The start time can only be less than the end time")
        except Exception as e:
            print(e)
            exit(-1)
        return args.startTime, args.endTime, args.dirName, args.onlyLog, args.ip, args.zip


if __name__ == '__main__':
    d = CmdArgs()
    print(d.ip,d.startTime,d.endTime,d.dirName,d.onlyLog)