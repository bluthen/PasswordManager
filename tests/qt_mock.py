import os
import sys
from unittest.mock import MagicMock


class DummyWidget:
    RejectRole = 0
    AcceptRole = 0
    ApplyRole = 0
    ActionRole = 0

    def __init__(self, *args, **kwargs):
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

    def setLayout(self, *args, **kwargs):
        pass

    def setText(self, *args, **kwargs):
        pass

    def addButton(self, *args, **kwargs):
        return DummyWidget()

    @property
    def clicked(self):
        return MagicMock()

    @property
    def released(self):
        return MagicMock()


class DummyLineEdit(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text = ""

    def text(self):
        return self._text

    def setText(self, t):
        self._text = t


class DummyCheckBox(DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._checked = False

    def isChecked(self):
        return self._checked

    def setChecked(self, c):
        self._checked = c


def setup_qt_mock():
    dummy_qt = MagicMock()
    dummy_qtwidgets = MagicMock()
    dummy_qtwidgets.QDialog = DummyWidget
    dummy_qtwidgets.QWidget = DummyWidget
    dummy_qtwidgets.QGridLayout = DummyWidget
    dummy_qtwidgets.QGroupBox = DummyWidget
    dummy_qtwidgets.QLineEdit = DummyLineEdit
    dummy_qtwidgets.QPushButton = DummyWidget
    dummy_qtwidgets.QCheckBox = DummyCheckBox
    dummy_qtwidgets.QLabel = DummyWidget
    dummy_qtwidgets.QDialogButtonBox = DummyWidget

    dummy_qt.QtWidgets = dummy_qtwidgets

    sys.modules["PyQt5"] = dummy_qt
    sys.modules["PyQt5.QtCore"] = MagicMock()
    sys.modules["PyQt5.QtGui"] = MagicMock()
    sys.modules["PyQt5.QtWidgets"] = dummy_qtwidgets

    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


setup_qt_mock()
