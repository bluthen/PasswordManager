import os
import sys
from unittest.mock import MagicMock


class DummySignal:
    def __init__(self, *args, **kwargs):
        pass

    def emit(self, *args, **kwargs):
        pass

    def connect(self, *args, **kwargs):
        pass


class DummyWidget:
    RejectRole = 0
    AcceptRole = 0
    ApplyRole = 0
    ActionRole = 0

    def __init__(self, *args, **kwargs):
        pass

    def accept(self):
        pass

    def reject(self):
        pass

    def setModal(self, *args, **kwargs):
        pass

    def setWindowTitle(self, *args, **kwargs):
        pass

    def setFocus(self, *args, **kwargs):
        pass

    def setDefault(self, *args, **kwargs):
        pass

    def isHidden(self):
        return False

    def show(self):
        pass

    def addWidget(self, *args, **kwargs):
        pass

    def addLayout(self, *args, **kwargs):
        pass

    def addStretch(self, *args, **kwargs):
        pass

    def setLayout(self, *args, **kwargs):
        pass

    def setContentsMargins(self, *args, **kwargs):
        pass

    def setSpacing(self, *args, **kwargs):
        pass

    def setText(self, *args, **kwargs):
        pass

    def addButton(self, *args, **kwargs):
        return DummyWidget()

    @property
    def clicked(self):
        return DummySignal()

    @property
    def released(self):
        return DummySignal()


class DummyLineEdit(DummyWidget):
    PasswordEchoOnEdit = 2
    Normal = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text = ""
        self._echo_mode = 0

    def text(self):
        return self._text

    def setText(self, t):
        self._text = str(t)

    def setEchoMode(self, mode):
        self._echo_mode = mode


class DummyCheckBox(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._checked = False

    def isChecked(self):
        return self._checked

    def setChecked(self, c):
        self._checked = bool(c)

    @property
    def toggled(self):
        return DummySignal()


class DummyComboBox(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = []
        self._current_index = 0
        self._editable = False
        self._custom_text = ""

    def setEditable(self, editable):
        self._editable = editable

    def addItem(self, item):
        self._items.append(str(item))

    def clear(self):
        self._items = []
        self._current_index = 0
        self._custom_text = ""

    def count(self):
        return len(self._items)

    def itemText(self, idx):
        if 0 <= idx < len(self._items):
            return self._items[idx]
        return ""

    def currentText(self):
        if self._custom_text:
            return self._custom_text
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]
        return ""

    def setEditText(self, text):
        self._custom_text = str(text)
        if text in self._items:
            self._current_index = self._items.index(text)

    def setCurrentText(self, text):
        self.setEditText(text)

    def setCurrentIndex(self, idx):
        self._current_index = idx
        self._custom_text = ""

    def findText(self, text):
        try:
            return self._items.index(text)
        except ValueError:
            return -1

    def blockSignals(self, block):
        pass

    @property
    def currentTextChanged(self):
        return DummySignal()

    @property
    def currentIndexChanged(self):
        return DummySignal()


class DummyAbstractTableModel:
    def __init__(self, parent=None):
        self.layoutAboutToBeChanged = DummySignal()
        self.layoutChanged = DummySignal()

    def index(self, row, column, parent=None):
        return MagicMock()


class DummyQtCore:
    Qt = MagicMock()
    Qt.DescendingOrder = 1
    Qt.AscendingOrder = 0
    Qt.DisplayRole = 0
    Qt.ActiveWindowFocusReason = 0

    QAbstractTableModel = DummyAbstractTableModel

    @staticmethod
    def pyqtSignal(*args, **kwargs):
        return DummySignal()

    @staticmethod
    def pyqtSlot(*args, **kwargs):
        return lambda fn: fn

    @staticmethod
    def QVariant(val=None):
        return val

    def __getattr__(self, name):
        return MagicMock()


def setup_qt_mock():
    dummy_qt = MagicMock()
    dummy_qtwidgets = MagicMock()
    dummy_qtwidgets.QDialog = DummyWidget
    dummy_qtwidgets.QWidget = DummyWidget
    dummy_qtwidgets.QGridLayout = DummyWidget
    dummy_qtwidgets.QVBoxLayout = DummyWidget
    dummy_qtwidgets.QHBoxLayout = DummyWidget
    dummy_qtwidgets.QGroupBox = DummyWidget
    dummy_qtwidgets.QLineEdit = DummyLineEdit
    dummy_qtwidgets.QPushButton = DummyWidget
    dummy_qtwidgets.QCheckBox = DummyCheckBox
    dummy_qtwidgets.QComboBox = DummyComboBox
    dummy_qtwidgets.QLabel = DummyWidget
    dummy_qtwidgets.QDialogButtonBox = DummyWidget

    dummy_qtcore = DummyQtCore()

    dummy_qt.QtWidgets = dummy_qtwidgets
    dummy_qt.QtCore = dummy_qtcore

    sys.modules["PyQt5"] = dummy_qt
    sys.modules["PyQt5.QtCore"] = dummy_qtcore
    sys.modules["PyQt5.QtGui"] = MagicMock()
    sys.modules["PyQt5.QtWidgets"] = dummy_qtwidgets

    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


setup_qt_mock()
