"""T108 (#308's G14a, #331, #327): play the next game over the core: the round, the captain, the own match as the
original's quick result, the half-time bench, the results and the bulletins, and the desktop's round pages.

The text page is the oracle: each view (goal2/core/views.py, read from memory only) must equal what the original
prints at the same wait, and each wait's kind the one its kinds.tsv text rule gives (or, for a goal2 kind, its quotes
in docs/core.md), the driver taking the original there by its own keys. No test writes guest memory. Nothing of the
original is in this file: it reads .cache/ and skips without.

[designed: #316] The tests that play a round are slow tests (GOAL2_SLOW=1; the gate runs them when goal2/core/, the
round's pages or this module change, tools/check_premerge.py SLOW_PATHS); #327's runner checks are the module's one
real case in the default run.
"""
import os
import re
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

TEMPLATE = "e006-r0001-main.sav"
NEEDS = {"modules": ("unicorn",), "files": (TEMPLATE, "GOAL.DAT"), "archaeology": True}
DESKTOP = {"modules": ("unicorn", "PySide6"), "files": (TEMPLATE, "GOAL.DAT")}
SIZES = ((1440, 900), (1050, 780), (900, 640), (2560, 1600))
# [confirmed: seg_214B_02.asm 08DD-0941] the codes 08DD returns, written out here apart from goal2/core as the oracle
ENTER, C_KEY = 0x0D, ord("c")
CAPTAIN = 0x9978          # routines.tsv 0791:CC7B: the captain's word at DS:9978 + 10 side


def start():
    """A Driver at the manager menu: E006-r0001 by Esc from its team-info browser, keeping every wait."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    requires.require(**NEEDS)
    driver = Driver(Core.start((requires.CACHE / TEMPLATE).read_bytes()).core)
    driver.trail = [driver.wait]
    driver.to_menu()
    return driver


def resumed(blob):
    from goal2.core import Core
    from goal2.core.driver import Driver
    driver = Driver(Core.load(blob))
    driver.trail = [driver.wait]
    return driver


def t103():
    from goal2.tests import test_core_screens_t103 as module
    return module


def documented_gap(kind):
    """docs/core.md's section "A text rule narrower than its screen": the kinds it names."""
    text = (requires.ROOT / "docs/core.md").read_text()
    section = text.split("**A text rule narrower than its screen.**", 1)
    if len(section) < 2:
        return False
    return f"`{kind}`" in section[1].split("\n\n", 1)[0]


def oracle(kind, text):
    """The kind the text gives (T103's oracle), or ('round-results', 'gap') for the one documented case: the
    round's results of a round with no friendly, which kinds.tsv's rule (+friendly) misses; every other part of the
    rule must hold (+hit any key, -THE SOCCER BULLETIN, -MAN OF THE MATCH) and the text must list qualifiers."""
    found = t103().text_kind(text)
    flat = " ".join(text.split())
    if (found is None and kind == "round-results" and documented_gap("round-results") and "hit any key" in flat
            and "friendly" not in flat and "qualifying" in flat and "THE SOCCER BULLETIN" not in flat
            and "MAN OF THE MATCH" not in flat):
        return "round-results", "gap"
    return found


def same_line_pairs(bench_view, count):
    """Pairs (off, on) of the managed eleven and bench with the same position code (the original keeps each
    player's own, 0791:E022), the goalkeeper left on: chosen by the test, passed to the original as they are."""
    rows = {r["player"]: r for r in bench_view["squad"]}
    pairs, used = [], set()
    for off in bench_view["eleven"][1:]:
        for on in bench_view["bench"]:
            if on not in used and rows[on]["position"] == rows[off]["position"]:
                pairs.append((off, on));used.add(on)
                break
        if len(pairs) == count:
            break
    return pairs


# -- reading the original's printed screens (the oracle) ---------------------------------------------------------
SIDE_ROW = re.compile(r"│([A-Z][A-Z .'&-]*?)-*│\s*(\d*)│")


