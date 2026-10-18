"""[designed: T74] Fixtures container for existing window-owned controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    self.standings_dialog=None
    self.standings=QPushButton('Competition table');self.standings.setObjectName('showStandings')
    self.pages[3].content.addWidget(self.standings)
    layout=self.pages[3].content
    play_bar=QHBoxLayout();self.play=QPushButton('Play quick friendly');self.stop=QPushButton('Cancel match');self.stop.setEnabled(False)
    self.watch=QPushButton('Watch original friendly');self.watch.setObjectName('watchOriginal')
    play_bar.addWidget(self.play);play_bar.addWidget(self.watch);layout.addLayout(play_bar)
    half_bar=QGridLayout();self.half_out=QComboBox();self.half_in=QComboBox()
    self.substitute=QPushButton('Substitute');self.continue_match=QPushButton('Continue second half')
    half_bar.addWidget(QLabel('Off'),0,0);half_bar.addWidget(self.half_out,0,1);half_bar.addWidget(self.substitute,0,2)
    half_bar.addWidget(QLabel('On'),1,0);half_bar.addWidget(self.half_in,1,1);half_bar.addWidget(self.continue_match,1,2)
    half_bar.setColumnStretch(1,1)
    for widget in (self.half_out,self.half_in,self.substitute,self.continue_match):widget.setEnabled(False)
    layout.addLayout(half_bar);self.half_preview=None
    self.result=QLabel();self.result.setWordWrap(True);self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.result)
