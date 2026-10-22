"""The screen catalogue of the core (T103, G9): which screen the original shows at each key read and each poll.

[designed: owner, 2026-10-22, #308; estimate 99, Stage 3 G9] Each key-read site is mapped to a screen kind and the
state it shows, read from the original's memory and stack, never from the text page. The table is `SITES`: a key
**read** is keyed by the return address of its 214B:08DD call (the wait's site), a **poll** by the return address of
its 214B:0723 call ("key pressed?"). A site shared by several screens is told apart by the caller frames the
original pushed, or, where frames are not enough, by a named memory field cited below. A site with no entry, or an
entry that names no kind for what it finds, gives None: the runner then stops (`UnknownScreen`); it never guesses.

Kinds are named as in goal2-archaeology `static/screens/kinds.tsv`; their keys are the `screen` rows of
`static/screens/catalogue.tsv` (T39a; `owner.tsv` has no rows), each with the code 214B:08DD returns for it.
A screen no rule there names has a [designed] goal2 kind (`DESIGNED`, docs/core.md), whose keys are the hints
the screen prints. Evidence is goal2-archaeology at 53d7ef5 (static/goal-exe/code/, named/, annotations/).
"""
from __future__ import annotations

from dataclasses import dataclass

# -- key codes, as 214B:08DD stores them at DS:A976 -------------------------------------------------------------
# [confirmed: seg_214B_02.asm 08DD-0941] the character, or for an extended key (AL 0) its scan code adjusted (Left
# 0x4B - 1, Right 0x4D - 2, End..PgDn 0x4F..0x51 - 3) plus 0x64.
RETURN, ESCAPE, SPACE = 0x0D, 0x1B, 0x20
F1, F2, F3, F4, F5, F7, F9, F10 = 0x9F, 0xA0, 0xA1, 0xA2, 0xA3, 0xA5, 0xA7, 0xA8      # scan 0x3B.. + 0x64
HOME, UP, PGUP, LEFT, RIGHT = 0xAB, 0xAC, 0xAD, 0xAE, 0xAF                          # 0x47, 0x48, 0x49, 0x4B-1, 0x4D-2
END, DOWN, PGDN, INSERT = 0xB0, 0xB1, 0xB2, 0xB6                                    # 0x4F-3, 0x50-3, 0x51-3, 0x52
ANY = "any"        # the screen says only "hit any key"
TYPED = "typed"    # characters typed into a line

# The X keysyms of catalogue.tsv's `keysyms` column (E015's key log), as codes.
KEYSYMS = {"Return": RETURN, "Escape": ESCAPE, "space": SPACE, "Insert": INSERT, "Up": UP, "Down": DOWN,
           "Left": LEFT, "Right": RIGHT, "Prior": PGUP, "Next": PGDN, "Home": HOME, "End": END,
           "F1": F1, "F2": F2, "F3": F3, "F4": F4, "F5": F5, "F7": F7, "F9": F9, "F10": F10,
           "(any)": ANY, "(typed)": TYPED}


def keys(*rows):
    """Rows (label, keysyms) as the catalogue writes them -> ((label, (code, ...)), ...)."""
    def code(sym):
        return KEYSYMS[sym] if sym in KEYSYMS else ord(sym)
    return tuple((label, tuple(code(s) for s in syms.split())) for label, syms in rows)


@dataclass(frozen=True)
class Kind:
    """A screen kind: its name, the keys it accepts (rows of (label, codes)), whether goal2 named it ([designed])
    and the evidence. `polled`: the screen reads a key only after a poll says one waits."""
    name: str
    keys: tuple
    designed: bool = False
    polled: bool = False
    evidence: str = ""

    def accepts(self, key):
        for _, codes in self.keys:
            for c in codes:
                if c == ANY or key == c or (c == TYPED and 0x20 <= key < 0x7F):
                    return True
        return False


_CAT = "[confirmed: catalogue.tsv, the kind's screen rows, E015-r0007]"
_YES_NO = keys(("Y N", "y n"))
_MATCH_MENU = keys(("INS", "Insert"), ("↑↓←→", "Up Down Left Right"), ("◄┘", "Return"))
_BENCH_ANY = keys(("Esc ◄┘", "Escape Return"), ("any key", "(any)"))

