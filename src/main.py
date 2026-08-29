#!/usr/bin/env python3
import csv
import os
import re
import shlex
import subprocess
import sys
import tempfile
import traceback
from io import StringIO

from PyQt5 import QtCore, QtGui, QtWidgets

import misc
import passwordGenerator
from aboutDialog import AboutDialog
from config import Config
from misc import URL
from simpleDialogs import OKDialog, DialogBase, ConfirmDialog


class Document:
    def __init__(self):
        self.data = []
        self.file = None
        self.modified = False

    def isModified(self):
        return self.modified

    def setModified(self):
        self.modified = True
        return

    def getFile(self):
        return self.file

    def _normalize_row(self, row):
        if len(row) == 4:
            # Backward compatibility: [Name, Username, Password, Comment] -> [Name, "", Username, Password, Comment]
            return [str(row[0]), "", str(row[1]), str(row[2]), str(row[3])]
        elif len(row) < 4:
            name = str(row[0]) if len(row) > 0 else ""
            user = str(row[1]) if len(row) > 1 else ""
            pwd = str(row[2]) if len(row) > 2 else ""
            return [name, "", user, pwd, ""]
        else:
            r = [str(x) for x in row]
            while len(r) < 5:
                r.append("")
            return r[:5]

    def getCategories(self):
        cats = set()
        for row in self.data:
            if len(row) > 1 and str(row[1]).strip():
                cats.add(str(row[1]).strip())
        return sorted(list(cats))

    def importCSV(self, filename, delim, quote):
        with open(filename, "r", newline="", encoding="utf-8", errors="replace") as f:
            if quote is not None and len(str(quote)) == 1:
                csvReader = csv.reader(
                    f, delimiter=str(delim), quotechar=str(quote), escapechar="\\"
                )
            else:
                csvReader = csv.reader(
                    f, delimiter=str(delim), quoting=csv.QUOTE_NONE, escapechar="\\"
                )
            mydata = []
            for row in csvReader:
                mydata.append(self._normalize_row(row))
            self.setData(mydata)
        self.setModified()

    def load(self, filename):
        preOpen = Config().getPreOpenCommand()
        if preOpen and preOpen.strip() != "":
            preOpen_list = shlex.split(preOpen)
            misc.replace_open_save_symbols(preOpen_list, filename)
            try:
                subprocess.check_call(preOpen_list, shell=False)
            except Exception as e:
                ok = OKDialog(None, "Problem with pre-open.", str(e))
                traceback.print_exc(file=sys.stdout)
                if hasattr(ok, "exec_"):
                    ok.exec_()
                else:
                    ok.exec()
        # if encrypted
        # gpg -d filename | prog
        dec_cmd = Config().getDecCommand()
        decrypt = shlex.split(dec_cmd)
        misc.replace_gpg_symbols(decrypt, filename)
        process = subprocess.Popen(
            decrypt, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = process.communicate()
        code = process.returncode
        f = StringIO(output[0].decode())
        if code != 0:
            err_msg = output[1].decode(errors="replace") if output[1] else ""
            raise Exception(
                "Failed to decrypt file (Code: " + str(code) + ") -- " + err_msg
            )
        if Config().getCSVDelimiterTab():
            delim = "\t"
        else:
            delim = Config().getCSVDelimiter()
            if not delim or len(str(delim)) != 1:
                delim = ","
        quote_char = Config().getCSVQuote()
        if not quote_char or len(str(quote_char)) != 1:
            quote_char = '"'

        if Config().getCSVQuoteCheck():
            csvReader = csv.reader(
                f, delimiter=delim, quotechar=quote_char, escapechar="\\"
            )
        else:
            csvReader = csv.reader(
                f, delimiter=delim, quoting=csv.QUOTE_NONE, escapechar="\\"
            )
        mydata = []
        for row in csvReader:
            mydata.append(self._normalize_row(row))
        self.setData(mydata)
        if f:
            f.close()
        self.file = filename

    def save(self, filename):
        gpg_key = Config().getGPGKey()
        enc_cmd = Config().getEncCommand()
        if "$k" in enc_cmd and (
            not gpg_key or (isinstance(gpg_key, str) and not gpg_key.strip())
        ):
            raise Exception(
                "GPG Key is not configured. Please select or enter a GPG Key in File -> Settings."
            )

        f = StringIO()
        if Config().getCSVDelimiterTab():
            delim = "\t"
        else:
            delim = str(Config().getCSVDelimiter())
            if not delim or len(str(delim)) != 1:
                delim = ","
        quote_char = Config().getCSVQuote()
        if not quote_char or len(str(quote_char)) != 1:
            quote_char = '"'

        if Config().getCSVQuoteCheck():
            csvWriter = csv.writer(
                f, delimiter=delim, quotechar=quote_char, escapechar="\\"
            )
        else:
            csvWriter = csv.writer(
                f, delimiter=delim, quoting=csv.QUOTE_NONE, escapechar="\\"
            )
        csvWriter.writerows(self.getData())
        output = f.getvalue()
        f.close()
        # cat file | gpg -a --encrypt -r keyid -o - > newfile
        encrypt = shlex.split(enc_cmd)
        misc.replace_gpg_symbols(encrypt, None)
        process = subprocess.Popen(
            encrypt,
            shell=False,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        noutput = process.communicate(output.encode())
        if process.returncode != 0:
            err_msg = noutput[1].decode(errors="replace") if noutput[1] else ""
            raise Exception(
                "Failed to encrypt data."
                + (f" (Code: {process.returncode}) -- {err_msg}" if err_msg else "")
            )

        # Write actual file atomically with restrictive permissions (0o600)
        target_dir = os.path.dirname(os.path.abspath(filename))
        temp_fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix=".tmp_gcsv_")
        try:
            os.chmod(temp_path, 0o600)
            with os.fdopen(temp_fd, "wb") as f_out:
                f_out.write(noutput[0])
            os.replace(temp_path, filename)
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise

        self.file = filename
        self.modified = False
        if Config().getOpenLast():
            Config().setOpenLastFile(self.file)
        postSave = Config().getPostSaveCommand()
        if postSave and postSave.strip() != "":
            postSave_list = shlex.split(postSave)
            misc.replace_open_save_symbols(postSave_list, filename)
            try:
                subprocess.check_call(postSave_list, shell=False)
            except Exception as e:
                ok = OKDialog(None, "Problem with post-save.", str(e))
                traceback.print_exc(file=sys.stdout)
                if hasattr(ok, "exec_"):
                    ok.exec_()
                else:
                    ok.exec()

    def setData(self, data):
        normalized = []
        if data is not None:
            for row in data:
                normalized.append(self._normalize_row(row))
        self.data = normalized

    def getData(self):
        return self.data


class KeyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.header = ["Key"]

        self.data = []

    def refresh(self):
        self.layoutAboutToBeChanged.emit()
        getKeys = shlex.split("$g --no-tty --with-colons --fixed-list-mode --batch -K")
        misc.replace_gpg_symbols(getKeys)
        process = subprocess.Popen(
            getKeys, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = process.communicate()
        code = process.returncode
        if code != 0:
            err_msg = output[1].decode(errors="replace") if output[1] else ""
            raise Exception(
                "Failed to get key listing (Code: " + str(code) + ") -- " + err_msg
            )
        output_text = output[0].decode(errors="replace")
        self.data = self._parse_keys(output_text)
        self.layoutChanged.emit()

    @staticmethod
    def _parse_keys(output_text):
        data = []
        lines = output_text.strip().splitlines()
        if not lines:
            return data

        is_colon_format = any(line.startswith("sec:") for line in lines)

        if is_colon_format:
            current_key = None
            current_uids = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":")
                if parts[0] == "sec":
                    if current_key:
                        uid_str = (
                            f" - {', '.join(current_uids)}" if current_uids else ""
                        )
                        data.append([f"sec {current_key}{uid_str}", current_key])
                    current_key = parts[4] if len(parts) > 4 and parts[4] else ""
                    current_uids = []
                elif parts[0] == "uid" and current_key is not None:
                    if len(parts) > 9 and parts[9]:
                        uid = parts[9].replace("\\x3a", ":")
                        current_uids.append(uid)
                elif parts[0] == "fpr" and not current_key and len(parts) > 9:
                    current_key = parts[9]
            if current_key:
                uid_str = f" - {', '.join(current_uids)}" if current_uids else ""
                data.append([f"sec {current_key}{uid_str}", current_key])
        else:
            # Fallback for human-readable output
            foundKey = False
            key = ""
            aline = ""
            for line in lines:
                rline = line.rstrip()
                if not foundKey and rline.startswith("sec"):
                    m = re.search(r"/(\w+)", rline)
                    if m:
                        key = m.group(1)
                    else:
                        m2 = re.search(r"\b([0-9A-Fa-f]{8,40})\b", rline)
                        key = m2.group(1) if m2 else rline
                    aline = rline
                    foundKey = True
                elif len(rline) == 0:
                    if len(key) != 0:
                        data.append([aline, key])
                    key = ""
                    aline = ""
                    foundKey = False
                elif foundKey:
                    aline += "\n" + rline
            if len(key) != 0:
                data.append([aline, key])

        return data

    def data(self, index, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        try:
            return QtCore.QVariant(self.data[index.row()][index.column()])
        except:
            return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.header[section])
        return QtCore.QVariant()


class KeyDialog(DialogBase):
    def __init__(self, parent):
        DialogBase.__init__(
            self, "Key Selector", ok=True, cancel=True, modal=True, parent=parent
        )

        self.parent = parent

        keyBox = QtWidgets.QGroupBox("Select Key")
        keyLayout = QtWidgets.QGridLayout()
        keyBox.setLayout(keyLayout)
        self.model = KeyTableModel(self)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setCornerButtonEnabled(False)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        keyLayout.addWidget(self.table, 0, 0)
        self.addWidget(keyBox)

    def refresh(self):
        self.model.refresh()
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def slotCancel(self):
        self.reject()

    def slotOk(self):
        row = self.table.selectedIndexes()[0].row()
        self.parent.gpgKey.setText(self.model.data[row][1])
        self.accept()


class MainTableModel(QtCore.QAbstractTableModel):
    def __init__(self, document, main, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.main = main

        self.document = document
        self.header = ["Name", "Category", "Username", "Password", "Comment"]
        self.categoryFilter = "All Categories"
        self.visibleIndices = []
        self.sortColumn = 0
        self.sortOrder = QtCore.Qt.AscendingOrder
        self.sort(0, QtCore.Qt.AscendingOrder)

    def updateVisibleRows(self):
        data = self.document.getData()
        if data is None:
            self.visibleIndices = []
            return
        if self.categoryFilter == "All Categories" or not self.categoryFilter:
            self.visibleIndices = list(range(len(data)))
        else:
            self.visibleIndices = [
                i
                for i, row in enumerate(data)
                if len(row) > 1 and str(row[1]) == self.categoryFilter
            ]

    def setCategoryFilter(self, category):
        self.layoutAboutToBeChanged.emit()
        self.categoryFilter = category
        self.updateVisibleRows()
        self.layoutChanged.emit()

    def getDocRow(self, table_row):
        if 0 <= table_row < len(self.visibleIndices):
            return self.visibleIndices[table_row]
        return table_row

    def rowCount(self, parent=None):
        return len(self.visibleIndices)

    def columnCount(self, parent=None):
        return len(self.header)

    def data(self, index, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if self.document.getData() is not None and 0 <= index.row() < len(
            self.visibleIndices
        ):
            doc_row = self.visibleIndices[index.row()]
            try:
                if index.column() == 3:  # Password column
                    if self.main.viewPasswords.isChecked():
                        return QtCore.QVariant(
                            self.document.getData()[doc_row][index.column()]
                        )
                    else:
                        return QtCore.QVariant("****")
                else:
                    return QtCore.QVariant(
                        self.document.getData()[doc_row][index.column()]
                    )
            except:
                return QtCore.QVariant()
        return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.header[section])
        return QtCore.QVariant()

    def resort(self):
        self.sort(self.sortColumn, self.sortOrder)

    def sort(self, column, order):
        self.sortColumn = column
        self.sortOrder = order
        if self.document.getData() is not None:
            self.layoutAboutToBeChanged.emit()
            self.document.setData(
                sorted(
                    self.document.getData(),
                    key=lambda a: str(a[column]).lower() if len(a) > column else "",
                    reverse=(order == QtCore.Qt.DescendingOrder),
                )
            )
            self.updateVisibleRows()
            self.layoutChanged.emit()


class AdvancedConfigWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        encryptionBox = QtWidgets.QGroupBox("Encryption")
        eboxLayout = QtWidgets.QGridLayout()
        encryptionBox.setLayout(eboxLayout)
        encLabel = QtWidgets.QLabel("$g - gpg path; $k - keyid; $f - file")
        encLabel.setWordWrap(True)
        eboxLayout.addWidget(encLabel, 0, 0, 1, 2)
        eboxLayout.addWidget(QtWidgets.QLabel("Encrypt Command:"), 1, 0)
        self.encCommand = QtWidgets.QLineEdit()
        eboxLayout.addWidget(self.encCommand, 1, 1)
        eboxLayout.addWidget(QtWidgets.QLabel("Decrypt Command:"), 2, 0)
        self.decCommand = QtWidgets.QLineEdit()
        eboxLayout.addWidget(self.decCommand, 2, 1)
        layout.addWidget(encryptionBox)

        openSaveBox = QtWidgets.QGroupBox("Open/Save commands")
        openSaveLayout = QtWidgets.QGridLayout()
        openSaveBox.setLayout(openSaveLayout)
        openSaveLabel = QtWidgets.QLabel("$f - file, $d - file directory")
        openSaveLabel.setWordWrap(True)
        openSaveLayout.addWidget(openSaveLabel, 0, 0, 1, 2)
        openSaveLayout.addWidget(QtWidgets.QLabel("Pre-Open Command:"), 1, 0)
        self.preOpenCommand = QtWidgets.QLineEdit()
        openSaveLayout.addWidget(self.preOpenCommand, 1, 1)
        openSaveLayout.addWidget(QtWidgets.QLabel("Post-SaveCommand:"), 2, 0)
        self.postSaveCommand = QtWidgets.QLineEdit()
        openSaveLayout.addWidget(self.postSaveCommand, 2, 1)
        layout.addWidget(openSaveBox)

        csvBox = QtWidgets.QGroupBox("CSV")
        cboxLayout = QtWidgets.QGridLayout()
        csvBox.setLayout(cboxLayout)
        cboxLayout.addWidget(QtWidgets.QLabel("Delimiter:"), 0, 0)
        delimiterButtonGroup = QtWidgets.QButtonGroup()
        self.delimiterTab = QtWidgets.QRadioButton("Tab")
        self.delimiterTab.setChecked(True)
        self.delimiterTab.toggled.connect(self.slotDelimiterTab)
        cboxLayout.addWidget(self.delimiterTab, 0, 1, 1, 2)
        self.delimiterOther = QtWidgets.QRadioButton("Other")
        cboxLayout.addWidget(self.delimiterOther, 1, 1)
        delimiterButtonGroup.addButton(self.delimiterTab)
        delimiterButtonGroup.addButton(self.delimiterOther)
        self.delimiter = QtWidgets.QLineEdit()
        self.delimiter.setText(",")
        self.delimiter.setEnabled(False)
        cboxLayout.addWidget(self.delimiter, 1, 2)

        self.quoteCheck = QtWidgets.QCheckBox("Quote:")
        self.quoteCheck.toggled.connect(self.slotQuoteCheck)
        cboxLayout.addWidget(self.quoteCheck, 2, 0)
        self.quote = QtWidgets.QLineEdit()
        self.quote.setText('"')
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
        delim = Config().getCSVDelimiter()
        self.delimiter.setText(delim if delim and delim != "\t" else ",")
        is_tab = Config().getCSVDelimiterTab()
        if is_tab:
            self.delimiterTab.setChecked(True)
            self.delimiter.setEnabled(False)
        else:
            self.delimiterOther.setChecked(True)
            self.delimiter.setEnabled(True)
        quote_enabled = Config().getCSVQuoteCheck()
        self.quoteCheck.setChecked(quote_enabled)
        self.quote.setEnabled(quote_enabled)
        quote_char = Config().getCSVQuote()
        self.quote.setText(quote_char if quote_char else '"')
        self.preOpenCommand.setText(Config().getPreOpenCommand())
        self.postSaveCommand.setText(Config().getPostSaveCommand())

    def saveConfig(self):
        Config().setEncCommand(self.encCommand.text())
        Config().setDecCommand(self.decCommand.text())
        delim_text = self.delimiter.text().strip()
        if not delim_text:
            delim_text = ","
        Config().setCSVDelimiter(delim_text)
        Config().setCSVDelimiterTab(self.delimiterTab.isChecked())
        Config().setCSVQuoteCheck(self.quoteCheck.isChecked())
        quote_text = self.quote.text()
        if not quote_text:
            quote_text = '"'
        Config().setCSVQuote(quote_text)
        Config().setPreOpenCommand(self.preOpenCommand.text())
        Config().setPostSaveCommand(self.postSaveCommand.text())


class GeneralConfigWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        settingsBox = QtWidgets.QGroupBox("Settings")
        boxLayout = QtWidgets.QGridLayout()
        settingsBox.setLayout(boxLayout)
        self.autoOpen = QtWidgets.QCheckBox(
            "Try to open last saved document on startup."
        )
        boxLayout.addWidget(self.autoOpen, 0, 0, 1, 3)
        boxLayout.addWidget(QtWidgets.QLabel("GPG Path:"), 1, 0)
        self.gpgPath = QtWidgets.QLineEdit()
        boxLayout.addWidget(self.gpgPath, 1, 1)
        self.gpgPathBrowse = QtWidgets.QPushButton("...")
        boxLayout.addWidget(self.gpgPathBrowse, 1, 2)
        self.gpgPathBrowse.released.connect(self.slotBrowseGPGPath)
        boxLayout.addWidget(QtWidgets.QLabel("GPG Key:"), 2, 0)
        self.gpgKey = QtWidgets.QLineEdit()
        boxLayout.addWidget(self.gpgKey, 2, 1)
        self.browseButton = QtWidgets.QPushButton("...")
        boxLayout.addWidget(self.browseButton, 2, 2)
        self.browseButton.released.connect(self.slotBrowseKeys)

        self.keyDialog = KeyDialog(self)
        layout.addWidget(settingsBox)

    def slotBrowseGPGPath(self):
        fileName = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "GPG Location",
            "",
            "GPG Executable (gpg*)",
            None,
            QtWidgets.QFileDialog.DontUseNativeDialog,
        )[0]
        if fileName is None or len(fileName) == 0:
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
        if not self.autoOpen.isChecked():
            Config().setOpenLastFile("")
        Config().setGPGPath(self.gpgPath.text())
        Config().setGPGKey(self.gpgKey.text())


class ConfigDialog(DialogBase):
    def __init__(self, parent):
        super().__init__("Config", ok=True, cancel=True, modal=False, parent=parent)

        tabWidget = QtWidgets.QTabWidget()
        self.genTab = GeneralConfigWidget()
        tabWidget.addTab(self.genTab, "General")
        self.advTab = AdvancedConfigWidget()
        tabWidget.addTab(self.advTab, "Advanced")
        self.addWidget(tabWidget)
        self.parent = parent
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
        DialogBase.__init__(
            self, "Delete Entry", ok=True, cancel=True, modal=True, parent=parent
        )
        self.document = document
        self.okButton.setText("Yes")
        self.cancelButton.setText("No")
        self.label = QtWidgets.QLabel('Are you sure you want to remove "Entryname"?')
        self.addWidget(self.label)

    def setRow(self, row):
        self.label.setText(
            'Are you sure you want to remove "' + self.document.getData()[row][0] + '"?'
        )


class FindDialog(DialogBase):
    def __init__(self, parent, table, document):
        DialogBase.__init__(
            self, "Find", ok=False, cancel=True, modal=False, parent=parent
        )

        self.table = table
        self.document = document

        self.cancelButton.setText("Close")

        findBox = QtWidgets.QGroupBox("Find")
        findLayout = QtWidgets.QGridLayout()
        findBox.setLayout(findLayout)
        findLayout.addWidget(QtWidgets.QLabel("Search For:"), 0, 0)
        self.findText = QtWidgets.QLineEdit()
        findLayout.addWidget(self.findText, 0, 1)
        self.next = QtWidgets.QPushButton("Next")
        self.next.released.connect(self.slotNext)
        self.previous = QtWidgets.QPushButton("Previous")
        self.previous.released.connect(self.slotPrevious)
        findLayout.addWidget(self.next, 0, 2)
        findLayout.addWidget(self.previous, 1, 2)
        self.caseCheck = QtWidgets.QCheckBox("Case sensitive")
        findLayout.addWidget(self.caseCheck, 1, 0)

        self.addWidget(findBox)

        self.lastC = None
        self.lastRow = None
        self.lastText = None

    def getRowCount(self):
        if self.table is not None and hasattr(self.table, "model"):
            try:
                model = self.table.model()
                if model is not None and hasattr(model, "rowCount"):
                    rc = model.rowCount(None)
                    if isinstance(rc, int):
                        return rc
            except Exception:
                pass
        return len(self.document.getData())

    def getCellValue(self, visible_row, col):
        if self.table is not None and hasattr(self.table, "model"):
            try:
                model = self.table.model()
                if model is not None and hasattr(model, "getDocRow"):
                    doc_row = model.getDocRow(visible_row)
                    if isinstance(doc_row, int):
                        data = self.document.getData()
                        if 0 <= doc_row < len(data) and 0 <= col < len(data[doc_row]):
                            return str(data[doc_row][col])
            except Exception:
                pass
        data = self.document.getData()
        if 0 <= visible_row < len(data) and 0 <= col < len(data[visible_row]):
            return str(data[visible_row][col])
        return ""

    def slotNext(self, forwardSearch=True):
        if self.isHidden():
            self.show()
            self.findText.setFocus(QtCore.Qt.ActiveWindowFocusReason)
            self.next.setDefault(True)
        f = str(self.findText.text())
        if len(f) == 0:
            return
        total_rows = self.getRowCount()
        if total_rows == 0:
            return
        if self.lastText != f:
            self.lastText = f
            self.lastForwardSearch = forwardSearch
            if forwardSearch:
                self.lastC = 0
                self.nextRow = 0
            else:
                self.lastC = 0
                self.nextRow = total_rows - 1
        # Correct for when switching from next and previous
        if forwardSearch:
            if self.lastForwardSearch != forwardSearch:
                if self.nextRow == total_rows - 1:
                    self.nextRow = 1
                    self.lastC = self.lastC - 1
                else:
                    self.nextRow = self.nextRow + 2
        else:
            if self.lastForwardSearch != forwardSearch:
                if self.nextRow == 0:
                    self.nextRow = total_rows - 2
                    self.lastC = self.lastC - 1
                else:
                    self.nextRow = self.nextRow - 2
        self.lastForwardSearch = forwardSearch

        for c in range(self.lastC, 5):
            if forwardSearch:
                en = range(self.nextRow, total_rows)
            else:
                en = range(self.nextRow, -1, -1)
            for i in en:
                found = False
                cell_val = self.getCellValue(i, c)
                if self.caseCheck.isChecked():
                    if cell_val.find(f) >= 0:
                        found = True
                else:
                    if cell_val.lower().find(f.lower()) >= 0:
                        found = True
                if found:
                    self.table.selectRow(i)
                    self.table.scrollTo(self.table.model().index(i, 0))
                    self.lastC = c
                    if forwardSearch:
                        self.nextRow = i + 1
                        if self.nextRow >= total_rows:
                            self.nextRow = 0
                            self.lastC = c + 1
                    else:
                        self.nextRow = i - 1
                        if self.nextRow < 0:
                            self.nextRow = total_rows - 1
                            self.lastC = c + 1
                    return
        # At end, start at top of bottom
        self.lastText = None
        ok = OKDialog(
            self,
            "Find End",
            "At end of search, next search will start at the beginning.",
        )
        ok.show()

    def slotPrevious(self):
        self.slotNext(False)


class ImportCSVConfirmDialog(DialogBase):
    def __init__(self, parent, document, model):
        DialogBase.__init__(
            self,
            "Import without saving?",
            ok=True,
            cancel=True,
            modal=True,
            parent=parent,
        )

        self.document = document
        self.model = model

        self.okButton.setText("Yes")
        self.cancelButton.setText("No")
        self.label = QtWidgets.QLabel("Import file without saving current document?")
        self.addWidget(self.label)
        self.file = None
        self.delim = None
        self.quote = None

    def setFile(self, file):
        self.file = file

    def setDelimiter(self, delim):
        self.delim = delim

    def setQuote(self, quote):
        self.quote = quote

    def slotCancel(self):
        self.reject()

    def slotOk(self):
        try:
            self.accept()
            self.model.layoutAboutToBeChanged.emit()
            self.document.importCSV(self.file, self.delim, self.quote)
            self.model.resort()
            self.model.layoutChanged.emit()
            if hasattr(self.parent, "parent") and hasattr(
                self.parent.parent, "updateCategoryFilterList"
            ):
                self.parent.parent.updateCategoryFilterList()
        except Exception as e:
            ok = OKDialog(self, "Problem importing file", e.__str__())
            traceback.print_exc(file=sys.stdout)
            ok.show()


class ImportCSVDialog(DialogBase):
    def __init__(self, parent, document, model):
        DialogBase.__init__(
            self, "Import CSV", ok=True, cancel=True, modal=True, parent=parent
        )

        self.document = document
        self.model = model

        csvBox = QtWidgets.QGroupBox("CSV")
        cboxLayout = QtWidgets.QGridLayout()
        csvBox.setLayout(cboxLayout)
        cboxLayout.addWidget(QtWidgets.QLabel("Delimiter:"), 0, 0)
        delimiterButtonGroup = QtWidgets.QButtonGroup()
        self.delimiterTab = QtWidgets.QRadioButton("Tab")
        self.delimiterTab.toggled.connect(self.slotDelimiterTab)
        cboxLayout.addWidget(self.delimiterTab, 0, 1, 1, 2)
        self.delimiterOther = QtWidgets.QRadioButton("Other")
        self.delimiterOther.setChecked(True)
        cboxLayout.addWidget(self.delimiterOther, 1, 1)
        delimiterButtonGroup.addButton(self.delimiterTab)
        delimiterButtonGroup.addButton(self.delimiterOther)
        self.delimiter = QtWidgets.QLineEdit()
        self.delimiter.setText(",")
        cboxLayout.addWidget(self.delimiter, 1, 2)

        self.quoteCheck = QtWidgets.QCheckBox("Quote:")
        self.quoteCheck.setChecked(True)
        self.quoteCheck.toggled.connect(self.slotQuoteCheck)
        cboxLayout.addWidget(self.quoteCheck, 2, 0)
        self.quote = QtWidgets.QLineEdit()
        self.quote.setText('"')
        cboxLayout.addWidget(self.quote, 2, 1, 1, 2)

        self.file = None

        self.addWidget(csvBox)
        self.importConfirmDialog = ImportCSVConfirmDialog(self, document, model)

    def setFile(self, file):
        self.file = file

    def getFile(self):
        return self.file

    def slotDelimiterTab(self, checked):
        self.delimiter.setEnabled(not checked)

    def slotQuoteCheck(self, checked):
        self.quote.setEnabled(checked)

    def reset(self):
        self.quoteCheck.setEnabled(True)
        self.quote.setText('"')
        self.delimiter.setText(",")
        self.delimiterOther.setEnabled(True)

    def slotCancel(self):
        self.reset()
        self.reject()

    def slotOk(self):
        self.accept()
        self.importConfirmDialog.setFile(self.file)
        if self.delimiterTab.isChecked():
            self.importConfirmDialog.setDelimiter("\t")
        else:
            self.importConfirmDialog.setDelimiter(self.delimiter.text())
        if self.quoteCheck.isChecked():
            self.importConfirmDialog.setQuote(self.quote.text())
        else:
            self.importConfirmDialog.setQuote(None)
        if self.document.isModified():
            self.importConfirmDialog.show()
        else:
            self.importConfirmDialog.slotOk()


def create_eye_icon(visible=False):
    theme_name = "view-password" if not visible else "view-password-hidden"
    icon = QtGui.QIcon.fromTheme(theme_name)
    if not icon.isNull():
        return icon

    try:
        pixmap = QtGui.QPixmap(20, 20)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor(90, 90, 90), 1.5)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)

        painter.drawArc(2, 4, 16, 12, 30 * 16, 120 * 16)
        painter.drawArc(2, 4, 16, 12, 210 * 16, 120 * 16)

        painter.setBrush(QtGui.QBrush(QtGui.QColor(90, 90, 90)))
        painter.drawEllipse(8, 8, 4, 4)

        if visible:
            painter.drawLine(3, 17, 17, 3)

        painter.end()
        return QtGui.QIcon(pixmap)
    except Exception:
        return QtGui.QIcon()


