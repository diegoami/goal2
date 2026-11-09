"""The new window's look: the original's palette by role, the vendored VGA font, the text sizes and the style sheet.

[designed: owner, 2026-11-03, #526, #536] The colours are the design's palette table, by role
(docs/design/ui-2026-11/README.md §3, read from the original's captures by palette.py); each constant below is one
row of that table, and the test checks them against the README itself. The font is "PxPlus IBM VGA 8x16" (CC BY-SA
4.0), vendored in `goal2/ui/fonts/` with its licence and provenance and loaded from there, never from a system
install. [designed: owner, 2026-11-08, #666, #667; docs/design/ui-2026-11/fidelity-review.md §3] The cell is 16 x 32, the
page 90 x 28 cells (1440 x 896), and there is **one text size**, `TEXT` = 32 px: every glyph on every screen is one cell
wide, and hierarchy is colour, frame and position, never size. The page is presented at 4:3, stretched 1.2 vertically
(`STRETCH`), by the page's own font (`text_font`: a taller pixel size and a narrower `QFont` stretch, so a glyph keeps its
16 px advance) and by the page's lengths (goal2/desktop/fixed_page.py). This supersedes the owner's #598 (24 px text, 32 px
headings) in the direction it went.

Importing this module needs no Qt; `load_font` and `install` do.
"""
from __future__ import annotations

from pathlib import Path

# The palette, one constant per role of the README's §3 table. [confirmed: docs/design/ui-2026-11/README.md §3,
# `python3 docs/design/ui-2026-11/palette.py` on the captures it names]
GROUND = "#000000"            # ground
TEXT_BRIGHT = "#ffffff"       # text, bright
TEXT_NORMAL = "#aaaaaa"       # text, normal
FRAME = "#aaaaaa"             # frame lines
FRAME_DARK = "#555555"        # frame lines, dark grey
HEADING = "#00aaaa"           # headings, cyan
CARD_HEADING = "#aa0000"      # card headings, red
CARD_LABEL = "#aa5500"        # card labels, brown
KEY_HINT = "#aa00aa"          # key hints, magenta
HIGHLIGHT = "#aaaaaa"         # highlight bar
VALUE = "#ffff55"             # values, yellow
TITLE_BANNER = "#ff5555"      # title banner, light red
GOALKEEPER = "#00aa00"        # goalkeeper
DEFENCE = "#ff5555"           # defence
MIDFIELD = "#00aaaa"          # midfield
ATTACK = "#ffff55"            # attack
BAR_FILLED = "#aaaaaa"        # bar, filled
BAR_EMPTY = "#aa00aa"         # bar, empty
PITCH_LINES = "#aaaaaa"       # pitch lines
PITCH_SURROUND = "#00aa00"    # pitch surround

# The table as it reads, role name to colour, in the README's order.
PALETTE = {
    "ground": GROUND, "text, bright": TEXT_BRIGHT, "text, normal": TEXT_NORMAL, "frame lines": FRAME,
    "frame lines, dark grey": FRAME_DARK, "headings, cyan": HEADING, "card headings, red": CARD_HEADING,
    "card labels, brown": CARD_LABEL, "key hints, magenta": KEY_HINT, "highlight bar": HIGHLIGHT,
    "values, yellow": VALUE, "title banner, light red": TITLE_BANNER, "goalkeeper": GOALKEEPER, "defence": DEFENCE,
    "midfield": MIDFIELD, "attack": ATTACK, "bar, filled": BAR_FILLED, "bar, empty": BAR_EMPTY,
    "pitch lines": PITCH_LINES, "pitch surround": PITCH_SURROUND,
}

# What the mockups' style sheet derives from the table. [derived: docs/design/ui-2026-11/mockups/style.css,
# `--primary-text`, `--good`, `--bad`] Text on the highlight bar is black; a check that passed is bright text, one
# that failed light red. A translucent ground dims a screen under a box (`.scrim`, 62%).
ON_HIGHLIGHT = GROUND
GOOD = TEXT_BRIGHT
BAD = TITLE_BANNER
SCRIM_ALPHA = 158   # 0.62 of 255

