"""Pure readers of the core's memory: the manager's desk, the fixture list, the tournament and the history (T105, #308's G11).

[designed: owner, 2026-10-22, #308, #321] goal2's pages read everything from the original's memory. Each function
here takes the memory at a wait (a `KeyWait.state`, or the kit's `Image`) and returns plain data; it never reads the
text page (the text is only the tests' oracle) and never writes a byte.

Evidence, goal2-archaeology at 53d7ef5 (static/goal-exe/annotations/globals.tsv and fields.tsv, the named listings
named/seg_*.c; the vendored kit's `Image`, PROVENANCE.md). [confirmed] cites the routine that draws the field:
- [confirmed: routines.tsv 2139:0000] the name arrays are far pointers DS:9B68 (country names, 16-byte Pascal
  records by country, 1771:0F58), DS:9B6C (player surnames, 11 bytes, 1771:2E93), DS:9B70 (player initials),
  DS:9B74 (manager surnames, 13 bytes) and DS:9B78 (manager initials) (1771:0947, F024 section 5).
- [confirmed: globals.tsv, fields.tsv; F007, F011, F023] DS:A917 countries (0xBF bytes: +0x2A continent rank,
  +0x2B world rank, +0x2C continent, +0x2E manager), DS:A91F manager_countries (manager m's country at
  3 * (0x80 + m), its rating byte at +1), DS:A923 the game record (+0 the number of managers, +1 the current
  manager, +0x26 the fixture index, +0x28 the fixture count, +0x38 the year word, +0x3A the start year, +0x3C the
  stage, +0x40 the class, +0x47 + m sacked), DS:A92B fixtures (8 bytes: +0 mark or score, +1 score, +2 kind,
  +3 result, +4 and +6 the countries), DS:A92F country_fixture_lists (36 words per country), DS:A933 group_tables.
- Strings the original prints are read from its own memory where its code keeps them (the kind names of 1771:580B,
  the continent names DS:6E92, home and away DS:6EBA, ...), never written into goal2.
"""
from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager

from goal2.engine.original_match.image import Image
from goal2.core.runner import CP437_LOW

# [designed: T136] Pure display calls may resolve identities; original driver/oracle reads default to raw names.
_display_names = ContextVar('goal2_display_names', default=None)


@contextmanager
def display_player_names(resolver):
    token = _display_names.set(resolver)
    try:
        yield
    finally:
        _display_names.reset(token)

# [confirmed: globals.tsv; image.py] the far pointers
COUNTRIES, COUNTRY_SIZE, MANAGERS, GAME, FIXTURES, FIXTURE_LISTS, GROUP_TABLES = (
    0xA917, 0xBF, 0xA91F, 0xA923, 0xA92B, 0xA92F, 0xA933)
PLAYERS, PLAYER_SIZE, POOL_INDICES, POOL_BASE = 0xA91B, 0x14, 0xA927, 0x6D18
COUNTRY_NAMES, PLAYER_NAMES, PLAYER_INITIALS, MANAGER_NAMES, MANAGER_INITIALS = 0x9B68, 0x9B6C, 0x9B70, 0x9B74, 0x9B78
CLASS_FIRST_FIXTURE = 0x6936          # word[2] (globals.tsv, F023): 1 and 1361
# [confirmed: goal2/game/roles.py, F002 R011, F028] the position code table and the line of each position
CODE_TABLE, LINE_TABLE = 0x69A8, 0x0D5C
LINES = ("goalkeeper", "defence", "midfield", "attack")
# [confirmed: named/seg_1771_04.c f_1771_580B] the kind names, Pascal strings in code segment 1771, by fixture kind
KIND_NAMES = ((0, 0x577F), (1, 0x5789), (2, 0x5792), (5, 0x5792), (6, 0x579D), (3, 0x57A6), (7, 0x57A6),
              (200, 0x57B2), (0x65, 0x57BC), (0xC9, 0x57BC), (0x67, 0x57C7), (0xCB, 0x57C7), (0x66, 0x57CD),
              (0xCA, 0x57CD), (8, 0x57D7), (0xFC, 0x57DF), (0xFD, 0x57E6), (0xFE, 0x57EC), (0xFF, 0x57F7))
KIND_OTHER = 0x57FF
FINALS_STAGES = (3, 4, 7, 8)          # [confirmed: stage_uses_finals_table 1771:59D8, the set CS:59B8]
KNOCKOUT_STAGES = (4, 8)              # [confirmed: 1771:958D, the set CS:956D = bytes 10 01]


class Memory:
    """Reads of the original's memory through the kit's Image (`state` is a StateView or an Image)."""

    def __init__(self, state):
        self.image = state if isinstance(state, Image) else state._image
        self.mem, self.ds, self.load = self.image.memory, self.image.DS, self.image.load

    def byte(self, a):
        return self.mem[a]

    def word(self, a):
        return self.mem[a] | self.mem[a + 1] << 8

    def ds_byte(self, off):
        return self.byte(self.ds * 16 + off)

    def ds_word(self, off):
        return self.word(self.ds * 16 + off)

    def far(self, ptr):
        return self.image.far(ptr)

    def pstr(self, a, limit=255):
        n = min(self.mem[a], limit)
        return bytes(self.mem[a + 1:a + 1 + n]).decode("cp437")

    def code_str(self, segment, off):
        """A Pascal string the original keeps in its code segment `segment` (the listing's number)."""
        return self.pstr(((self.load + segment) & 0xFFFF) * 16 + off)

    # -- records ----------------------------------------------------------------------------------------
    def country(self, n, off, size=1):
        a = self.far(COUNTRIES) + COUNTRY_SIZE * n + off
        return self.byte(a) if size == 1 else self.word(a)

    def country_name(self, n):
        """1771:0F58 draw_country_name: DS:9B68 + 16 n (blank for 0)."""
        return self.pstr(self.far(COUNTRY_NAMES) + 16 * n, 15) if n else ""

    def raw_player_name(self, w):
        """1771:2E93 player_name: the initial [DS:9B70] + w, a space, the surname [DS:9B6C] + 11 w."""
        surname = self.pstr(self.far(PLAYER_NAMES) + 11 * w, 10)
        return f"{chr(self.byte(self.far(PLAYER_INITIALS) + w))} {surname}"

    def display_player_name(self, w, original):
        """[designed: T136] Resolve an identified full name; unidentified history copies stay raw."""
        resolver = _display_names.get()
        return original if resolver is None or w is None else resolver(w, original)

    def player_name(self, w):
        return self.display_player_name(w, self.raw_player_name(w))

    def copied_player_name(self, w, original):
        """[designed: T136] A stale copied name must not acquire another player's alias."""
        # [derived: F002/F007] 2560 national records and500 unassigned names end at3060.
        if _display_names.get() is None or not 1 <= w <= 3060:
            return original
        return (self.display_player_name(w, original)
                if original == self.raw_player_name(w) else original)

    def player_surname(self, w, original):
        """[designed: T136] Commentary keeps surname formatting, with full-name rename intent."""
        if not w:
            return original
        raw = self.raw_player_name(w)
        display = self.display_player_name(w, raw)
        return original if display == raw else (display.partition(' ')[2] or display)

    def game(self, off, size=1):
        a = self.far(GAME) + off
        return self.byte(a) if size == 1 else self.word(a)

    def fixture(self, n):
        a = self.far(FIXTURES) + 8 * n - 8
        rec = bytes(self.mem[a:a + 8])
        return {"number": n, "mark": rec[0], "score_b": rec[1], "kind": rec[2], "result": rec[3],
                "b": rec[4] | rec[5] << 8, "a": rec[6] | rec[7] << 8}

    def kind_name(self, kind):
        """1771:580B: the fixture kind's word."""
        return self.code_str(0x1771, dict(KIND_NAMES).get(kind, KIND_OTHER))

    def manager_name(self, m):
        """1771:0947(m): the initial [DS:9B78] + m, the string at 1771:0945, the surname [DS:9B74] + 13 m; 14 at
        most."""
        text = (chr(self.byte(self.far(MANAGER_INITIALS) + m)) + self.code_str(0x1771, 0x0945)
                + self.pstr(self.far(MANAGER_NAMES) + 13 * m))
        return text[:14]

    def manager_country(self, m):
        return self.byte(self.far(MANAGERS) + 3 * m)


