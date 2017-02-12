#!/usr/bin/python 
import sys
import re
import os
import traceback
import csv
import operator
import subprocess
from StringIO import StringIO

from PyQt4 import QtGui, QtCore

from simpleDialogs import OKDialog, DialogBase, ConfirmDialog
from aboutDialog import AboutDialog
import passwordGenerator
import misc
from misc import URL
from config import Config


class Document():
    def __init__(self):
        self.data=[]
        self.file=None
        self.modified=False
    def isModified(self):
        return self.modified
    def setModified(self):
        self.modified=True
        return
    def getFile(self):
        return self.file
    def importCSV(self, filename, delim, quote):
        f=open(filename)
        if(quote != None):
            csvReader = csv.reader(f, delimiter=str(delim), quotechar=str(quote))
        else:
            csvReader = csv.reader(f, delimiter=str(delim), quoting=csv.QUOTE_NONE)
        mydata=[]
        for row in csvReader:
            while(len(row) < 4):
                row.append("")
            mydata.append(row)
        self.setData(mydata)
        if(f):
            f.close()
        self.setModified()
    def load(self, filename):
        #if encrypted
        # gpg -d filename | prog
        decrypt = Config().getDecCommand().split(' ')
        misc.replaceGPGSymbols(decrypt, filename)
        process = subprocess.Popen(decrypt, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output=process.communicate()
        code=process.returncode
        f = StringIO(output[0])
        if(code != 0):
            raise Exception("Failed to decrypt file (Code: "+str(code)+") -- "+str(output[1]))
        if(Config().getCSVDelimiterTab()):
            delim="\t"
        else:
            delim=Config().getCSVDelimiter()
        if(Config().getCSVQuoteCheck()):
            csvReader = csv.reader(f, delimiter=delim, quotechar=Config().getCSVQuote())
        else:
            csvReader = csv.reader(f, delimiter=delim, quoting=csv.QUOTE_NONE)
        mydata=[]
        for row in csvReader:
            while(len(row) < 4):
                row.append("")
            mydata.append(row)
        self.setData(mydata)
        if(f):
            f.close()
        self.file=filename
    def save(self, filename):
        f = StringIO()
        if(Config().getCSVDelimiterTab()):
            delim="\t"
        else:
            delim=str(Config().getCSVDelimiter())
        if(Config().getCSVQuoteCheck()):
            csvWriter = csv.writer(f, delimiter=delim, quotechar=Config().getCSVQuote())
        else:
            csvWriter = csv.writer(f, delimiter=delim, quoting=csv.QUOTE_NONE)
        csvWriter.writerows(self.getData())
        output=f.getvalue()
        f.close()
        #cat file | gpg -a --encrypt -r keyid -o - > newfile
        encrypt=Config().getEncCommand().split(' ')
        misc.replaceGPGSymbols(encrypt, None)
        process = subprocess.Popen(encrypt, shell=False, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        noutput=process.communicate(output)
        if(process.returncode != 0):
            raise Exception("Failed to encrypt data.")

        #Write actual file now
        f=open(filename, 'w')
        #XXX: make backup
        f.write(noutput[0])
        f.close()
        self.file=filename
        self.modified=False
        if(Config().getOpenLast()):
            Config().setOpenLastFile(self.file)
    def setData(self, data):
        self.data=data
    def getData(self):
        return self.data

class KeyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.header=["Key"]

        self.data=[]

    def refresh(self):
        self.layoutAboutToBeChanged.emit()
        getKeys="$g --no-tty -K".split(' ')
        misc.replaceGPGSymbols(getKeys)
        process = subprocess.Popen(getKeys, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output=process.communicate()
        code=process.returncode
        f=StringIO(output[0])
        if(code != 0):
            raise Exception("Failed to get key listing (Code: "+str(code)+") -- "+str(output[1]))
        self.data=[]
        foundKey=False
        key=""
        aline=""
        for line in f:
            line=line.rstrip()
            if(not foundKey and line[0:3]=="sec"):
                m=re.search("/(\w*) ", line)
                key=m.group(1)
                aline=line
                foundKey=True
            elif(len(line)==0):
                if(len(key) != 0):
                    self.data.append([aline, key])       
                key=""
                aline=""
                foundKey=False
            elif(foundKey):
                aline+="\n"+line
        if(len(key) != 0):
            self.data.append([aline, key])
        self.layoutChanged.emit()
        f.close()
    def columnCount(self, parent):
        return len(self.header)
    def rowCount(self, parent):
        return len(self.data)
    def data(self, index, role):
        if(role != QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        try:
            return QtCore.QVariant(self.data[index.row()][index.column()])
        except:
            return QtCore.QVariant()
    def headerData(self, section, orientation, role):
        if (orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant(self.header[section])
        return QtCore.QVariant()

class KeyDialog(DialogBase):
    def __init__(self, parent):
        DialogBase.__init__(self, "Key Selector", ok=True, cancel=True, modal=True, parent=parent)

        self.parent=parent

        keyBox=QtGui.QGroupBox("Select Key")
        keyLayout = QtGui.QGridLayout()
        keyBox.setLayout(keyLayout)
        self.model=KeyTableModel(self) 
        self.table = QtGui.QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setCornerButtonEnabled(False)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        keyLayout.addWidget(self.table, 0, 0)
        self.addWidget(keyBox)

    def refresh(self):
        self.model.refresh()
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
    def slotCancel(self):
        self.reject()
    def slotOk(self):
        row=self.table.selectedIndexes()[0].row()
        self.parent.gpgKey.setText(self.model.data[row][1])
        self.accept()

class MainTableModel(QtCore.QAbstractTableModel):
    def __init__(self, document, main, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.main=main

        self.document=document
        self.header=["Name", "Username", "Password", "Comment"]
        self.sort(0, QtCore.Qt.DescendingOrder)
    def rowCount(self, parent):
        return len(self.document.getData()) 
    def columnCount(self, parent):
        return len(self.header)
    def data(self, index, role):
        if(role != QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        if(self.document.getData() != None):
            try:
                if(index.column() == 2): #Password column
                    if (self.main.viewPasswords.isChecked()):
                        return QtCore.QVariant(self.document.getData()[index.row()][index.column()])
                    else:
                        return QtCore.QVariant("****")
                else:
                    return QtCore.QVariant(self.document.getData()[index.row()][index.column()])
            except:
                return QtCore.QVariant()
        return QtCore.QVariant()
    def headerData(self, section, orientation, role):
        if (orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant(self.header[section])
        return QtCore.QVariant()
    def resort(self):
        self.sort(self.sortColumn, self.sortOrder)
    def sort(self, column, order):
        self.sortColumn=column
        self.sortOrder=order
        if(self.document.getData() != None):
            self.layoutAboutToBeChanged.emit()
            #self.document.setData(sorted(self.document.getData(), key=operator.itemgetter(column), reverse=(order == QtCore.Qt.DescendingOrder)))
            self.document.setData(sorted(self.document.getData(), key=lambda a: a[column].lower(), reverse=(order != QtCore.Qt.DescendingOrder)))
            self.layoutChanged.emit()

class AdvancedConfigWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        encryptionBox = QtGui.QGroupBox("Encryption")    
        eboxLayout = QtGui.QGridLayout()
        encryptionBox.setLayout(eboxLayout)
        encLabel = QtGui.QLabel("$g - gpg path; $k - keyid; $f - file")
        encLabel.setWordWrap(True)
        eboxLayout.addWidget(encLabel, 0, 0, 1, 2)
        eboxLayout.addWidget(QtGui.QLabel("Encrypt Command:"), 1, 0)
        self.encCommand = QtGui.QLineEdit()
        eboxLayout.addWidget(self.encCommand, 1, 1)
        eboxLayout.addWidget(QtGui.QLabel("Decrypt Command:"), 2, 0)
        self.decCommand = QtGui.QLineEdit()
        eboxLayout.addWidget(self.decCommand, 2, 1)
        layout.addWidget(encryptionBox)

        csvBox = QtGui.QGroupBox("CSV")
        cboxLayout = QtGui.QGridLayout()
        csvBox.setLayout(cboxLayout)
        cboxLayout.addWidget(QtGui.QLabel("Delimiter:"), 0, 0)
        delimiterButtonGroup = QtGui.QButtonGroup()
        self.delimiterTab = QtGui.QRadioButton("Tab")
        self.delimiterTab.setChecked(True)
        self.delimiterTab.toggled.connect(self.slotDelimiterTab)
        cboxLayout.addWidget(self.delimiterTab, 0, 1, 1, 2)
        self.delimiterOther = QtGui.QRadioButton("Other")
        cboxLayout.addWidget(self.delimiterOther, 1, 1)
        delimiterButtonGroup.addButton(self.delimiterTab)
        delimiterButtonGroup.addButton(self.delimiterOther)
        self.delimiter = QtGui.QLineEdit()
        self.delimiter.setEnabled(False)
        cboxLayout.addWidget(self.delimiter, 1, 2)

        self.quoteCheck = QtGui.QCheckBox("Quote:")
        self.quoteCheck.toggled.connect(self.slotQuoteCheck)
        cboxLayout.addWidget(self.quoteCheck, 2, 0)
        self.quote = QtGui.QLineEdit()
        self.quote.setEnabled(False)
        cboxLayout.addWidget(self.quote, 2, 1, 1, 2)

        layout.addWidget(csvBox)
    def slotDelimiterTab(self, checked):
        self.delimiter.setEnabled(not checked)
    def slotQuoteCheck(self, checked):
        self.quote.setEnabled(checked)
    def readConfig(self):
        self.encCommand.setText(Config().getEncCommand())
        self.decCommand.setText(Config().getDecCommand())
        self.delimiter.setText(Config().getCSVDelimiter())
        self.delimiterTab.setChecked(Config().getCSVDelimiterTab())
        self.quoteCheck.setChecked(Config().getCSVQuoteCheck())
        self.quote.setText(Config().getCSVQuote())
    def saveConfig(self):
        Config().setEncCommand(self.encCommand.text())
        Config().setDecCommand(self.decCommand.text())
        Config().setCSVDelimiter(self.delimiter.text())
        Config().setCSVDelimiterTab(self.delimiterTab.isChecked())
        Config().setCSVQuoteCheck(self.quoteCheck.isChecked())
        Config().setCSVQuote(self.quote.text())


class GeneralConfigWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        settingsBox = QtGui.QGroupBox("Settings")
        boxLayout = QtGui.QGridLayout()
        settingsBox.setLayout(boxLayout)
        self.autoOpen = QtGui.QCheckBox("Try to open last saved document on startup.")
        boxLayout.addWidget(self.autoOpen, 0, 0, 1, 3)
        boxLayout.addWidget(QtGui.QLabel("GPG Path:"), 1, 0)
        self.gpgPath = QtGui.QLineEdit()
        boxLayout.addWidget(self.gpgPath, 1, 1) 
        self.gpgPathBrowse = QtGui.QPushButton("...")
        boxLayout.addWidget(self.gpgPathBrowse, 1, 2)
        self.gpgPathBrowse.released.connect(self.slotBrowseGPGPath)
        boxLayout.addWidget(QtGui.QLabel("GPG Key:"), 2, 0)
        self.gpgKey = QtGui.QLineEdit()
        boxLayout.addWidget(self.gpgKey, 2, 1)
        self.browseButton = QtGui.QPushButton("...")
        boxLayout.addWidget(self.browseButton, 2, 2)
        self.browseButton.released.connect(self.slotBrowseKeys)

        self.keyDialog=KeyDialog(self)
        layout.addWidget(settingsBox)
    def slotBrowseGPGPath(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "GPG Location", "", "GPG Executable (gpg*)", None, QtGui.QFileDialog.DontUseNativeDialog)
        if(fileName == None or len(fileName) == 0):
            return
        self.gpgPath.setText(fileName)
    def slotBrowseKeys(self):
        self.keyDialog.refresh()
        self.keyDialog.show()
    def readConfig(self):
        self.autoOpen.setChecked(Config().getOpenLast())
        self.gpgPath.setText(Config().getGPGPath())
        self.gpgKey.setText(Config().getGPGKey())
    def saveConfig(self):
        Config().setOpenLast(self.autoOpen.isChecked())
        if(self.autoOpen.isChecked()):
            Config().setOpenLastFile("")
        Config().setGPGPath(self.gpgPath.text())
        Config().setGPGKey(self.gpgKey.text())

class ConfigDialog(DialogBase):
    def __init__(self, parent):
        DialogBase.__init__(self, "Config", ok=True, cancel=True,  modal=False, parent=parent)

        tabWidget = QtGui.QTabWidget()
        self.genTab = GeneralConfigWidget()
        tabWidget.addTab(self.genTab, "General")
        self.advTab = AdvancedConfigWidget()
        tabWidget.addTab(self.advTab, "Advanced")
        self.addWidget(tabWidget)
        self.parent=parent
        self.rejected.connect(self.slotRej)

        self.genTab.readConfig()
        self.advTab.readConfig()
    def slotRej(self):
        self.genTab.readConfig()
        self.advTab.readConfig()
    def slotCancel(self):
        self.reject()
    def slotOk(self):
        self.genTab.saveConfig()
        self.advTab.saveConfig()
        self.accept()

class DelDialog(DialogBase):
    def __init__(self, parent, document):
        DialogBase.__init__(self, "Delete Entry", ok=True, cancel=True,  modal=True, parent=parent)
        self.document=document
        self.okButton.setText("Yes")
        self.cancelButton.setText("No")
        self.label=QtGui.QLabel("Are you sure you want to remove \"Entryname\"?")
        self.addWidget(self.label)
    def setRow(self, row):
        self.label.setText("Are you sure you want to remove \""+self.document.getData()[row][0]+"\"?")

class FindDialog(DialogBase):
    def __init__(self, parent, table, document):
        DialogBase.__init__(self, "Find", ok=False, cancel=True, modal=False, parent=parent)

        self.table=table
        self.document=document

        self.cancelButton.setText("Close")

        findBox = QtGui.QGroupBox("Find")
        findLayout = QtGui.QGridLayout()
        findBox.setLayout(findLayout)
        findLayout.addWidget(QtGui.QLabel("Search For:"), 0, 0)
        self.findText = QtGui.QLineEdit()
        findLayout.addWidget(self.findText, 0, 1)
        self.next = QtGui.QPushButton("Next")
        self.next.released.connect(self.slotNext)
        self.previous = QtGui.QPushButton("Previous")
        self.previous.released.connect(self.slotPrevious)
        findLayout.addWidget(self.next, 0, 2)
        findLayout.addWidget(self.previous, 1, 2)
        self.caseCheck = QtGui.QCheckBox("Case sensitive")
        findLayout.addWidget(self.caseCheck, 1, 0)

        self.addWidget(findBox)
        
        self.lastC=None
        self.lastRow=None
        self.lastText=None

    def slotNext(self, forwardSearch=True):
        if(self.isHidden()):
            self.show()
            self.findText.setFocus(QtCore.Qt.ActiveWindowFocusReason)
            self.next.setDefault(True)
        f=str(self.findText.text())
        if(len(f) == 0):
            return
        if(self.lastText != f):
            self.lastText=f
            self.lastForwardSearch=forwardSearch
            if(forwardSearch):
                self.lastC=0
                self.nextRow=0
            else:
                self.lastC=0
                self.nextRow=len(self.document.getData())-1
        #Correct for when switching from next and previous
        if(forwardSearch):
            if(self.lastForwardSearch != forwardSearch):
                if(self.nextRow == len(self.document.getData())-1):
                    self.nextRow=1
                    self.lastC=self.lastC-1
                else:
                    self.nextRow=self.nextRow+2
        else:
            if(self.lastForwardSearch != forwardSearch):
                if(self.nextRow == 0):
                    self.nextRow=len(self.document.getData())-2
                    self.lastC=self.lastC-1
                else:
                    self.nextRow=self.nextRow-2
        self.lastForwardSearch=forwardSearch

        for c in range(self.lastC, 4):
            if(forwardSearch):
                en=range(self.nextRow, len(self.document.getData()))
            else:
                en=range(self.nextRow, -1, -1)
            for i in en:
                found = False
                if(self.caseCheck.isChecked()):
                    if(self.document.getData()[i][c].find(f) >= 0):
                        found=True
                else:
                    if(self.document.getData()[i][c].lower().find(f) >= 0):
                        found=True
                if(found):
                    self.table.selectRow(i)
                    self.table.scrollTo(self.table.model().index(i,0))
                    self.lastC=c
                    if(forwardSearch):
                        self.nextRow=i+1
                        if(self.nextRow >= len(self.document.getData())):
                            self.nextRow=0
                            self.lastC=c+1
                    else:
                        self.nextRow=i-1
                        if(self.nextRow < 0):
                            self.nextRow=len(self.document.getData())-1
                            self.lastC=c+1
                    return
        #At end, start at top of bottom
        self.lastText=None
        ok = OKDialog(self, "Find End", "At end of search, next search will start at the beginning.")
        ok.show()
    def slotPrevious(self):
        self.slotNext(False)

class ImportCSVConfirmDialog(DialogBase):
    def __init__(self, parent, document, model):
        DialogBase.__init__(self, "Import without saving?", ok=True, cancel=True,  modal=True, parent=parent)

        self.document=document
        self.model=model

        self.okButton.setText("Yes")
        self.cancelButton.setText("No")
        self.label = QtGui.QLabel("Import file without saving current document?")
        self.addWidget(self.label)
        self.file=None
        self.delim=None
        self.quote=None
    def setFile(self, file):
        self.file=file
    def setDelimiter(self, delim):
        self.delim = delim
    def setQuote(self, quote):
        self.quote=quote
    def slotCancel(self):
        self.reject()
    def slotOk(self):
        try:
            self.accept()
            self.model.layoutAboutToBeChanged.emit()
            self.document.importCSV(self.file, self.delim, self.quote)
            self.model.resort()
            self.model.layoutChanged.emit()
        except Exception, e:
            ok = OKDialog(self, "Problem importing file", e.__str__())
            traceback.print_exc(file=sys.stdout)
            ok.show()



class ImportCSVDialog(DialogBase):
    def __init__(self, parent, document, model):
        DialogBase.__init__(self, "Import CSV", ok=True, cancel=True,  modal=True, parent=parent)

        self.document=document
        self.model=model

        csvBox = QtGui.QGroupBox("CSV")
        cboxLayout = QtGui.QGridLayout()
        csvBox.setLayout(cboxLayout)
        cboxLayout.addWidget(QtGui.QLabel("Delimiter:"), 0, 0)
        delimiterButtonGroup = QtGui.QButtonGroup()
        self.delimiterTab = QtGui.QRadioButton("Tab")
        self.delimiterTab.toggled.connect(self.slotDelimiterTab)
        cboxLayout.addWidget(self.delimiterTab, 0, 1, 1, 2)
        self.delimiterOther = QtGui.QRadioButton("Other")
        self.delimiterOther.setChecked(True)
        cboxLayout.addWidget(self.delimiterOther, 1, 1)
        delimiterButtonGroup.addButton(self.delimiterTab)
        delimiterButtonGroup.addButton(self.delimiterOther)
        self.delimiter = QtGui.QLineEdit()
        self.delimiter.setText(",")
        cboxLayout.addWidget(self.delimiter, 1, 2)

        self.quoteCheck = QtGui.QCheckBox("Quote:")
        self.quoteCheck.setChecked(True)
        self.quoteCheck.toggled.connect(self.slotQuoteCheck)
        cboxLayout.addWidget(self.quoteCheck, 2, 0)
        self.quote = QtGui.QLineEdit()
        self.quote.setText("\"")
        cboxLayout.addWidget(self.quote, 2, 1, 1, 2)

        self.file=None

        self.addWidget(csvBox)
        self.importConfirmDialog=ImportCSVConfirmDialog(self, document, model)
    def setFile(self, file):
        self.file=file
    def getFile(self):
        return self.file
    def slotDelimiterTab(self, checked):
        self.delimiter.setEnabled(not checked)
    def slotQuoteCheck(self, checked):
        self.quote.setEnabled(checked)
    def reset(self):
        self.quoteCheck.setEnabled(True)
        self.quote.setText("\"")
        self.delimiter.setText(",")
        self.delimiterOther.setEnabled(True)
    def slotCancel(self):
        self.reset()
        self.reject()
    def slotOk(self):
        self.accept()
        self.importConfirmDialog.setFile(self.file)
        if(self.delimiterTab.isChecked()):
            self.importConfirmDialog.setDelimiter("\t")
        else:    
            self.importConfirmDialog.setDelimiter(self.delimiter.text())
        if(self.quoteCheck.isChecked()):
            self.importConfirmDialog.setQuote(self.quote.text())
        else:
            self.importConfirmDialog.setQuote(None)
        if(self.document.isModified()):
            self.importConfirmDialog.show()
        else:
            self.importConfirmDialog.slotOk()
 


class EditDialog(DialogBase):
    def __init__(self, parent, document, model):
        DialogBase.__init__(self, "New/Edit", ok=True, cancel=True,  modal=True, parent=parent)
        self.document=document
        self.model=model
        entryBox = QtGui.QGroupBox("Entry")
        boxLayout = QtGui.QGridLayout()
        entryBox.setLayout(boxLayout)
        boxLayout.addWidget(QtGui.QLabel("Name:"), 0, 0)
        self.name = QtGui.QLineEdit()
        boxLayout.addWidget(self.name, 0, 1)
        boxLayout.addWidget(QtGui.QLabel("Username:"), 1, 0)
        self.username = QtGui.QLineEdit()
        boxLayout.addWidget(self.username, 1, 1)
        boxLayout.addWidget(QtGui.QLabel("Password:"), 2, 0)
        self.password = QtGui.QLineEdit()
        self.password.setEchoMode(QtGui.QLineEdit.PasswordEchoOnEdit)
        boxLayout.addWidget(self.password, 2, 1)
        self.showCheck = QtGui.QCheckBox("Show")
        self.showCheck.toggled.connect(self.slotShowCheck)
        boxLayout.addWidget(self.showCheck, 3, 0)
        self.generateButton = QtGui.QPushButton("Generate")
        self.generateButton.released.connect(self.slotGenerate)
        boxLayout.addWidget(self.generateButton, 3, 1)
        boxLayout.addWidget(QtGui.QLabel("Comment:"), 4, 0)
        self.comment = QtGui.QLineEdit()
        boxLayout.addWidget(self.comment, 4, 1)
        self.addWidget(entryBox)

        self.row=None
    def setRow(self, row):
        self.row=row
        self.name.setText(self.document.getData()[row][0])
        self.username.setText(self.document.getData()[row][1])
        self.password.setText(self.document.getData()[row][2])
        self.comment.setText(self.document.getData()[row][3])
    def clear(self):
        self.row=None
        self.name.setText("")
        self.username.setText("")
        self.password.setText("")
        self.comment.setText("")
        self.showCheck.setChecked(False)
    def slotGenerate(self):
        self.password.setText(passwordGenerator.generatePassword()) 
    def slotShowCheck(self, checked):
        if(checked):
            self.password.setEchoMode(QtGui.QLineEdit.Normal)
        else:
            self.password.setEchoMode(QtGui.QLineEdit.PasswordEchoOnEdit)
    def slotCancel(self):
        self.clear()
        self.reject()
    def slotOk(self):
        line=[str(self.name.text()), str(self.username.text()), str(self.password.text()), str(self.comment.text())]
        if(self.row == None):
            self.document.getData().append(line)
        else:
            self.document.getData()[self.row]=line
        self.model.resort()
        self.document.setModified()
        self.accept()


class MainWindow(QtGui.QMainWindow):
    def __init__(self, app):
        QtGui.QMainWindow.__init__(self)
        self.app = app
        self.clipboard = QtGui.QApplication.clipboard()

        self.setWindowTitle("Password Manager")

        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileOpen = QtGui.QAction("&Open", self.fileMenu, shortcut=QtGui.QKeySequence.Open, triggered=self.slotFileOpen)
        self.fileMenu.addAction(self.fileOpen)
        self.fileSave = QtGui.QAction("&Save", self.fileMenu, shortcut=QtGui.QKeySequence.Save, triggered=self.slotFileSave)
        self.fileMenu.addAction(self.fileSave)
        self.fileSaveAs = QtGui.QAction("Save &As...", self.fileMenu, shortcut=QtGui.QKeySequence.SaveAs, triggered=self.slotFileSaveAs)
        self.fileMenu.addAction(self.fileSaveAs)
        self.fileMenu.addSeparator()
        self.fileImportCSV = QtGui.QAction("&Import CSV...", self.fileMenu, triggered=self.slotFileImportCSV)
        self.fileMenu.addAction(self.fileImportCSV)
        self.fileMenu.addSeparator()
        self.fileSettings = QtGui.QAction("S&ettings", self.fileMenu, triggered=self.slotSettings)
        self.fileMenu.addAction(self.fileSettings)
        self.fileMenu.addSeparator()
        self.fileQuit = QtGui.QAction("&Quit", self.fileMenu, shortcut=QtGui.QKeySequence.mnemonic("&Quit"), triggered=self.slotQuit)
        self.fileMenu.addAction(self.fileQuit)

        self.viewMenu = self.menuBar().addMenu("&View")
        self.viewPasswords = QtGui.QAction("Show &Passwords", self.viewMenu, triggered=self.slotViewPasswords)
        self.viewPasswords.setCheckable(True)
        self.viewMenu.addAction(self.viewPasswords)
        self.viewMenu.addSeparator()
        self.viewFind = QtGui.QAction("Find...", self.viewMenu, triggered=self.slotViewFind)
        self.viewMenu.addAction(self.viewFind)

        self.entryMenu = self.menuBar().addMenu("&Entry")
        self.entryMenu.aboutToShow.connect(self.slotEntryMenuAboutToShow)
        self.entryCopyU = QtGui.QAction("Copy Username to Clipboard", self.entryMenu, triggered=self.slotEntryCopyU)
        self.entryMenu.addAction(self.entryCopyU)
        self.entryCopyP = QtGui.QAction("Copy Password to Clipboard", self.entryMenu, triggered=self.slotEntryCopyP)
        self.entryMenu.addAction(self.entryCopyP)
        self.entryMenu.addSeparator()

        #Detect if an X system
        if(os.name=='posix'): #Is there a better way?
            self.entryCopyUS = QtGui.QAction("Copy Username to Selection", self.entryMenu, triggered=self.slotEntryCopyUS)
            self.entryMenu.addAction(self.entryCopyUS)
            self.entryCopyPS = QtGui.QAction("Copy Password to Selection", self.entryMenu, triggered=self.slotEntryCopyPS)
            self.entryMenu.addAction(self.entryCopyPS)
            self.entryMenu.addSeparator()

        self.entryNew = QtGui.QAction("New Entry", self.entryMenu, triggered=self.slotEntryNew)
        self.entryMenu.addAction(self.entryNew)
        self.entryEdit = QtGui.QAction("Edit Entry", self.entryMenu, triggered=self.slotEntryEdit)
        self.entryMenu.addAction(self.entryEdit)
        self.entryDel = QtGui.QAction("Delete Entry", self.entryMenu, triggered=self.slotEntryDelete)
        self.entryMenu.addAction(self.entryDel)
        self.entryEdit.setEnabled(False)
        self.entryDel.setEnabled(False)
        self.entryCopyU.setEnabled(False)
        self.entryCopyP.setEnabled(False)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpAbout = QtGui.QAction("&About", self.helpMenu, triggered=self.slotHelpAbout)
        self.helpMenu.addAction(self.helpAbout)

        self.table = QtGui.QTableView()
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.customContextMenuRequested.connect(self.doTableContextMenu)
        self.document=Document()
        self.mymodel=MainTableModel(self.document, self)
        self.table.setModel(self.mymodel)
        self.table.setSortingEnabled(True)
        self.table.setCornerButtonEnabled(False)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setCentralWidget(self.table)

        self.configDialog=ConfigDialog(self)


        self.editDialog=EditDialog(self, self.document, self.mymodel)
        self.delDialog=DelDialog(self, self.document)
        self.openConfirmDialog=ConfirmDialog(self, "Open without saving?", "Open new file without saving current document?")
        self.importCSVDialog=ImportCSVDialog(self, self.document, self.mymodel)
        self.helpAboutDialog = AboutDialog(self)
        self.quitConfirmDialog = ConfirmDialog(self, "Quit without saving?", "Quit without saving current document?")

        self.findDialog=FindDialog(self, self.table, self.document)

        self.viewFindShortcut = QtGui.QShortcut(QtGui.QKeySequence.Find, self)
        self.viewFindShortcut.activated.connect(self.slotViewFind)
        self.viewFindNextShortcut = QtGui.QShortcut(QtGui.QKeySequence.FindNext, self)
        self.viewFindNextShortcut.activated.connect(self.slotViewFindNext)
        self.viewFindPreviousShortcut = QtGui.QShortcut(QtGui.QKeySequence.FindPrevious, self)
        self.viewFindPreviousShortcut.activated.connect(self.slotViewFindPrevious)

        self.dialogFindNextShortcut = QtGui.QShortcut(QtGui.QKeySequence.FindNext, self.findDialog)
        self.dialogFindNextShortcut.activated.connect(self.slotViewFindNext)
        self.dialogFindPreviousShortcut = QtGui.QShortcut(QtGui.QKeySequence.FindPrevious, self.findDialog)
        self.dialogFindPreviousShortcut.activated.connect(self.slotViewFindPrevious)

        app.aboutToQuit.connect(self.slotAboutToQuit)

        size = Config().getGeometry()
        self.resize(size)

        self.table.horizontalHeader().resizeSection(0, Config().getGeometryH0())
        self.table.horizontalHeader().resizeSection(1, Config().getGeometryH1())
        self.table.horizontalHeader().resizeSection(2, Config().getGeometryH2())

        self.firstShow=False

    def showEvent(self, e):
        e.ignore()
        if(not self.firstShow):
            self.firstShow=True
    	    QtCore.QTimer.singleShot(10, self.loadLast)
    def loadLast(self):
        #Load up last file
        if(Config().getOpenLast()):
            self.slotFileOpen(fileName=Config().getOpenLastFile())
    def closeEvent(self, event):
        if(self.document.isModified() and self.quitConfirmDialog.exec_() != QtGui.QDialog.Accepted):
            event.ignore()
            return
        app.quit()
    def customEvent(self, event):
        QtGui.QMessageBox.critical(self, "PasswordManager Error", event.getMessage())
    def slotQuit(self):
        self.app.postEvent(self, QtGui.QCloseEvent())
    def slotAboutToQuit(self):
        Config().setGeometry(self.size())
        Config().setGeometryH0(self.table.horizontalHeader().sectionSize(0))
        Config().setGeometryH1(self.table.horizontalHeader().sectionSize(1))
        Config().setGeometryH2(self.table.horizontalHeader().sectionSize(2))
    def slotHelpAbout(self):
        self.helpAboutDialog.show()
    def getSelRow(self):
        return self.table.selectedIndexes()[0].row()
    def slotFileOpen(self, checked=False, fileName=None):
        if(fileName == None):
            fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File", "", "Encrypted CSV (*.gcsv *.csv)", None, QtGui.QFileDialog.DontUseNativeDialog)
        if(fileName == None or len(fileName) == 0):
            return
        url=URL(fullPath=str(fileName))
        if(not url.empty()):
            if(self.document.isModified() and self.openConfirmDialog.exec_() != QtGui.QDialog.Accepted):
                return
            try:
                self.mymodel.layoutAboutToBeChanged.emit()
                self.document.load(url.getFullPath())
                self.mymodel.resort()
                self.mymodel.layoutChanged.emit()
                self.setWindowTitle("Password Manager - "+url.getFullPath())
            except Exception, e:
                ok = OKDialog(self, "Problem opening file", e.__str__())
                traceback.print_exc(file=sys.stdout)
                ok.show()
            
    def slotFileSave(self):
        if(self.document.getFile() == None):
            self.slotFileSaveAs()
        else:
            try:
                self.document.save(self.document.getFile())
            except Exception, e:
                ok = OKDialog(self, "Problem saving file", e.__str__())
                traceback.print_exc(file=sys.stdout)
                ok.show()
    def slotFileSaveAs(self):
        try:
            fileName = QtGui.QFileDialog.getSaveFileName(self, "Save File", "", "Encrypted CSV (*.gcsv *.csv)", None, QtGui.QFileDialog.DontUseNativeDialog)
            if(fileName == None or len(fileName) == 0):
                return
            url=URL(fullPath=str(fileName))
            if(not url.empty()):
                self.document.save(url.getFullPath())
        except Exception, e:
            ok = OKDialog(self, "Problem saving file", e.__str__())
            traceback.print_exc(file=sys.stdout)
            ok.show()
    def slotFileImportCSV(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Import CSV", "", "Comma Seperated Value File (*.csv)", None, QtGui.QFileDialog.DontUseNativeDialog)

        if(fileName == None or len(fileName) == 0):
            return
        url=URL(fullPath=str(fileName))
        if(not url.empty()):
            self.importCSVDialog.setFile(url.getFullPath())
            self.importCSVDialog.show()
    def slotEntryNew(self):
        self.editDialog.clear()
        self.editDialog.show()
    def slotEntryEdit(self):
        self.editDialog.setRow(self.getSelRow())
        self.editDialog.show()
    def slotEntryDelete(self):
        self.delDialog.setRow(self.getSelRow())
        if(self.delDialog.exec_() == QtGui.QDialog.Accepted):
            del self.document.getData()[self.getSelRow()]
            self.document.setModified()
    def slotEntryCopyU(self):
        self.clipboard.setText(self.document.getData()[self.getSelRow()][1])
    def slotEntryCopyP(self):
        self.clipboard.setText(self.document.getData()[self.getSelRow()][2])
    def slotEntryCopyUS(self):
        self.clipboard.setText(self.document.getData()[self.getSelRow()][1], QtGui.QClipboard.Selection)
    def slotEntryCopyPS(self):
        self.clipboard.setText(self.document.getData()[self.getSelRow()][2], QtGui.QClipboard.Selection)
    def slotSettings(self):
        self.configDialog.show()
    def slotViewFind(self):
        self.findDialog.hide()
        self.findDialog.show()
        self.findDialog.findText.setFocus(QtCore.Qt.ActiveWindowFocusReason)
        self.findDialog.findText.setSelection(0, len(str(self.findDialog.findText.text())))
        self.findDialog.next.setDefault(True)
    def slotViewFindNext(self):
        self.findDialog.show()
        self.findDialog.slotNext()
    def slotViewFindPrevious(self):
        self.findDialog.slotPrevious()
    def slotViewPasswords(self, checked):
        self.mymodel.layoutChanged.emit()

    def slotEntryMenuAboutToShow(self):
        if(len(self.table.selectedIndexes()) > 0):
            self.entryEdit.setEnabled(True)
            self.entryDel.setEnabled(True)
            self.entryCopyU.setEnabled(True)
            self.entryCopyP.setEnabled(True)
            self.entryCopyUS.setEnabled(True)
            self.entryCopyPS.setEnabled(True)
        else:
            self.entryEdit.setEnabled(False)
            self.entryDel.setEnabled(False)
            self.entryCopyU.setEnabled(False)
            self.entryCopyP.setEnabled(False)
            self.entryCopyUS.setEnabled(False)
            self.entryCopyPS.setEnabled(False)
    def doTableContextMenu(self, point):
        self.entryMenu.exec_(QtGui.QCursor.pos())

class ExceptionEvent(QtCore.QEvent):
    def __init__(self, message):
        QtCore.QEvent.__init__(self, QtCore.QEvent.User)
        self.message=message
    def getMessage(self):
        return self.message

def excepthook(type, value, trackbackobj):
    global app
    global window
    lines=traceback.format_exception(type, value, trackbackobj)
    msg="\n".join(lines)
    sep="------------------------------------------------------------------------------------------"
    print >> sys.stderr, msg
    #Probably need better dialog box
    app.postEvent(window, ExceptionEvent(sep+"\n"+str(type)+":"+str(value)+"\n"+sep+"\n"+msg))

if __name__=="__main__":
    app=QtGui.QApplication(sys.argv)
    window = MainWindow(app)
    sys.excepthook=excepthook
    path=os.path.abspath(os.path.dirname(sys.argv[0]))
    app.setWindowIcon(QtGui.QIcon(path+os.sep+"windowicon-128.png"))
    window.show()
    #QtCore.QTimer.singleShot(1000, window.loadLast)
    sys.exit(app.exec_())