def board_text(text):
    """The board's printed score (rows 1 and 3: `│NAME---│ n│`) and each panel's scorers (the panel's country name on
    row 6, then rows 11..21 `│name│ min│`, the left panel at column 0, the right at column 59)."""
    lines = text.splitlines() + [""] * 25
    score = {}
    for row in (1, 3):
        m = SIDE_ROW.search(lines[row])
        score[m.group(1).strip()] = int(m.group(2) or 0)
    panels = re.findall(r"│ ([A-Za-z][A-Za-z .'&]*?)-* │", lines[6])
    scorers = {}
    for name, column in zip(panels, (0, 59)):
        found = []
        for row in range(11, 22):
            m = re.match(r"│(.{15})│\s*(\d+)│", lines[row][column:column + 21])
            if m and m.group(1).strip():
                found.append((m.group(1).strip(), int(m.group(2))))
        scorers[name.strip()] = found
    return score, scorers


RESULT_ROW = re.compile(r"│ -*(\S.*?)\s+(\d+)v(\d+)\s+(\S.*?)-*\s+(\S+)\s*│")


def results_text(text):
    """The round's results as the original lists them: `first  AvB  second   kind` per row."""
    out = []
    for line in text.splitlines():
        m = RESULT_ROW.search(line)
        if m:
            out.append((m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)))
    return out


class Oracle:
    def check_results(self, trail):
        """Each results view equals the original's printed round results and summary at that wait."""
        from goal2.core import views
        checked = []
        for wait in trail:
            if wait.kind == "round-results":
                view = views.round_results(wait.state, wait.view["first"], wait.view["last"])
                printed = results_text(wait.text)
                rows = [(r["first_name"], r["score"][0], r["score"][1], r["second_name"], r["kind_name"])
                        for r in view["rows"]]
                self.assertEqual(rows, printed, wait.text)
                checked.append(wait.kind)
            elif wait.kind in ("match-board", "match-summary"):
                view = views.board(wait.state)
                score, scorers = board_text(wait.text)
                self.assertEqual({n.upper(): s for n, s in zip(view["names"], view["score"])}, score, wait.text)
                for side in (0, 1):
                    shown = scorers[view["names"][side]]
                    self.assertEqual([(s["name"][:15], s["minute"]) for s in view["scorers"][side]], shown, wait.text)
                checked.append(wait.kind)
            elif wait.kind == "fixture-result":
                row = views.fixture_result(wait.state)
                score, _ = board_text(wait.text)
                self.assertEqual(score, {row["first_name"].upper(): row["score"][0],
                                         row["second_name"].upper(): row["score"][1]}, wait.text)
                checked.append(wait.kind)
        return checked

    def check_oracle(self, trail):
        gaps = []
        for wait in trail:
            found = oracle(wait.kind, wait.text)
            if isinstance(found, tuple):
                gaps.append(wait);found = found[0]
            self.assertEqual(wait.kind, found, f"{wait.site}\n{wait.text}")
            for p in wait.passed:
                self.assertEqual(p.kind, t103().text_kind(p.text), p.text)
        return gaps


# -- #327: the runner's DOS answers (the module's real case) -----------------------------------------------------
@requires.need(modules=("unicorn",), files=(TEMPLATE,))
class Runner327(unittest.TestCase):
    def test_intr_returns_the_cpus_flags_with_the_carry_clear(self):
        """[confirmed: seg_235C_01.asm 0045] Intr stores the CPU's flags after the call (pushf), not the request's."""
        from goal2.core import Core
        from goal2.core.runner import RECORD
        core = Core.start((requires.CACHE / TEMPLATE).read_bytes()).core
        core.files[5] = [b"", 0]                    # the core's own table of open files: no guest byte is written
        regs = dict.fromkeys(RECORD, 0);regs.update(AX=0x3E00, BX=5, FLAGS=0x08D5)
        cpu = core.m.reg("eflags") & 0xFFFF
        self.assertNotEqual(cpu & ~1, 0x08D5 & ~1)  # the case tells the two apart
        out = core._serve_dos(0x21, regs, "test", "Intr")
        self.assertEqual(out["FLAGS"], cpu & ~1)
        self.assertEqual(out["FLAGS"] & 1, 0)
        self.assertNotIn(5, core.files)

    def test_the_date_sets_cx_dx_and_al_only_and_the_weekday(self):
        from goal2.core.runner import date_registers
        regs = {"EAX": 0x5678ABFF, "ECX": 0xABCD1234, "EDX": 0x12345678}
        out = date_registers(regs, (1991, 10, 4))                  # a Friday
        self.assertEqual(out["ecx"], 0xABCD0000 | 1991)             # CX only: ECX's upper half kept
        self.assertEqual(out["edx"], 0x12340000 | (10 << 8) | 4)
        self.assertEqual(out["eax"], 0x5678AB00 | 5)                # AL the weekday, 0 Sunday; AH kept
        self.assertEqual(date_registers(regs, (1991, 10, 6))["eax"] & 0xFF, 0)   # a Sunday
        self.assertEqual(date_registers(regs, (2000, 2, 29))["eax"] & 0xFF, 2)   # a Tuesday


