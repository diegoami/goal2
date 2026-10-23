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
# [designed: owner, 2026-10-22, T107's amendment] A kinds.tsv kind also accepts a key its own screen's hint prints
# at a kept state; each is quoted in docs/core.md ("Keys the screen prints") with the state and the row, and backed
# by the catalogue's burst rows (the keys a recorded run read there).
PRINTED = {
    # E006-r0001, team info's T on the managed country, text row 3: "Use ↑↓ to move"; catalogue.tsv's burst row
    # "team-tactics Up" (E015-r0007 state 119); 1771:1981 moves its row DS:0D8E with them (u214b_menu_read_key_and_move)
    "team-tactics": keys(("↑↓", "Up Down")),
}
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
    Kind("team-tactics", keys(("Esc", "Escape"), ("◄┘", "Return")) + PRINTED["team-tactics"],
         evidence=_CAT + "; ↑↓ printed on the screen (PRINTED)"),
    Kind("squad-substitution-take-off", keys(("Esc", "Escape"), ("F2", "F2"), ("R,C", "r c"), ("T", "t"),
                                             ("◄┘", "Return")), evidence=_CAT),
    Kind("bulletin", keys(("any key", "(any)")), evidence=_CAT),
    Kind("captain-select", keys(("C", "c"), ("↑↓", "Up Down"), ("◄┘", "Return")), polled=True, evidence=_CAT),
    Kind("match-live", keys(("Esc ◄┘", "Escape Return"), ("F9", "F9"), ("R", "r"), ("spacebar", "space"),
                            ("←→", "Left Right"), ("↓↑", "Up Down")), polled=True, evidence=_CAT),
    Kind("match-summary-save-prompt", _YES_NO, polled=True, evidence=_CAT),
    # the new game (T106): [confirmed: catalogue.tsv's screen rows, E015-r0001 state 2, E015-r0004 state 2,
    # E015-r0007 states 3 and 10]
    Kind("title-load-prompt", _YES_NO, evidence=_CAT),
    Kind("title-player-count", keys(("←→", "Left Right"), ("◄┘", "Return")), evidence=_CAT),
    Kind("country-select", keys(("INS", "Insert"), ("spacebar", "space"), ("←→↑↓", "Left Right Up Down"),
                                ("◄┘", "Return")), evidence=_CAT),
    Kind("country-select-name-entry", keys(("Esc", "Escape"), ("characters", "(typed)"), ("◄┘", "Return")),
         polled=True, evidence=_CAT + "; polled: F032 (poll 214B:0DB9, read 214B:112B)"),
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
    Kind("title-tune", _YES_NO, designed=True, polled=True,
         evidence="[designed] the title's tune under the load question (1771:06F3): it ends at a key, which the "
                  "title's read then takes; its keys are the question's"),
    # the Team and Pool route (T107): SELECT YOUR TEAM outside a match and the screens it opens
    Kind("select-squad", keys(("←→", "Left Right"), ("↑↓", "Up Down"), ("◄┘", "Return"), ("Ins", "Insert"),
                              ("F2", "F2"), ("R,C", "r c"), ("T", "t"), ("Esc", "Escape")), designed=True,
         evidence="[designed] SELECT YOUR TEAM, the squad list (0791:E44F from the manager menu): 'Use ←→ to toggle', "
                  "'Use ↑↓ to find player, ◄┘ to select', 'Hit Ins for assistant's recommended 20', 'F2-new name', "
                  "'R,C-reposition', 'T-tactics', '◄┘-move player', 'Esc-exit'"),
    Kind("select-squad-pool", keys(("←→", "Left Right"), ("↑↓", "Up Down"), ("◄┘", "Return"), ("F2", "F2"),
                                   ("R,C", "r c"), ("T", "t"), ("Esc", "Escape")), designed=True,
         evidence="[designed] SELECT YOUR TEAM, the pool list (0791:E2E6): 'Use ←→ to toggle', 'Use ↑↓ to find "
                  "player, ◄┘ to select', 'F2-new name', 'R,C-reposition', 'T-tactics', '◄┘-move player', 'Esc-exit'"),
    Kind("own-tactics", keys(("↓↑←→", "Up Down Left Right"), ("◄┘", "Return"), ("Esc", "Escape")), designed=True,
         evidence="[designed] a player's own tactics outside a match (1771:4B61 from SELECT YOUR TEAM's T): "
                  "'↓↑←→-select', '◄┘-alter tactic', 'Esc-exit'"),
    Kind("player-name-entry", keys(("Esc", "Escape"), ("characters", "(typed)"), ("◄┘", "Return")), designed=True,
         polled=True, evidence="[designed] F2's new name (1771:4859 from SELECT YOUR TEAM): the line editor "
                               "214B:1086, polled as the new game's name entry (F032): 'Type in characters'"),
    Kind("squad-change-refused", keys(("any key", "(any)")), designed=True,
         evidence="[designed] 0791:DBFA's refusal of a pool exchange (F031): 'cannot alter squad', 'PRESS ANY KEY' "
                  "(214B:04F8)"),
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
PLAYER_COUNT = 0x0C4E         # manager_count_menu 1771:0021: the highlighted count 1..6, u214b_menu_move_word_wrap(6, 0xC4E)
GAME = 0xA923                 # the game record (globals.tsv): +1 the current manager (set_managed_countries 1771:2D15)


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
    # mode 2 is the new game's PLEASE SELECT YOUR COUNTRY (DS:14F4), called by set_managed_countries 1771:2D15 for
    # each manager (push cs; call, returning to 1771:2D55: E038-r0001's country-select state, F032).
    if f.byte(f.bp, -1) != 0:
        return None
    mode = f.byte(f.bp, 6)
    if mode == 2:
        return "country-select" if f.far_caller(f.bp) == "1771:2D55" else None
    return {1: "team-info", 3: "history-browse"}.get(mode)


