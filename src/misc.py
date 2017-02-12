import os

from config import Config


def replaceGPGSymbols(gpglist, filename=""):
    for i in range(len(gpglist)):
        if(gpglist[i] == "$g"):
            gpglist[i]=Config().getGPGPath()
        elif(gpglist[i] == "$f"):
            gpglist[i]=filename
        elif(gpglist[i] == "$k"):
            gpglist[i]=Config().getGPGKey()


def getExtension(filename):
    ext = os.path.splitext(str(filename))
    return ext[1].lower()



class URL:
    def __init__(self, fullPath=None, url=None):
        fp=fullPath
        if(url):
            fp=url.getFullPath()
        self.setFullPath(fp)
    def setFullPath(self, path):
        self.fullPath=str(path)
        idx=self.fullPath.rfind(os.sep)
        if(idx >= 0 and idx < len(self.fullPath)):
            self.fileName=self.fullPath[idx+1:]
        else:
            raise Exception("Couldn't extract filename from full path.")
        self.ext=getExtension(self.fileName)
    def setFileName(self, fileName):
        idx=self.fullPath.rfind(os.sep)
        fp=self.fullPath[:idx+1]+fileName
        self.setFullPath(fp)
    def getFileName(self):
        return self.fileName
    def getExtension(self):
        return self.ext
    def getFullPath(self):
        return self.fullPath
    def getDirPath(self):
        idx = self.fullPath.rfind(os.sep)
        return self.fullPath[:idx]
    def empty(self):
        if(self.fullPath):
            return False
        else:
            return True

