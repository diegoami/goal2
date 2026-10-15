"""Plain-text renderer for the character grid.

[designed: T23 uses this renderer for interactive stdout frames as well as
tests and logs. Colour is omitted in the rendered output; the grid still
holds the colour so a later window renderer can use it.]
"""
from goal2.ui.grid import Grid, HEIGHT, WIDTH
import os
import sys
from typing import TextIO


def render(grid: Grid) -> str:
    """Render the grid as a plain string.

    Each row is 80 characters followed by a newline (25 lines total,
    terminated with a trailing newline: 25 rows × (80 + 1) = 2025 chars).
    Colour is omitted; the returned string contains only the character
    data.
    [designed: 25 lines × (80 + 1) = 2025 chars; char code 0 (null) is
    rendered as a space so a fresh grid reads as 25 blank rows. The
    trailing newline means `split("\n")[:25]` collects the 25 rows.]
    """
    lines: list[str] = []
    for r in range(HEIGHT):
        row_chars = []
        for c in range(WIDTH):
            char_code = grid.cell(r, c)[0]
            # Char code 0 (null) renders as a space in plain text
            row_chars.append(chr(char_code) if char_code != 0 else " ")
        lines.append("".join(row_chars))
    return "\n".join(lines) + "\n"


def display(grid: Grid, stream: TextIO | None = None) -> None:
    """Write one frame, redrawing in place on an ANSI-capable terminal.

    [designed: T31] Interactive terminals clear and home before each frame;
    redirected and dumb-terminal output remains the plain append-only frame.
    The terminal frame omits its last newline so row 25 does not scroll.
    """
    output = sys.stdout if stream is None else stream
    frame = render(grid)
    is_terminal = output.isatty() and os.environ.get("TERM", "") not in ("", "dumb")
    if is_terminal:
        output.write("\x1b[2J\x1b[H" + frame.rstrip("\n"))
    else:
        output.write(frame)
    output.flush()