def _team_info_view(f):
    # [confirmed: named/seg_1771_02.c 26B9] Up and Down move the row DS:0DB6 (1..16) within a column of 16, crossing
    # to the next or previous column at its ends; Left and Right move the column's first index DS:0DB4 (1, 17, ...,
    # 113) by 16; the country is the order's byte DS:0DB4 + DS:0DB6 - 1.
    row, top = f.ds_byte(BROWSE_ROW), f.ds_word(BROWSE_TOP)
    out = {"country": f.far_byte(COUNTRY_ORDER, row + top - 1), "row": row}
    if f.byte(f.bp, 6) == 2:
        out.update(top=top, index=top + row - 1, manager=f.far_byte(GAME, 1))
    return out


def _title_tune(f):
    # [confirmed: named/seg_1771_01.c 080C, 07B4, 06F3] The title (1771:080C) draws the load question, then plays its
    # tune (07B4 near-calls 06F3 at 07B8), which polls "key pressed?" before each note (returns 0723 and 0782) and
    # returns at a key; 080C near-calls 07B4 at 0857 and then reads the key (1771:085F). E039's traces: 216 + 117
    # polls when no key comes.
    return "title-tune" if f.near_caller(f.bp) == 0x07BB and f.near_caller(f.up(f.bp)) == 0x085A else None


