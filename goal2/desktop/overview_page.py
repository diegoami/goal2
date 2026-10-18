"""[designed: T74] Overview container for existing window-owned controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    self.new=QPushButton('New campaign');self.new.setObjectName('newCampaign')
    self.friendly=QPushButton('New standalone friendly');
    layout=self.pages[0].content
    layout.addWidget(self.new);layout.addWidget(self.friendly)
    self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