def _rankings(mem, country):
    """000E:715E: the continent's name DS:6E92 + 8 * continent, the world rank +0x2B and the continent rank +0x2A."""
    return {"country": country, "name": mem.country_name(country),
            "continent": mem.pstr(mem.ds * 16 + 0x6E92 + 8 * mem.country(country, 0x2C)),
            "world_rank": mem.country(country, 0x2B), "continent_rank": mem.country(country, 0x2A)}


def next_fixture(mem):
    """1771:55FC find_next_managed_fixture, as the manager menu calls it at each draw (000E:724A): 0 for a sacked
    manager; else the first of the trailing run of the country's list entries whose fixture's +0 >= 0xFE and that
    are >= the fixture index +0x26 (0 when none)."""
    m = mem.game(1)
    if mem.game(0x47 + m):
        return 0
    country = mem.manager_country(0x80 + m)
    base = mem.far(FIXTURE_LISTS) + 0x48 * country
    entry = [mem.word(base + 2 * i) for i in range(36)]
    k = 36
    while k and mem.fixture(entry[k - 1])["mark"] > 0xFD and mem.game(0x26, 2) <= entry[k - 1]:
        k -= 1
    return 0 if k == 36 else entry[k]


def squad(mem, country):
    """draw_squad_list's twenty (main_menu_loop): each player's word, initial and surname, and his position +6 with
    the original's code DS:69A8 and line DS:0D5C [confirmed: goal2/game/roles.py]."""
    rows = []
    for slot in range(20):
        w = mem.country(country, 2 * slot, 2)
        p = mem.byte(mem.far(PLAYERS) + PLAYER_SIZE * w + 6)
        code = bytes([mem.ds_byte(CODE_TABLE + p)]).decode("cp437") if p < 14 else "?"
        line = LINES[mem.ds_byte(LINE_TABLE + p)] if p < 14 else "unknown"
        rows.append({"player": w, "name": mem.player_name(w), "position": p, "code": code, "line": line})
    return rows


