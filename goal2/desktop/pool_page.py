"""[designed: T74] Pool container for existing window-owned controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    layout=self.pages[2].content
    pool_panel=QWidget();pool_layout=QVBoxLayout(pool_panel);self.pool_panel=pool_panel
    self.pool_summary=QLabel();self.pool_summary.setWordWrap(True);pool_layout.addWidget(self.pool_summary)
    filter_bar=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search reserve name')
    self.position=QComboBox();self.position.addItem('All position codes',None)
    for code in range(14):self.position.addItem(f'Position code {code}',code)
    filter_bar.addWidget(self.search,1);filter_bar.addWidget(self.position);pool_layout.addLayout(filter_bar)
    self.reserves=QTableWidget(0,7);self.reserves.setObjectName('reserves')
    self.reserves.setHorizontalHeaderLabels(['ID','Player','Position','Ability','Energy','Confidence','Availability'])
    self.reserves.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.reserves.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    self.reserves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.reserves.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
    pool_layout.addWidget(self.reserves,1)
    self.exchange=QPushButton('Exchange selected squad player and reserve');pool_layout.addWidget(self.exchange)
    self.reserves.setTabKeyNavigation(False);self.reserves.setMinimumHeight(300);layout.addWidget(pool_panel)
