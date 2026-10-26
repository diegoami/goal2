"""[designed: owner #436] The pool's existing original caps word beside each player's name."""
from goal2.desktop.roster import RosterView
from PySide6.QtCore import Qt


def caps_for(state, players):
    """[confirmed: F002/F008; core/views.player_card] Player +8/+9 is the unsigned caps word."""
    from goal2.core import views
    mem = views.Memory(state)
    base = mem.far(views.PLAYERS)
    return {word: mem.word(base + views.PLAYER_SIZE * word + 8) for word in players}


class PoolRoster(RosterView):
    detail_heading = 'CAPS'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.caps = {}
        self.caption = 'POOL'

    def detail_text(self, row):
        value = self.caps.get(row[0])
        return str(value) if value is not None else ''

    def row_text(self, row):
        text = super().row_text(row)
        value = self.detail_text(row)
        return text + (f' CAPS {value}' if value else '')

    def paintEvent(self, event):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QFont, QPainter
        from goal2.desktop.player_card import BLACK, CYAN, LINE, GREY
        super().paintEvent(event)
        painter = QPainter(self);s = self.scale();painter.scale(s,s)
        right = self.width()/s - 76
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(17);font.setBold(True);painter.setFont(font);painter.setPen(QColor(CYAN))
        painter.drawText(QRectF(right-50,10,50,24), Qt.AlignmentFlag.AlignRight, 'CAPS')
        # [designed: #436] Counts use the card's existing16px descriptor size; names/roles keep20px.
        font.setPixelSize(16);painter.setFont(font)
        for position,index in enumerate(self.order):
            row = self.rows[index]
            painter.setPen(QColor(BLACK if index == self.current else LINE.get(row[3],GREY)))
            painter.drawText(QRectF(right-50,self.baseline(position)-20,50,24),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,self.detail_text(row))
        painter.end()
