"""[confirmed: original157D; T200/T201] Stored Now/Top ranks and VGA strip glyph attributes."""
from PySide6.QtCore import QSize,QRectF,Qt
from PySide6.QtGui import QPainter,QFont,QFontMetricsF,QColor
from PySide6.QtWidgets import QWidget,QGridLayout,QSizePolicy,QFrame,QVBoxLayout,QHBoxLayout
from goal2.ui.screen import label
from goal2.ui import theme
from goal2.ui.kits import DOS,NAMES
from goal2.game.country_card import NOT_DECODED
from goal2.desktop.country_card import CODE_LINE
from goal2.ui.start_look import key_value, coloured_codes, refresh


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


class TeamHeader(QFrame):
    """[derived: original157D; #646] Shared TEAM header, stacked beside S10's editor."""
    def __init__(self, family, *, chooser=False, compact=False):
        super().__init__()
        self.family, self.chooser = family, chooser
        self.setObjectName('box')
        inner = QVBoxLayout(self)
        inner.setContentsMargins(16, 8, 16, 8)
        inner.setSpacing(2)
        top = QHBoxLayout()
        who = QVBoxLayout()
        who.setSpacing(2)
        if self.chooser:
            who.addWidget(label("Player 1 · choose your country", "sub"))
        self.name = label("", "h1")
        who.addWidget(self.name)
        self.first = label("", "sub")
        who.addWidget(self.first)
        self.first.setVisible(self.chooser)
        top.addLayout(who)
        top.addStretch(1)
        if self.chooser:
            level = QVBoxLayout()
            level.addWidget(label("level of difficulty", "sub"), 0, Qt.AlignmentFlag.AlignRight)
            level.addWidget(label(NOT_DECODED, "undecoded"), 0, Qt.AlignmentFlag.AlignRight)
            level.addStretch(1)
            top.addLayout(level)
        inner.addLayout(top)
        facts = QVBoxLayout() if compact else QHBoxLayout()
        facts.setSpacing(6 if compact else 28)
        team, self.team = key_value((("status", "status"), ("manager", "manager")))
        ranks = RankColumns(); self.ranks = ranks.values
        shape, self.shape = key_value((("formation", "formation"), ("skill", "skill"), ("strips", "strips")))
        old_strips = self.shape["strips"]
        shape.layout().removeWidget(old_strips)
        self.strip_view = StripGlyphs(self.family)
        self.strip_view.caption = old_strips.caption
        shape.layout().addWidget(self.strip_view, 2, 1)
        old_strips.hide(); old_strips.deleteLater(); self.shape["strips"] = self.strip_view
        for part in (team, ranks, shape):
            facts.addWidget(part, 0, Qt.AlignmentFlag.AlignTop)
        facts.addStretch(1)
        inner.addLayout(facts)
        self.role_codes = label("", "value")
        self.role_codes.setTextFormat(Qt.TextFormat.RichText)
        inner.addWidget(self.role_codes)

    def set_card(self, c, first=None):
        self.name.setText(c['name'])
        if first is not None:
            self.first.setText('first: ' + first)
        self.team["status"].setText(c.get("status", NOT_DECODED))
        self.team["manager"].setText(c["manager"] or "")
        self.ranks["world"].setText(str(c["world"]))
        self.ranks["continental"].caption.setText(c["continent"])
        self.ranks["continental"].setText(str(c["continental"]))
        self.ranks["top_world"].setText(str(c["top_world"]) if "top_world" in c else NOT_DECODED)
        self.ranks["top_continental"].setText(str(c["top_continental"]) if "top_continental" in c else NOT_DECODED)
        self.shape["formation"].setTextFormat(Qt.TextFormat.RichText)
        self.shape["formation"].setText(c['formation'])
        self.role_codes.setText(coloured_codes(
            (code, CODE_LINE.get(code, "unknown")) for code in c["eleven"]))
        self.shape["skill"].setText(c.get("skill", NOT_DECODED) or "")
        if "strips" in c: self.strip_view.set_strips(c["strips"])
        else: self.strip_view.set_unknown()
        for widget in (*self.team.values(), *self.ranks.values(), *self.shape.values()):
            if widget is self.strip_view: continue
            if widget.text() == NOT_DECODED: widget.setText("unknown")
            widget.setObjectName("undecoded" if widget.text() in (NOT_DECODED, "unknown") else "value")
        refresh(self)
