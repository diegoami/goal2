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

from goal2.engine.original_match.image import Image
from goal2.core.runner import CP437_LOW

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

    def player_name(self, w):
        """1771:2E93 player_name: the initial [DS:9B70] + w, a space, the surname [DS:9B6C] + 11 w."""
        surname = self.pstr(self.far(PLAYER_NAMES) + 11 * w, 10)
        return f"{chr(self.byte(self.far(PLAYER_INITIALS) + w))} {surname}"

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


def tournament(state):
    """The tournament (1771:958D from the manager menu, the managed country's): which display it opens and, for the
    qualifying display, the group tables of the country's continent.

    [confirmed: named/seg_1771_07.c 1771:958D; seg_1771_06.c 1771:8E9A, 8A87, 8CA2] The display is 1 (qualifying)
    + 1 when the stage is in the finals tables (3, 4, 7, 8) + 1 when it is a knockout stage (4, 8); the class is
    +0x40. Group g's slot s (1..4) is 8 bytes at [DS:A933] + 8 s + 0x38 g + 0x1C0 continent + 0x700 table
    + 0xE00 class - 0x200: the country word, W, D, L, F, A, T (P = W + D + L); its fixtures are the twelve words
    at [DS:A933] + 2 k + 0x38 g + 0x1C0 continent + 0xE00 class - 0x1DA. [designed] Only the qualifying display is
    read here (every kept state is in a qualifying stage); the finals groups (1771:9028), the bracket (1771:91CE)
    and the play-off view (group 9, 1771:8D84) are left to the task that first reaches them, and `groups` is then
    None."""
    mem = Memory(state)
    m = mem.game(1)
    country = mem.manager_country(0x80 + m)
    stage, klass = mem.game(0x3C), mem.game(0x40)
    display = 1 + (stage in FINALS_STAGES) + (stage in KNOCKOUT_STAGES)
    continent = mem.country(country, 0x2C)
    out = {"display": ("qualifying", "finals", "championship")[display - 1], "stage": stage, "class": klass,
           "continent": mem.pstr(mem.ds * 16 + 0x6E92 + 8 * continent), "country": country, "groups": None}
    if display != 1 or stage == 6:
        return out
    tables = mem.far(GROUP_TABLES)
    groups = []
    for g in range(1, 9):
        base = tables + 0x38 * g + 0x1C0 * continent + 0xE00 * klass - 0x200
        rows = []
        for s in range(1, 5):
            r = bytes(mem.mem[base + 8 * s:base + 8 * s + 8])
            c = r[0] | r[1] << 8
            rows.append({"country": c, "name": mem.country_name(c), "played": r[2] + r[3] + r[4], "won": r[2],
                         "drawn": r[3], "lost": r[4], "for": r[5], "against": r[6], "points": r[7]})
        if not any(r["country"] for r in rows):
            continue
        fixtures = [mem.word(tables + 2 * k + 0x38 * g + 0x1C0 * continent + 0xE00 * klass - 0x1DA)
                    for k in range(1, 13)]
        groups.append({"group": chr(0x40 + g), "number": g, "rows": rows,
                       "fixtures": [_row(mem, mem.fixture(n)) for n in fixtures if n]})
    out["groups"] = groups
    return out


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
        table.append((chr(mem.byte(a)), mem.pstr(a + 1, 10), mem.word(a + 0xC)) if managed else ("\0", "", 0))
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
                            mem.pstr(mem.far(PLAYER_NAMES) + 11 * w, 10), value)
                break
    sep = mem.code_str(0x1771, 0x1D5A)
    return [{"name": initial + sep + name, "count": count} for initial, name, count in table if count]


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
