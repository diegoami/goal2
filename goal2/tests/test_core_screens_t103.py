"""T103 (G9, #315): the screen catalogue of the core: each read and poll site is a kind, checked against the text.

Evidence (goal2-archaeology at 53d7ef5): the kinds and their text rules static/screens/kinds.tsv, their keys
static/screens/catalogue.tsv (docs/screens.md, T39a); the key codes of 214B:08DD (static/goal-exe/code/
seg_214B_02.asm 08DD-0941); the captain table DS:9978 + 10 side (routines.tsv 0791:CC7B, F029, F030). The goal2
kinds' quoted texts are docs/core.md's table. Nothing of the original is in this file: it reads .cache/ and skips
without.

The text page is the oracle: the core never reads it to identify a screen (goal2/core/screens.py); here every wait's
kind, and every polled screen's at its first poll, must be the kind kinds.tsv's rule gives that text, or, for a goal2
kind, the one whose quotes docs/core.md lists.
"""
import hashlib
import re
import unittest

from goal2.tests import requires

TEMPLATE, HALFTIME = "e006-r0001-main.sav", "e010-r0001-halftime.sav"
NEEDS = {"modules": ("unicorn",), "files": (TEMPLATE, HALFTIME, "GOAL.DAT"), "archaeology": True}
# [designed: #316] The tests that run the original are slow tests (GOAL2_SLOW=1; the gate runs them whenever
# goal2/core/ changes, tools/check_premerge.py SLOW_PATHS), but Unknown, its one real case in the default run.

# [confirmed: seg_214B_02.asm 08DD-0941] the code 08DD returns: the character, or an extended key's scan code
# (Left -1, Right -2, End..PgDn -3) + 0x64. Written out here, apart from goal2/core/screens.py, as the oracle.
SCAN = {"F1": 0x3B, "F2": 0x3C, "F3": 0x3D, "F4": 0x3E, "F5": 0x3F, "F7": 0x41, "F9": 0x43, "F10": 0x44,
        "Home": 0x47, "Up": 0x48, "Prior": 0x49, "Left": 0x4B - 1, "Right": 0x4D - 2, "End": 0x4F - 3,
        "Down": 0x50 - 3, "Next": 0x51 - 3, "Insert": 0x52}
CHARS = {"Return": 0x0D, "Escape": 0x1B, "space": 0x20, "BackSpace": 0x08}
ESC, ENTER, UP, DOWN, LEFT, RIGHT = 0x1B, 0x0D, 0x48 + 0x64, 0x4D + 0x64, 0x4A + 0x64, 0x4B + 0x64
F10 = 0x44 + 0x64
CAPTAIN = 0x9978          # routines.tsv 0791:CC7B: the captain's word at DS:9978 + 10 side
FIRST_TEAM = 0x9B34       # the first side's country (kit match.py; screens.py of the kit)


def code(sym):
    if sym in ("(any)", "(typed)"):
        return sym[1:-1]
    return SCAN[sym] + 0x64 if sym in SCAN else CHARS.get(sym, ord(sym) if len(sym) == 1 else None)


def tsv(path):
    lines = (requires.archaeology() / path).read_text().splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, line.split("\t"))) for line in lines[1:] if line.strip()]


def rules():
    return {r["kind"]: [(p[0], " ".join(p[1:].split())) for p in r["rule"].split(" ;; ")]
            for r in tsv("static/screens/kinds.tsv")}


def catalogue_keys(kind):
    """The kind's screen and owner rows of catalogue.tsv as {(label, (code, ...))} (owner.tsv rows count too)."""
    rows = [r for r in tsv("static/screens/catalogue.tsv") if r["kind"] == kind and r["source"] in ("screen", "owner")]
    rows += [r for r in tsv("static/screens/owner.tsv") if r.get("kind") == kind]
    return {(r["key"], tuple(code(s) for s in r["keysyms"].split())) for r in rows}


def printed_keys():
    """docs/core.md's table "Keys the screen prints" [T107]: {kind: [(keys, state, row, quote)]}."""
    out = {}
    for line in (requires.ROOT / "docs/core.md").read_text().splitlines():
        cells = [c.strip() for c in line.split("|")]
        if (len(cells) > 6 and cells[1].startswith("`") and cells[1].endswith("`") and cells[4].startswith("row ")
                and '"' in cells[5]):
            out.setdefault(cells[1].strip("`"), []).append((cells[2], cells[3], cells[4],
                                                            re.findall(r'"([^"]+)"', cells[5])))
    return out