def desk(state):
    """The manager's desk: what the manager menu (main_menu_loop 000E:7439 and 000E:724A) shows.

    [confirmed: named/seg_000E_05.c f_000E_724A, main_menu_loop; seg_1771_01.c 1771:0947, 1771:0AF8;
    seg_1771_04.c 1771:5BF6, 1771:5AC4, 1771:580B] The current manager m (+1), his name (1771:0947(0x80 + m)), his
    rating (1771:0AF8: the byte [DS:A91F] + 3 (0x80 + m) + 1; 0 prints the string 1771:0AF0, else
    DS:6EB4 + 16 * DS:7894[(rating - 1) / 8]), his country and its rankings (000E:715E), the next fixture
    (1771:55FC) with the opponent (the side that is not his country), its rankings and the fixture's kind (1771:580B
    of +2, then, for a kind not 0 that is a friendly or outside the finals tables, the string 000E:7248 and
    DS:6EBA + 5 when his country is +6, else DS:6EBA: "home", "away"), the managers 1.. +0 with a country, and the
    year and stage word of the title (1771:5AC4: +0x38 * 2 + +0x3A - 2 when +0x40 differs from stage > 4;
    DS:0F5E + 11 * finals)."""
    mem = Memory(state)
    m = mem.game(1)
    country = mem.manager_country(0x80 + m)
    rating = mem.byte(mem.far(MANAGERS) + 3 * (0x80 + m) + 1)
    rating_text = (mem.code_str(0x1771, 0x0AF0) if rating == 0
                   else mem.pstr(mem.ds * 16 + 0x6EB4 + 16 * mem.ds_byte(0x7894 + (rating - 1) // 8)))
    stage = mem.game(0x3C)
    finals = stage in FINALS_STAGES
    year = mem.game(0x38, 2) * 2 + mem.game(0x3A, 2) - 2 * (mem.game(0x40) != (stage > 4))
    sacked = bool(mem.game(0x47 + m))
    out = {"manager_number": m, "manager": mem.manager_name(0x80 + m), "rating": rating_text,
           "team": _rankings(mem, country), "sacked": sacked, "year": year, "stage": stage,
           "stage_word": mem.pstr(mem.ds * 16 + 0x0F5E + 11 * finals), "squad": squad(mem, country),
           "opponent": None, "fixture": None, "fixture_kind": "",
           "managers": []}
    for n in range(1, mem.game(0) + 1):
        if mem.manager_country(0x80 + n):
            out["managers"].append({"number": n, "name": mem.manager_name(0x80 + n),
                                    "country": mem.manager_country(0x80 + n)})
    if sacked:
        return out             # the menu draws the SACKED template (DS:591E) instead of the rankings and fixture
    n = next_fixture(mem)
    if n:
        f = mem.fixture(n)
        other = f["a"] if f["a"] != country else f["b"]
        text = mem.kind_name(f["kind"])[:0x14]
        if f["kind"] != 0 and (f["kind"] == 1 or not finals):
            text = (text + mem.code_str(0x000E, 0x7248) + mem.pstr(mem.ds * 16 + 0x6EBA + 5 * (f["a"] == country)))[:0x14]
        out.update(fixture=n, opponent=_rankings(mem, other), fixture_kind=text)
    return out


def _row(mem, f):
    """A fixture as 1771:7812 and 1771:77C3 draw it: the side +6 first, the side +4 second, the kind's word, the
    mark (+0 = 0xFE with a kind), and for a played fixture (+0 < 0xFE with a kind, 1771:76FA) the score, +1 for the
    first side and +0 for the second."""
    played = f["kind"] != 0 and f["mark"] < 0xFE
    return {"number": f["number"], "kind": f["kind"], "kind_name": mem.kind_name(f["kind"]),
            "first": f["a"], "second": f["b"], "first_name": mem.country_name(f["a"]),
            "second_name": mem.country_name(f["b"]), "mark": f["mark"] == 0xFE and f["kind"] != 0,
            "played": played, "score": (f["score_b"], f["mark"]) if played else None}


def fixture_list(state):
    """The fixture list (000E:0000): the fixtures from the index +0x26 (from the class's first fixture DS:6938 when
    the class +0x40 is set, the year word +0x38 is 0 and the index is below it) to the count +0x28 less one, each as
    the row 1771:7812 draws ([confirmed: named/seg_000E_01.c f_000E_0000; seg_1771_05.c 7812, 77C3, 76FA])."""
    mem = Memory(state)
    start = mem.game(0x26, 2)
    if mem.game(0x40) and mem.game(0x38, 2) == 0 and start < mem.ds_word(CLASS_FIRST_FIXTURE + 2):
        start = mem.ds_word(CLASS_FIRST_FIXTURE + 2)
    last = mem.game(0x28, 2) - 1
    return {"first": start, "rows": [_row(mem, mem.fixture(n)) for n in range(start, last + 1)]}


def tournament(state, country=None, world=None, display=None):
    """The tournament (1771:958D from the manager menu, the managed country's): which display it opens and, for the
    qualifying display's regional tables or the current finals groups.

    [confirmed: named/seg_1771_07.c 1771:958D; seg_1771_06.c 1771:8E9A, 8A87, 8CA2] The display is 1 (qualifying)
    + 1 when the stage is in the finals tables (3, 4, 7, 8) + 1 when it is a knockout stage (4, 8); the class is
    +0x40. Group g's slot s (1..4) is 8 bytes at [DS:A933] + 8 s + 0x38 g + 0x1C0 continent + 0x700 table
    + 0xE00 class - 0x200: the country word, W, D, L, F, A, T (P = W + D + L); its fixtures are the twelve words
    at [DS:A933] + 2 k + 0x38 g + 0x1C0 continent + 0xE00 class - 0x1DA. [confirmed: 9028, 8A87; T111]
    Finals add 0x700 and use six fixtures; 1136/1137 give two/eight groups. World finals use country 1's
    continent and top-scorer region 5 (9028/883F; T113). [designed] The stage-6 play-off view (group 9,
    1771:8D84) awaits its evidence; `groups` is then None. Knockout data is returned as `bracket`."""
    mem = Memory(state)
    m = mem.game(1)
    stage = mem.game(0x3C)
    klass = mem.game(0x40) if world is None else int(world)
    display = (1 + (stage in FINALS_STAGES) + (stage in KNOCKOUT_STAGES) if display is None
               else ("qualifying", "finals", "championship").index(display) + 1)
    # [confirmed: 958D 95AD, 9028 at 53d7ef5; T113] World finals use country 1's shared table, regardless
    # of the manager's continent; 9028 temporarily forces it even after Space selects another continent.
    country = (1 if klass and display > 1 else mem.manager_country(0x80 + m)) if country is None else country
    if klass and display == 2:country = 1
    continent = mem.country(country, 0x2C)
    out = {"display": ("qualifying", "finals", "championship")[display - 1], "stage": stage, "class": klass,
           "continent": mem.pstr(mem.ds * 16 + 0x6E92 + 8 * continent), "country": country, "groups": None}
    if display == 3:
        out['bracket'] = bracket(state, country, world=bool(klass))
        return out
    if stage == 6:
        return out
    # [confirmed: named/seg_1771_06.c 9028, 8A87] Continental finals use table 1 and six fixtures per group.
    table = int(display == 2)
    if table:out['top_scorers'] = competition_scorers(mem, 5 if klass else continent)
    last_group = mem.ds_byte(0x1136 + klass) if table else 8
    tables = mem.far(GROUP_TABLES)
    groups = []
    for g in range(1, last_group + 1):
        base = tables + 0x38 * g + 0x1C0 * continent + 0xE00 * klass + 0x700 * table - 0x200
        rows = []
        for s in range(1, 5):
            r = bytes(mem.mem[base + 8 * s:base + 8 * s + 8])
            c = r[0] | r[1] << 8
            rows.append({"country": c, "name": mem.country_name(c), "played": r[2] + r[3] + r[4], "won": r[2],
                         "drawn": r[3], "lost": r[4], "for": r[5], "against": r[6], "points": r[7]})
        if not any(r["country"] for r in rows):
            continue
        fixtures = [mem.word(tables + 2 * k + 0x38 * g + 0x1C0 * continent + 0xE00 * klass + 0x700 * table - 0x1DA)
                    for k in range(1, 7 if table else 13)]
        groups.append({"group": chr(0x40 + g), "number": g, "rows": rows,
                       "fixtures": [_row(mem, mem.fixture(n)) for n in fixtures if n]})
    out["groups"] = groups
    return out


def competition_scorers(mem, region):
    """[confirmed: named/seg_1771_06.c 883F at 53d7ef5] Three copied initial/surname/goals/player records."""
    top = []
    for k in range(3):
        a = mem.far(0xA93F) + (region - 1) * 0x60 + 16 * k
        if mem.word(a + 14):
            player = mem.word(a + 14)
            original = chr(mem.byte(a)) + ' ' + mem.pstr(a + 1, 10)
            top.append(dict(player=player, name=mem.copied_player_name(player, original),
                            goals=mem.word(a + 12)))
    return top


def bracket(state, country=None, world=None):
    """[confirmed: named/seg_1771_07.c 91CE, 9509; seg_1771_06.c 8CCF, 883F; F023 at 53d7ef5]
    Continental knockout fixtures 7..10 of the continent's table, their stored winner selectors and original
    draw coordinates. Top scorers are copied records at A93F, not inferred from current player names.
    [confirmed: 937C/9509, 5AC4; T113 captures] World slots read the knockout start +2A, use their own
    coordinate tables and top-scorer region 5. No match is simulated here."""
    mem = Memory(state)
    world = bool(mem.game(0x40)) if world is None else bool(world)
    if country is None:country = 1 if world else mem.manager_country(0x80 + mem.game(1))
    region = mem.country(country, 0x2C)
    base = mem.far(GROUP_TABLES) + 0x1C0 * region
    matches = []
    if world:
        slots = [dict(slot=k, x=mem.ds_byte(0x1159+k), y=mem.ds_byte(0x1149+k),
                      score_x=mem.ds_byte(0x1179+k), score_y=mem.ds_byte(0x1169+k)) for k in range(1,17)]
        start = mem.game(0x2A,2)
        # [confirmed: code/seg_1771_13.asm 935C, 93B3-942C] Stages 5/6/7 hide the World knockout data.
        ready = mem.game(0x3C) not in (5,6,7) and bool(start)
        numbers = [(s, start+s['slot']-1) for s in slots
                   if not mem.game(0x40) or start+s['slot'] <= mem.game(0x28,2)]
        final,third = start+15,start+14
        places_ready = ready and (not mem.game(0x40) or mem.game(0x28,2)-start==16)
    else:
        slots = [dict(slot=k, x=mem.ds_byte(0x1142+(k>8)), y=mem.ds_byte(0x1137+k),
                      score_x=mem.ds_byte(0x1148+(k>8)), score_y=mem.ds_byte(0x113D+k)) for k in range(7,11)]
        ready = mem.game(0x3C)>3
        numbers = [(s,mem.word(base+0x55E+2*s['slot'])) for s in slots]
        final,third = mem.word(base+0x572),mem.word(base+0x570)
        places_ready = ready
    if ready:
        for slot,number in numbers:
            if not number:continue
            raw = mem.fixture(number)
            if not raw['kind']:continue
            row = _row(mem, raw)
            row.update(**slot, winner=(raw['a'] if raw['result']==1 else raw['b']) if row['played'] else None)
            matches.append(row)
    places = []
    if places_ready and final and mem.fixture(final)['mark'] < 0xFE:
        f = mem.fixture(final)
        winner, loser = (f['a'], f['b']) if f['result'] == 1 else (f['b'], f['a'])
        t = mem.fixture(third)
        countries = [winner, loser, t['a'] if t['result'] == 1 else t['b']]
        places = [dict(place=i+1, country=c, name=mem.country_name(c)) for i,c in enumerate(countries)]
    # [confirmed: 937C 947A-94FF; T113 final wait] The World places template replaces the top-scorer panel.
    top = [] if world and places else competition_scorers(mem,5 if world else region)
    # [confirmed: named/seg_1771_04.c 5AC4 at 53d7ef5] The title subtracts two when +40 differs from the
    # displayed competition (9509), including browsing the previous competition.
    year = mem.game(0x3A, 2) + 2 * mem.game(0x38, 2) - 2 * (mem.game(0x40) != int(world))
    return dict(country=country, world=world, continent=mem.pstr(mem.ds * 16 + 0x6E92 + 8 * region), year=year,
                matches=matches, slots=slots, top_scorers=top, places=places,
                winner_mark=mem.code_str(0x1771,0x8CCD))


def _top(mem, country, goals):
    """1771:1B2E over the country's twenty (and, for a managed country, its manager's 80 pool players), from the
    manager's kept table at [DS:A93B] (goals) or [DS:A937] (caps) + 0x8C (e - 1), or from an empty table for a
    computer country: each player's count (+0xA goals, +8 caps) goes in before the first entry whose count is not
    above it, the entries from there move down one and the tenth drops. [confirmed: named/seg_1771_02.c 1D5C, 1B2E]
    The history computes these tables on display and puts the kept ones back before its key read, so memory at the
    wait holds no copy: the view runs the same insertion over the same records."""
    managed = mem.country(country, 0x2E) > 0x80
    e = mem.country(country, 0x2E) - 0x80 if managed else 1
    table = []
    base = mem.far(0xA93B if goals else 0xA937) + 0x8C * (e - 1)
    for i in range(10):
        a = base + 0xE * i
        # Kept records have no full ID: preserve their copied names without guessing identity.
        table.append((chr(mem.byte(a)), mem.pstr(a + 1, 10), mem.word(a + 0xC), None)
                     if managed else ("\0", "", 0, None))
    words = [mem.country(country, 2 * s, 2) for s in range(20)]
    if managed:
        first = mem.ds_word(POOL_BASE + 2 * e)
        words += [mem.word(mem.far(POOL_INDICES) + 2 * i) for i in range(first, first + 0x50)]
    players = mem.far(PLAYERS)
    for w in words:
        value = mem.word(players + PLAYER_SIZE * w + (0xA if goals else 8))
        for i in range(10):
            if table[i][2] <= value:
                table[i + 1:] = table[i:9]
                table[i] = (chr(mem.byte(mem.far(PLAYER_INITIALS) + w)),
                            mem.pstr(mem.far(PLAYER_NAMES) + 11 * w, 10), value, w)
                break
    sep = mem.code_str(0x1771, 0x1D5A)
    out = []
    for initial, surname, count, player in table:
        if count:
            original = initial + ' ' + surname
            display = mem.display_player_name(player, original)
            if display == original:
                shown = initial + sep + surname
            else:
                first, space, family = display.partition(' ')
                shown = first + sep + family if space else display
            out.append({"name": shown, "count": count})
    return out


def history(state, country=None):
    """A country's history (1771:1D5C), the managed country's by default, as main_menu_loop's item 4 opens it.

    [confirmed: named/seg_1771_02.c 1771:1D5C, 1C85; seg_1771_05.c 76FA] The successes: two rows of places 1..4,
    the bytes +0x33.. and +0x37.. The results: entries k = 1..10 of 6 bytes at
    +0x35 + 6 k, present up to the last whose +0 is not 0, shown newest first: the season ending in the year
    +0x3A + 2 (+0x38 - k + 1) (1C85), the competition (the string 1771:1D55 in a world cup year, year mod 4 = 2,
    else the letter DS:0DB2 [continent is 1] and the string 1771:1D58), W, D, L, F, A, and the best place (1771:580B
    of +0). The records: wins and defeats at home, away and neutral, 8-byte fixtures at +0x77 + 8 k + 0x18 f, shown
    when their +6 is not 0: the score as 76FA draws it and the opponent(s). The statistics: consecutive wins,
    defeats, games without a win and without defeat, the bytes +0xA7, +0xAD, +0xB3, +0xB9 [k + 3 f], in the
    screen's column order (DS:0DAF[k] - DS:0DAD[f]). Successes and records are placed by their tables likewise (below).
    The top scorers and top caps: `_top`."""
    mem = Memory(state)
    if country is None:
        country = mem.manager_country(0x80 + mem.game(1))
    continent = mem.country(country, 0x2C)
    # The two rows are drawn at the rows DS:0DA2[f]; the template's upper row is the world cup's (WC), the lower the
    # championship's (CH) [derived: the screen's labels, checked by goal2/tests/test_core_desktop_t105.py].
    upper, lower = sorted(range(2), key=lambda f: mem.ds_byte(0x0DA2 + f))
    successes = {"world_cup": [mem.country(country, 0x33 + 4 * upper + i) for i in range(4)],
                 "championship": [mem.country(country, 0x33 + 4 * lower + i) for i in range(4)]}
    last = max([k for k in range(1, 11) if mem.country(country, 0x35 + 6 * k)] or [0])
    results = []
    for k in range(last, 0, -1):
        r = [mem.country(country, 0x35 + 6 * k + i) for i in range(6)]
        year = mem.game(0x3A, 2) + 2 * (mem.game(0x38, 2) - k + 1)
        season = f"{year - 1}{mem.code_str(0x1771, 0x1C83)}{year % 100:02d}"
        competition = (mem.code_str(0x1771, 0x1D55) if year % 4 == 2
                       else chr(mem.ds_byte(0x0DB2 + (continent == 1))) + mem.code_str(0x1771, 0x1D58))
        results.append({"season": season, "competition": competition, "won": r[1], "drawn": r[2], "lost": r[3],
                        "for": r[4], "against": r[5], "best": mem.kind_name(r[0])})
    # A record f, k is drawn at the column DS:0DA8[f] and the row DS:0DAA[k]; the template's columns are wins then
    # defeats, its rows home, away, neutral [derived: the screen's labels, checked as above].
    records = {"wins": {}, "defeats": {}}
    columns_f = sorted(range(2), key=lambda f: mem.ds_byte(0x0DA8 + f))
    rows_k = sorted(range(3), key=lambda k: mem.ds_byte(0x0DAA + k))
    for f, what in zip(columns_f, ("wins", "defeats")):
        for k, where in zip(rows_k, ("home", "away", "neutral")):
            off = 0x77 + 8 * k + 0x18 * f
            a = mem.far(COUNTRIES) + COUNTRY_SIZE * country + off
            raw = bytes(mem.mem[a:a + 8])
            sides = (raw[4] | raw[5] << 8, raw[6] | raw[7] << 8)
            entry = None
            if sides[1]:
                shown = raw[2] != 0 and raw[0] < 0xFE
                entry = {"score": (raw[1], raw[0]) if shown else None,
                         "opponents": [mem.country_name(s) for s in sides if s != country]}
            records[what][where] = entry
    columns = sorted(((mem.ds_byte(0x0DAF + k) - mem.ds_byte(0x0DAD + f), k, f) for k in range(3) for f in range(2)))
    # [derived] the template's columns, left to right: home, away, all, each now then top.
    statistics = {}
    for name, off in (("consecutive wins", 0xA7), ("consecutive defeats", 0xAD), ("games without a win", 0xB3),
                      ("games without defeat", 0xB9)):
        statistics[name] = [mem.country(country, off + k + 3 * f) for _, k, f in columns]
    return {"country": country, "name": mem.country_name(country), "successes": successes, "results": results,
            "records": records, "statistics": statistics, "top_scorers": _top(mem, country, True),
            "top_caps": _top(mem, country, False)}


# -- the new game (T106) ---------------------------------------------------------------------------------------------
# [confirmed: named/seg_1771_02.c 1771:26B9 country_list_screen; screens.py BROWSE_TOP, BROWSE_ROW, COUNTRY_ORDER] The
# browser lists the countries in the order DS:9B56 (a far pointer to DS:9C7E or DS:9BFD, by the game record's +0x40
# or INS), columns of 16 from DS:0DB4, the row DS:0DB6.
COUNTRY_ORDER, BROWSE_TOP, BROWSE_ROW = 0x9B56, 0x0DB4, 0x0DB6
# [confirmed: goal2/game/country_card.py tactic_word (F008)] the tactic words, and the card's two groups
TACTIC_WORDS, MARKING_WORDS = 0x6AA0, 0x0E90
TEAM_TACTICS = (("defence system", 5), ("protection", 6), ("offside", 7))
PLAYER_DEFAULTS = (("positioning", 1), ("possession", 2), ("passing", 3), ("tackling", 4), ("marking", 8))


def country_select(state):
    """The country browser of a new game (1771:26B9 mode 2, PLEASE SELECT YOUR COUNTRY): the 128 countries in the
    order it lists them, each with its name and rankings (000E:715E's fields), and the browsed one (the order's byte
    DS:0DB4 + DS:0DB6 - 1), the manager choosing (+1) and the start year and stage the title's new game set
    (1771:9B85: +0x3A, +0x3C) [confirmed: NG-9]."""
    mem = Memory(state)
    order = mem.far(COUNTRY_ORDER)
    top, row = mem.ds_word(BROWSE_TOP), mem.ds_byte(BROWSE_ROW)
    countries = [_rankings(mem, mem.byte(order + i)) for i in range(1, 129)]     # the order's bytes 1..128
    return {"countries": countries, "index": top + row - 1, "top": top, "row": row,
            "country": countries[top + row - 2]["country"], "manager": mem.game(1),
            "start_year": mem.game(0x3A, 2), "stage": mem.game(0x3C)}


def country_card(state, country):
    """A country as the new game's browser shows it (draw_team_panel, 1771:26B9), in the shape of the Python route's
    card (goal2/game/country_card.py) so the desktop's card paints it: the name, the manager (1771:0947 of the
    country's +0x2E, as the browser's F3 edits it), the world rank +0x2B, the continent's name (DS:6E92) and the rank
    within it +0x2A, the formation (the eleven's lines, DS:0D5C), the eleven's codes (DS:69A8) and the tactic words
    of the country's tactics byte +0x2D. [designed] The fields no finding decodes stay as the Python route names
    them (country_card.UNDECODED)."""
    from goal2.game.country_card import UNDECODED
    mem = Memory(state)
    if not 1 <= country <= 128:
        raise ValueError("country must be 1..128")
    rank = _rankings(mem, country)
    team = squad(mem, country)
    eleven = team[:11]
    formation = "-".join(str(sum(1 for p in eleven if p["line"] == line)) for line in LINES[1:])
    tactics = mem.country(country, 0x2D)

    def word(element):
        bit = tactics >> (element - 1) & 1
        if element == 8:
            return mem.pstr(mem.ds * 16 + MARKING_WORDS + 11 * bit, 10)
        return mem.pstr(mem.ds * 16 + TACTIC_WORDS + 32 * element + 16 * bit, 15)
    return {"country": country, "name": rank["name"], "manager": mem.manager_name(mem.country(country, 0x2E)),
            "world": rank["world_rank"], "continent": rank["continent"], "continental": rank["continent_rank"],
            "formation": formation, "eleven": [p["code"] for p in eleven],
            "team_tactics": [(n, word(e)) for n, e in TEAM_TACTICS],
            "player_defaults": [(n, word(e)) for n, e in PLAYER_DEFAULTS],
            "players": [p["player"] for p in team], "squad": team, "not_decoded": UNDECODED}


# [confirmed: named/seg_000E_01.c 000E:070B, 062F, 075F, 05F6] A bulletin is composed in the page buffer [DS:A96E]
# (000E:038E unpacks its template) and moved to the screen by 000E:05F6 before its key read: 070B writes line n of
# the middle story at column 0x1F, row n + 8 (20 characters, centred and upper-cased), 062F the left story at column 5
# and 075F the right at column 0x3B, rows 0x0B..0x0D (18 characters). The animation 000E:0572 draws on the screen
# only, so the buffer holds the page as composed.
PAGE_BUFFER = 0xA96E
# [derived: the writers' columns and rows above, 1-based; E038-r0001's bulletins] each story's masthead row and box:
# (masthead row, first row, last row, first column, last column), 0-based, the box's inside.
BULLETIN_PANELS = {"left": (8, 10, 18, 3, 22), "middle": (6, 8, 20, 29, 50), "right": (8, 10, 18, 57, 76)}
FILLER = set("≡░ ")                   # [derived: the template's text lines] the page's filler glyphs, words of no story


def bulletin(state):
    """THE SOCCER BULLETIN as its writers composed it in the page buffer: each story's masthead and its lines, top
    to bottom, without the template's filler (rows made of ≡ and ░ only)."""
    mem = Memory(state)
    base = mem.far(PAGE_BUFFER)

    def cells(row, a, b):
        raw = bytes(mem.mem[base + 160 * row + 2 * a:base + 160 * row + 2 * b + 2:2])
        return "".join(" " if c == 0 else CP437_LOW[c - 1] if c < 32 else bytes([c]).decode("cp437")
                       for c in raw).strip()
    out = {}
    for name, (head, first, last, a, b) in BULLETIN_PANELS.items():
        lines = [cells(r, a, b) for r in range(first, last + 1)]
        out[name] = {"masthead": cells(head, a, b), "lines": [t for t in lines if t and not set(t) <= FILLER]}
    return out


def achievement_bulletin(state):
    """[confirmed: #395; 000E:0584-05A6 at archaeology 44cea4de] Qualified best-place
    caption from original code plus the untouched three-column composed page."""
    return dict(bulletin(state), achievement=Memory(state).code_str(0x000E, 0x055F))


def congratulations_bulletin(state):
    """[confirmed: #409 genuine T123 capture; 0572's packed template DS:5B94 at source 44cea4de]
    Its fixed caption is row 2, columns 31..48 of the original display buffer. This is
    presentation readback only; caller/flag classification never reads this text."""
    mem = Memory(state)
    start = mem.far(0xA96A) + 160*2 + 2*31
    caption = bytes(mem.mem[start:start+2*18:2]).decode('cp437').strip()
    return dict(bulletin(state), achievement=caption)


# -- the Team and Pool pages (T107) ---------------------------------------------------------------------------------
# [confirmed: annotations/fields.tsv (F007, F008)] the player record (20 bytes at [DS:A91B] + 20 n): +0 country, +1 age,
# +2 peak age, +3 rating, +4 ability, +5 skill profile, +6 position, +7 club position, +8 caps, +0xA goals, +0xC
# morale, +0xD fitness, +0xE energy, +0xF own tactics (a set: elements 1..4 the values, 5..8 "his own"), +0x10
# status (a set), +0x12 performance. A set's element k is bit k - 1 (214B:0C57 u214b_set_test_bit).
SKILL_NAMES = ("keeping", "kicking", "tackling", "heading", "marking", "passing", "crossing", "feinting", "control",
               "dribbling", "shooting", "penalties")          # [confirmed: F008] the screen's twelve, in its order
TACTIC_NAMES = ("position", "possession", "passing", "tackling")   # [confirmed: F008] the tactics panel's rows
POSITION_NAMES = 0x69B6       # [confirmed: 1771:42BC] the position's name: DS:69B6 + 19 * code (DS:69B5 + 1)
MATCH_SET_UP = 0x0C1E         # [confirmed: F031] set while a match is set up (match_set_up)
IN_MATCH_MENU = 0x0C1F        # [confirmed: F031] in_match_menu_used
# [confirmed: named/seg_1771_02.c 1771:1981; screens.py TACTICS_ROW] the team tactics screen's row r shows element
# DS:6BBF[r]; the rows' names are the screen's (T99's categories, docs/original-game/images/m244-team-tactics.png).
ELEMENT_OF_ROW = 0x6BBF
TACTIC_LABELS = {5: "defence system", 6: "protection", 7: "offside", 1: "positioning", 2: "possession",
                 3: "passing", 4: "tackling", 8: "marking"}


def _bit(value, element):
    """214B:0C57: element k of a set is bit k - 1."""
    return value >> (element - 1) & 1


def _player(mem, w):
    a = mem.far(PLAYERS) + PLAYER_SIZE * w
    return bytes(mem.mem[a:a + PLAYER_SIZE])


def _word(mem, table, index):
    """A characteristic's word: DS:6EB4 + 16 * DS:table[index] (1771:42BC); the index is the guest's 16-bit sum."""
    return mem.pstr(mem.ds * 16 + 0x6EB4 + 16 * mem.ds_byte((table + index) & 0xFFFF))


def _signed(b):
    return b - 256 if b > 127 else b


def tactic_word(mem, element, bit, keeper=False):
    """The word of tactic element 1..8 (DS:6AA0 + 32 e + 16 bit, the team tactics screen and 1771:3BD3); for a
    goalkeeper 1771:3BD3 shows elements 1 and 3 from DS:0EA6 and DS:0EC6 instead (it swaps them into DS:6AC0 and
    DS:6B00 while it draws)."""
    if keeper and element in (1, 3):
        return mem.pstr(mem.ds * 16 + (0x0EA6 if element == 1 else 0x0EC6) + 16 * bit)
    return mem.pstr(mem.ds * 16 + TACTIC_WORDS + 32 * element + 16 * bit)


def player_card(state, w):
    """Player `w`'s card as the player screen 1771:42BC draws it (SELECT YOUR TEAM's left side).

    [confirmed: named/seg_1771_03.c 42BC, 3827, 3947, 3BD3, 3B3F, 3AE2; seg_1771_02.c 2E93, 2E20, 2FAD, 2FFB, 3041,
    3088, 30D9; F008] The name (1771:2E93), age +1, caps +8, goals +0xA, height DS:0E46[+7] + DS:0E54[w mod 12] inches,
    the foot ("two footed" 1771:425D when +5 + +2 = 30, else DS:0F2C + 6 * DS:0E60[14 DS:0E7C[w mod 3] + +7]), the
    position +6 and club position +7 by name (DS:69B6 + 19 code); the cards: status elements 4 and 5 a yellow card and
    6 a red one (the glyph 1771:4268); the status word (1771:426A.. by elements 8, energy 0, 5, 6, 3, else, for a squad
    player, 1771:4298 or, with a match set up, 1771:42A6 for slots 1..11 and 1771:42AF); the performance as 1771:3827
    buckets it (None for 0x7FFF, else 1..9, the length of DS:0E86's stars); the twelve skill bars of 1771:3947
    (DS:6DCD[12 (+5) + DS:6D25[12 (+7) + i]] * (+4 + 1) div 256 cells of 26); the characteristics' words and bars
    (hardness +5 - (+3 and 1) by DS:78C4, 14 h div 16 cells; fitness by DS:78D5 (energy's index when +0xE is 0, no
    bar then), 14 f div 32; energy by DS:78F6, 14 e div 32; morale by DS:78A3[min(32, m)], 14 m div 32 when below 32;
    leadership ((+3 - +5) mod 8, halved when +1 < 0x15) by DS:7917, 14 l div 7); the four tactics (own +0xF elements 5..8
    say "his own", then the value is +0xF's, with " P" (1771:3BCE); else the country's +0x2D); and the mark (blank
    for positions 0 and 1; status element 7: 1771:3B30; else DS:0E90 + 11 * element 8 of the country's +0x2D)."""
    mem = Memory(state)
    r = _player(mem, w)
    country, position, club = r[0], r[6], r[7]
    team_tactics = mem.country(country, 0x2D)
    status = r[0x10]
    inches = mem.ds_byte(0x0E46 + club) + mem.ds_byte(0x0E54 + w % 12)
    if r[5] + r[2] == 30:
        foot = mem.code_str(0x1771, 0x425D)
    else:
        foot = mem.pstr(mem.ds * 16 + 0x0F2C + 6 * mem.ds_byte(0x0E60 + 14 * mem.ds_byte(0x0E7C + w % 3) + club))
    cards = [colour for element, colour in ((4, "yellow"), (5, "yellow"), (6, "red")) if _bit(status, element)]
    set_up = mem.ds_byte(MATCH_SET_UP)
    slot = next((s + 1 for s in range(20) if mem.country(country, 2 * s, 2) == w), 0)
    if _bit(status, 8):
        readiness = mem.code_str(0x1771, 0x426A)
    elif r[0x0E] == 0:
        readiness = mem.code_str(0x1771, 0x4274)
    elif _bit(status, 5):
        readiness = mem.code_str(0x1771, 0x427C)
    elif _bit(status, 6):
        readiness = mem.code_str(0x1771, 0x4283)
    elif _bit(status, 3):
        readiness = mem.code_str(0x1771, 0x428C)
    elif slot:
        readiness = mem.code_str(0x1771, 0x4298 if not set_up else (0x42A6 if slot < 12 else 0x42AF))
    else:
        readiness = ""
    performance = r[0x12] | r[0x13] << 8
    if performance == 0x7FFF:
        bucket = None
    else:
        p = performance - 10000 if _signed16(performance) > 5000 else performance
        d = _signed16(p & 0xFFFF) - 0x37
        bucket = 1 + sum(d >= edge for edge in (-0x32, 0, 0x32, 100, 0x96, 200, 300, 400))
    skills = []
    for i in range(1, 13):
        cls = mem.ds_byte(0x6D25 + 12 * club + i)
        skills.append((SKILL_NAMES[i - 1], mem.ds_byte(0x6DCD + 12 * r[5] + cls) * (r[4] + 1) // 256))
    hardness = (r[5] - (r[3] & 1)) & 0xFF
    morale = _signed(r[0x0C])
    difference = r[3] - r[5]
    lead = (difference - int(difference / 8) * 8) & 0xFFFF   # 30D9: Pascal's mod (the dividend's sign), a word
    if r[1] < 0x15:
        lead //= 2
    fitness, energy = _signed(r[0x0D]), _signed(r[0x0E])
    characteristics = [
        ("hardness", _word(mem, 0x78C4, hardness), hardness * 14 // 16),
        ("fitness", _word(mem, 0x78D5, energy if energy == 0 else fitness), _div(fitness * 14, 32) if energy else 0),
        ("energy", _word(mem, 0x78F6, energy), _div(energy * 14, 32)),
        ("morale", _word(mem, 0x78A3, min(32, morale)), _div(morale * 14, 32) if morale < 32 else 0),
        ("leadership", _word(mem, 0x7917, lead), (lead * 14 & 0xFFFF) // 7),
    ]
    tactics = []
    for e, name in enumerate(TACTIC_NAMES, 1):
        own = bool(_bit(r[0x0F], e + 4))
        bit = _bit(r[0x0F] if own else team_tactics, e)
        tactics.append((name, tactic_word(mem, e, bit, keeper=position == 0), own))
    if position < 2:
        mark = ""
    elif _bit(status, 7):
        mark = mem.code_str(0x1771, 0x3B30)
    else:
        element = _bit(team_tactics, 8)
        mark = (mem.pstr(mem.ds * 16 + MARKING_WORDS + 11 * element) if not set_up or not element
                else mem.code_str(0x1771, 0x3AD5))
    code = bytes([mem.ds_byte(CODE_TABLE + position)]).decode("cp437") if position < 14 else "?"
    return {"player": w, "name": mem.player_name(w), "country": country, "age": r[1],
            "caps": r[8] | r[9] << 8, "goals": r[0xA] | r[0xB] << 8, "height": (inches // 12, inches % 12),
            "foot": foot, "position": position, "code": code,
            "line": LINES[mem.ds_byte(LINE_TABLE + position)] if position < 14 else "unknown",
            "position_name": mem.pstr(mem.ds * 16 + POSITION_NAMES + 19 * position) if position < 14 else "",
            "club_position": club,
            "club_position_name": mem.pstr(mem.ds * 16 + POSITION_NAMES + 19 * club) if club < 14 else "",
            "club_code": bytes([mem.ds_byte(CODE_TABLE + club)]).decode("cp437") if club < 14 else "?",
            "cards": cards, "readiness": readiness, "performance": bucket, "skills": skills,
            "characteristics": characteristics, "tactics": tactics, "mark": mark,
            "own_tactics": r[0x0F], "status": status, "slot": slot}


def _div(a, b):
    """The guest's signed division: the quotient truncated toward zero."""
    return int(a / b)


def _signed16(v):
    return v - 0x10000 if v > 0x7FFF else v


def team(state):
    """The managed country's squad as SELECT YOUR TEAM lists it: the twenty words +0..+0x27 in order, the first
    eleven the team and the rest the bench (draw_squad_screen 1771:4E22, the rule after the eleventh), each with its
    name and role code (1771:2F37: DS:69A8[+6], the line DS:0D5C) [confirmed: F008, F029]."""
    mem = Memory(state)
    country = mem.manager_country(0x80 + mem.game(1))
    rows = squad(mem, country)
    for i, row in enumerate(rows):
        row["slot"] = i + 1
        row["eleven"] = i < 11
    return {"country": country, "name": mem.country_name(country), "squad": rows}


def team_tactics(state, country=None):
    """The team tactics (1771:1981) of the managed country by default: the byte +0x2D and, in the screen's row order
    (DS:6BBF[1..8]), each element's name, bit and value word (DS:6AA0 + 32 e + 16 bit; F010: element k is bit k - 1)."""
    mem = Memory(state)
    if country is None:
        country = mem.manager_country(0x80 + mem.game(1))
    byte = mem.country(country, 0x2D)
    rows = []
    for row in range(1, 9):
        e = mem.ds_byte(ELEMENT_OF_ROW + row)
        bit = _bit(byte, e)
        rows.append({"row": row, "element": e, "name": TACTIC_LABELS[e], "on": bool(bit),
                     "word": tactic_word(mem, e, bit), "words": (tactic_word(mem, e, 0), tactic_word(mem, e, 1))})
    return {"country": country, "name": mem.country_name(country), "byte": byte, "rows": rows}


def pool(state):
    """The current manager's pool (F011): the eighty A927 words from DS:6D18[m] on, in the order the pool list draws
    them (0791:E2E6: item k is [DS:A927][DS:6D18[m] + k - 1], the name and code by 1771:2F37), and the list's top and
    highlighted row (the game record's words +0x52 + 2m and +0x5E + 2m)."""
    mem = Memory(state)
    m = mem.game(1)
    first = mem.ds_word(POOL_BASE + 2 * m)
    players = mem.far(PLAYERS)
    rows = []
    for k in range(1, 0x51):
        w = mem.word(mem.far(POOL_INDICES) + 2 * (first + k - 1))
        p = mem.byte(players + PLAYER_SIZE * w + 6)
        rows.append({"item": k, "player": w, "name": mem.player_name(w) if w else "", "position": p,
                     "code": bytes([mem.ds_byte(CODE_TABLE + p)]).decode("cp437") if p < 14 else "?",
                     "line": LINES[mem.ds_byte(LINE_TABLE + p)] if p < 14 else "unknown"})
    return {"manager": m, "first": first, "top": mem.game(0x52 + 2 * m, 2), "row": mem.game(0x5E + 2 * m, 2),
            "rows": rows}


# -- the round (T108) -----------------------------------------------------------------------------------------------
# [confirmed: kit match.py, F029; named/seg_0791_12.c ED8A, seg_0791_10.c CC7B, seg_0791_11.c E44F] A match's two
# sides: team 0 DS:9B34, team 1 DS:9B36 (the host of a friendly); the captain's word DS:9978 + 10 t; the
# substitutions left DS:9B3A + t (A4A1 sets 5 a side for a friendly, kind 1, and 2 for every other kind, F027); DS:9B41
# set: substitutions are made now; DS:9B40: one is asked for at the next stoppage.
TEAM_WORDS, CAPTAIN, SUBS_LEFT, SUBS_NOW, SUBS_REQUEST = 0x9B34, 0x9978, 0x9B3A, 0x9B41, 0x9B40
SCORE, SCORERS, SCORER_SIDE, MAN_OF_THE_MATCH, QUICK, STATS = 0x9B3C, 0x7BD1, 0x21, 0x7C3A, 0x9A3F, 0x7B7E
# [confirmed: named/seg_0791_01.c 0106] the nine statistics per side, in the board's row order (kit match.py)
STAT_NAMES = ("corners", "free kicks", "penalties", "shots", "on target", "saves", "fouls", "bookings", "red cards")


def match_sides(state):
    """The match's sides (DS:9B34, DS:9B36), which is the managed one, its eleven and bench (its squad words, slots
    1..11 and 12..20) and its captain (DS:9978 + 10 t)."""
    mem = Memory(state)
    teams = [mem.ds_word(TEAM_WORDS), mem.ds_word(TEAM_WORDS + 2)]
    side = next((t for t in (0, 1) if mem.country(teams[t], 0x2E) > 0x80), None)
    out = {"teams": teams, "names": [mem.country_name(c) for c in teams], "managed_side": side,
           "eleven": [], "bench": [], "captain": None}
    if side is not None:
        words = [mem.country(teams[side], 2 * s, 2) for s in range(20)]
        out.update(eleven=words[:11], bench=[w for w in words[11:] if w], captain=mem.ds_word(CAPTAIN + 10 * side))
    return out


def captain_choice(state):
    """The captain prompt's list (0791:CC7B draws the eleven, slots 1..11, by 1771:2F37's names and codes) and the
    captain the original holds now (DS:9978 + 10 t)."""
    sides = match_sides(state)
    rows = [r for r in team(state)["squad"] if r["player"] in sides["eleven"]]
    return {"eleven": rows, "captain": sides["captain"], "country": sides["teams"][sides["managed_side"]],
            "name": sides["names"][sides["managed_side"]]}


def bench(state):
    """The bench in a match as SELECT TEAM shows it (0791:E44F with DS:0C1F set): the eleven and the bench of the
    managed side (draw_squad_screen 1771:4E22), the substitutions left (the counter E44F draws, DS:9B3A + t), whether
    they are made now (DS:9B41) or asked for (DS:9B40), and with none left E44F's own line, the template DS:2538 as
    214B:0329 unpacks it into the page buffer ([DS:A96E], `message`)."""
    mem = Memory(state)
    sides = match_sides(state)
    t = sides["managed_side"]
    left = mem.ds_byte(SUBS_LEFT + t)
    rows = team(state)["squad"]
    out = {"side": t, "country": sides["teams"][t], "name": sides["names"][t], "left": left,
           "now": bool(mem.ds_byte(SUBS_NOW)), "requested": bool(mem.ds_byte(SUBS_REQUEST)),
           "eleven": sides["eleven"], "bench": sides["bench"], "squad": rows, "message": None}
    if left == 0:
        out["message"] = template_text(mem, NO_SUBSTITUTES)
    return out


NO_SUBSTITUTES = 0x2538


def match_speed(state):
    """[confirmed: F030, 0791:9372 / 93E8–944D] Original delay 0..5, changed by Right/Left; 0 has no delay."""
    mem = Memory(state)
    return mem.byte(mem.far(GAME) + 0x3F)


def pitch(state, sequence, watermark):
    """[derived: T109; F013/F028, watched_pitch.snapshot] The same signed pitch records as the Python viewer,
    read at 0791:93C2's live poll. Slot identity is checked against the current original squad, substitutions included.
    [confirmed: original_match/match.py] DS:831F is the minute; DS:9B3C holds the two score bytes."""
    from types import SimpleNamespace
    from goal2.game.watched_pitch import snapshot
    mem = Memory(state)
    teams = [mem.ds_word(TEAM_WORDS), mem.ds_word(TEAM_WORDS + 2)]
    reader = SimpleNamespace(DS=mem.ds, rd=mem.image.rd,
                             read=lambda a, n: bytes(mem.mem[a:a + n]))
    match = SimpleNamespace(m=reader, opts=dict(first=teams[0], second=teams[1]),
                            _squad=lambda c: [mem.country(c, 2 * s, 2) for s in range(20)])
    event = SimpleNamespace(minute=mem.ds_word(0x831F), score=[mem.ds_byte(0x9B3C + t) for t in (0, 1)])
    return snapshot(match, event, sequence, watermark)


def pitch_identity(state):
    """[derived: T109; F002/F028] Countries and current squad role codes for the existing pitch renderer."""
    mem = Memory(state)
    sides = match_sides(state)
    roles = {}
    for c in sides['teams']:
        for i in range(20):
            w = mem.country(c, 2 * i, 2)
            if w:
                position = mem.byte(mem.far(PLAYERS) + PLAYER_SIZE * w + 6)
                roles[str(w)] = bytes([mem.ds_byte(CODE_TABLE + position)]).decode('cp437') if position < 14 else '?'
    return dict(countries=sides['names'], managed=sides['managed_side'], roles=roles, kind='Match')


def commentary(state, previous=0):
    """[confirmed: 0791:1D4A, code/seg_0791_03.asm; original_match/match.py _flush] The ring's new rows in
    order. DS:80EE is its newest index, wrapping 1..200; each 6-byte row at DS:7C38 holds template, two player
    words and team. Text is decoded from the original's own templates, never its drawn screen."""
    from goal2.engine.original_match.image import names_and_templates
    mem = Memory(state)
    newest = mem.ds_word(0x80EE)
    if newest == previous:
        return newest, []
    name, templates = names_and_templates(lambda a, n: bytes(mem.mem[a:a + n]), mem.ds, mem.image.far)
    resolver = _display_names.get()
    if resolver is not None:
        raw_name = name
        name = lambda word: mem.player_surname(word, raw_name(word))
    rows = []
    index = previous
    for _ in range(200):
        index = index % 200 + 1
        a = mem.ds * 16 + 0x7C38 + 6 * index
        template, p1, p2, side = mem.byte(a), mem.word(a + 1), mem.word(a + 3), mem.byte(a + 5)
        text = ' '.join(templates[template].replace('\x01', f' {name(p1)} ')
                        .replace('\x02', f' {name(p2)} ').split())
        rows.append(dict(template=template, players=[p1, p2], team=side, text=text))
        if index == newest:
            return newest, rows
    raise ValueError('commentary ring index is outside 1..200')
BOX = {ord(c): " " for c in "─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╒╓╕╖╘╙╛╜╞╟╡╢╤╥╧╨╪╫"}   # a template's frame, not its words        # [confirmed: named/seg_0791_11.c E44F] drawn when DS:9B3A + t is 0


def template_text(mem, offset):
    """The text a screen template DS:offset writes, row by row, runs of blanks as one space: 214B:0147
    (u214b_unpack_screen_rle, under 214B:0329) reads a word (the first cell, 1-based), a byte (the rows) and a byte (the
    width), then per cell a character, or 0xFF and an attribute byte (the attribute of the cells that follow), or 0
    and a count (the last cell repeated) [confirmed: named/seg_214B_01.c 0147]. Read from the program's own data,
    never written into goal2."""
    a = mem.ds * 16 + offset
    rows, width = mem.byte(a + 2), mem.byte(a + 3)
    a += 4
    cells, last = [], 0x20
    while len(cells) < rows * width:
        c = mem.byte(a)
        if c == 0xFF:
            a += 2
            continue
        if c == 0:
            cells += [last] * mem.byte(a + 1)
            a += 2
            continue
        cells.append(c)
        last = c
        a += 1
    lines = []
    for r in range(rows):
        text = "".join(" " if c < 32 else bytes([c]).decode("cp437") for c in cells[r * width:(r + 1) * width])
        lines.append(" ".join(text.translate(BOX).split()))
    return " ".join(t for t in lines if t)


def board(state):
    """The match board 0791:0106 draws (half time, full time, a quick result's and the summary): the two sides and
    their names, the score DS:9B3C (team 0, team 1), each side's scorers (0x7BD1 + 0x21 t + 3 k, k = 1..11: the player
    word and the minute, a minute >= 0x81 drawn as minute - 0x80 with the mark 1771:0101 or, for a scorer outside the
    side's squad, 1771:0103), and when not a quick result (DS:9A3F clear) the man of the match DS:7C3A and the nine
    statistics per side (DS:7B7E + 10 t) [confirmed: named/seg_0791_01.c 0106]."""
    mem = Memory(state)
    sides = match_sides(state)
    scorers = [[], []]
    for t in (0, 1):
        squad_words = [mem.country(sides["teams"][t], 2 * s, 2) for s in range(20)]
        for k in range(1, 12):
            a = mem.ds * 16 + SCORERS + SCORER_SIDE * t + 3 * k
            w, minute = mem.word(a), mem.byte(a + 2)
            if not w:
                continue
            mark = ""
            if minute >= 0x81:
                minute -= 0x80
                mark = mem.code_str(0x1771, 0x0101 if w in squad_words else 0x0103)
            scorers[t].append({"player": w, "name": mem.player_name(w), "minute": minute, "mark": mark})
    quick = bool(mem.ds_byte(QUICK))
    out = {"teams": sides["teams"], "names": sides["names"], "managed_side": sides["managed_side"],
           "score": [mem.ds_byte(SCORE), mem.ds_byte(SCORE + 1)], "scorers": scorers, "quick": quick,
           "man_of_the_match": None, "statistics": None}
    if not quick:
        motm = mem.ds_word(MAN_OF_THE_MATCH)
        out["man_of_the_match"] = mem.player_name(motm) if motm else None
        out["statistics"] = {n: [mem.ds_byte(STATS + k), mem.ds_byte(STATS + 10 + k)] for k, n in enumerate(STAT_NAMES)}
    return out


def _shootout_available(player):
    """[confirmed: 1771:3216 at 53d7ef5] Positive signed energy; status elements 8/6/3 clear.
    Element5 (next-match suspension) is deliberately not this current-match test."""
    return _signed(player[0x0E])>0 and not any(_bit(player[0x10],e) for e in (8,6,3))


def taker_choice(state, selection):
    """[confirmed: T88/T89; CC7B] The actual eleven and selected full card; the guest judges Enter.

    Goal-kick choices are not restricted to goalkeepers: T89's actual stored player383 has position2.
    """
    mem = Memory(state)
    rows = squad(mem, selection['country'])[:11]
    selected = rows[selection['slot']-1]['player']
    return dict(selection, name=mem.country_name(selection['country']), players=rows,
                selected_player=selected, card=player_card(state, selected))


def shootout_order(state, selection):
    """[confirmed: F015/F030 at 53d7ef5, 0791:9B93 / 1771:3216; T118 E031 original continuation]
    The XI, their original availability and the Pascal-string pick order read from the active frame."""
    mem = Memory(state)
    rows = squad(mem, selection['country'])[:11]
    for slot,row in enumerate(rows,1):
        player = _player(mem,row['player'])
        row.update(slot=slot, available=_shootout_available(player),
                   rank=selection['picks'].index(slot)+1 if slot in selection['picks'] else None)
    return dict(selection, name=mem.country_name(selection['country']), players=rows,
                selected_player=rows[selection['slot']-1]['player'])


def round_results(state, first, last):
    """The round's results as simulate_fixture 000E:6970 lists them (1771:7812 for each fixture from `first` to `last`,
    the window the original drew: max(last - 15, the round's first fixture) [confirmed: named/seg_000E_05.c 6970];
    the bounds come from the wait's view, screens.py), each row as `fixture_list` reads it."""
    mem = Memory(state)
    return {"first": first, "last": last, "rows": [_row(mem, mem.fixture(n)) for n in range(first, last + 1)]}


def fixture_result(state):
    """The result of a fixture marked to watch and declined (simulate_fixture with first byte 0xFE: draw_score and the
    template DS:25CC over the match screen): the fixture +0x26 as `fixture_list` reads it."""
    mem = Memory(state)
    return _row(mem, mem.fixture(mem.game(0x26, 2)))