KINDS = {k.name: k for k in (
    # -- kinds.tsv's own, their keys from catalogue.tsv ------------------------------------------------------
    Kind("manager-menu", keys(("F1", "F1"), ("F10", "F10"), ("F3", "F3"), ("F4", "F4"), ("F5", "F5"),
                              ("F7", "F7"), ("↑↓", "Up Down"), ("◄┘", "Return")), evidence=_CAT),
    Kind("quit-confirm", _YES_NO, evidence=_CAT),
    Kind("save-game-prompt", _YES_NO, evidence=_CAT),
    Kind("fixtures-watch", keys(("Esc", "Escape"), ("↑↓", "Up Down"), ("◄┘", "Return")), evidence=_CAT),
    Kind("fixtures-auto", keys(("Esc", "Escape"), ("↑↓", "Up Down"), ("◄┘", "Return")), evidence=_CAT),
    Kind("match-menu", _MATCH_MENU, evidence=_CAT),
    Kind("match-menu-halftime", _MATCH_MENU, evidence=_CAT),
    Kind("match-menu-fulltime", _MATCH_MENU, evidence=_CAT),
    Kind("match-summary", _BENCH_ANY, evidence=_CAT),
    Kind("team-tactics", keys(("Esc", "Escape"), ("◄┘", "Return")), evidence=_CAT),
    Kind("squad-substitution-take-off", keys(("Esc", "Escape"), ("F2", "F2"), ("R,C", "r c"), ("T", "t"),
                                             ("◄┘", "Return")), evidence=_CAT),
    Kind("bulletin", keys(("any key", "(any)")), evidence=_CAT),
    Kind("captain-select", keys(("C", "c"), ("↑↓", "Up Down"), ("◄┘", "Return")), polled=True, evidence=_CAT),
    Kind("match-live", keys(("Esc ◄┘", "Escape Return"), ("F9", "F9"), ("R", "r"), ("spacebar", "space"),
                            ("←→", "Left Right"), ("↓↑", "Up Down")), polled=True, evidence=_CAT),
    Kind("match-summary-save-prompt", _YES_NO, polled=True, evidence=_CAT),
    # -- [designed] goal2 kinds for screens no kinds.tsv rule names; keys from the hints they print (docs/core.md)
    Kind("team-info", keys(("←→↑↓", "Left Right Up Down"), ("◄┘", "Return"), ("Esc", "Escape"), ("INS", "Insert"),
                           ("spacebar", "space"), ("T", "t")), designed=True,
         evidence="[designed] E006-r0001's main screen: 'Use ←→↑↓ to select', 'Hit ◄┘ for fixtures', 'Esc to exit', "
                  "'use INS to swap', 'spacebar-players T-tactics'"),
    Kind("fixture-list", keys(("↑↓", "Up Down"), ("Esc", "Escape")), designed=True,
         evidence="[designed] the fixture list on a row it offers nothing for: 'Use ↑↓ to scroll', 'Esc-exit'"),
    Kind("match-board", _BENCH_ANY, designed=True,
         evidence="[designed] the match board without the man of the match: 'hit any key', 'Esc,◄┘-bench'"),
    Kind("team-tactics-view", keys(("any key", "(any)")), designed=True,
         evidence="[designed] another country's team tactics, view only: 'hit any key'"),
    Kind("history", keys(("Esc", "Escape")), designed=True,
         evidence="[designed] a country's history (1771:1D5C, from the manager menu's history): 'Esc-exit'"),
    Kind("history-browse", keys(("←→↑↓", "Left Right Up Down"), ("◄┘", "Return"), ("Esc", "Escape"),
                                ("INS", "Insert"), ("spacebar", "space")), designed=True,
         evidence="[designed] the country browser of the history (1771:26B9 mode 3): 'Use ←→↑↓ to select', "
                  "'Hit ◄┘ for team history', 'Esc to exit', 'use INS to swap', 'spacebar-players'"),
    Kind("tournament", keys(("↓↑", "Up Down"), ("spacebar", "space"), ("←→", "Left Right"), ("Esc", "Escape")),
         designed=True, evidence="[designed] the tournament view: 'Use ↓↑ to select group', 'Hit spacebar to select "
                                 "continent', 'Use ←→ to select display', 'Esc-exit'"),
    Kind("action-replay-prompt", _YES_NO, designed=True, polled=True,
         evidence="[designed] 'Do you want an action replay? (Y/N)' (0791:0B7C asked by 0C65 at 0C87)"),
    Kind("substitution-notice", keys(("any key", "(any)")), designed=True, polled=True,
         evidence="[designed] the computer side's substitution: 'SUBSTITUTION ... press any key' (0791:C50C)"),
)}
DESIGNED = tuple(k for k, v in KINDS.items() if v.designed)


