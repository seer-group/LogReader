from PyQt5.QtCore import QObject, QByteArray, pyqtSignal, QDir
from PyQt5.QtNetwork import QTcpSocket
from typing import Union
import os
import json
import binascii
from enum import Enum
from CmdArgs import CmdArgs


class ProtocolType(Enum):
    GetDebugFileList = 5130
    GetFile = 5101


class SocketState(Enum):
    UnconnectedState = 0
    HostLookupState = 1
    ConnectingState = 2
    ConnectedState = 3
    BoundState = 4
    ClosingState = 6
    ListeningState = 5


class SocketError(Enum):
    ConnectionRefusedError = 0
    RemoteHostClosedError = 1
    HostNotFoundError = 2
    SocketAccessError = 3
    SocketResourceError = 4
    SocketTimeoutError = 5
    DatagramTooLargeError = 6
    NetworkError = 7
    AddressInUseError = 8
    SocketAddressNotAvailableError = 9
    UnsupportedSocketOperationError = 10
    UnfinishedSocketOperationError = 11
    ProxyAuthenticationRequiredError = 12
    SslHandshakeFailedError = 13
    ProxyConnectionRefusedError = 14
    ProxyConnectionClosedError = 15
    ProxyConnectionTimeoutError = 16
    ProxyNotFoundError = 17
    ProxyProtocolError = 18
    OperationError = 19
    SslInternalError = 20
    SslInvalidUserDataError = 21
    TemporaryError = 22

    UnknownSocketError = -1


class SeerObj():
    def __init__(self):
        self.__sync = 0x5A
        self.__version = 1
        self.__number = 0
        self.__type = ProtocolType.GetDebugFileList.value
        self.__reserved = bytes(6)
        self.__length = 0
        self.__data = bytearray()

    def __str__(self):
        return {
            "className": self.__class__.__name__,
            "sync": hex(self.__sync),
            "version": hex(self.__version),
            "number": self.__number,
            "type": hex(self.__type),
            "reserved": self.__reserved,
            "length": self.__length,
            "data": self.__data
        }.__str__()

    @staticmethod
    def checkIfComplete(d: QByteArray):
        length = int.from_bytes(d.data()[4:8], "big")
        return d.count() - 16 >= length

    @property
    def sync(self):
        return self.__sync

    @property
    def version(self):
        return self.__version

    @property
    def number(self):
        return self.__number

    @number.setter
    def number(self, v: int):
        self.__number = v

    @property
    def type(self):
        return self.__type

    @type.setter
    def type(self, v: ProtocolType):
        self.__type = v.value

    @property
    def length(self):
        return self.__length

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, v: Union[bytearray, bytes]):
        self.__data = v
        self.__length = len(v)

    def fromBytearray(self, data: Union[bytearray, bytes]):
        self.__sync = data[0]
        self.__version = data[1]
        self.__number = int.from_bytes(data[2:4], "big")
        self.__length = int.from_bytes(data[4:8], "big")
        self.__type = int.from_bytes(data[8:10], "big")
        self.__reserved = data[10:16]
        self.__data = data[16:]
        return self

    def toBytearray(self):
        barr = bytearray()
        barr.append(self.__sync)
        barr.append(self.__version)
        barr += self.__number.to_bytes(2, "big")
        barr += self.__length.to_bytes(4, "big")
        barr += self.__type.to_bytes(2, "big")
        barr += self.__reserved
        barr += self.__data
        return barr