def _name_entry(f, bp):
    # [confirmed: F032 (E038-r0001's trace); seg_214B_02.asm 1086, 1124, 1128; named/seg_1771_01.c 09A0,
    # seg_1771_02.c 2D15] The manager's name is edited by the line editor 214B:1086 (u214b_edit_string_input),
    # far-called by 1771:09A0 at 0A1D, which set_managed_countries 1771:2D15 calls after the country is chosen
    # (push cs; call, returning to 1771:2E05). The editor near-calls its cursor wait 214B:0D90 at 1124, which polls
    # (return 0DB9), and reads at 1128 (return 112B). `bp` is the editor's frame.
    if f.far_caller(bp) == "1771:0A22" and f.far_caller(f.up(bp)) == "1771:2E05":
        return "country-select-name-entry"
    # [T107; confirmed: named/seg_1771_03.c 1771:4859, named/seg_0791_12.c E44F] F2 on SELECT YOUR TEAM calls
    # 1771:4859(2, 8, player) at 0791:E6FB (return E700), which far-calls the editor at 1771:489B (return 48A0).
    if f.far_caller(bp) == "1771:48A0" and f.far_caller(f.up(bp)) == "0791:E700" and not f.ds_byte(MATCH_MENU_USED):
        return "player-name-entry"
    return None


def _bulletin(f):
    # 000E:05F6, the news pages' key wait, near-called by: post_match_news_and_sack 4E0E at 4F6F; welcome_new_manager
    # 000E:68A4 at 6961 ("APPOINT A NEW MANAGER", F032's first bulletin); announce_stage_to_manager 000E:60CB at 6622
    # ("GROUPS ARE ANNOUNCED", the second) [confirmed: named/seg_000E_04.c, seg_000E_05.c; E038-r0001's trace].
    return "bulletin" if f.near_caller(f.bp) in (0x4F72, 0x6964, 0x6625) else None


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
    if caller == "1771:4C0A":
        return _own_tactics(f)
    return None


def _menu_view(f):
    caller, up = f.far_caller(f.bp), f.up(f.bp)
    if caller == "1771:4C0A":
        return _own_view(f)
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


# [confirmed: code/seg_000E_09.asm 7620, 771A] main_menu_loop far-calls select_team_screen at 7620 (Space, Left or
# Right on the menu) and at 771A (Enter on its item 5, select squad): the return addresses its frame holds.
SELECT_FROM_MENU = ("000E:7625", "000E:771F")
POOL_TOP, POOL_CURSOR = 0x52, 0x5E   # the game record's words +0x52 + 2m and +0x5E + 2m: the pool list's top and row


def _select_team(f):
    # select_team_screen 0791:E44F(country): with DS:066D, DS:0C20 clear, DS:0C1F set (a match's menu), a
    # substitution left (DS:9B3A + local_5 [bp-3]) and DS:9B41 set, E2A0 draws "make substitutions now" (DS:4840) and,
    # with the cursor DS:0C1B below 12, "take off this player" (DS:4720) (named/seg_0791_11.c E44F, E2A0); the squad
    # view is local_7 [bp-5] = 1 (seg_0791_22.asm E495).
    # [T107; confirmed: named/seg_0791_12.c E44F] Called by the manager menu (SELECT_FROM_MENU) with DS:0C1F clear
    # (outside a match, F031), it is SELECT YOUR TEAM: local_7 [bp-5] 1 shows the squad list, 2 the pool list (Left
    # and Right toggle it); E44F clears DS:0C20 itself when no match is set up. Its other states have no entry yet.
    if (not f.ds_byte(MATCH_MENU_USED) and not f.ds_byte(SUMMARY_FILE) and not f.ds_byte(VIEW_ONLY)
            and f.far_caller(f.bp) in SELECT_FROM_MENU):
        return {1: "select-squad", 2: "select-squad-pool"}.get(f.word(f.bp, -5))
    if (f.ds_byte(SUMMARY_FILE) or f.ds_byte(VIEW_ONLY) or not f.ds_byte(MATCH_MENU_USED)
            or not f.ds_byte(SUBSTITUTIONS_LEFT + f.byte(f.bp, -3)) or not f.ds_byte(SUBS_ALLOWED)
            or f.word(f.bp, -5) != 1):
        return None
    return "squad-substitution-take-off" if f.ds_word(SELECT_CURSOR) < 12 else None