# -- the round ------------------------------------------------------------------------------------------------------
@requires.need(**NEEDS, slow=True)
class Round(Oracle, unittest.TestCase):
    """E006-r0001's first round (a friendly with Sweden) with a chosen captain and one substitution at half time, then
    its second round (the round's results, a qualifier, the table) with the original's own captain (C)."""

    @classmethod
    def setUpClass(cls):
        from goal2.core import views
        driver = cls.driver = start()
        cls.menu = driver.core.save()
        cls.menu_index = views.Memory(driver.wait.state).game(0x26, 2)
        wait = driver.round_start()
        cls.sides = views.match_sides(wait.state)
        cls.captain = cls.sides["eleven"][3]
        wait = driver.kick_off(cls.captain)
        cls.half_time = driver.core.save()
        cls.captain_at_kick_off = views.match_sides(wait.state)["captain"]
        cls.pair = same_line_pairs(views.bench(wait.state), 1)[0]
        cls.sub = driver.substitute(*cls.pair)
        driver.play_on()
        cls.first_sha = driver.core.memory_sha256()
        cls.first_trail = list(driver.trail)
        cls.first_pages = list(driver.pages)
        driver.trail = [driver.wait]
        cls.second = driver.play_round(captain=None)
        cls.second_trail = list(driver.trail)

    def test_a_whole_round_returns_to_the_menu_with_its_results_in_memory(self):
        from goal2.core import views
        for trail in (self.first_trail, self.second_trail):
            self.assertEqual(trail[-1].kind, "manager-menu")
        # the own fixture of round 1 is played in memory, with the score the full-time board printed
        state = self.first_trail[-1].state
        boards = [w for w in self.first_trail if w.kind == "match-board"]
        self.assertEqual(len(boards), 2)                             # half time and full time
        board = views.board(boards[-1].state)
        mem = views.Memory(state)
        row = views._row(mem, mem.fixture(self.menu_index))          # the fixture the round began at
        self.assertTrue(row["played"])
        self.assertEqual({row["first"], row["second"]}, set(board["teams"]))
        score = dict(zip(board["teams"], board["score"]))
        self.assertEqual((row["score"][0], row["score"][1]), (score[row["first"]], score[row["second"]]))
        # each results view equals what the original printed: both boards of round 1; the round's results, the boards
        checked = self.check_results(self.first_trail) + self.check_results(self.second_trail)
        self.assertGreaterEqual(checked.count("match-board"), 4)
        self.assertIn("round-results", checked)
        kinds = [k for k, _ in self.second["pages"]]
        self.assertEqual(kinds[0], "round-results")
        self.assertIn("tournament-table", kinds)
        self.assertIn("bulletin", kinds)
        self.assertEqual([k for k, _ in self.first_pages], ["match-board", "match-board", "bulletin"])

    def test_every_wait_has_the_kind_its_text_gives(self):
        gaps = self.check_oracle(self.first_trail + self.second_trail)
        self.assertEqual(gaps, [])        # these rounds' results list friendlies: no exception is used
        kinds = {w.kind for w in self.first_trail + self.second_trail}
        self.assertLessEqual({"manager-menu", "match-menu", "captain-select", "match-board", "match-menu-halftime",
                              "squad-substitution-take-off", "squad-substitution-put-on", "match-menu-fulltime",
                              "bulletin", "round-results", "tournament-table"}, kinds)
        passed = {p.kind for w in self.first_trail + self.second_trail for p in w.passed}
        self.assertLessEqual({"round-playing", "match-live"}, passed)

    def test_the_captain_chosen_and_the_originals_own(self):
        self.assertEqual(self.captain_at_kick_off, self.captain)
        self.assertNotEqual(self.captain, self.sides["captain"])     # moved off the original's pick by Up and Down
        log = [(k, key) for k, key in self.driver.log if k == "captain-select"]
        self.assertIn(("captain-select", C_KEY), log)
        from goal2.core import views
        boards = [w for w in self.second_trail if w.kind == "match-board"]
        sides = views.match_sides(boards[0].state)
        self.assertIn(sides["captain"], sides["eleven"])
        self.assertEqual(boards[0].state.rd(CAPTAIN + 10 * sides["managed_side"], 2), sides["captain"])

    def test_the_substitution_at_half_time(self):
        off, on = self.pair
        self.assertTrue(self.sub["made"]);self.assertIsNone(self.sub["refused"])
        self.assertIn(on, self.sub["eleven"]);self.assertNotIn(off, self.sub["eleven"])
        self.assertEqual(self.sub["left"], 4)

    def test_determinism_the_same_round_twice_and_saved_at_half_time(self):
        again = resumed(self.menu)
        again.round_start();again.kick_off(self.captain);again.substitute(*self.pair);again.play_on()
        self.assertEqual(again.core.memory_sha256(), self.first_sha)
        loaded = resumed(self.half_time)
        self.assertEqual(loaded.wait.kind, "match-menu-halftime")
        loaded.substitute(*self.pair);loaded.play_on()
        self.assertEqual(loaded.core.memory_sha256(), self.first_sha)


