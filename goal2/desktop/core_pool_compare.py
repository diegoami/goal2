"""[designed: owner #434/T134] Two simultaneous player summaries, using the accepted card bars.

Values are supplied by existing core_card/F008 readers; this view never chooses or exchanges players.
"""
import copy
from PySide6.QtCore import QSize, QRectF
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from goal2.desktop.player_card import PlayerCardView, BLACK, WHITE, GOLD, GREEN, CYAN, GREY, LINE


class PlayerComparisonView(PlayerCardView):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.cards=[None,None]
        self.explanation=''
        self.setObjectName('poolComparison')

    def sizeHint(self):
        s=self.scale()
        return QSize(round(1000*s),round(560*s))

    def set_cards(self,team,pool,explanation=''):
        self.cards=copy.deepcopy([team,pool])
        self.explanation=explanation
        summaries=[]
        for heading,card in zip(('TEAM','POOL'),self.cards):
            if card is None:
                summaries.append(heading+': no player selected')
            else:
                summaries.append(f"{heading}: {card['full_name']}, {card['role']}, {card['position']}; "
                                 f"caps {card['caps']}; goals {card['goals']}; age {card['age']}; "
                                 + '; '.join(f'{name} {value}' for name,value in card['skills'])
                                 + '; '+ '; '.join(f'{name} {word}' for name,word,_,_ in card['characteristics']))
        self.setAccessibleName('; '.join(summaries+[explanation]));self.update()

    def paintEvent(self,event):
        self.drawn=[];self.bottom=0
        painter=QPainter(self);painter.fillRect(self.rect(),QColor(BLACK))
        s=self.scale();painter.scale(s,s)
        for side,(heading,card) in enumerate(zip(('TEAM','POOL'),self.cards)):
            x=20+500*side
            painter.setPen(QColor(CYAN));painter.drawRect(QRectF(x-12,4,488,516))
            self.text(painter,x,26,heading,GOLD,20,True)
            if card is None:
                self.text(painter,x,70,'Choose a player to compare',GREY,18)
                continue
            colour=LINE.get(card['line'],WHITE)
            self.text(painter,x,52,card['full_name'],colour,24,True)
            self.text(painter,x,76,f"{card['role']} · {card['position']} / Club {card['club_role']}",WHITE,18)
            self.text(painter,x,98,f"CAPS {card['caps']}  GOALS {card['goals']}  AGE {card['age']}",GREEN,18)
            self.text(painter,x,120,card['readiness'],CYAN,18)
            for i,(name,value) in enumerate(card['skills']):
                y=146+21*i
                self.text(painter,x,y,name.capitalize(),GOLD,18,True)
                self.bar(painter,x+240,y,208,value,card['skill_cells'])
            for i,(name,word,bar,_) in enumerate(card['characteristics']):
                y=404+25*i
                self.text(painter,x,y,name.capitalize(),GOLD,18,True)
                self.bar(painter,x+240,y,208,bar,14)
                font=QFont('DejaVu Sans Mono');font.setPixelSize(16)
                painter.fillRect(QRectF(x+241,y-15,QFontMetrics(font).horizontalAdvance(word)+6,18),QColor(GREY))
                self.text(painter,x+244,y,word,BLACK,16)
        if self.explanation:self.text(painter,20,545,self.explanation,CYAN,16)
        painter.end()