# -- reading the original's frames and memory ---------------------------------------------------------------------
class Frame:
    """The original's stack and data at a hooked instruction: `read(linear, n)` the memory, `load` the program's load
    segment, `ds` and `ss` the segments, `bp` the BP of the routine that made the call (a hooked routine's first
    instruction has not pushed its own)."""

    def __init__(self, read, load, ds, ss, bp):
        self.read, self.load, self.ds, self.ss, self.bp = read, load, ds, ss, bp

    def word(self, bp, off):
        a = self.ss * 16 + ((bp + off) & 0xFFFF)
        return int.from_bytes(self.read(a, 2), "little")

    def byte(self, bp, off):
        return self.read(self.ss * 16 + ((bp + off) & 0xFFFF), 1)[0]

    def far_caller(self, bp):
        """The far return address of the routine whose BP is `bp`, as the listing writes it."""
        return "%04X:%04X" % ((self.word(bp, 4) - self.load) & 0xFFFF, self.word(bp, 2))

    def near_caller(self, bp):
        return self.word(bp, 2)

    def up(self, bp):
        return self.word(bp, 0)

    def ds_byte(self, off):
        return self.read(self.ds * 16 + off, 1)[0]

    def ds_word(self, off):
        return int.from_bytes(self.read(self.ds * 16 + off, 2), "little")

    def far(self, ptr):
        return self.ds_word(ptr + 2) * 16 + self.ds_word(ptr)

    def far_byte(self, ptr, off):
        return self.read(self.far(ptr) + off, 1)[0]

    def far_word(self, ptr, off):
        return int.from_bytes(self.read(self.far(ptr) + off, 2), "little")


# [confirmed: annotations/globals.tsv, fields.tsv (F007, F008)] the arrays and fields the entries read.
COUNTRIES, COUNTRY_SIZE, MANAGER = 0xA917, 0xBF, 0x2E    # country +0x2E: managed when > 0x80 (1771:0B77)
FIXTURES, FIXTURE_SIZE = 0xA92B, 8                        # fixture n at +8n-8 (F023)
COUNTRY_ORDER = 0x9B56                                    # the country order the browser lists (F017)
MAN_OF_THE_MATCH = 0x7C3A                                 # F014: drawn on the summary only when DS:9A3F is clear
SUBSTITUTIONS_LEFT = 0x9B3A                               # per side (F012, F027)
MATCH_MENU_USED = 0x0C1F                                  # in_match_menu_used
QUICK = 0x9A3F                                            # set by the quick result 0791:92FC (routines.tsv)
# [confirmed: the listings named below] fields no annotation names yet.
MENU_ITEM = 0x00B0            # main_menu_loop 000E:7439: u214b_menu_move_word_wrap(6, 0xB0); the item 1..6
BROWSE_TOP, BROWSE_ROW = 0x0DB4, 0x0DB6   # 1771:26B9: the country is order[DS:0DB6 + DS:0DB4 - 1] (word, byte)
TACTICS_ROW = 0x0D8E          # 1771:1981: the row 1..8 (word), u214b_menu_read_key_and_move(8, 0xD8E)
VIEW_ONLY = 0x0C20            # 1771:1981 and 0791:E44F: set, the screens only show
SELECT_CURSOR = 0x0C1B        # 0791:E44F: the squad cursor 1..20 (word), u214b_menu_move_word_wrap(0x14, 0xC1B)
SUBS_ALLOWED, SUMMARY_FILE = 0x9B41, 0x066D   # 0791:E44F: 9B41 set, substitutions now (E2A0); 066D clear
MANAGER_NAMES = ("team info", "fixture list", "tournament", "history", "select squad", "play next game")
MATCH_MENU_ITEMS = ("team tactics", "players", "tournament", "match stats", "play")   # ED8A per side (kit screens.py)


