"""[derived: F036–F038; T198] Render delivered TEAM cells without recomputing values."""
from PySide6.QtCore import Qt,QSize,QRectF
from PySide6.QtGui import QFont,QFontMetricsF,QPainter,QColor
from PySide6.QtWidgets import QWidget,QGridLayout,QVBoxLayout,QSizePolicy
from goal2.desktop.country_card import characteristic_view
from goal2.ui import theme
from goal2.ui.screen import label
from goal2.ui.squad_card import Bar,colour

LINES=('keeper','defence','midfield','attack')
FIELDS=('hardness','fitness','energy','morale')


class LineBars(QWidget):
    def __init__(self):
        super().__init__();self.panel=None;self.rows={};self.labels={}
        grid=QGridLayout(self);grid.setContentsMargins(0,0,0,0);grid.setHorizontalSpacing(8);grid.setVerticalSpacing(8)
        for row,name in enumerate(LINES):
            heading=label(name,'barLabel');colour(heading,theme.CARD_LABEL)
            bar=Bar();grid.addWidget(heading,row,0);grid.addWidget(bar,row,1)
            self.rows[name]=(bar,heading);self.labels[name]=heading
        grid.setColumnStretch(1,1)
        self.set_panel(None)

    def set_panel(self,panel):
        self.panel=panel
        values={} if panel is None else {row['line']:row['cells'] for row in panel['bars']}
        for name,(bar,_) in self.rows.items():bar.set(values.get(name),25)
        self.setAccessibleName(self.text())

    def text(self):
        return ' · '.join(f'{name} '+('undrawn' if bar.value[0] is None else f'{bar.value[0]} of 25') for name,(bar,_) in self.rows.items())


class _CellRow(QWidget):
    def __init__(self,family):
        super().__init__();self.family=family;self.grid=[]
        self.setSizePolicy(QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Fixed)

    def metrics(self):
        font=QFont(self.font());font.setFamily(self.family)
        return font,QFontMetricsF(font)

    def content_size(self):
        _,metrics=self.metrics()
        return QSize(round(16*metrics.horizontalAdvance('M')),round(metrics.height()))

    def sizeHint(self):return self.content_size()
    def minimumSizeHint(self):return self.content_size()

    def paintEvent(self,event):
        font,metrics=self.metrics();step=metrics.horizontalAdvance('M');height=metrics.height()
        painter=QPainter(self);painter.setFont(font)
        for column,(character,active) in enumerate(self.grid):
            rect=QRectF(column*step,0,step,height)
            if active:painter.fillRect(rect,QColor(theme.BAR_FILLED))
            painter.setPen(QColor('#000000' if active else theme.BAR_EMPTY if character=='■' else theme.VALUE))
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,character)


class DescriptorCells(QWidget):
    """The existing row-major viewport, with readable labels above each original16-cell row."""
    def __init__(self,family):
        super().__init__();self.grid=[];self.labels={};self.row_widgets=[]
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(1)
        for field in FIELDS:
            group=QWidget();inner=QVBoxLayout(group);inner.setContentsMargins(0,0,0,0);inner.setSpacing(0)
            heading=label(field,'barLabel');colour(heading,theme.CARD_LABEL)
            cells=_CellRow(family);self.labels[field]=heading;self.row_widgets.append(cells)
            inner.addWidget(heading);inner.addWidget(cells);layout.addWidget(group)

    def set_panel(self,panel):
        self.grid=characteristic_view(panel['descriptors'])
        for widget,row in zip(self.row_widgets,self.grid):widget.grid=row;widget.updateGeometry();widget.update()
        self.updateGeometry()

    def content_size(self):
        return QSize(max(row.content_size().width() for row in self.row_widgets),self.layout().minimumSize().height())


class CharacteristicPanel(QWidget):
    def __init__(self,family):
        super().__init__();layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.cells=DescriptorCells(family);self.labels=self.cells.labels;self.panel=None;layout.addWidget(self.cells)

    def set_panel(self,panel):
        self.panel=panel;self.cells.set_panel(panel)
        self.setAccessibleName(self.text())

    def text(self):
        return '' if self.panel is None else ' · '.join(f"{d['field']} {d['text']}" for d in self.panel['descriptors'])
