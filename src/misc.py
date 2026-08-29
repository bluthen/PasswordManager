import os

from config import Config


def replace_gpg_symbols(gpglist, filename=""):
    gpg_path = Config().getGPGPath()
    gpg_key = Config().getGPGKey()
    fname = filename if filename is not None else ""
    for i in range(len(gpglist)):
        if gpglist[i] == "$g":
            gpglist[i] = gpg_path
        elif "$g" in gpglist[i]:
            gpglist[i] = gpglist[i].replace("$g", gpg_path)
        if gpglist[i] == "$f":
            gpglist[i] = fname
        elif "$f" in gpglist[i]:
            gpglist[i] = gpglist[i].replace("$f", fname)
        if gpglist[i] == "$k":
            gpglist[i] = gpg_key
        elif "$k" in gpglist[i]:
            gpglist[i] = gpglist[i].replace("$k", gpg_key)


def replace_open_save_symbols(commandlist, filename=""):
    dirname = os.path.dirname(os.path.abspath(filename)) if filename else ""
    fname = filename if filename is not None else ""
    for i in range(len(commandlist)):
        if commandlist[i] == "$f":
            commandlist[i] = fname
        elif "$f" in commandlist[i]:
            commandlist[i] = commandlist[i].replace("$f", fname)
        if "$d" in commandlist[i]:
            commandlist[i] = commandlist[i].replace("$d", dirname)


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
        if len(self.fullpath) > idx >= 0:
            self.filename = self.fullpath[idx + 1 :]
        elif self.fullpath:
            self.filename = self.fullpath
        else:
            raise Exception("Couldn't extract filename from full path.")
        self.ext = get_extension(self.filename)

    def set_filename(self, filename):
        idx = self.fullpath.rfind(os.sep)
        if idx >= 0:
            fp = self.fullpath[: idx + 1] + filename
        else:
            fp = filename
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
