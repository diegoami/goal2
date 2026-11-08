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
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.start_look import box

SIDE_WIDTH = 330   # [designed: s05-bulletin.html, the side panels' `width:330px`]


class BulletinScreen(Screen):
    title = "news"
    escape_text = None   # [confirmed: T156-R1 steps 11–12] the bulletin goes forward only

    def __init__(self, window, pages, then):
        super().__init__(window)
        self.pages, self.then, self.index = list(pages), then, 0
        self._build()
        self.set_enter("Next page (any key)", self.next_page)
        self._show()

    def _build(self):
        heading = label("THE SOCCER BULLETIN", "bulletinTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.body_layout.addWidget(heading)
        rule = QFrame()
        rule.setObjectName("rule")
        rule.setFixedHeight(3)
        self.body_layout.addWidget(rule)
        row = QHBoxLayout()
        row.setSpacing(18)
        self.panels = {}
        for name in ("left", "middle", "right"):
            frame, layout = box()
            head = label("", "boxHeading")
            tag = label("", "tag")
            masthead = para("", "masthead" if name == "middle" else "boxHeading")
            story = para("", "story" if name == "middle" else "sub")
            if name == "middle":
                for part in (head, masthead, story):
                    part.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                layout.addWidget(head)
                layout.addWidget(tag, 0, Qt.AlignmentFlag.AlignHCenter)
                layout.addSpacing(20)
            else:
                frame.setFixedWidth(SIDE_WIDTH)
                head.hide()
                layout.addWidget(tag, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(masthead)
            layout.addWidget(story)
            layout.addStretch(1)
            row.addWidget(frame, 1 if name == "middle" else 0)
            self.panels[name] = (head, tag, masthead, story)
        self.body_layout.addLayout(row, 1)

    def _show(self):
        page = self.pages[self.index]
        for name, (head, tag, masthead, story) in self.panels.items():
            panel = page[name]
            head.setText(f"FRONT PAGE · {self.index + 1} OF {len(self.pages)}")
            tag.setText(page.get("tag", ""))
            tag.setVisible(bool(page.get("tag")))
            set_para(masthead, panel["masthead"])
            set_para(story, "\n".join(panel["lines"]))

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
