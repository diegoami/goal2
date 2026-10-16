"""Key drivers for the original's screens: goal2 gives a decision, these press the original's keys for it.

Each driver is closed-loop: at every key read it looks at the screen's own state in guest memory (the highlighted
item, row or squad slot, the byte a key changes) and returns the next key, so nothing depends on a recorded key
sequence. The screens are the original's (static/goal-exe/named/): the team menu 0791:ED8A, the tactics screen
1771:1981, SELECT TEAM 0791:E44F, a player's own tactics 1771:4B61, the captain prompt 0791:CC7B. goal2 never
sees them.

Key codes are what 214B:08DD stores in DS:A976 (seg_214B_02.asm:16-54): the character, or for an extended key its
scan code adjusted (Left -1, Right -2, End..PgDn -3) plus 0x64."""
ENTER, ESC = 0x0D, 0x1B
UP, DOWN, LEFT, RIGHT = 0xAC, 0xB1, 0xAE, 0xAF
KEY_R, KEY_T = ord("R"), ord("T")     # upcased by 23E4:19B2 before E44F compares them

# The team menu ED8A (named seg_0791_12.c in_match_menu): ten items, 1-5 for team 1 (DS:9B36) and 6-10 for
# team 0 (DS:9B34): `local_4 = local_9 < 6; local_7 = DS:9B34[local_4]`. Per side: +0 team tactics (1771:1981),
# +1 select team (E949 -> E44F), +2 E929, +3 the match board, +4 leave ("play", checked by EA09).
MENU_TACTICS, MENU_SELECT, MENU_PLAY = 0, 1, 4
MENU_ITEM_BP = -7       # ED8A's local_9 (the highlighted item, a word) at [bp - 7] (Ghidra's local_N = [bp-(N-2)])
TACTICS_ROW, TACTICS_ELEMENT_OF_ROW = 0x0D8E, 0x6BBF   # 1771:1981: row DS:0D8E toggles element DS:6BBF[row]
# SELECT TEAM E44F: the squad cursor DS:0C1B (1..20); in a match Enter marks then swaps (E022) when DS:9B41 is set
# and a substitution is left, else toggles the request DS:9B40; R steps the player's position (1771:4952 ->
# 4925: +1, wrapping 0..13), T opens his own tactics (1771:4B61).
SELECT_CURSOR, SUBS_REQUEST, SUBS_ALLOWED = 0x0C1B, 0x9B40, 0x9B41
SUBS_LEFT = 0x9B3A      # substitutions left of side t at DS:9B3A + t: A4A1 sets them (A605), C5DC counts down
                        # (C7DC); DS:9B38 is only the action replay's copy (17E5 saves it, 0F08 restores it)
OWN_ROW = 0x0F38        # 1771:4B61's row (1..4 the player's override of elements 1..4, 5 his man-marking)
MARKING = 0x9A40        # the marking word of side t's squad slot s at DS:9A3E + 0x28 t + 2 s (1771:49B8)
PROMPT_SLOT_BP = -5     # CC7B's local_7 (the highlighted slot) at [bp - 5]
N_POSITIONS = 14        # position codes 0..13 (1771:4925 wraps with 214B:1452(0xE))
MAX_MOVES = 40          # cursor moves allowed for one target: every list here has at most 20 entries


class ScreenError(RuntimeError):
    """A screen did not move as its driver expects (the kit stops rather than press keys forever)."""


def step_toward(current, target):
    return DOWN if target > current else UP


