from PyQt5.QtCore import QThread, QFileInfo, pyqtSignal
import zipfile
import re


class ExtractZipThread(QThread):
    filesReady = pyqtSignal(str)
    error = pyqtSignal(str)
    extractProgressChanged = pyqtSignal(int)
    extractFileChanged = pyqtSignal(str)

    def __init__(self, zipFile, parent=None):
        super(ExtractZipThread, self).__init__(parent)
        self.zipFile = zipFile

    def run(self):
        if not zipfile.is_zipfile(self.zipFile):
            self.error.emit(f"\"{self.zipFile}\" is not a zip file !")
            return
        zipFile = zipfile.ZipFile(self.zipFile)
        isContainLogDir = False
        for fn in zipFile.namelist():
            if re.match("^log/", fn):
                isContainLogDir = True
                break
        if not isContainLogDir:
            self.error.emit("There is no log directory in this zip file !")
            return
        total = len(zipFile.filelist)
        i = 0
        f = QFileInfo(self.zipFile)
        dir = f.path() + "/" + f.baseName()
        try:
            for file in zipFile.namelist():
                zipFile.extract(file, dir)
                i += 1
                self.extractProgressChanged.emit(i / total * 100)
                self.extractFileChanged.emit("Extract:" + file)
        except Exception as e:
            self.error.emit(str(e))
            return
        self.filesReady.emit(dir + "/log")


if __name__ == '__main__':
    s = ExtractZipThread("C:/Users/User/Downloads/robokit-Debug.zip")
    s.error.connect(print)
    s.filesReady.connect(print)
    s.extractFileChanged.connect(print)
    s.extractProgressChanged.connect(print)
    s.run()
