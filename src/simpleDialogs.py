
from PyQt4 import Qt, QtCore, QtGui

class DialogBase(QtGui.QDialog):
    def __init__(self, title, ok=False, cancel=False, apply=False, user1=False, user2=False, modal=False, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(int(modal))
        self.grid = QtGui.QGridLayout(self) 
        w = QtGui.QWidget()
        self.setWindowTitle(title)
        self.user1Button = None
        self.user2Button = None
        #Ok, Cancel, User1, User2 Buttons
        self.buttonBox = QtGui.QDialogButtonBox()
        self.grid.addWidget(self.buttonBox, 1, 0)
        if(ok):
            self.okButton = self.buttonBox.addButton("Ok", QtGui.QDialogButtonBox.AcceptRole)
            self.okButton.clicked.connect(self.slotOk)
        if(apply):
            self.applyButton = self.buttonBox.addButton("Apply", QtGui.QDialogButtonBox.ApplyRole)
            self.applyButton.clicked.connect(self.slotApply)
        if(cancel):
            self.cancelButton = self.buttonBox.addButton("Cancel", QtGui.QDialogButtonBox.RejectRole)
            self.cancelButton.clicked.connect(self.slotCancel)
        if(user1):
            self.user1Button = self.buttonBox.addButton("User1", QtGui.QDialogButtonBox.ActionRole) 
            self.user1Button.clicked.connect(self.slotUser1)
        if(user2):
            self.user2Button = self.buttonBox.addButton("User2", QtGui.QDialogButtonBox.ActionRole) 
            self.user2Button.clicked.connect(self.slotUser2)

    def addWidget(self, widget):
        self.grid.addWidget(widget, 0, 0)
    def setUser1ButtonText(self, text):
        self.user1Button.setText(text)
    def setUser2ButtonText(self, text):
        self.user2Button.setText(text)
    def setCancelButtonText(self, text):
        self.cancelButton.setText(text)
    def enableCancelButton(self, enabled):
        self.cancelButton.setEnabled(enabled)
    def enableApplyButton(self, enabled):
        self.cancelButton.setEnabled(enabled)
    def enableOkButton(self, enabled):
        self.okButton.setEnabled(enabled)
    def enableUser1Button(self, enabled):
        self.user1Button.setEnabled(enabled)
    def enableUser2Button(self, enabled):
        self.user2Button.setEnabled(enabled)
    def slotOk(self):
        self.slotApply()
        self.accept()
    def slotApply(self):
        pass
    def slotCancel(self):
        self.reject()
    def slotUser1(self):
        pass
    def slotUser2(self):
        pass
        

class OKDialog(DialogBase):
    def __init__(self, parent, caption, message):
        DialogBase.__init__(self, caption, ok=True, modal=True, parent=parent)

        label = QtGui.QLabel(message)
        self.addWidget(label)



class ConfirmDialog(DialogBase):
    yes = QtCore.pyqtSignal()
    no = QtCore.pyqtSignal()
    def __init__(self, parent, title, question):
        DialogBase.__init__(self, title, ok=True, cancel=True, modal=True, parent=parent)

        self.okButton.setText("Yes")
        self.cancelButton.setText("No")
        self.label=QtGui.QLabel(question)
        self.addWidget(self.label)
    def slotCancel(self):
        self.reject()
        self.no.emit()
    def slotOk(self):
        self.accept()
        self.yes.emit()

