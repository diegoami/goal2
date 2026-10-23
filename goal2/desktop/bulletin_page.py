"""[designed: T110; confirmed: F032/E038, views.BULLETIN_PANELS] The original's three paper columns.

Launch and the core round share this presentation of the already-read bulletin view. Text and line order are
preserved; this widget has no game state or driver and sends no keys.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


def sheet(*, frame, masthead, text, hint, story_size=26, masthead_size=24):
    """[designed: T110] T106's paper style; the core's sidebar leaves less room for its type."""
    return f"""
QFrame#bulletinPanel {{border:2px solid {frame};}}
QLabel#bulletinTitle {{font-size:30px;font-weight:700;color:{frame};}}
QLabel#bulletinMasthead {{font-size:{masthead_size}px;font-weight:700;color:{masthead};}}
QLabel#bulletinStory {{font-size:{story_size}px;font-weight:700;color:{text};}}
QLabel#bulletinCount {{color:{hint};}}
"""


class BulletinColumns(QWidget):
    """Three boxes with a masthead and every story line. `panels` retains Launch's label interface."""

    def __init__(self, title=None):
        super().__init__();self.setObjectName('bulletinColumns')
        layout = QVBoxLayout(self);layout.setContentsMargins(0, 0, 0, 0);layout.setSpacing(12)
        if title is not None:
            heading = QLabel(title);heading.setObjectName('bulletinTitle')
            heading.setTextFormat(Qt.TextFormat.PlainText);heading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(heading)
        row = QHBoxLayout();row.setSpacing(20);layout.addLayout(row, 1)
        self.panels = {}
        for name, stretch in (('left', 2), ('middle', 3), ('right', 2)):
            panel = QFrame();panel.setObjectName('bulletinPanel');body = QVBoxLayout(panel);body.setSpacing(12)
            masthead = QLabel();masthead.setObjectName('bulletinMasthead');masthead.setWordWrap(True)
            masthead.setTextFormat(Qt.TextFormat.PlainText)
            masthead.setAlignment(Qt.AlignmentFlag.AlignHCenter);body.addWidget(masthead)
            story = QLabel();story.setObjectName('bulletinStory');story.setWordWrap(True)
            story.setTextFormat(Qt.TextFormat.PlainText)
            story.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            story.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            body.addWidget(story, 1);row.addWidget(panel, stretch)
            self.panels[name] = (masthead, story)

    def set_content(self, view):
        for name, (masthead, story) in self.panels.items():
            masthead.setText(view[name]['masthead'])
            story.setText('\n'.join(view[name]['lines']))