def designed_quotes():
    """docs/core.md's table of goal2 kinds: {kind: [quoted text, ...]}."""
    out = {}
    for line in (requires.ROOT / "docs/core.md").read_text().splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 5 and cells[1].startswith("`") and cells[1].endswith("`") and '"' in cells[4]:
            out[cells[1].strip("`")] = re.findall(r'"([^"]+)"', cells[4])
    return out


def text_kind(text):
    """The text oracle: the kinds.tsv kind whose rule matches (docs/screens.md: runs of whitespace as one space),
    else the goal2 kind all of whose docs/core.md quotes occur; None when neither."""
    flat = " ".join(text.split())
    hits = [k for k, rule in rules().items() if all((p in flat) == (s == "+") for s, p in rule)]
    if len(hits) > 1:
        raise AssertionError(f"two kinds.tsv rules match: {hits}")
    if hits:
        return hits[0]
    designed = [k for k, quotes in designed_quotes().items() if all(" ".join(q.split()) in flat for q in quotes)]
    if len(designed) > 1:
        raise AssertionError(f"two goal2 kinds match: {designed}")
    return designed[0] if designed else None


def highlighted(wait):
    """The runs of reverse-video cells (attribute 0x70, 214B:13C5) on the screen: [(row, column, text)]."""
    lines = wait.text.splitlines() + [""] * 25
    runs, cur = [], None
    for i in range(2000):
        row, col = divmod(i, 80)
        if wait.screen[2 * i + 1] == 0x70:
            ch = lines[row][col] if col < len(lines[row]) else " "
            if cur and cur[0] == row and cur[3] == col - 1:
                cur[2] += ch
                cur[3] = col
            else:
                cur = [row, col, ch, col]
                runs.append(cur)
    return [(r, c, t) for r, c, t, _ in runs]


def savestate(name):
    requires.require(**NEEDS)
    return (requires.CACHE / name).read_bytes()


def play(core, steps, waits):
    """Press or queue each step; before a press, the wait's kind must list the key (never press an unlisted key)."""
    from goal2.core.screens import KINDS
    for step in steps:
        if isinstance(step, tuple):
            core.queue(*step)
            continue
        kind = core.wait.kind
        assert KINDS[kind].accepts(step), f"{kind} does not list the key {step:#04x}"
        waits.append(core.press(step))
    return waits


# Tour Q (E006-r0001): team info, the menu, the fixture list's three cases, the match menu, both tactics screens,
# then play with keys queued: Down and Enter at the captain prompt (the next slot's player), R in play (the quick
# result), and on through both boards, the menus, the bulletin, F10 and Y.
TO_MATCH_MENU = [ESC, DOWN, ENTER, DOWN, ENTER, ENTER, ESC] + [DOWN] * 4 + [ENTER]
TACTICS = [LEFT, UP, ENTER, ESC, RIGHT, ENTER, ESC, UP]
QUEUED = [("captain-select", DOWN), ("captain-select", ENTER), ("match-live", ord("r"))]
AFTER_PLAY = [ENTER, ENTER, ENTER, ENTER, ENTER, F10, ord("y")]
# Tour W (E006-r0001): the same match menu, play with nothing queued: the captain prompt and both halves pass by
# themselves; the boards, the menus, the bulletin.
WATCHED = [ENTER, ENTER, ENTER, ENTER, ENTER, ENTER]
# Tour E (E010-r0001, at half time): the board, the match menu, the bench, the tournament, the match stats.
HALF_TIME = [ENTER, LEFT, ENTER, ESC, DOWN, ENTER, ESC, DOWN, ENTER, ENTER]