def pool_item(f):
    """The pool list's highlighted item 1..80 and its A927 index [confirmed: named/seg_0791_12.c 0791:DDCB
    pool_selection_index, 214B:15B1]: item = top + row - 1, index = DS:6D18[m] + item - 1 (F011)."""
    game = f.far(GAME)
    m = f.read(game + 1, 1)[0]
    top = int.from_bytes(f.read(game + POOL_TOP + 2 * m, 2), "little")
    row = int.from_bytes(f.read(game + POOL_CURSOR + 2 * m, 2), "little")
    item = top + row - 1
    return item, top, row, f.ds_word(POOL_BASE + 2 * m) + item - 1


POOL_BASE, POOL_INDICES = 0x6D18, 0xA927     # F011: manager m's first pool index DS:6D18[m]; the indices [DS:A927]


def _select_view(f):
    slot, country = f.ds_word(SELECT_CURSOR), f.word(f.bp, 6)
    out = {"slot": slot, "player": f.far_word(COUNTRIES, COUNTRY_SIZE * country + 2 * (slot - 1))}
    if not f.ds_byte(MATCH_MENU_USED):
        # [confirmed: named/seg_0791_12.c DEA6] local_3 [bp-1] set: a player is marked by the first Enter; local_9
        # [bp-7] is his list (1 the squad, 2 the pool) and local_b [bp-9] his slot or pool index (DE27).
        out.update(country=country, side=f.word(f.bp, -5),
                   marked=(f.word(f.bp, -7), f.word(f.bp, -9)) if f.byte(f.bp, -1) else None)
        if out["side"] == 2:
            item, top, row, index = pool_item(f)
            out.update(item=item, top=top, row=row, index=index,
                       player=f.far_word(POOL_INDICES, 2 * index))
    return out


def _own_tactics(f):
    # [confirmed: named/seg_1771_04.c 1771:4B61 edit_own_tactics] its key read is u214b_menu_read_key_and_move, far-
    # called at 1771:4C05 (return 4C0A); 4B61's own caller is SELECT YOUR TEAM's T (0791:E758, return E75D). Outside a
    # match (DS:0C1F clear) it is own-tactics; in a match it is kinds.tsv's squad-substitution-tactic (no entry yet).
    up = f.up(f.bp)
    if f.far_caller(up) != "0791:E75D" or f.ds_byte(MATCH_MENU_USED):
        return None
    return "own-tactics"


def _own_view(f):
    # [confirmed: code/seg_0791_22.asm E748-E758, seg_1771_07.asm 4BF7-4C05] E44F pushes the player, then the flag
    # "the squad list is up", so 4B61 finds the player at [bp+8] and the flag at [bp+6]; 4B61 pushes DS:0F38's far
    # pointer, then the row count cVar1 + 4, so the reader 1560 finds the count at its [bp+6]. The row DS:0F38: 1..4
    # the elements 1..4, 5 the man-marking, offered (a count of 5) only with a match set up.
    up = f.up(f.bp)
    return {"row": f.ds_word(OWN_ROW), "player": f.word(up, 8), "squad": bool(f.byte(up, 6)), "rows": f.word(f.bp, 6)}


OWN_ROW = 0x0F38           # 1771:4B61: the row (word), u214b_menu_read_key_and_move(cVar1 + 4, 0xF38)


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


def _refusal_chain(f):
    up = f.up(f.bp)
    if f.far_caller(f.bp) != "214B:054E" or f.far_caller(up) != "214B:1793":
        return None
    return f.up(up)


def _refusal(f):
    box = _refusal_chain(f)
    return "squad-change-refused" if box is not None and f.far_caller(box) in ("0791:DC3D", "0791:DC68") else None