@requires.need(**NEEDS, slow=True)
class HalfTime(Oracle, unittest.TestCase):
    """The bench at E006-r0001's first half time: a substitution through the bench is the same keys pressed on the core
    directly; five in a friendly; the sixth refused by the original; a pair of the same block refused by it."""

    @classmethod
    def setUpClass(cls):
        driver = start()
        driver.round_start();driver.kick_off(None)
        cls.blob = driver.core.save()

    def test_a_substitution_is_the_originals_keys_and_its_counter(self):
        from goal2.core import Core, views
        driver = resumed(self.blob)
        bench = views.bench(driver.wait.state)
        self.assertEqual(bench["left"], 5)                           # a friendly: 5 a side (A4A1, F027)
        fixture = views.Memory(driver.wait.state).fixture(views.Memory(driver.wait.state).game(0x26, 2))
        self.assertEqual(fixture["kind"], 1)
        pairs = same_line_pairs(bench, 5)
        self.assertEqual(len(pairs), 5)
        result = driver.substitute(*pairs[0])
        direct = Core.load(self.blob)
        for kind, key in driver.log:
            direct.press(key)                                        # the same keys, pressed on the core directly
        self.assertEqual(direct.memory_sha256(), driver.core.memory_sha256())
        self.assertEqual(direct.wait.kind, "match-menu-halftime")
        self.assertTrue(result["made"]);self.assertIn(pairs[0][1], result["eleven"])
        self.assertEqual(result["left"], 4)
        for pair in pairs[1:]:
            self.assertTrue(driver.substitute(*pair)["made"])
        self.assertEqual(views.bench(driver.wait.state)["left"], 0)
        # the sixth: the original offers none; the bench shows its own line and counter
        eleven = views.bench(driver.wait.state)["eleven"]
        sixth = driver.substitute(eleven[1], views.bench(driver.wait.state)["bench"][0])
        self.assertFalse(sixth["made"]);self.assertEqual(sixth["eleven"], eleven);self.assertEqual(sixth["left"], 0)
        used = [w for w in driver.trail if w.kind == "substitutions-used"]
        self.assertTrue(used)
        self.assertEqual(sixth["refused"], "no more substitutes")
        self.assertIn(sixth["refused"], used[-1].text)
        self.assertRegex(used[-1].text, r"substitutions left │ 0 │")
        self.check_oracle(driver.trail)

    def test_a_pair_of_the_same_block_is_the_originals_refusal(self):
        from goal2.core import views
        driver = resumed(self.blob)
        eleven = views.bench(driver.wait.state)["eleven"]
        result = driver.substitute(eleven[2], eleven[3])
        self.assertFalse(result["made"]);self.assertEqual(result["left"], 5);self.assertEqual(result["eleven"], eleven)
        shown = [w for w in driver.trail if w.kind == "squad-substitution-illegal"]
        self.assertTrue(shown)
        self.assertIn(result["refused"], shown[0].text)
        self.check_oracle(driver.trail)