def is_managed(f, country):
    """1771:0B77 (is_managed): the country's +0x2E > 0x80."""
    return f.far_byte(COUNTRIES, COUNTRY_SIZE * country + MANAGER) > 0x80


# -- the sites ------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Site:
    """One read or poll site: `kind(frame)` the kind it shows (None: not one the table knows), `view(frame)` its
    cursor or selection (a dict), `routine` and `evidence` where it is read and which record shows it."""
    site: str
    poll: bool
    routine: str
    evidence: str
    kind: object
    view: object = None


def _team_info(f):
    # 1771:26B9 country_list_screen(mode) [bp+6]; local_3 [bp-1] set: the players view (seg_1771_04.asm 26CB).
    # Mode 1 is the main menu's team info (000E:767D); mode 3 the history's browser (main_menu_loop item 4,
    # named/seg_000E_05.c `country_list_screen(3)`; it first shows the manager's country's history, 1771:1D5C);
    # mode 2, the new game's PLEASE SELECT YOUR COUNTRY (DS:14F4), is not reached by the core (docs/core.md) and has
    # no entry.
    if f.byte(f.bp, -1) != 0:
        return None
    return {1: "team-info", 3: "history-browse"}.get(f.byte(f.bp, 6))


def _team_info_view(f):
    row, top = f.ds_byte(BROWSE_ROW), f.ds_word(BROWSE_TOP)
    return {"country": f.far_byte(COUNTRY_ORDER, row + top - 1), "row": row}


def _fixture(f):
    """000E:0000's highlighted fixture: number [bp-6] + [bp-8] - 1 (local_8 + local_a - 1, seg_000E_01.asm 0188)."""
    n = f.word(f.bp, -6) + f.word(f.bp, -8) - 1
    base = f.far(FIXTURES) + FIXTURE_SIZE * (n - 1)
    rec = f.read(base, FIXTURE_SIZE)
    return n, rec


def _fixture_list(f):
    # named/seg_000E_01.c f_000E_0000 (lines 37-50): with neither country managed, the first byte 0xFE draws
    # DS:207E ("auto result") and 0xFF DS:2050 ("watch match"); else no hint.
    n, rec = _fixture(f)
    one, two = int.from_bytes(rec[6:8], "little"), int.from_bytes(rec[4:6], "little")
    if not is_managed(f, one) and not is_managed(f, two):
        if rec[0] == 0xFE:
            return "fixtures-auto"
        if rec[0] == 0xFF:
            return "fixtures-watch"
    return "fixture-list"


def _fixture_view(f):
    n, rec = _fixture(f)
    return {"fixture": n, "row": f.word(f.bp, -8), "teams": (int.from_bytes(rec[4:6], "little"),
                                                             int.from_bytes(rec[6:8], "little"))}


def _yes_no(f):
    # 214B:09A7 (wait_key_in_set) far-called by 214B:0566 (ask_yes_no) at 05B0; 0566's caller says which question:
    # 1771:090F asks DS:08D3 "Are you sure you want to quit" (0917) then DS:08F1 "Do you want to save this game" (092D).
    if f.far_caller(f.bp) != "214B:05B3":
        return None
    return {"1771:091C": "quit-confirm", "1771:0932": "save-game-prompt"}.get(f.far_caller(f.up(f.bp)))


MATCH_MENUS = {0xF20A: "match-menu", 0x9AE3: "match-menu-halftime", 0xF331: "match-menu-fulltime"}


