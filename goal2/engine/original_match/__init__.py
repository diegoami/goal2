"""original_match: the original goal (version 2)'s watched match, run interactively on goal2's own state.

Self-contained (the standard library and `unicorn`), vendorable as one folder, holding no byte of the original:
the original's code and data come from an image goal2 already holds or fetches by hash (assets.py). See README.md.

    from original_match import Image, Match, Fixture
    m = Match(Image.from_memory_component(state.mem), Fixture(first=7, second=19), managed=7)
    for ev in m.events():
        if ev.kind == "decision":
            m.answer(substitutions=[(off, on)], tactics={4: True})
    result = m.result()
"""
from .image import Image
from .machine import GuestError
from .match import Match, Fixture, Event, MatchError, VERSION
from .screens import ScreenError

__all__ = ["Image", "Match", "Fixture", "Event", "MatchError", "GuestError", "ScreenError", "VERSION"]
