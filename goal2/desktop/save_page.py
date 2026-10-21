"""[designed: T74] Save container for existing window-owned controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    layout=self.pages[4].content
    save_bar=QHBoxLayout();save_bar.addWidget(QLabel('Save file'));self.path=QLineEdit(str(model.save_path));self.path.setObjectName('savePath');save_bar.addWidget(self.path,1)
    self.save=QPushButton('Save');self.save.setObjectName('save');self.resume=QPushButton('Resume');self.resume.setObjectName('resume');save_bar.addWidget(self.save);save_bar.addWidget(self.resume);layout.addLayout(save_bar)
    # [designed: T87] Save as names another file; overwriting an existing one asks first.
    self.save_as=QPushButton('Save as…');self.save_as.setObjectName('saveAs');save_bar.insertWidget(save_bar.count()-1,self.save_as)


def game_menu(self):
    """[designed: T87] Game menu: Save (Ctrl+S, the existing shortcut), Save as…, Quit (Ctrl+Q)."""
    from PySide6.QtGui import QAction,QKeySequence,QShortcut
    menu=self.menuBar().addMenu('&Game');menu.setObjectName('gameMenu')
    for label,slot,name in (('Save\tCtrl+S',self.save.click,'menuSave'),('Save as…',self.save_as_dialog,'menuSaveAs'),
                            ('Quit\tCtrl+Q',self.quit_game,'menuQuit')):
        action=QAction(label,self);action.setObjectName(name);action.triggered.connect(slot);menu.addAction(action)
    self.quit_shortcut=QShortcut(QKeySequence('Ctrl+Q'),self);self.quit_shortcut.activated.connect(self.quit_game)