def _menu_reader(f):
    # 214B:1560 (u214b_menu_read_key_and_move), far-called; its caller says which menu (kit match.py SITE_MENU).
    caller, up = f.far_caller(f.bp), f.up(f.bp)
    if caller == "0791:EE9F":
        # in_match_menu 0791:ED8A, near-called by run_match F207 (pre-match), F32E (post-match), 9A32 at 9AE0
        # (half time) (kit match.py MENU_CONTEXT); its other callers (substitution, pause, extra time) have no entry.
        return MATCH_MENUS.get(f.near_caller(up))
    if caller == "1771:1A24":
        # edit_team_tactics 1771:1981(country) [bp+6]: it edits only a managed country with DS:0C20 clear, else
        # it shows DS:14A6 and returns at the first key (named/seg_1771_02.c lines 163-176).
        country = f.word(up, 6)
        return "team-tactics" if is_managed(f, country) and not f.ds_byte(VIEW_ONLY) else "team-tactics-view"
    if caller == "1771:9022":
        return "tournament"         # 1771:8E9A's read (9022 lies in it; 9028 is the next routine)
    return None


def _menu_view(f):
    caller, up = f.far_caller(f.bp), f.up(f.bp)
    if caller == "0791:EE9F":
        item = f.word(up, -7)       # ED8A local_9 [bp-7] (seg_0791_22.asm EDE4; kit screens.py MENU_ITEM_BP)
        label = MATCH_MENU_ITEMS[(item - 1) % 5]
        if label == "play" and MATCH_MENUS.get(f.near_caller(up)) == "match-menu-fulltime":
            label = "exit"          # after the match the leave item reads "exit" (E006-r0001's tours)
        return {"item": item, "label": label}
    if caller == "1771:1A24":
        return {"country": f.word(up, 6), "row": f.ds_word(TACTICS_ROW)}
    return {}


def _board(f):
    # draw_match_summary 0791:0106 draws DS:14C8 ("MAN OF THE MATCH", strings.tsv 2581:14D6) only when DS:9A3F is
    # clear and DS:7C3A (man_of_the_match) is not 0 (named/seg_0791_01.c lines 90-93).
    if not f.ds_byte(QUICK) and f.ds_word(MAN_OF_THE_MATCH):
        return "match-summary"
    return "match-board"


def _select_team(f):
    # select_team_screen 0791:E44F(country): with DS:066D, DS:0C20 clear, DS:0C1F set (a match's menu), a
    # substitution left (DS:9B3A + local_5 [bp-3]) and DS:9B41 set, E2A0 draws "make substitutions now" (DS:4840) and,
    # with the cursor DS:0C1B below 12, "take off this player" (DS:4720) (named/seg_0791_11.c E44F, E2A0); the squad
    # view is local_7 [bp-5] = 1 (seg_0791_22.asm E495). Its other states have no entry yet.
    if (f.ds_byte(SUMMARY_FILE) or f.ds_byte(VIEW_ONLY) or not f.ds_byte(MATCH_MENU_USED)
            or not f.ds_byte(SUBSTITUTIONS_LEFT + f.byte(f.bp, -3)) or not f.ds_byte(SUBS_ALLOWED)
            or f.word(f.bp, -5) != 1):
        return None
    return "squad-substitution-take-off" if f.ds_word(SELECT_CURSOR) < 12 else None


def _select_view(f):
    slot, country = f.ds_word(SELECT_CURSOR), f.word(f.bp, 6)
    return {"slot": slot, "player": f.far_word(COUNTRIES, COUNTRY_SIZE * country + 2 * (slot - 1))}


def _ask(near_return):
    # ask_do_you_want 0791:0B7C, near-called: by run_match at F33D ("to save the match summary to disk", F1D4) and by
    # action_replay 0C65 at 0C87 ("an action replay", 0C42); 0CA8 (save this goal) has no entry yet.
    return {0xF340: "match-summary-save-prompt", 0x0C8A: "action-replay-prompt"}.get(near_return)


