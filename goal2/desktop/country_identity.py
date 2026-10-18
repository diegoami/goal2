"""[designed: T75] Original neutral identity art for every country, never a kit claim."""
from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QColor,QPainter,QPolygonF,QPen
from PySide6.QtWidgets import QWidget
from goal2.desktop.style import COLORS


class CountryIdentity(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('countryIdentityArt')
        self.setFixedSize(72,88);self.setAccessibleName('Generic shirt and neutral decorative stripe')
        self.setToolTip('Original generic shirt · neutral identity fallback, not a national kit')

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(COLORS['divider']),2));painter.setBrush(QColor(COLORS['secondary']))
        points=((22,6),(5,18),(13,34),(22,29),(22,66),(50,66),(50,29),(59,34),(67,18),(50,6),(43,13),(29,13))
        painter.drawPolygon(QPolygonF([QPointF(x,y) for x,y in points]))
        painter.setPen(Qt.PenStyle.NoPen)
        for index,color in enumerate(('#f5f2e8','#bbcfc5','#507365')):
            painter.setBrush(QColor(color));painter.drawRect(index*24,77,24,7)