@requires.need(**NEEDS, slow=True)
class SeveralRounds(Oracle, unittest.TestCase):
    """E006-r0001's rounds until the original refuses the eleven (an ineligible player, round 9 of this run): the test
    fixes it through the pre-match SELECT YOUR TEAM (prematch_swap, Enter on each), and the round completes."""

    def test_rounds_through_a_refused_eleven(self):
        from goal2.core import views
        driver = start()
        refusals, fixes = [], []

        def fix(d, message):
            refusals.append(message)
            # the test reads the original's own status words (1771:42BC) to choose the pair; the original decides
            state = d.wait.state
            team = views.team(state)["squad"]
            cards = {r["player"]: views.player_card(state, r["player"]) for r in team}
            selected = views.Memory(state).code_str(0x1771, 0x42A6)
            benched = views.Memory(state).code_str(0x1771, 0x42AF)
            out = next(r for r in team if r["eleven"] and cards[r["player"]]["readiness"] != selected)
            on = next(r for r in team if not r["eleven"] and r["line"] == out["line"]
                      and cards[r["player"]]["readiness"] == benched)
            fixes.append((out["player"], on["player"]))
            d.prematch_swap(out["player"], on["player"])
        rounds = 0
        while not refusals and rounds < 12:
            driver.play_round(fix_eleven=fix)
            rounds += 1
            self.assertEqual(driver.wait.kind, "manager-menu")
        self.assertTrue(refusals, "no round of the tour met a refused eleven")
        self.assertIn("has an ineligible player in the first team", refusals[0])
        shown = [w for w in driver.trail if w.kind == "eleven-refused"]
        self.assertTrue(shown);self.assertIn(refusals[0], shown[0].text)
        out, on = fixes[0]
        boards = [w for w in driver.trail if w.kind == "match-board"]
        self.assertIn(on, views.match_sides(boards[-1].state)["eleven"])
        self.assertNotIn(out, views.match_sides(boards[-1].state)["eleven"])
        # [T108] the next rounds, until the managed side's substitution notice comes at a stoppage (an injury in the
        # quick result): a key opens the original's match menu; the test takes off the player the original marks
        # injured (its status word) for one of the bench of his line, the original makes it, and play goes on.
        made = []

        def at_stoppage(d):
            state = d.wait.state
            bench = views.bench(state)
            selected = views.Memory(state).code_str(0x1771, 0x42A6)
            hurt = [w for w in bench["eleven"] if views.player_card(state, w)["readiness"] != selected]
            line = {r["player"]: r["line"] for r in bench["squad"]}
            pairs = [(h, next(b for b in bench["bench"] if line[b] == line[h])) for h in hurt
                     if any(line[b] == line[h] for b in bench["bench"])]
            if pairs and bench["left"]:
                made.append(d.substitute(*pairs[0]))
        notices = 0
        for _ in range(3):
            out = driver.play_round(fix_eleven=fix, on_notice=lambda d, w: True, on_stoppage=at_stoppage)
            notices += out["notices"]
            if notices:
                break
        self.assertGreaterEqual(notices, 1)
        shown = [w for w in driver.trail if w.kind == "substitution-notice" and w.view.get("managed")]
        self.assertTrue(shown);self.assertIn("SUBSTITUTION OPPORTUNITY", shown[0].text)
        stoppage = [w for w in driver.trail if w.kind == "match-menu" and w.view.get("context") == "stoppage"]
        self.assertTrue(stoppage)
        self.assertTrue(made and made[0]["made"], made)
        self.assertEqual(driver.wait.kind, "manager-menu")
        self.check_results(driver.trail)
        gaps = self.check_oracle(driver.trail)
        for wait in gaps:                    # only the documented case: a list of qualifiers, no friendly
            self.assertEqual(wait.kind, "round-results")
            self.assertNotIn("friendly", wait.text)


