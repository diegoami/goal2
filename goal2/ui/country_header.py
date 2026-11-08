"""[confirmed: original157D; T200/T201] Stored Now/Top ranks and VGA strip glyph attributes."""
from PySide6.QtCore import QSize,QRectF,Qt
from PySide6.QtGui import QPainter,QFont,QFontMetricsF,QColor
from PySide6.QtWidgets import QWidget,QGridLayout,QSizePolicy
from goal2.ui.screen import label
from goal2.ui import theme
from goal2.ui.kits import DOS,NAMES
from goal2.game.country_card import NOT_DECODED


class RankColumns(QWidget):
    def __init__(self):
        super().__init__();self.values={};grid=QGridLayout(self)
        grid.setContentsMargins(0,0,0,0);grid.setHorizontalSpacing(12);grid.setVerticalSpacing(4)
        grid.addWidget(label('now','sub'),0,1);grid.addWidget(label('top','sub'),0,2)
        for row,(key,title) in enumerate((('world','world'),('continental','continent')),1):
            caption=label(title,'cardLabel');grid.addWidget(caption,row,0)
            for column,name in ((1,key),(2,'top_'+key)):
                value=label('','value');value.caption=caption;grid.addWidget(value,row,column);self.values[name]=value


class StripGlyphs(QWidget):
    """Initial rendered VGA cells; raw blink/background bits remain in attributes.

    Genuine R007 uses foreground9..15. None retains the monochrome template's
    three glyph2/attribute7 cells; absent fields remain explicitly unavailable.
    """
    def __init__(self,family):
        super().__init__();self.family=family;self.attributes=None;self.display_attributes=(7,7,7);self.unknown=False
        self.setSizePolicy(QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Fixed)

    def set_strips(self,attributes):
        if attributes is not None and (len(attributes)!=3 or any(type(a) is not int or not 0<=a<=255 for a in attributes)):
            raise ValueError('three raw strip attribute bytes required')
        self.unknown=False;self.attributes=None if attributes is None else tuple(attributes)
        self.display_attributes=(7,7,7) if attributes is None else tuple(attributes)
        self.setAccessibleName('strips: '+', '.join(NAMES[a&15] for a in self.display_attributes));self.updateGeometry();self.update()

    def set_unknown(self):self.unknown=True;self.setAccessibleName('strips unknown');self.updateGeometry();self.update()
    def text(self):return NOT_DECODED if self.unknown else '☻ ☻ ☻'
    def metrics(self):
        font=QFont(self.font());font.setFamily(self.family);return font,QFontMetricsF(font)
    def sizeHint(self):
        _,fm=self.metrics();return QSize(round(fm.horizontalAdvance('unknown') if self.unknown else 3*fm.horizontalAdvance('M')+16),round(fm.height()))
    def minimumSizeHint(self):return self.sizeHint()
    def paintEvent(self,event):
        font,fm=self.metrics();p=QPainter(self);p.setFont(font)
        try:
            if self.unknown:
                p.setPen(QColor(theme.TEXT_NORMAL));p.drawText(self.rect(),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,'unknown');return
            step=fm.horizontalAdvance('M')
            for index,attribute in enumerate(self.display_attributes):
                rect=QRectF(index*(step+8),0,step,fm.height())
                p.fillRect(rect,QColor(DOS[(attribute>>4)&7]));p.setPen(QColor(DOS[attribute&15]));p.drawText(rect,Qt.AlignmentFlag.AlignCenter,'☻')
        finally:p.end()