@requires.need(**NEEDS, slow=True)
class Tours(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.core import Core
        data = savestate(TEMPLATE)
        core = Core.start(data).core
        cls.q = play(core, TO_MATCH_MENU + TACTICS, [core.wait])
        cls.pre_play = core.save()                      # the match menu, nothing queued (Tour W starts here)
        play(core, QUEUED, [])
        cls.midway = core.save()                        # the same, with the three keys queued
        cls.q_captain = None
        play(core, [ENTER], cls.q)
        cls.q_captain = core.wait.state.rd(CAPTAIN + 10 * cls.side(core.wait), 2)
        cls.q_squad = cls.squad(core.wait)
        play(core, AFTER_PLAY, cls.q)
        cls.q_sha = core.memory_sha256()

        resumed = Core.load(cls.midway)
        cls.resumed = [resumed.wait]
        play(resumed, [ENTER] + AFTER_PLAY, cls.resumed)
        cls.resumed_sha = resumed.memory_sha256()

        core = Core.load(cls.pre_play)
        cls.w = play(core, [ENTER], [core.wait])
        cls.w_captain = core.wait.state.rd(CAPTAIN + 10 * cls.side(core.wait), 2)
        play(core, WATCHED[1:], cls.w)

        core = Core.start(savestate(HALFTIME)).core
        cls.e = play(core, HALF_TIME, [core.wait])
        cls.waits = cls.q + cls.w + cls.e

    @staticmethod
    def side(wait):
        return 0 if wait.state.rd(FIRST_TEAM, 2) in wait.state.managed else 1

    @staticmethod
    def squad(wait):
        country = wait.state.managed[0]
        return wait.state.squad(country)

    def passed(self, tour):
        return [p for w in tour for p in w.passed]

    def test_the_tours_visit_sixteen_kinds(self):
        waited = {w.kind for w in self.waits}
        polled = {p.kind for p in self.passed(self.waits)}
        for kind in ("manager-menu", "quit-confirm", "save-game-prompt", "fixtures-watch", "fixtures-auto",
                     "match-menu", "match-menu-halftime", "match-menu-fulltime", "match-summary", "team-tactics",
                     "squad-substitution-take-off", "bulletin"):
            self.assertIn(kind, waited)
        self.assertGreaterEqual(len(waited | polled), 16, sorted(waited | polled))
        for kind in ("captain-select", "match-live"):
            with_keys = [p for p in self.passed(self.q) if p.kind == kind]
            without = [p for p in self.passed(self.w) if p.kind == kind]
            self.assertTrue(any(p.keys for p in with_keys), kind)     # read a queued key
            self.assertTrue(without and not any(p.keys for p in without), kind)
        self.assertEqual([p.keys for p in self.passed(self.q) if p.kind == "captain-select"], [(DOWN, ENTER)])
        self.assertEqual([p.keys for p in self.passed(self.q) if p.kind == "match-live"][0], (ord("r"),))
        self.assertGreaterEqual([p.polls for p in self.passed(self.w) if p.kind == "captain-select"][0], 1000)

    def test_a_queued_key_at_the_captain_prompt_picks_the_next_slot(self):
        # No key: the computer's pick stands (F030). Down then Enter: the highlight moves one slot and Enter picks it.
        slot = self.q_squad.index(self.w_captain)
        self.assertNotEqual(self.q_captain, self.w_captain)
        self.assertEqual(self.q_captain, self.q_squad[slot + 1])

    def test_every_kind_is_the_one_its_text_gives(self):
        for w in self.waits:
            self.assertEqual(w.kind, text_kind(w.text), f"{w.site}\n{w.text}")
        for p in self.passed(self.waits):
            self.assertEqual(p.kind, text_kind(p.text), p.text)

    def test_shared_readers_are_told_apart(self):
        tactics = {w.kind for w in self.q if w.site == "214B:157C" and w.view.get("country")}
        self.assertEqual(tactics, {"team-tactics", "team-tactics-view"})
        fixtures = [w.kind for w in self.q if w.site == "000E:016C"]
        self.assertEqual(set(fixtures), {"fixture-list", "fixtures-watch", "fixtures-auto"})
        questions = [w.kind for w in self.q if w.site == "214B:09C4"]
        self.assertEqual(questions, ["quit-confirm", "save-game-prompt"])

    def test_views_show_the_highlighted_item(self):
        from goal2.data import goaldat
        names = goaldat.load((requires.CACHE / "GOAL.DAT").read_bytes()).country_names
        tactic_rows = ("defence", "protection", "offside", "positioning", "possession", "passing", "tackling",
                       "marking")
        seen = set()
        for w in self.waits:
            runs = highlighted(w)
            v = w.view
            if w.kind in ("manager-menu",) or w.kind.startswith("match-menu"):
                hit = [t for _, _, t in runs if t.strip() == v["label"]]
                self.assertEqual(len(hit), 1, (w.kind, v, runs))
            elif w.kind == "team-info":
                self.assertIn((v["row"] + 6, 64, names[v["country"]].ljust(15, "-")), runs)
            elif w.kind.startswith("fixture"):
                line = [t for r, _, t in runs if r == v["row"] + 6]
                self.assertEqual(len(line), 1, runs)
                for c in v["teams"]:
                    self.assertIn(names[c], line[0])
            elif w.kind == "team-tactics":
                self.assertTrue(any(t.startswith(tactic_rows[v["row"] - 1]) for _, _, t in runs), (v, runs))
                self.assertEqual(names[v["country"]], names[w.state.managed[0]])
            elif w.kind == "team-tactics-view":
                self.assertIn("│" + names[v["country"]].ljust(15, "-") + " status", w.text)
            elif w.kind == "squad-substitution-take-off":
                surname = w.state.name(v["player"])
                self.assertTrue(any(c == 64 and surname[:9] in t for _, c, t in runs), (v, surname, runs))
            else:
                self.assertEqual(v, {}, w.kind)
                continue
            seen.add(w.kind)
        self.assertLessEqual({"manager-menu", "team-info", "fixture-list", "fixtures-watch", "fixtures-auto",
                              "match-menu", "match-menu-halftime", "team-tactics", "team-tactics-view",
                              "squad-substitution-take-off"}, seen)

    def test_straight_and_saved_midway_with_queued_keys_are_the_same(self):
        n = len(self.resumed)
        self.assertEqual(self.resumed, self.q[-n:])
        self.assertEqual([(w.site, w.kind, w.text, w.passed) for w in self.resumed],
                         [(w.site, w.kind, w.text, w.passed) for w in self.q[-n:]])
        self.assertEqual(self.resumed_sha, self.q_sha)


@requires.need(**NEEDS)
class Keys(unittest.TestCase):
    def test_each_kind_accepts_the_catalogues_keys(self):
        from goal2.core.screens import KEYSYMS, KINDS, PRINTED
        KEYSYMS_OF = {v: k for k, v in KEYSYMS.items()}
        for name, kind in KINDS.items():
            if kind.designed:
                self.assertNotIn(name, rules(), f"{name} is a kinds.tsv kind")
                self.assertIn(name, designed_quotes(), f"docs/core.md does not quote {name}")
                continue
            self.assertIn(name, rules())
            # [T107's amendment] the catalogue's screen and owner rows, and the keys the screen's own hint prints
            # (screens.PRINTED), each quoted in docs/core.md with its state and row and backed by a burst row.
            printed = set(PRINTED.get(name, ()))
            self.assertEqual(set(kind.keys), catalogue_keys(name) | printed, name)
            quoted = printed_keys().get(name, [])
            bursts = {r["key"] for r in tsv("static/screens/catalogue.tsv")
                      if r["kind"] == name and r["source"].startswith("run:")}
            for label, codes in printed:
                rows = [q for q in quoted if q[0] == label]
                self.assertTrue(rows, f"docs/core.md does not quote {name}'s printed key {label}")
                self.assertTrue(all(q[1] and q[3] and label in " ".join(q[3]) for q in rows), (name, rows))
                self.assertTrue(any(KEYSYMS_OF.get(c) in bursts for c in codes),
                                f"no catalogue burst row reads {label} on {name}")

    @requires.need(slow=True)
    def test_a_key_the_kind_does_not_accept_is_refused(self):
        from goal2.core import Core
        core = Core.start(savestate(TEMPLATE)).core
        with self.assertRaises(ValueError):
            core.queue("captain-select", ord("x"))
        with self.assertRaises(ValueError):
            core.queue("match-live", ord("y"))
        with self.assertRaises(ValueError):
            core.queue("manager-menu", ENTER)            # not a polled screen
        core.queue("captain-select", ord("c"))
        self.assertEqual(core.queued, [("captain-select", ord("c"))])


@requires.need(**NEEDS)
class Unknown(unittest.TestCase):
    def test_an_unmapped_site_stops_with_the_site_and_the_text(self):
        from goal2.core import Core, CoreError, UnknownScreen
        from goal2.core.screens import SITES
        core = Core.start(savestate(TEMPLATE)).core
        core.press(ESC)
        for _ in range(2):
            core.press(DOWN)                                 # the menu's "tournament"
        self.assertEqual(core.press(ENTER).kind, "tournament")
        # [T105] the history is mapped now; the tournament's championship display (Left, 1771:9509, reading at
        # 1771:9567) is not.
        with self.assertRaises(UnknownScreen) as caught:
            core.press(LEFT)
        e = caught.exception
        self.assertRegex(e.site, r"^[0-9A-F]{4}:[0-9A-F]{4}$")
        self.assertNotIn(e.site, SITES)
        self.assertEqual(e.text, e.text.rstrip())
        self.assertIn(e.site, str(e))
        self.assertIn(e.text, str(e))
        self.assertTrue(e.text.strip())
        self.assertIsNone(text_kind(e.text))
        with self.assertRaises(CoreError):
            core.press(ESC)


if __name__ == "__main__":
    unittest.main()
