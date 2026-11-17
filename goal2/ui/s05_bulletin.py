"""S05 Bulletin: THE SOCCER BULLETIN, page *n of m*, Enter (any key) for the next page and then on.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S05 and its mockup s05-bulletin.html] The original's
three newspaper pictures: the tallest front page in the middle and a story on each side. A page is the shape today's
bulletins have (goal2/core/views.py `bulletin`, goal2/desktop/bulletin_page.py): `{"left", "middle", "right"}`, each
`{"masthead": str, "lines": [str]}`; an optional `"tag"` labels a page (the screenshot's stand-ins say so).
[confirmed: F032/E038, views.BULLETIN_PANELS; T156-R1 steps 11–12, 200, 317]

[designed: owner, 2026-11-03, #509] The Python route has no bulletins yet: today's come from the original's memory on
the Core route, and the news text is Track B's port (U2). Until then a new career goes from S04 straight home
(`Window.open_career` shows this screen only for a career that supplies pages), and this screen is visited with
stand-in pages only.
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from goal2.ui.screen import Screen, set_para


from PySide6.QtGui import QColor,QPainter,QPen
from goal2.ui.cells import Cells,cell_w,row_px
from goal2.ui import theme


class BulletinSpread(Cells):
    """[derived: original bulletin.png/t156-011; #680] The horizontal rules behind the three newspaper pictures."""
    def paintEvent(self,event):
        import math
        from goal2.desktop import fixed_page
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor(theme.GROUND))
        pen=max(1,math.ceil(2*fixed_page.scale_y_of(self)))
        painter.setPen(QPen(QColor(theme.FRAME_DARK),pen))
        for row in range(1,self.rows+1):
            y=row_px(self,row)-1
            painter.drawLine(0,y,self.width(),y)
        painter.end()


class Newspaper(Cells):
    """[derived: F032, original bulletin.png; #680] Coloured paper, greeked columns and a halftone; the story stays text."""
    STYLES={"left":("#aaaaaa","#aa0000","#000000"),
            "middle":("#0000aa","#ffaa00","#ffffff"),
            "right":("#00aa00","#ffffff","#000000")}

    def __init__(self,name,cols,rows):
        super().__init__(cols,rows,"newspaper")
        self.name=name
        self.paper_colour,self.masthead_colour,self.ink=self.STYLES[name]
        self.furniture_top=rows

    def paintEvent(self,event):
        from goal2.desktop import fixed_page
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor(self.paper_colour))
        thick=max(1,round(2*fixed_page.scale_of(self)))
        painter.setPen(QPen(QColor(self.ink),thick))
        edge=thick
        painter.drawRect(self.rect().adjusted(edge,edge,-edge,-edge))
        cw,rh=cell_w(self),row_px(self)
        split=self.cols//2
        # [derived: F032 template filler] Furniture carries no source words and never covers the projected story.
        for row in range(self.furniture_top,self.rows-1):
            for first,last in ((1,split-1),(split+1,self.cols-1)):
                for col in range(first,last):
                    for stripe in (0.3,0.5,0.7):
                        y=round(row*rh+stripe*rh)
                        painter.drawLine(round(col*cw),y,round((col+.7)*cw),y)
        if self.name=="left" and self.rows-self.furniture_top>=4:
            left,top=round(5*cw),round((self.furniture_top+1)*rh)
            width,height=round((self.cols-10)*cw),round((self.rows-self.furniture_top-3)*rh)
            dot=max(1,round(2*fixed_page.scale_of(self)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.ink))
            for y in range(top,top+height,dot):
                for x in range(left,left+width,dot):
                    if ((x-left)//dot+(y-top)//dot)%2==0:painter.drawRect(x,y,dot,dot)
        painter.end()



class BulletinScreen(Screen):
    GRID = True   # [designed: owner, #667; T216]
    title = "news"
    escape_text = None   # [confirmed: T156-R1 steps 11–12] the bulletin goes forward only

    def __init__(self, window, pages, then):
        super().__init__(window)
        self.pages, self.then, self.index = list(pages), then, 0
        self._build()
        self.set_enter("Next page (any key)", self.next_page)
        self._show()

    def _build(self):
        """[designed: #667/#680; T216] Three newspaper pictures on cells, retaining every projected word and control."""
        from goal2.ui.cells import CellLabel,CellPara
        from goal2.ui.screen import Clickable
        from goal2.ui.squad_card import colour
        body=BulletinSpread(90,25,"bulletinBody")
        self.body_layout.addWidget(body,1)
        self.panels={};self.papers={}
        for name,col,row,cols,rows in (("left",2,4,27,18),("middle",30,1,30,22),("right",61,4,27,18)):
            paper=Newspaper(name,cols,rows)
            body.put(paper,col,row,cols,rows)
            head=CellLabel("","bulletinCount")
            if name=="middle":body.put(head,0,0,30)
            else:paper.put(head,1,0,cols-2);head.hide()
            tag=CellPara("","tag")
            masthead=CellPara("","masthead")
            story=CellPara("","story")
            for widget in (tag,masthead,story):
                widget.setTextFormat(Qt.TextFormat.PlainText)
                widget.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                paper.put(widget,1,1,cols-2)
                colour(widget,paper.ink)
            colour(masthead,paper.masthead_colour)
            self.panels[name]=(head,tag,masthead,story);self.papers[name]=paper
        plate=Clickable("gridLine");plate.setProperty("on",True)
        from PySide6.QtWidgets import QHBoxLayout
        layout=QHBoxLayout(plate);layout.setContentsMargins(0,0,0,0)
        caption=CellLabel("hit any key","enterText");caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(caption);plate.clicked.connect(self.next_page)
        body.put(plate,38,24,14)

    def _show(self):
        page=self.pages[self.index]
        for name,(head,tag,masthead,story) in self.panels.items():
            paper=self.papers[name];cols=paper.cols-2;top=1
            head.setText(f"FRONT PAGE · {self.index+1} OF {len(self.pages)}")
            tag.setText(page.get("tag",""));tag.setVisible(bool(page.get("tag")))
            if page.get("tag"):
                rows=max(1,len(tag.lines(round(cols*cell_w(tag)))))
                paper.move(tag,1,top,cols,rows);top+=rows
            masthead.setText(page[name]["masthead"])
            rows=max(1,len(masthead.lines(round(cols*cell_w(masthead)))))
            paper.move(masthead,1,top,cols,rows);top+=rows+1
            story.setText("\n".join(page[name]["lines"]))
            used=max(1,len(story.lines(round(cols*cell_w(story)))))
            paper.move(story,1,top,cols,max(1,paper.rows-top-1))
            paper.furniture_top=min(paper.rows,top+used+1)
            paper.update()

    def count_text(self) -> str:
        return self.panels["middle"][0].text()

    def next_page(self):
        """The next page; after the last, on (`then`)."""
        if self.index + 1 < len(self.pages):
            self.index += 1
            self._show()
            return None
        return self.then()

    def handle_key(self, key) -> bool:
        """Any key turns the page, as the original's news (F1 still opens the help)."""
        if key == Qt.Key.Key_F1:
            return super().handle_key(key)
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return False
        self.next_page()
        return True