def _captain(f, bp):
    # choose_captain_or_taker 0791:CC7B(role [bp+4], side): role 1 the captain (CF0B; routines.tsv); the takers
    # (roles 2..5) have no entry yet.
    return "captain-select" if f.byte(bp, 4) == 1 else None


def _wait_or_key(f):
    # wait_or_key 0791:CC2E polls at CC4F; near-called by CC7B at CED6, 0B7C at 0BD4, C50C at C5C0 (and 7FCF at 803F,
    # no entry yet). Its caller's frame is [bp].
    near, up = f.near_caller(f.bp), f.up(f.bp)
    if near == 0xCED9:
        return _captain(f, up)
    if near == 0x0BD7:
        return _ask(f.near_caller(up))
    if near == 0xC5C3:
        return "substitution-notice"
    return None


_ROUTES = "the tours of goal2/tests/test_core_screens_t103.py"
SITES = {s.site: s for s in (
    # -- reads (the return address of a call of 214B:08DD) ----------------------------------------------------------
    Site("1771:28F5", False, "1771:26B9 country_list_screen", "E006-r0001's first wait (T100)", _team_info,
         _team_info_view),
    # [confirmed: named/seg_1771_02.c f_1771_1D5C] the history of a country ends in u214b_read_key; its return
    # address 1771:25E4 lies in 1D5C (the next routine is 1771:25EA). E006-r0001, the manager menu's item 4.
    Site("1771:25E4", False, "1771:1D5C (a country's history)", "T105; E006-r0001, the manager menu's history",
         lambda f: "history", lambda f: {"country": f.word(f.bp, 4)}),
    Site("000E:75D1", False, "000E:7439 main_menu_loop", "T100; " + _ROUTES, lambda f: "manager-menu",
         lambda f: {"item": f.ds_word(MENU_ITEM), "label": MANAGER_NAMES[f.ds_word(MENU_ITEM) - 1]}),
    Site("000E:016C", False, "000E:0000 (the fixture list)", _ROUTES, _fixture_list, _fixture_view),
    Site("214B:09C4", False, "214B:09A7 under 214B:0566 ask_yes_no", "T100 (F030)", _yes_no),
    Site("214B:157C", False, "214B:1560 menu reader", "T100; " + _ROUTES, _menu_reader, _menu_view),
    Site("0791:041A", False, "0791:0106 draw_match_summary", "T100; " + _ROUTES, _board),
    Site("0791:E61F", False, "0791:E44F select_team_screen", _ROUTES, _select_team, _select_view),
    Site("000E:0629", False, "000E:05F6, the news pages' key wait", _ROUTES,
         lambda f: "bulletin" if f.near_caller(f.bp) == 0x4F72 else None),   # post_match_news_and_sack 4E0E at 4F6F
    # -- polls (the return address of a call of 214B:0723) ------------------------------------------------------------
    Site("0791:93C2", True, "0791:9372 match_key_poll (93BD; reads at 93CE)", _ROUTES, lambda f: "match-live"),
    Site("0791:CC54", True, "0791:CC2E wait_or_key", "T100 (F030); " + _ROUTES, _wait_or_key),
    Site("0791:CEDE", True, "0791:CC7B choose_captain_or_taker (CED9; reads at CEE8)", _ROUTES,
         lambda f: _captain(f, f.bp)),
    Site("0791:0BE1", True, "0791:0B7C ask_do_you_want (0BDC; reads at 0BE7)", _ROUTES,
         lambda f: _ask(f.near_caller(f.bp))),
    Site("0791:C5C8", True, "0791:C50C show_computer_substitution_notice (C5C3; reads at C5CC)", _ROUTES,
         lambda f: "substitution-notice"),
)}


def identify(site, frame):
    """The kind the original shows at `site` (a read's or a poll's), or None when the table has no entry for it."""
    entry = SITES.get(site)
    return None if entry is None else entry.kind(frame)


def view(site, frame):
    """The cursor or selection of the screen at a read `site` ({} for a screen without one)."""
    entry = SITES.get(site)
    return {} if entry is None or entry.view is None else entry.view(frame)