# -- the desktop ----------------------------------------------------------------------------------------------------
@requires.need(**DESKTOP, slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def fits(self, w, what):
        from PySide6.QtWidgets import QCheckBox, QTableWidget
        from goal2.desktop.fixed_page import problems
        found = []
        for size in SIZES:
            w.resize(*size);self.app.processEvents()
            shown = w.pages[3]
            found += [f"{what} {size}: {p}" for p in problems(w)]
            need = shown.minimumSizeHint()
            if need.width() > 0.9 * shown.width() or need.height() > 0.9 * shown.height():
                found.append(f"{what} {size}: needs {need.width()}x{need.height()} of {shown.width()}x{shown.height()}")
            for kind in (QTableWidget, QCheckBox):
                found += [f"{what}: a {kind.__name__}" for x in shown.findChildren(kind) if x.isVisible()]
        w.resize(1440, 900);self.app.processEvents()
        self.assertEqual(found, [])

    def measured(self, board):
        """Every line of a TextBoard fits its width, measured in the bundled DejaVu Sans Mono."""
        from PySide6.QtGui import QFontMetricsF
        from goal2.desktop.core_window import board_font
        metrics = QFontMetricsF(board_font(board.font_size))
        width = board.page_size().width() - 24
        for line in board.lines:
            self.assertLessEqual(metrics.horizontalAdvance(''.join(t for t, _ in line)), width + 0.5, line)

    def test_play_next_game_runs_the_round_through_its_pages(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        requires.require(**DESKTOP)
        model = CoreModel.open(requires.CACHE / TEMPLATE, requires.CACHE / "GOAL.DAT",
                               Path(tempfile.gettempdir()) / "t108.g2core")
        w = CoreWindow(model);w.show();self.app.processEvents()
        play = w.core_routes["play next game"]
        self.assertTrue(play.isEnabled())
        play.click()
        self.assertTrue(w.core_jobs.busy);self.assertFalse(play.isEnabled())
        self.assertEqual(w.finish_core(300)[0], "done")
        r = w.core_round
        self.assertIn("G14b", r.pitch_note.text())
        seen = []
        # round 1 has no other fixture: the captain page comes first
        self.assertEqual(r.views.currentIndex(), 0);seen.append("captain")
        self.assertEqual(len(r.captain_roster.rows), 11)
        self.fits(w, "captain")
        r.captain_roster.current = 3;r.kick_off.click()
        self.assertEqual(w.finish_core(300)[0], "done")
        self.assertEqual(r.views.currentIndex(), 1);seen.append("bench")
        self.assertEqual(model.core.wait.kind, "match-menu-halftime")
        self.assertEqual(r.bench.counter.text(), "substitutions left 5")
        self.assertIn("0 - 0", r.bench.context.text())
        self.fits(w, "bench")
        state = model.round_state()
        off, on = same_line_pairs(state["bench"], 1)[0]
        rows = [x[0] for x in r.bench.roster.rows]
        r.bench.enter(rows.index(off));r.bench.enter(rows.index(on))
        self.assertEqual(w.finish_core(300)[0], "done")
        self.assertEqual(r.bench.counter.text(), "substitutions left 4")
        self.assertIn(on, [x[0] for x in r.bench.roster.rows][:11])
        r.bench.play.click()
        self.assertEqual(w.finish_core(300)[0], "done")
        while w.fixture_views.currentIndex() == 2 and r.views.currentIndex() == 2:
            seen.append(r.page_board.title)
            self.fits(w, r.page_board.title);self.measured(r.page_board)
            r.page_next.click();self.app.processEvents()
        self.assertEqual(model.core.wait.kind, "manager-menu")
        self.assertEqual(w.page_stack.currentIndex(), 0)
        self.assertTrue(play.isEnabled())
        self.assertEqual(seen, ["captain", "bench", "RESULT AND SUMMARY", "THE SOCCER BULLETIN"])
        # round 2: its results come first, then the captain; the original's own captain (C)
        play.click();self.assertEqual(w.finish_core(300)[0], "done")
        self.assertEqual(r.views.currentIndex(), 2);self.assertEqual(r.page_board.title, "THE ROUND'S RESULTS")
        self.fits(w, "round results");self.measured(r.page_board)
        while r.views.currentIndex() == 2:
            r.page_next.click();self.app.processEvents()
        self.assertEqual(r.views.currentIndex(), 0)
        r.computer.click();self.assertEqual(w.finish_core(300)[0], "done")
        r.bench.play.click();self.assertEqual(w.finish_core(300)[0], "done")
        titles = []
        while w.fixture_views.currentIndex() == 2 and r.views.currentIndex() == 2:
            titles.append(r.page_board.title);self.fits(w, r.page_board.title);self.measured(r.page_board)
            r.page_next.click();self.app.processEvents()
        self.assertEqual(titles, ["RESULT AND SUMMARY", "THE TABLE", "THE SOCCER BULLETIN"])
        self.assertEqual(model.core.wait.kind, "manager-menu")


if __name__ == "__main__":
    unittest.main()