class LogDownloader(QObject):
    filesReady = pyqtSignal(str)
    error = pyqtSignal(str)
    downloadStatusChanged = pyqtSignal(str)
    reqOrResInfoChanged = pyqtSignal(str)
    downloadProgressChanged = pyqtSignal(int)
    connectionChanged = pyqtSignal(str)

    def __init__(self, cmdArgs: CmdArgs, parent=None):
        super(LogDownloader, self).__init__(parent)
        self.PORT = 19208
        self.recvByteArray = QByteArray()
        self.recvSeerObj = None
        self.downloadFileIte = None
        self.currentReqFile = None
        self.reqFilesTotal = 0
        self.socket = QTcpSocket(self)
        self.cmdArgs = cmdArgs

        self.socket.stateChanged.connect(self._slotStateChanged)
        self.socket.readyRead.connect(self._slotReadyRead)
        self.socket.error.connect(self._slotError)

    def run(self):
        self._connectToHost()

    def _connectToHost(self):
        self.socket.connectToHost(self.cmdArgs.ip, self.PORT)
        self._slotStateChanged(f"Connecting to {self.cmdArgs.ip}:{self.PORT}")

    def _slotStateChanged(self, e: Union[str, int]):
        if isinstance(e, str):
            self.connectionChanged.emit(e)
            return
        self.connectionChanged.emit(str(SocketState(e)))
        if SocketState.ConnectedState.value == e:
            # 获取debug文件列表
            reqDict = {"endTime": self.cmdArgs.endTime, "isDownloadLogOnly": self.cmdArgs.onlyLog,
                       "startTime": self.cmdArgs.startTime}
            seerObj = SeerObj()
            seerObj.type = ProtocolType.GetDebugFileList
            seerObj.data = json.dumps(reqDict, separators=(',', ':')).encode("utf-8")
            self._sendRequest(seerObj)

    def _slotReadyRead(self):
        if self.currentReqFile:
            self.downloadStatusChanged.emit(f"Downloading:{self.currentReqFile[2]}")
        else:
            self.downloadStatusChanged.emit("Get:DebugFileList")
        self.recvByteArray += self.socket.readAll()
        if not SeerObj.checkIfComplete(self.recvByteArray):
            return
        seerObj = SeerObj().fromBytearray(self.recvByteArray.data())
        info = self._statusInfofmt(seerObj)
        self.reqOrResInfoChanged.emit(info)
        if seerObj.type - 10000 == ProtocolType.GetDebugFileList.value:
            fileDict = json.loads(seerObj.data)
            if not "fileList" in fileDict.keys():
                self._slotError(fileDict)
                return
            for d in fileDict["fileList"]:
                for v in d.values():
                    if isinstance(v, list):
                        self.reqFilesTotal += len(v)
            self.downloadFileIte = self._debugFileGenerator(fileDict)

        elif seerObj.type - 10000 == ProtocolType.GetFile.value:
            self.downloadProgressChanged.emit(self.currentReqFile[3])
            dirPath = self.cmdArgs.dirName + "/" + self.currentReqFile[0]

            if not QDir().exists(dirPath):
                QDir().mkpath(dirPath)
            filePath = dirPath + "/" + self.currentReqFile[2]
            with open(filePath, "wb") as file:
                file.write(seerObj.data)
        else:
            self._slotError(str(seerObj))
            return
        self.recvByteArray.clear()
        self._sendRequestFile()
        return

    def _slotError(self, e: Union[str, int]):
        if isinstance(e, str):
            text = e
        else:
            text = str(SocketError(e))
        self.error.emit(text)

    def _statusInfofmt(self, seerObj: SeerObj):
        info = f"Type:{seerObj.type}\nPort:{self.PORT}\nNumber:{seerObj.number}\nHeader:{'0x'}{str(binascii.b2a_hex(seerObj.toBytearray()[0:17]))[2:-1]}\nDataLength:{seerObj.length}\nData:"
        if seerObj.type - 10000 == ProtocolType.GetFile.value:
            info += "File"
        else:
            info += seerObj.data.__str__()
        return info

    def _sendRequest(self, seerObj: SeerObj):
        self.socket.write(seerObj.toBytearray())
        if seerObj.type == ProtocolType.GetDebugFileList.value:
            self.downloadStatusChanged.emit(f"Req:DebugFileList")
        else:
            self.downloadStatusChanged.emit(f"Req:{self.currentReqFile[2]}")
        info = self._statusInfofmt(seerObj)
        self.reqOrResInfoChanged.emit(info)

    def _sendRequestFile(self):
        try:
            self.currentReqFile: tuple = next(self.downloadFileIte)
        except Exception as e:
            self.socket.close()
            dirPath = self.cmdArgs.dirName + "/log"
            self.filesReady.emit(dirPath)
            return
        reqDict = {"path": self.currentReqFile[1], "file_name": self.currentReqFile[2]}
        seerObj = SeerObj()
        seerObj.type = ProtocolType.GetFile
        seerObj.data = json.dumps(reqDict, separators=(',', ':')).encode("utf-8")
        self._sendRequest(seerObj)

    def _debugFileGenerator(self, filesDict: dict):
        i = 0
        for dir in filesDict["fileList"]:
            for filePath in dir["filePaths"]:
                fp, fn = os.path.split(filePath)
                i += 1
                yield dir["dirName"], fp, fn, i / self.reqFilesTotal * 100


if __name__ == '__main__':
    s = SeerObj()
    print(s.toBytearray())