class MenuPlan:
    """One visit of the team menu, from goal2's answer: tactics, then SELECT TEAM (substitutions, positions, own
    tactics and man-marking), then play.

    tactics: {element 1..8: bool}. subs: [(off, on)]. positions: {player: code 0..13}. marking: {player: opponent
    player word or 0}. own: {player: {element 1..4: True, False or None (no override)}}."""

    def __init__(self, side, tactics=None, subs=None, positions=None, marking=None, own=None):
        self.side = side
        self.tactics = {int(e): bool(v) for e, v in (tactics or {}).items()}   # keys may be JSON strings
        self.jobs = [("sub", int(a), int(b)) for a, b in (subs or [])]
        self.jobs += [("position", int(p), int(c)) for p, c in (positions or {}).items()]
        players = {int(p) for p in (marking or {})} | {int(p) for p in (own or {})}
        for p in sorted(players):
            self.jobs.append(("own", p, {int(e): v for e, v in ((own or {}).get(p) or (own or {}).get(str(p)) or {}).items()},
                              (marking or {}).get(p, (marking or {}).get(str(p)))))
        self.steps = (["tactics"] if self.tactics else []) + (["select"] if self.jobs else []) + ["play"]
        self.in_screen = None             # "tactics" or "select" while that screen is open
        self.job = 0
        self.sub_marked = False
        self.presses = 0                  # presses spent on the current job (a bound against a refusal)
        self.in_own = False
        self.own_failed = False
        self.done, self.refused = [], []  # jobs made; (job, why) refused
        self.requested = False
        self.menu_reads_after_play = 0
        self.pending_check = None
        self.last_message = None
        self.moves = 0                    # cursor moves since the last key that was not a move

    def move(self, current, target):
        self.moves += 1
        if self.moves > MAX_MOVES:
            raise ScreenError(f"the cursor does not reach {target} (it reads {current})")
        return step_toward(current, target)

    def act(self, key):
        self.moves = 0
        return key

    def item(self, step):
        base = 6 if self.side == 0 else 1
        return base + {"tactics": MENU_TACTICS, "select": MENU_SELECT, "play": MENU_PLAY}[step]

    # -- the team menu -------------------------------------------------------------------------------
    def menu_key(self, item):
        if self.in_screen is not None:     # back from a screen: that step is done
            self.steps.pop(0)
            self.in_screen = None
        step = self.steps[0]
        target = self.item(step)
        if item != target:
            return self.move(item, target)
        if step == "play":
            self.menu_reads_after_play += 1
        else:
            self.in_screen = step
        return self.act(ENTER)

    # -- the tactics screen ----------------------------------------------------------------------------
    def tactics_key(self, row, element_of_row, tactics_byte):
        for element, want in self.tactics.items():
            if bool(tactics_byte >> (element - 1) & 1) != want:
                rows = [r for r in range(1, 9) if element_of_row[r] == element]
                if not rows:
                    raise ValueError(f"tactic element {element} has no row on the tactics screen")
                if row != rows[0]:
                    return self.move(row, rows[0])
                self.presses += 1
                if self.presses > 2 * len(self.tactics) + 2:      # the screen does not toggle (view only)
                    break
                return self.act(ENTER)
        return self.act(ESC)

    # -- SELECT TEAM -----------------------------------------------------------------------------------
    def _next_job(self, why=None):
        if why is not None:
            self.refused.append((self.jobs[self.job], why))
        self.job += 1
        self.sub_marked, self.presses = False, 0

    def select_key(self, s):
        """s: the screen state: cursor, squad (20 words), allowed, request, subs_left, position(player)."""
        if self.pending_check is not None:        # the swap Enter was pressed: did the original make it?
            job = self.pending_check
            self.pending_check = None
            if job[2] in s["squad"][:11] and job[1] not in s["squad"][:11]:
                self.done.append(job)
            else:
                self.refused.append((job, self.last_message or "refused by the original"))
            self.last_message = None
        while self.job < len(self.jobs):
            job = self.jobs[self.job]
            kind, player = job[0], job[1]
            if kind == "sub" and (not s["allowed"] or s["subs_left"] == 0):
                if s["request"] == 0 and s["subs_left"] and not self.requested:
                    self.requested = True
                    return self.act(ENTER)        # toggles DS:9B40 on: the original offers it at the next stoppage
                self.job += 1                     # requested (or nothing left): the swap waits for the notice
                continue
            want = job[2] if (kind == "sub" and self.sub_marked) else player
            if want not in s["squad"]:
                self._next_job(f"player {want} is not in the squad")
                continue
            slot = s["squad"].index(want) + 1
            if s["cursor"] != slot:
                return self.move(s["cursor"], slot)
            if kind == "sub":
                self.sub_marked = not self.sub_marked
                if not self.sub_marked:           # the second Enter: the swap (or the original's refusal)
                    self.pending_check = job
                    self.job += 1
                return self.act(ENTER)
            if kind == "position":
                if s["position"](player) == job[2]:
                    self.done.append(job)
                    self._next_job()
                    continue
                self.presses += 1
                if self.presses > N_POSITIONS + 1:
                    self._next_job(f"position {job[2]} not reached")
                    continue
                return self.act(KEY_R)
            if kind == "own":
                if self.in_own:                   # back from his own tactics
                    self.in_own = False
                    if not self.own_failed:
                        self.done.append(job)
                    self._next_job()
                    continue
                self.in_own, self.own_failed, self.presses = True, False, 0
                return self.act(KEY_T)
        return self.act(ESC)

    # -- a player's own tactics (1771:4B61) ---------------------------------------------------------------
    def own_key(self, row, own_set, marking_word, team_set, can_mark):
        """row: DS:0F38; own_set: his +0xF; marking_word: his DS:9A3E slot word; can_mark: row 5 is shown."""
        job = self.jobs[self.job]
        wanted, mark = job[2], job[3]
        for e, v in sorted(wanted.items()):
            has = bool(own_set >> (e + 3) & 1)            # element e + 4: he has his own setting for tactic e
            val = bool(own_set >> (e - 1) & 1)
            if (v is None and has) or (v is not None and (not has or val != v)):
                if row != e:
                    return self.move(row, e)
                self.presses += 1
                if self.presses > 3 * len(wanted) + 3:
                    return self._own_refused(job, f"own tactic {e} not reached")
                return self.act(ENTER)
        if mark is not None and marking_word != mark:
            if not can_mark:
                return self._own_refused(job, "the original offers no man-marking for this player")
            if row != 5:
                return self.move(row, 5)
            self.presses += 1
            if self.presses > 3 * len(wanted) + 14:
                return self._own_refused(job, f"cannot mark player {mark}")
            return self.act(ENTER)
        return self.act(ESC)

    def _own_refused(self, job, why):
        self.refused.append((job, why))
        self.own_failed = True
        return self.act(ESC)
