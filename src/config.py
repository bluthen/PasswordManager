from PyQt5 import QtCore


class Config:
    """ config singleton """

    class __impl:
        """ Implementation of the singleton interface """

        def __init__(self):
            self.con = QtCore.QSettings("ColdstoneLabs", "passwordManager")
            self.openLast = self.getKey("OpenLast", bool)
            self.openLastFile = self.getKey("OpenLastFile")
            self.gpgPath = self.getKey("GPGPath")
            self.gpgKey = self.getKey("GPGKey")
            self.encCommand = self.getKey("EncCommand")
            self.decCommand = self.getKey("DecCommand")
            self.csvDelimiter = self.getKey("CSVDelimiter")
            self.csvDelimiterTab = self.getKey("CSVDelimiterTab", bool)
            self.csvQuoteCheck = self.getKey("CSVQuoteCheck", bool)
            self.csvQuote = self.getKey("CSVQuote")

            # Defaults
            if not self.gpgPath or len(self.gpgPath) == 0:
                self.openLast = True
                self.openLastFile = ""
                self.gpgPath = "/usr/bin/gpg2"
                self.gpgKey = ""
                self.encCommand = "$g --encrypt --no-tty -r $k -o -"
                self.decCommand = "$g --no-tty -d $f"
                self.csvDelimiter = "\t"
                self.csvDelimiterTab = True
                self.csvQuoteCheck = False
                self.csvQuote = ""

        def setKey(self, key, value):
            self.con.beginGroup("General Options")
            self.con.setValue(key, QtCore.QVariant(value))
            self.con.endGroup()
            self.con.sync()

        def getKey(self, key, vtype=str):
            self.con.beginGroup("General Options")
            s = self.con.value(key, type=vtype)
            self.con.endGroup()
            return s

        def getGeometry(self):
            self.con.beginGroup("General Options")
            size = self.con.value("Geometry")
            self.con.endGroup()
            if size is None or size.width() < 100:
                return QtCore.QSize(400, 400)
            return size

        def setGeometry(self, size):
            self.setKey("Geometry", size)

        def getGeometryH0(self):
            size = self.getKey("GeometryH0", int)
            if size < 10:
                return 100
            return size

        def setGeometryH0(self, size):
            self.setKey("GeometryH0", size)

        def getGeometryH1(self):
            size = self.getKey("GeometryH1", int)
            if size < 10:
                return 100
            return size

        def setGeometryH1(self, size):
            self.setKey("GeometryH1", size)

        def getGeometryH2(self):
            size = self.getKey("GeometryH2", int)
            if size < 10:
                return 100
            return size

        def setGeometryH2(self, size):
            self.setKey("GeometryH2", size)

        def getOpenLast(self):
            return self.openLast

        def setOpenLast(self, ol):
            self.openLast = ol
            self.setKey("OpenLast", ol)

        def getOpenLastFile(self):
            return self.openLastFile

        def setOpenLastFile(self, file):
            self.openLastFile = str(file)
            self.setKey("OpenLastFile", file)

        def getGPGPath(self):
            return self.gpgPath

        def setGPGPath(self, path):
            self.gpgPath = str(path)
            self.setKey("GPGPath", path)

        def getGPGKey(self):
            return self.gpgKey

        def setGPGKey(self, key):
            self.gpgKey = str(key)
            self.setKey("GPGKey", key)

        def setEncCommand(self, cmd):
            self.encCommand = str(cmd)
            self.setKey("EncCommand", cmd)

        def getEncCommand(self):
            return self.encCommand

        def setDecCommand(self, cmd):
            self.decCommand = str(cmd)
            self.setKey("DecCommand", cmd)

        def getDecCommand(self):
            return self.decCommand

        def getCSVDelimiter(self):
            return self.csvDelimiter

        def setCSVDelimiter(self, delim):
            self.csvDelimiter = str(delim)
            self.setKey("CSVDelimiter", delim)

        def getCSVDelimiterTab(self):
            return self.csvDelimiterTab

        def setCSVDelimiterTab(self, checked):
            self.csvDelimiterTab = checked
            self.setKey("CSVDelimiterTab", checked)

        def getCSVQuoteCheck(self):
            return self.csvQuoteCheck

        def setCSVQuoteCheck(self, qc):
            self.csvQuoteCheck = qc
            self.setKey("CSVQuoteCheck", qc)

        def getCSVQuote(self):
            return self.csvQuote

        def setCSVQuote(self, quote):
            self.csvQuote = str(quote)
            self.setKey("CSVQuote", quote)

        def getSettingsObj(self):
            return self.con

    # storage for the instance reference
    __instance = None

    def __init__(self):
        """ Create singleton instance """
        # Check whether we already have an instance
        if Config.__instance is None:
            # Create and remember instance
            Config.__instance = Config.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_Config__instance'] = Config.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