def _refusal_view(f):
    # [confirmed: named/seg_214B_01.c 04F8] the box's message is its local_53, a Pascal string of 80 at [bp - 0x51].
    up = f.up(f.bp)
    n = min(f.byte(up, -0x51), 80)
    text = bytes(f.read(f.ss * 16 + ((up - 0x50) & 0xFFFF), n)).decode("cp437")
    return {"message": text, "why": {"0791:DC3D": "finals", "0791:DC68": "tour"}[f.far_caller(_refusal_chain(f))]}


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
    Site("000E:0629", False, "000E:05F6, the news pages' key wait", _ROUTES + "; E038-r0001's after-name states",
         _bulletin),
    # [T107; confirmed: code/seg_214B_02.asm 0983-098A, seg_214B_01.asm 054B, seg_214B_03.asm 1790, seg_0791_22.asm
    # DC38, DC63] 214B:0983 reads a key (push cs; call 08DD, return 098A) for the message box 214B:04F8 (near-called at
    # 054B, return 054E), which 214B:1765 calls at 1790 (return 1793); 0791:DBFA calls 1765 at DC38 ("during finals",
    # return DC3D) and DC63 ("whilst on tour", return DC68): F031's refusals of a pool exchange.
    Site("214B:098A", False, "214B:0983 under 214B:04F8 (the message box), from 0791:DBFA", "T107 (F031)",
         _refusal, _refusal_view),
    # -- the new game's reads (T106) [confirmed: F032, E038-r0001: each state's 08DD frame and callers] ----------------
    Site("1771:085F", False, "1771:080C (the title), far-called by the main program at 0000:0024",
         "E038-r0001's title-keywait state; E039's records", lambda f: "title-load-prompt"
         if f.far_caller(f.bp) == "0000:0029" else None),
    Site("1771:0081", False, "1771:0021 manager_count_menu, near-called by 1771:080C at 08A5",
         "E038-r0001's title-player-count state", lambda f: "title-player-count" if f.near_caller(f.bp) == 0x08A8
         else None, lambda f: {"managers": f.ds_byte(PLAYER_COUNT)}),
    Site("214B:112B", False, "214B:1086 the line editor (reads after its cursor wait's poll says a key waits)",
         "F032; E038-r0001's trace", lambda f: _name_entry(f, f.bp)),
    # -- polls (the return address of a call of 214B:0723) ------------------------------------------------------------
    Site("0791:93C2", True, "0791:9372 match_key_poll (93BD; reads at 93CE)", _ROUTES, lambda f: "match-live"),
    Site("0791:CC54", True, "0791:CC2E wait_or_key", "T100 (F030); " + _ROUTES, _wait_or_key),
    Site("0791:CEDE", True, "0791:CC7B choose_captain_or_taker (CED9; reads at CEE8)", _ROUTES,
         lambda f: _captain(f, f.bp)),
    Site("0791:0BE1", True, "0791:0B7C ask_do_you_want (0BDC; reads at 0BE7)", _ROUTES,
         lambda f: _ask(f.near_caller(f.bp))),
    Site("0791:C5C8", True, "0791:C50C show_computer_substitution_notice (C5C3; reads at C5CC)", _ROUTES,
         lambda f: "substitution-notice"),
    Site("1771:0723", True, "1771:06F3, the title's tune (before each note)", "E039's traces (NG-10)", _title_tune),
    Site("1771:0782", True, "1771:06F3, the title's tune (the second run of notes)", "E039's traces (NG-10)",
         _title_tune),
    # the cursor wait 214B:0D90, near-called by the editor at 1124, polls at 0DB9 (F032); the editor's frame is [bp].
    Site("214B:0DB9", True, "214B:0D90, the line editor 214B:1086's cursor wait (1124; reads at 112B)",
         "F032; E038-r0001's trace", lambda f: _name_entry(f, f.up(f.bp)) if f.near_caller(f.bp) == 0x1127
         else None),
)}


def identify(site, frame):
    """The kind the original shows at `site` (a read's or a poll's), or None when the table has no entry for it."""
    entry = SITES.get(site)
    return None if entry is None else entry.kind(frame)


def view(site, frame):
    """The cursor or selection of the screen at a read `site` ({} for a screen without one)."""
    entry = SITES.get(site)
    return {} if entry is None or entry.view is None else entry.view(frame)