class EditDialog(DialogBase):
    def __init__(self, parent, document, model):
        DialogBase.__init__(
            self, "New/Edit", ok=True, cancel=True, modal=True, parent=parent
        )
        self.parent = parent
        self.document = document
        self.model = model
        entryBox = QtWidgets.QGroupBox("Entry")
        boxLayout = QtWidgets.QGridLayout()
        entryBox.setLayout(boxLayout)
        boxLayout.addWidget(QtWidgets.QLabel("Name:"), 0, 0)
        self.name = QtWidgets.QLineEdit()
        boxLayout.addWidget(self.name, 0, 1)

        boxLayout.addWidget(QtWidgets.QLabel("Category:"), 1, 0)
        self.category = QtWidgets.QComboBox()
        self.category.setEditable(True)
        boxLayout.addWidget(self.category, 1, 1)

        boxLayout.addWidget(QtWidgets.QLabel("Username:"), 2, 0)
        self.username = QtWidgets.QLineEdit()
        boxLayout.addWidget(self.username, 2, 1)
        boxLayout.addWidget(QtWidgets.QLabel("Password:"), 3, 0)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.togglePasswordAction = QtWidgets.QAction(self.password)
        self.togglePasswordAction.setIcon(create_eye_icon(visible=False))
        self.togglePasswordAction.setToolTip("Show password")
        self.togglePasswordAction.triggered.connect(self.slotTogglePassword)
        self.password.addAction(
            self.togglePasswordAction, QtWidgets.QLineEdit.TrailingPosition
        )
        boxLayout.addWidget(self.password, 3, 1)
        self.generateButton = QtWidgets.QPushButton("Generate")
        self.generateButton.released.connect(self.slotGenerate)
        boxLayout.addWidget(self.generateButton, 4, 1)
        boxLayout.addWidget(QtWidgets.QLabel("Comment:"), 5, 0)
        self.comment = QtWidgets.QLineEdit()
        boxLayout.addWidget(self.comment, 5, 1)
        self.addWidget(entryBox)

        self.row = None

    def slotTogglePassword(self):
        if self.password.echoMode() == QtWidgets.QLineEdit.Password:
            self.password.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.togglePasswordAction.setIcon(create_eye_icon(visible=True))
            self.togglePasswordAction.setToolTip("Hide password")
        else:
            self.password.setEchoMode(QtWidgets.QLineEdit.Password)
            self.togglePasswordAction.setIcon(create_eye_icon(visible=False))
            self.togglePasswordAction.setToolTip("Show password")

    def populateCategories(self, currentCat=""):
        self.category.clear()
        cats = self.document.getCategories()
        for c in cats:
            self.category.addItem(c)
        if currentCat:
            idx = self.category.findText(currentCat)
            if idx >= 0:
                self.category.setCurrentIndex(idx)
            else:
                self.category.setEditText(currentCat)
        else:
            self.category.setEditText("")

    def setRow(self, row):
        self.row = row
        data = self.document.getData()[row]
        self.name.setText(data[0] if len(data) > 0 else "")
        cat = data[1] if len(data) > 1 else ""
        self.populateCategories(cat)
        self.username.setText(data[2] if len(data) > 2 else "")
        self.password.setText(data[3] if len(data) > 3 else "")
        self.comment.setText(data[4] if len(data) > 4 else "")

    def clear(self, defaultCategory=""):
        self.row = None
        self.name.setText("")
        self.populateCategories(defaultCategory)
        self.username.setText("")
        self.password.setText("")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.togglePasswordAction.setIcon(create_eye_icon(visible=False))
        self.togglePasswordAction.setToolTip("Show password")
        self.comment.setText("")

    def slotGenerate(self):
        self.password.setText(passwordGenerator.generate_password())

    def slotCancel(self):
        self.clear()
        self.reject()

    def slotOk(self):
        cat_val = (
            str(self.category.currentText()).strip()
            if hasattr(self.category, "currentText")
            else ""
        )
        line = [
            str(self.name.text()),
            cat_val,
            str(self.username.text()),
            str(self.password.text()),
            str(self.comment.text()),
        ]
        if self.row is None:
            self.document.getData().append(line)
        else:
            self.document.getData()[self.row] = line
        self.model.resort()
        self.document.setModified()
        if hasattr(self.parent, "updateCategoryFilterList"):
            self.parent.updateCategoryFilterList()
        self.accept()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app):
        QtWidgets.QMainWindow.__init__(self)
        self.app = app
        self.clipboard = QtWidgets.QApplication.clipboard()

        self.setWindowTitle("Password Manager")

        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileOpen = QtWidgets.QAction(
            "&Open",
            self.fileMenu,
            shortcut=QtGui.QKeySequence.Open,
            triggered=self.slotFileOpen,
        )
        self.fileMenu.addAction(self.fileOpen)
        self.fileSave = QtWidgets.QAction(
            "&Save",
            self.fileMenu,
            shortcut=QtGui.QKeySequence.Save,
            triggered=self.slotFileSave,
        )
        self.fileMenu.addAction(self.fileSave)
        self.fileSaveAs = QtWidgets.QAction(
            "Save &As...",
            self.fileMenu,
            shortcut=QtGui.QKeySequence.SaveAs,
            triggered=self.slotFileSaveAs,
        )
        self.fileMenu.addAction(self.fileSaveAs)
        self.fileMenu.addSeparator()
        self.fileImportCSV = QtWidgets.QAction(
            "&Import CSV...", self.fileMenu, triggered=self.slotFileImportCSV
        )
        self.fileMenu.addAction(self.fileImportCSV)
        self.fileMenu.addSeparator()
        self.fileSettings = QtWidgets.QAction(
            "S&ettings", self.fileMenu, triggered=self.slotSettings
        )
        self.fileMenu.addAction(self.fileSettings)
        self.fileMenu.addSeparator()
        self.fileQuit = QtWidgets.QAction(
            "&Quit",
            self.fileMenu,
            shortcut=QtGui.QKeySequence.mnemonic("&Quit"),
            triggered=self.slotQuit,
        )
        self.fileMenu.addAction(self.fileQuit)

        self.viewMenu = self.menuBar().addMenu("&View")
        self.viewPasswords = QtWidgets.QAction(
            "Show &Passwords", self.viewMenu, triggered=self.slotViewPasswords
        )
        self.viewPasswords.setCheckable(True)
        self.viewMenu.addAction(self.viewPasswords)
        self.viewMenu.addSeparator()
        self.viewFind = QtWidgets.QAction(
            "Find...", self.viewMenu, triggered=self.slotViewFind
        )
        self.viewMenu.addAction(self.viewFind)

        self.entryMenu = self.menuBar().addMenu("&Entry")
        self.entryMenu.aboutToShow.connect(self.slotEntryMenuAboutToShow)
        self.entryCopyU = QtWidgets.QAction(
            "Copy Username to Clipboard", self.entryMenu, triggered=self.slotEntryCopyU
        )
        self.entryMenu.addAction(self.entryCopyU)
        self.entryCopyP = QtWidgets.QAction(
            "Copy Password to Clipboard", self.entryMenu, triggered=self.slotEntryCopyP
        )
        self.entryMenu.addAction(self.entryCopyP)
        self.entryMenu.addSeparator()

        # Detect if an X system
        if os.name == "posix":  # Is there a better way?
            self.entryCopyUS = QtWidgets.QAction(
                "Copy Username to Selection",
                self.entryMenu,
                triggered=self.slotEntryCopyUS,
            )
            self.entryMenu.addAction(self.entryCopyUS)
            self.entryCopyPS = QtWidgets.QAction(
                "Copy Password to Selection",
                self.entryMenu,
                triggered=self.slotEntryCopyPS,
            )
            self.entryMenu.addAction(self.entryCopyPS)
            self.entryMenu.addSeparator()

        self.entryNew = QtWidgets.QAction(
            "New Entry", self.entryMenu, triggered=self.slotEntryNew
        )
        self.entryMenu.addAction(self.entryNew)
        self.entryEdit = QtWidgets.QAction(
            "Edit Entry", self.entryMenu, triggered=self.slotEntryEdit
        )
        self.entryMenu.addAction(self.entryEdit)
        self.entryDel = QtWidgets.QAction(
            "Delete Entry", self.entryMenu, triggered=self.slotEntryDelete
        )
        self.entryMenu.addAction(self.entryDel)
        self.entryEdit.setEnabled(False)
        self.entryDel.setEnabled(False)
        self.entryCopyU.setEnabled(False)
        self.entryCopyP.setEnabled(False)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpAbout = QtWidgets.QAction(
            "&About", self.helpMenu, triggered=self.slotHelpAbout
        )
        self.helpMenu.addAction(self.helpAbout)

        centralWidget = QtWidgets.QWidget()
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setContentsMargins(4, 4, 4, 4)
        centralLayout.setSpacing(4)
        centralWidget.setLayout(centralLayout)

        filterLayout = QtWidgets.QHBoxLayout()
        filterLayout.addWidget(QtWidgets.QLabel("Category:"))
        self.categoryCombo = QtWidgets.QComboBox()
        self.categoryCombo.addItem("All Categories")
        self.categoryCombo.currentTextChanged.connect(self.slotCategoryChanged)
        filterLayout.addWidget(self.categoryCombo)
        filterLayout.addStretch()
        centralLayout.addLayout(filterLayout)

        self.table = QtWidgets.QTableView()
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.customContextMenuRequested.connect(self.doTableContextMenu)
        self.document = Document()
        self.mymodel = MainTableModel(self.document, self)
        self.table.setModel(self.mymodel)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.table.setCornerButtonEnabled(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        centralLayout.addWidget(self.table)
        self.setCentralWidget(centralWidget)

        self.configDialog = ConfigDialog(self)

        self.editDialog = EditDialog(self, self.document, self.mymodel)
        self.delDialog = DelDialog(self, self.document)
        self.openConfirmDialog = ConfirmDialog(
            self,
            "Open without saving?",
            "Open new file without saving current document?",
        )
        self.importCSVDialog = ImportCSVDialog(self, self.document, self.mymodel)
        self.helpAboutDialog = AboutDialog(self)
        self.quitConfirmDialog = ConfirmDialog(
            self, "Quit without saving?", "Quit without saving current document?"
        )

        self.findDialog = FindDialog(self, self.table, self.document)

        self.viewFindShortcut = QtWidgets.QShortcut(QtGui.QKeySequence.Find, self)
        self.viewFindShortcut.activated.connect(self.slotViewFind)
        self.viewFindNextShortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence.FindNext, self
        )
        self.viewFindNextShortcut.activated.connect(self.slotViewFindNext)
        self.viewFindPreviousShortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence.FindPrevious, self
        )
        self.viewFindPreviousShortcut.activated.connect(self.slotViewFindPrevious)

        self.dialogFindNextShortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence.FindNext, self.findDialog
        )
        self.dialogFindNextShortcut.activated.connect(self.slotViewFindNext)
        self.dialogFindPreviousShortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence.FindPrevious, self.findDialog
        )
        self.dialogFindPreviousShortcut.activated.connect(self.slotViewFindPrevious)

        app.aboutToQuit.connect(self.slotAboutToQuit)

        size = Config().getGeometry()
        self.resize(size)

        self.table.horizontalHeader().resizeSection(0, Config().getGeometryH0())
        self.table.horizontalHeader().resizeSection(1, Config().getGeometryH1())
        self.table.horizontalHeader().resizeSection(2, Config().getGeometryH2())
        self.table.horizontalHeader().resizeSection(3, Config().getGeometryH3())

        self.firstShow = False

    def slotCategoryChanged(self, text):
        self.mymodel.setCategoryFilter(text)

    def updateCategoryFilterList(self):
        current = self.categoryCombo.currentText()
        self.categoryCombo.blockSignals(True)
        self.categoryCombo.clear()
        self.categoryCombo.addItem("All Categories")
        cats = self.document.getCategories()
        for cat in cats:
            self.categoryCombo.addItem(cat)
        idx = self.categoryCombo.findText(current)
        if idx >= 0:
            self.categoryCombo.setCurrentIndex(idx)
        else:
            self.categoryCombo.setCurrentIndex(0)
        self.categoryCombo.blockSignals(False)
        self.mymodel.setCategoryFilter(self.categoryCombo.currentText())

    def showEvent(self, e):
        e.ignore()
        if not self.firstShow:
            self.firstShow = True
            QtCore.QTimer.singleShot(10, self.loadLast)

    def loadLast(self):
        # Load up last file
        if Config().getOpenLast():
            self.slotFileOpen(fileName=Config().getOpenLastFile())

    def closeEvent(self, event):
        if (
            self.document.isModified()
            and self.quitConfirmDialog.exec_() != QtWidgets.QDialog.Accepted
        ):
            event.ignore()
            return
        app.quit()

    def customEvent(self, event):
        QtWidgets.QMessageBox.critical(
            self, "PasswordManager Error", event.getMessage()
        )

    def slotQuit(self):
        self.app.postEvent(self, QtGui.QCloseEvent())

    def slotAboutToQuit(self):
        Config().setGeometry(self.size())
        Config().setGeometryH0(self.table.horizontalHeader().sectionSize(0))
        Config().setGeometryH1(self.table.horizontalHeader().sectionSize(1))
        Config().setGeometryH2(self.table.horizontalHeader().sectionSize(2))
        Config().setGeometryH3(self.table.horizontalHeader().sectionSize(3))

    def slotHelpAbout(self):
        self.helpAboutDialog.show()

    def getSelRow(self):
        if len(self.table.selectedIndexes()) > 0:
            return self.mymodel.getDocRow(self.table.selectedIndexes()[0].row())
        return 0

    def slotFileOpen(self, checked=False, fileName=None):
        if fileName is None:
            fileName = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Open File",
                "",
                "Encrypted CSV (*.gcsv *.csv)",
                None,
                QtWidgets.QFileDialog.DontUseNativeDialog,
            )[0]
        if fileName is None or len(fileName) == 0:
            return
        url = URL(fullpath=str(fileName))
        if not url.empty():
            if (
                self.document.isModified()
                and self.openConfirmDialog.exec_() != QtWidgets.QDialog.Accepted
            ):
                return
            try:
                self.mymodel.layoutAboutToBeChanged.emit()
                self.document.load(url.get_fullpath())
                self.mymodel.resort()
                self.mymodel.layoutChanged.emit()
                self.updateCategoryFilterList()
                self.setWindowTitle("Password Manager - " + url.get_fullpath())
            except Exception as e:
                ok = OKDialog(self, "Problem opening file", e.__str__())
                traceback.print_exc(file=sys.stdout)
                ok.show()

    def slotFileSave(self):
        if self.document.getFile() is None:
            self.slotFileSaveAs()
        else:
            try:
                self.document.save(self.document.getFile())
            except Exception as e:
                ok = OKDialog(self, "Problem saving file", e.__str__())
                traceback.print_exc(file=sys.stdout)
                ok.show()

    def slotFileSaveAs(self):
        try:
            fileName = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save File",
                "",
                "Encrypted CSV (*.gcsv *.csv)",
                None,
                QtWidgets.QFileDialog.DontUseNativeDialog,
            )[0]
            if fileName is None or len(fileName) == 0:
                return
            url = URL(fullpath=str(fileName))
            if not url.empty():
                self.document.save(url.get_fullpath())
        except Exception as e:
            ok = OKDialog(self, "Problem saving file", e.__str__())
            traceback.print_exc(file=sys.stdout)
            ok.show()

    def slotFileImportCSV(self):
        fileName = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import CSV",
            "",
            "Comma Seperated Value File (*.csv)",
            None,
            QtWidgets.QFileDialog.DontUseNativeDialog,
        )[0]

        if fileName is None or len(fileName) == 0:
            return
        url = URL(fullpath=str(fileName))
        if not url.empty():
            self.importCSVDialog.setFile(url.get_fullpath())
            self.importCSVDialog.show()

    def slotEntryNew(self):
        defaultCat = ""
        currentFilter = self.categoryCombo.currentText()
        if currentFilter and currentFilter != "All Categories":
            defaultCat = currentFilter
        self.editDialog.clear(defaultCategory=defaultCat)
        self.editDialog.show()

    def slotEntryEdit(self):
        self.editDialog.setRow(self.getSelRow())
        self.editDialog.show()

    def slotEntryDelete(self):
        selRow = self.getSelRow()
        self.delDialog.setRow(selRow)
        if self.delDialog.exec_() == QtWidgets.QDialog.Accepted:
            del self.document.getData()[selRow]
            self.document.setModified()
            self.mymodel.resort()
            self.updateCategoryFilterList()

    def slotEntryCopyU(self):
        self.clipboard.setText(self.document.getData()[self.getSelRow()][2])

    def slotEntryCopyP(self):
        self.clipboard.setText(self.document.getData()[self.getSelRow()][3])

    def slotEntryCopyUS(self):
        self.clipboard.setText(
            self.document.getData()[self.getSelRow()][2], QtGui.QClipboard.Selection
        )

    def slotEntryCopyPS(self):
        self.clipboard.setText(
            self.document.getData()[self.getSelRow()][3], QtGui.QClipboard.Selection
        )

    def slotSettings(self):
        self.configDialog.show()

    def slotViewFind(self):
        self.findDialog.hide()
        self.findDialog.show()
        self.findDialog.findText.setFocus(QtCore.Qt.ActiveWindowFocusReason)
        self.findDialog.findText.setSelection(
            0, len(str(self.findDialog.findText.text()))
        )
        self.findDialog.next.setDefault(True)

    def slotViewFindNext(self):
        self.findDialog.show()
        self.findDialog.slotNext()

    def slotViewFindPrevious(self):
        self.findDialog.slotPrevious()

    def slotViewPasswords(self, checked):
        self.mymodel.layoutChanged.emit()

    def slotEntryMenuAboutToShow(self):
        if len(self.table.selectedIndexes()) > 0:
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
        self.message = message

    def getMessage(self):
        return self.message


def excepthook(type, value, trackbackobj):
    global app
    global window
    lines = traceback.format_exception(type, value, trackbackobj)
    msg = "\n".join(lines)
    sep = "------------------------------------------------------------------------------------------"
    print(msg, file=sys.stderr)
    # Probably need better dialog box
    app.postEvent(
        window,
        ExceptionEvent(
            sep + "\n" + str(type) + ":" + str(value) + "\n" + sep + "\n" + msg
        ),
    )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(app)
    sys.excepthook = excepthook
    path = os.path.abspath(os.path.dirname(sys.argv[0]))
    app.setWindowIcon(QtGui.QIcon(path + os.sep + "windowicon-128.png"))
    window.show()
    # QtCore.QTimer.singleShot(1000, window.loadLast)
    sys.exit(app.exec_())
