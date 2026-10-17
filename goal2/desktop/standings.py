"""[designed: T49] Read-only competition table snapshot using named backend rows."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QLabel,QTableWidget,QTableWidgetItem,QVBoxLayout,QHeaderView


class CompetitionTable(QDialog):
    """[designed] Provisional progression markers do not claim qualification is clinched."""
    def __init__(self,view,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Competition table');self.resize(820,300)
        layout=QVBoxLayout(self)
        stage='Continental qualifying' if view['stage']==2 else 'World Cup qualifying'
        layout.addWidget(QLabel(f"{stage} — Continent {view['continent']}, group {view['group']}"))
        layout.addWidget(QLabel('Current positions; qualification is provisional. Two points for a win, one for a draw.'))
        self.table=QTableWidget(4,11);self.table.setObjectName('competitionTable')
        self.table.setHorizontalHeaderLabels(['Pos','Country','P','W','D','L','GF','GA','GD','Pts','Progression'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for i,row in enumerate(view['rows']):
            progress=('Playoff place' if view['playoff'] else 'Qualifying place') if row['advances'] else ''
            values=(row['rank'],row['name'],row['played'],row['won'],row['drawn'],row['lost'],
                    row['goals_for'],row['goals_against'],row['goal_difference'],row['points'],progress)
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable)
                if j==1:item.setData(Qt.ItemDataRole.UserRole,row['country'])
                self.table.setItem(i,j,item)
        layout.addWidget(self.table)
