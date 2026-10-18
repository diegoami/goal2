"""[designed: T74] Squad container for existing window-owned controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    layout=self.pages[1].content
    self.table=QTableWidget(20,7);self.table.setObjectName('squad')
    self.table.setHorizontalHeaderLabels(['XI','Player','Position','Ability','Energy','Confidence','Availability'])
    self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
    self.table.setTabKeyNavigation(False);self.table.setMinimumHeight(300);layout.addWidget(self.table)
    layout=self.pages[1].content
    captain_bar=QHBoxLayout();captain_bar.addWidget(QLabel('Captain'));self.captain=QComboBox();self.captain.setObjectName('captain');captain_bar.addWidget(self.captain,1)
    self.confirm=QPushButton('Confirm management');self.confirm.setObjectName('confirm');self.cancel=QPushButton('Discard draft')
    captain_bar.addWidget(self.cancel);captain_bar.addWidget(self.confirm);layout.addLayout(captain_bar)
    self.tactics=[]
    tactics=QGridLayout()
    for index,(element,label) in enumerate(TACTICS):
        box=QCheckBox(label);box.setObjectName(f'tactic{element}')
        self.tactics.append((element,box));tactics.addWidget(box,index//2,index%2,Qt.AlignmentFlag.AlignLeft)
    layout.addLayout(tactics)
