import os

from config import Config


def replace_gpg_symbols(gpglist, filename=""):
    for i in range(len(gpglist)):
        if gpglist[i] == "$g":
            gpglist[i] = Config().getGPGPath()
        elif gpglist[i] == "$f":
            gpglist[i] = filename
        elif gpglist[i] == "$k":
            gpglist[i] = Config().getGPGKey()


def get_extension(filename):
    ext = os.path.splitext(str(filename))
    return ext[1].lower()


class URL:
    def __init__(self, fullpath=None, url=None):
        self.filename = None
        self.ext = None
        self.fullpath = None

        fp = fullpath
        if url:
            fp = url.get_fullpath()
        self.set_fullpath(fp)

    def set_fullpath(self, path):
        self.fullpath = str(path)
        idx = self.fullpath.rfind(os.sep)
        print(path, idx)
        if len(self.fullpath) > idx >= 0:
            self.filename = self.fullpath[idx + 1:]
        else:
            raise Exception("Couldn't extract filename from full path.")
        self.ext = get_extension(self.filename)

    def set_filename(self, filename):
        idx = self.fullpath.rfind(os.sep)
        fp = self.fullpath[:idx + 1] + filename
        self.set_fullpath(fp)

    def get_filename(self):
        return self.filename

    def get_extension(self):
        return self.ext

    def get_fullpath(self):
        return self.fullpath

    def get_dirpath(self):
        idx = self.fullpath.rfind(os.sep)
        return self.fullpath[:idx]

    def empty(self):
        if self.fullpath:
            return False
        else:
            return True