# The cell, the page and the one text size. [designed: owner, 2026-11-08, #666, #667; fidelity-review.md §3] The font is
# 8 x 16; twice that is 16 x 32, and `TEXT` is the pixel size at which this font's cell is 16 x 32 [confirmed: measured
# 2026-11-09, `QFont` on the vendored font, offscreen Qt: pixel size 32 gives advance 16 and line height 32; 24 gives 12 and
# 24, off the grid].
CELL_W, CELL_H = 16, 32
CELL = (CELL_W, CELL_H)
COLS, ROWS = 90, 28
PAGE = (COLS * CELL_W, ROWS * CELL_H)   # 1440 x 896, the logical page
TEXT = CELL_H   # the only text size; nothing larger is drawn as type (larger things are line-art, #673-#675)
# [designed: owner, 2026-11-08, #667; DOSBox's 4:3] The page is shown with a 1.2 vertical stretch: 1440 x 896 becomes
# 1440 x 1075.2, half a per cent short of an exact 4:3 1440 x 1080, and a window letterboxes the remainder.
STRETCH = 1.2
PICTURE = (PAGE[0], PAGE[0] * 3 // 4)   # 1440 x 1080: the 4:3 window the page fills at scale 1, which the pictures are taken at

FONT_DIR = Path(__file__).with_name("fonts")
FONT_FILE = FONT_DIR / "PxPlus_IBM_VGA_8x16.ttf"
FONT_FAMILY = "PxPlus IBM VGA 8x16"   # the family the file declares [confirmed: fonts/PROVENANCE.md]
_LOADED: dict = {}


def load_font() -> str:
    """Register the vendored font with Qt, from the package's own file, once per process; returns its family."""
    if "family" not in _LOADED:
        from PySide6.QtGui import QFontDatabase
        font_id = QFontDatabase.addApplicationFont(str(FONT_FILE))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if not families:
            raise RuntimeError(f"cannot load the window's font from {FONT_FILE}")
        _LOADED.update(id=font_id, family=families[0])
    return _LOADED["family"]


def font_id() -> int:
    load_font()
    return _LOADED["id"]


def stretch_percent(scale: float = 1.0) -> int:
    """The `QFont` stretch that keeps a glyph one cell (16 x `scale`) wide when its pixel size is the stretched one
    (`TEXT` x `STRETCH` x `scale`, rounded): a taller glyph does not widen. [derived: the font's advance is half its
    pixel size; confirmed: measured 2026-11-09, pixel size 38 with stretch 83 gives advance 16 and height 39]"""
    height = max(1, round(TEXT * STRETCH * scale))
    return max(1, round(100 * TEXT * scale / height))


def text_font(family: str = FONT_FAMILY, scale: float = 1.0):
    """The one text size as the 4:3 page draws it at `scale` (the page's width over 1440): the pixel size and the stretch
    of `stretch_percent`. A widget that sets its own font starts from this or from `widget.font()`, never from a bare
    `QFont(family)` (a bare font has stretch 100 and is wider than the page's cell)."""
    from PySide6.QtGui import QFont
    font = QFont(family)
    font.setPixelSize(max(1, round(TEXT * STRETCH * scale)))
    font.setStretch(stretch_percent(scale))
    return font


def install(app) -> str:
    """Make the vendored font the application's font, at the one text size on the 4:3 page; returns its family."""
    family = load_font()
    app.setFont(text_font(family))
    return family


def stylesheet(family: str = FONT_FAMILY) -> str:
    """The window's style sheet, composed for the 1440x896 page (90 x 28 cells); the page scales every px length with the window
    (goal2/desktop/fixed_page.py). The sizes and colours are the mockups' (docs/design/ui-2026-11/mockups/style.css):
    [designed: owner, 2026-11-03, #526]."""
    return f"""
* {{ font-family: "{family}"; font-size: {TEXT}px; color: {TEXT_BRIGHT}; }}
#page {{ background: {GROUND}; }}
#screen {{ background: {GROUND}; }}
#titleBar {{ background: {GROUND}; border-bottom: 2px solid {FRAME_DARK}; }}
#brand {{ color: {HEADING}; }}
#brandNote, #crumb, #sub, #muted {{ color: {TEXT_NORMAL}; }}
#brandNote {{ padding-top: 8px; }}
#who {{ color: {TEXT_BRIGHT}; }}
#keyBar {{ background: {GROUND}; border-top: 2px solid {FRAME_DARK}; }}
#keyLabel {{ color: {KEY_HINT}; }}
#kbd {{ color: {TEXT_BRIGHT}; background: {GROUND}; border: 1px solid {FRAME_DARK}; padding: 1px 7px; }}
#enterHint {{ background: {HIGHLIGHT}; border: 1px solid {HIGHLIGHT}; }}
#enterHint #enterText {{ color: {ON_HIGHLIGHT}; background: transparent; }}
#enterHint #kbd {{ color: {ON_HIGHLIGHT}; background: transparent; border: 1px solid {ON_HIGHLIGHT}; }}
#box {{ background: {GROUND}; border: 1px solid {FRAME_DARK}; }}
#boxHeading, #th {{ color: {HEADING}; }}
#benchMetadata {{ color: {TEXT_NORMAL}; }}
#benchCounter {{ border: 1px solid {FRAME}; padding: 6px 14px; }}
#th {{ border-bottom: 1px solid {FRAME_DARK}; padding: 4px 8px; }}
#td {{ border-bottom: 1px solid {FRAME_DARK}; padding: 4px 8px; }}
#td[check="good"] {{ color: {GOOD}; }}
#td[check="bad"] {{ color: {BAD}; }}
#td[check="none"] {{ color: {TEXT_NORMAL}; }}
#h1, #h2 {{ color: {TEXT_BRIGHT}; }}
#tag {{ color: {HEADING}; border: 1px solid {HEADING}; padding: 2px 8px; }}
#tagNew {{ color: {GOALKEEPER}; border: 1px solid {GOALKEEPER}; padding: 2px 8px; }}
#screen[grid="true"] #tagNew {{ color: {GOALKEEPER}; border: none; padding: 0px; }}
#screen[grid="true"] #tag {{ color: {HEADING}; border: none; padding: 0px; }}
#screen[grid="true"] #brandNote {{ padding: 0px; }}
#error {{ color: {BAD}; }}
#field {{ background: {GROUND}; border: 2px solid {FRAME}; }}
#option {{ background: {GROUND}; border: 1px solid {FRAME_DARK}; }}
#option[on="true"] {{ background: {HIGHLIGHT}; border: 1px solid {HIGHLIGHT}; }}
#option[on="true"] QLabel {{ color: {ON_HIGHLIGHT}; }}
#keyCap {{ color: {TEXT_BRIGHT}; }}
#enterBar {{ background: {HIGHLIGHT}; }}
#enterBar #enterText, #enterBar #keyCap {{ color: {ON_HIGHLIGHT}; background: transparent; }}
#gridOption, #gridLine {{ background: {GROUND}; }}
#gridOption QLabel {{ color: {HEADING}; }}
#gridLine QLabel {{ color: {GOALKEEPER}; }}
#gridOption[on="true"], #gridLine[on="true"] {{ background: {HIGHLIGHT}; }}
#gridOption[on="true"] QLabel, #gridLine[on="true"] QLabel {{ color: {ON_HIGHLIGHT}; }}
#waitBox {{ background: {GROUND}; border: 1px solid {HIGHLIGHT}; }}
#waitHead {{ color: {VALUE}; }}
#dialog {{ background: {GROUND}; border: 2px solid {HEADING}; }}
#helpText {{ background: {GROUND}; color: {TEXT_BRIGHT}; border: 1px solid {FRAME_DARK}; padding: 14px 16px; }}
"""
