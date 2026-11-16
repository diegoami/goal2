"""S05 Bulletin: THE SOCCER BULLETIN, page *n of m*, Enter (any key) for the next page and then on.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S05 and its mockup s05-bulletin.html] The original's
three panels: the front page in the middle, under its count, and a story on each side. A page is the shape today's
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
        """[designed: owner, #667; T216] Preserve the three complete story projections; newspaper graphics remain #680."""
        from goal2.ui.cells import Cells,CellLabel,CellPara
        from goal2.ui.country_parts import framed
        from goal2.ui.squad_card import colour
        from goal2.ui import theme
        body=Cells(90,25,"bulletinBody")
        self.body_layout.addWidget(body,1)
        title=body.text("THE SOCCER BULLETIN","bulletinTitle",0,0,90)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.panels={};self.panel_areas={}
        for name,col,cols in (("left",0,29),("middle",30,30),("right",61,29)):
            frame,inner=framed("front page" if name=="middle" else "story",cols,23)
            head=CellLabel("","bulletinCount");colour(head,theme.HEADING)
            tag=CellPara("","tag")
            masthead=CellPara("","masthead")
            story=CellPara("","story" if name=="middle" else "sub")
            for widget in (head,tag,masthead,story):inner.put(widget,0,0,cols)
            if name=="middle":
                for widget in (head,masthead,story):widget.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            else:head.hide();colour(masthead,theme.HEADING)
            body.put(frame,col,1,cols,24)
            self.panels[name]=(head,tag,masthead,story)
            self.panel_areas[name]=inner

    def _show(self):
        from goal2.ui.cells import cell_w
        page=self.pages[self.index]
        for name,(head,tag,masthead,story) in self.panels.items():
            inner=self.panel_areas[name];cols=inner.cols;top=0
            head.setText(f"FRONT PAGE · {self.index+1} OF {len(self.pages)}")
            if name=="middle":inner.move(head,0,top,cols);top+=1
            tag.setText(page.get("tag",""));tag.setVisible(bool(page.get("tag")))
            if page.get("tag"):
                rows=max(1,len(tag.lines(round(cols*cell_w(tag)))))
                inner.move(tag,0,top,cols,rows);top+=rows
            set_para(masthead,page[name]["masthead"])
            rows=max(1,len(masthead.lines(round(cols*cell_w(masthead)))))
            inner.move(masthead,0,top,cols,rows);top+=rows+1
            set_para(story,"\n".join(page[name]["lines"]))
            inner.move(story,0,top,cols,max(1,23-top))

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
