"""Plain-text renderer for the character grid.

[designed: the renderer is for tests and logs, not the user; colour is
omitted in the rendered output — the grid still holds the colour so a
later window renderer can use it.]
"""
from goal2.ui.grid import Grid, HEIGHT, WIDTH


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
