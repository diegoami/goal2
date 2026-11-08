"""The new window's look: the original's palette by role, the vendored VGA font, the text sizes and the style sheet.

[designed: owner, 2026-11-03, #526, #536] The colours are the design's palette table, by role
(docs/design/ui-2026-11/README.md §3, read from the original's captures by palette.py); each constant below is one
row of that table, and the test checks them against the README itself. The font is "PxPlus IBM VGA 8x16" (CC BY-SA
4.0), vendored in `goal2/ui/fonts/` with its licence and provenance and loaded from there, never from a system
install. Text is 24 px (owner #598), with 32 px headings; the page scales as a whole with the window (docs/design/ui-2026-11 §3, "Text size").

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

# The text sizes: the font's 8x16 cell and its whole multiples. [designed: docs/design/ui-2026-11 §3, "Text size"]
CELL = 16
TEXT = 24   # [designed: owner #598] larger reading baseline
HEADING_SIZE = 2 * CELL

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


def install(app) -> str:
    """Make the vendored font the application's font, at the owner's 24 px baseline; returns its family."""
    from PySide6.QtGui import QFont
    family = load_font()
    font = QFont(family)
    font.setPixelSize(TEXT)
    app.setFont(font)
    return family


def stylesheet(family: str = FONT_FAMILY) -> str:
    """The window's style sheet, composed for the 1440x900 page; the page scales every px length with the window
    (goal2/desktop/fixed_page.py). The sizes and colours are the mockups' (docs/design/ui-2026-11/mockups/style.css):
    [designed: owner, 2026-11-03, #526]."""
    return f"""
* {{ font-family: "{family}"; font-size: {TEXT}px; color: {TEXT_BRIGHT}; }}
#page {{ background: {GROUND}; }}
#screen {{ background: {GROUND}; }}
#titleBar {{ background: {GROUND}; border-bottom: 2px solid {FRAME_DARK}; }}
#brand {{ color: {HEADING}; font-size: {HEADING_SIZE}px; }}
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
#benchMetadata {{ font-size: 20px; color: {TEXT_NORMAL}; }}
#benchCounter {{ border: 1px solid {FRAME}; padding: 6px 14px; }}
#th {{ border-bottom: 1px solid {FRAME_DARK}; padding: 4px 8px; }}
#td {{ border-bottom: 1px solid {FRAME_DARK}; padding: 4px 8px; }}
#td[check="good"] {{ color: {GOOD}; }}
#td[check="bad"] {{ color: {BAD}; }}
#td[check="none"] {{ color: {TEXT_NORMAL}; }}
#h1, #h2 {{ font-size: {HEADING_SIZE}px; color: {TEXT_BRIGHT}; }}
#tag {{ color: {HEADING}; border: 1px solid {HEADING}; padding: 2px 8px; }}
#tagNew {{ color: {GOALKEEPER}; border: 1px solid {GOALKEEPER}; padding: 2px 8px; }}
#error {{ color: {BAD}; }}
#field {{ background: {GROUND}; border: 2px solid {FRAME}; }}
#option {{ background: {GROUND}; border: 1px solid {FRAME_DARK}; }}
#option[on="true"] {{ background: {HIGHLIGHT}; border: 1px solid {HIGHLIGHT}; }}
#option[on="true"] QLabel {{ color: {ON_HIGHLIGHT}; }}
#waitBox {{ background: {GROUND}; border: 1px solid {HIGHLIGHT}; }}
#waitHead {{ color: {VALUE}; font-size: {HEADING_SIZE}px; }}
#dialog {{ background: {GROUND}; border: 2px solid {HEADING}; }}
#helpText {{ background: {GROUND}; color: {TEXT_BRIGHT}; border: 1px solid {FRAME_DARK}; padding: 14px 16px; }}
"""
