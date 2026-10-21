"""[designed: owner, 2026-10-21; #295] Localized names for the national pool.

[confirmed: F002 R003, F007] The original's 80-player pool is always records 2561..2640 of
GOAL.DAT, given the managed country's number but one fixed list of mostly English surnames. By
the owner's choice the rebuild names that pool, for the 32 best-ranked countries in GOAL.DAT,
with common surnames of the nation (goal2/data/pool_names.json, written for the rebuild; not
real players). The names follow the managed country and are never saved: a save made before
this change shows them too, and T92 renames still apply on top (goal2.game.identities).
"""
from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path

FIRST, COUNT = 2561, 80
PATH = Path(__file__).resolve().parents[1] / 'data' / 'pool_names.json'


@lru_cache(maxsize=1)
def table():
    """{country number: (country name, 80 surnames, 80 initials)}."""
    data = json.loads(PATH.read_text(encoding='utf-8'))['countries']
    return {int(n): (e['country'], tuple(e['surnames']), tuple(e['initials'])) for n, e in data.items()}


def localize(goaldat, country):
    """GOAL.DAT with the pool records named for `country`; the same object for an unlisted one."""
    entry = table().get(country)
    if entry is None:
        return goaldat
    name, surnames, initials = entry
    if goaldat.country_names[country] != name:
        # [designed] A GOAL.DAT whose country names differ (an ALTER-edited file) keeps its own.
        return goaldat
    names = list(goaldat.player_names);letters = list(goaldat.player_initials)
    names[FIRST:FIRST + COUNT] = surnames;letters[FIRST:FIRST + COUNT] = initials
    return replace(goaldat, player_names=names, player_initials=letters)
