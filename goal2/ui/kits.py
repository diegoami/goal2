"""The two sides' kit colours, as the original computes them at kick-off.

[confirmed: 0791:1073, goal2/engine/original_match/port/setup.py `kit_colours`; #583] Each country has three colour
bytes at `DS:9D80 + 3·country` (GOAL.DAT R007). Team 0's shirt is its first byte and team 1's its first byte; their
second colours (the keepers', `0791:045D`/`0691`) are the third bytes. When the shirts are equal, team 0 takes its
second byte; otherwise, when team 1's shirt equals team 0's second colour, that second colour becomes team 0's
second byte. Then, when team 0's shirt equals team 1's second colour, that becomes team 1's second byte. With
`DS:A964` set, the fixed 4, 1, 0xC and 9.

[confirmed: t156-045-kick-off.png, Holland (team 0) away to Norway: both first bytes are 12 (light red), so Holland
plays in its second byte, 15 (white); Norway's keeper is yellow (14) and Holland's blue (9)] Team 0 is the fixture's
side A and team 1 its side B, the home side (`pitch.HOME`, #562).

The bytes are read from the game's own memory (the template image), never from a table of goal2's.
"""
from __future__ import annotations

from dataclasses import dataclass

# The DOS text palette by index, and the colours' names [confirmed: goal2/desktop/pygame_viewer.py `DOS_PALETTE`,
# the VGA default palette].
DOS = ("#000000", "#0000aa", "#00aa00", "#00aaaa", "#aa0000", "#aa00aa", "#aa5500", "#aaaaaa",
       "#555555", "#5555ff", "#55ff55", "#55ffff", "#ff5555", "#ff55ff", "#ffff55", "#ffffff")
NAMES = ("BLACK", "BLUE", "GREEN", "CYAN", "RED", "MAGENTA", "BROWN", "GREY",
         "DARK GREY", "LIGHT BLUE", "LIGHT GREEN", "LIGHT CYAN", "LIGHT RED", "LIGHT MAGENTA", "YELLOW", "WHITE")
TABLE = 0x9D80
SPECIAL = 0xA964


@dataclass(frozen=True)
class Kits:
    """Palette indices by team (0, 1): the shirts and the second colours (the keepers')."""
    shirt: tuple
    keeper: tuple

    def colour(self, team: int, keeper: bool = False) -> str:
        return DOS[(self.keeper if keeper else self.shirt)[team]]

    def name(self, team: int) -> str:
        return NAMES[self.shirt[team]]


def compute(read, team0: int, team1: int) -> Kits:
    """`read(offset)` is a byte of the game's DS. The rule of 0791:1073, step for step."""
    if read(SPECIAL) != 0:
        return Kits(shirt=(4, 1), keeper=(0xC, 9))

    def kit(country, k):
        return read(TABLE + 3 * country + k)
    shirt1, second1 = kit(team1, 0), kit(team1, 2)
    shirt0, second0 = kit(team0, 0), kit(team0, 2)
    if shirt1 == shirt0:
        shirt0 = kit(team0, 1)
    elif shirt1 == second0:
        second0 = kit(team0, 1)
    if shirt0 == second1:
        second1 = kit(team1, 1)
    return Kits(shirt=(shirt0, shirt1), keeper=(second0, second1))


def for_fixture(model, fixture) -> Kits:
    """The kits of a fixture: side A is team 0, side B team 1, read from the model's template image."""
    from goal2.engine.original_match.image import Image
    image = Image.from_savestate(bytes(model.template_bytes))
    return compute(lambda off: image.rd(off, 1), fixture.side_a, fixture.side_b)
