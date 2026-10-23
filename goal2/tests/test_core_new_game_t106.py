"""T106 (#308's G10, #325, #319, #323): a new game over the core, from the DOS date call to the first manager menu.

The evidence is goal2-archaeology's: E038-r0001 (F032), a new game in DOSBox-X at DOS 10:00 with the keys
`n Enter Enter b o b Enter Enter Enter`, its savestates at each read and its Unicorn trace, which served only the
interrupts NG-7 lists and ended byte-equal to DOSBox-X's manager menu; E039-r0001/r0002 (F033), the same new game at
the DOS dates 10/04/1990 and 10/04/1992, and e039-r0005-date-call.sav, a state stopped at the program's date call.
The records are read from the goal2-archaeology checkout at ARCHAEOLOGY (git show), the savestates from .cache/.
Nothing of the original is in this file.

[designed: #316] The tests that run the original past its first screens are slow tests (GOAL2_SLOW=1; the gate runs
them whenever goal2/core/, goal2/desktop/core_* or this module changes, tools/check_premerge.py SLOW_PATHS), but the
byte-for-byte new game, the module's one real case in the default run (about a second).
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

# [confirmed: goal2-archaeology c9364f51 (the merge of #371, holding F032's #368 too)] the records' commit
ARCHAEOLOGY = "c9364f51686c3ee7edc56c5c601ac1e3beaae553"
E038 = "e038-r0001-{}.sav"
STEPS = ("title-keywait", "title-player-count", "country-select", "after-name-1", "after-name-2", "manager-menu")
DATE_CALL = "e039-r0005-date-call.sav"
NEEDS = {"modules": ("unicorn",), "files": tuple(E038.format(s) for s in STEPS + ("country-select-name-entry",))
         + (DATE_CALL, "GOAL.DAT"), "archaeology": True}
DESKTOP = {**NEEDS, "modules": ("unicorn", "PySide6")}
# [confirmed: E038's trace-r0001.json argv `--time 10:00:20.95`; E038-r0001's DS:7B64 145F at the manager menu]
E038_TIME = (10, 0, 20, 95)
# [confirmed: E038-r0001's keys, as 214B:08DD returns them; the trace's --keys] and the country Enter chose (Denmark)
E038_KEYS = [0x6E, 0x0D, 0x0D, 0x62, 0x6F, 0x62, 0x0D, 0x0D, 0x0D]
DENMARK = 7
# [confirmed: E039-r0001, E039-r0002 (F033)] the DOS dates and the game record's +0x3A start year, +0x3C stage
E039 = {"E039-r0001": ((1990, 10, 4), 1992, 2), "E039-r0002": ((1992, 10, 4), 1994, 5)}
SIZES = ((1440, 900), (1050, 780), (900, 640), (2560, 1600))
F10, ENTER = 0xA8, 0x0D
GAME, SEED, SEED2 = 0xA923, 0x7B62, 0x7B64
TUNE_COUNTERS = (0x7966, 0x7968)       # [confirmed: named/seg_1771_01.c 06F3] the title tune's DS:7966 and DS:7968


def cache(name):
    requires.require(**NEEDS)
    return (requires.CACHE / name).read_bytes()


def archaeology(path):
    """A file of goal2-archaeology at ARCHAEOLOGY, read with git show; the test skips when the checkout lacks it."""
    requires.require(archaeology=True)
    r = subprocess.run(["git", "-C", str(requires.archaeology()), "show", f"{ARCHAEOLOGY}:{path}"],
                       capture_output=True)
    if r.returncode:
        raise unittest.SkipTest(f"goal2-archaeology {ARCHAEOLOGY[:8]} absent: git -C <checkout> fetch origin main")
    return r.stdout


def record(run):
    """{(step, field prefix): value} of a run record's screen and memory observations."""
    d = json.loads(archaeology(f"runs/{run[:4]}/{run}.json"))
    return {o["field"]: o["value"] for o in d["observations"]}


def observed(rec, screen, what):
    hits = [v for k, v in rec.items() if k.startswith(f"{screen}: ") and what in k]
    assert len(hits) == 1, (screen, what, hits)
    return hits[0]


def ds_word(core, off):
    return core.m.rd(off)


def game_word(core, off, n=2):
    return core.m.rd_far(GAME, off, n)


def e038_core(dos_time=E038_TIME):
    from goal2.core import Core
    return Core.start(cache(E038.format("title-keywait")), dos_time=dos_time,
                      goal_dat=requires.CACHE / "GOAL.DAT").core


def e038_game(dos_time=E038_TIME, on_bulletin=None):
    """E038-r0001's new game by the driver: Denmark (the browser's first), the name 'bob'."""
    from goal2.core.driver import Driver
    driver = Driver(e038_core(dos_time))
    driver.new_game(DENMARK, "bob", on_bulletin=on_bulletin)
    return driver


def ranges(a, b):
    out, i, n = [], 0, min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            out.append(f"{i:05X}-{j:05X}")
            i = j
        else:
            i += 1
    return out


@requires.need(**NEEDS)
class ByteForByte(unittest.TestCase):
    """The module's one real case in the default run."""

    def test_e038s_new_game_reaches_dosbox_xs_manager_menu_byte_for_byte(self):
        from goal2.core.runner import TEXT_PAGE, text_page
        from goal2.engine.original_match.image import Image
        driver = e038_game()
        core = driver.core
        self.assertEqual(driver.wait.kind, "manager-menu")
        self.assertEqual([key for _, key in driver.log], E038_KEYS)      # the original's own keys, E038's
        ref = cache(E038.format("manager-menu"))
        image = Image.from_savestate(ref)
        mine, theirs = core.memory(), bytes(image.memory[:len(core.memory())])
        self.assertEqual(mine[TEXT_PAGE:TEXT_PAGE + 4000], text_page(ref))                 # the screen
        ds = image.DS * 16
        for off in (SEED, SEED2):                                                            # DS:7B62, DS:7B64
            self.assertEqual(mine[ds + off:ds + off + 2], theirs[ds + off:ds + off + 2], hex(off))
        self.assertEqual(ds_word(core, SEED), 0xEE42)
        for ptr, size in ((0xA91B, 0x14 * 3061), (0xA917, 0xBF * 129)):                       # players, countries
            a, b = core.m.far(ptr), image.far(ptr)
            self.assertEqual(a, b)
            self.assertEqual(mine[a:a + size], theirs[b:b + size], hex(ptr))
        # The rest of conventional memory differs where E038's own trace differed from DOSBox-X: the BIOS keyboard
        # buffer and tick, DOS's 0815E and the stack below SS:SP (trace-r0001.json, compare.conventional_differs).
        trace = json.loads(archaeology("experiments/E038-new-game-keywait/out/trace-r0001.json"))
        # [derived: #327, T108] but one: Intr's record now holds the CPU's flags with the carry clear, as 235C:0045
        # stores them, where E038's trace kept the request's flags; that word (on the stack, 3C565) is DOSBox-X's now.
        expected = [r for r in trace["compare"]["conventional_differs"] if r != INTR_FLAGS]
        self.assertEqual(len(expected), len(trace["compare"]["conventional_differs"]) - 1)
        self.assertEqual(ranges(mine[:0xA0000], theirs[:0xA0000]), expected)
        start, end = (int(x, 16) for x in INTR_FLAGS.split("-"))
        self.assertEqual(mine[start:end], theirs[start:end])


INTR_FLAGS = "3C565-3C567"     # [T108] the range of E038's trace where the record's flags word lies


@requires.need(**NEEDS, slow=True)
class Steps(unittest.TestCase):
    def test_each_wait_is_e038s_state_at_that_step_and_its_text(self):
        from goal2.core import Core, CoreError
        from goal2.core.runner import decode_text, text_page
        from goal2.tests.test_core_screens_t103 import text_kind
        rec = record("E038-r0001")
        waits = [e038_core().wait]
        core = waits[0].core
        for key in E038_KEYS[:3]:
            if key == ENTER and waits[-1].kind == "country-select":
                for ch in "bob\r":
                    core.queue("country-select-name-entry", ord(ch))
            waits.append(core.press(key))
        waits += [core.press(ENTER), core.press(ENTER)]
        screens = ("title-load-prompt", "title-player-count", "country-select", "after-name-1", "after-name-2",
                   "manager-menu")
        for wait, step, screen in zip(waits, STEPS, screens):
            state = cache(E038.format(step))
            theirs = Core.start(state, goal_dat=requires.CACHE / "GOAL.DAT")
            self.assertEqual(wait.kind, theirs.kind, step)                      # the kind of E038's state
            self.assertEqual(wait.site, theirs.site, step)
            self.assertEqual(wait.text, decode_text(text_page(state)), step)    # the text oracle: DOSBox-X's screen
            self.assertEqual(hashlib.sha256(wait.screen).hexdigest(), observed(rec, screen, "sha256"), step)
            kind = text_kind(wait.text)
            self.assertEqual(kind, "bulletin" if screen.startswith("after-name") else screen, step)
            self.assertEqual(wait.kind, kind, step)
        # The polled name entry: passed on the way to the first bulletin, its keys the letters and Enter; E038's
        # state there is not in a read (the core refuses it) and shows the same kind by the text oracle.
        entry = waits[3].passed
        self.assertEqual([(p.kind, p.keys) for p in entry], [("country-select-name-entry", tuple(b"bob\r"))])
        self.assertEqual(text_kind(entry[0].text), "country-select-name-entry")
        state = cache(E038.format("country-select-name-entry"))
        self.assertEqual(text_kind(decode_text(text_page(state))), "country-select-name-entry")
        with self.assertRaises(CoreError):
            Core.start(state)

    def test_the_views_read_the_browser_and_the_bulletins(self):
        from goal2.core import views
        seen = []
        driver = e038_game(on_bulletin=lambda w: seen.append((w.text, views.bulletin(w.state))))
        self.assertEqual(len(seen), 2)
        for text, view in seen:
            rows = text.splitlines()
            for name, (_, first, last, a, b) in views.BULLETIN_PANELS.items():
                shown = [rows[r][a:b + 1].strip() for r in range(first, last + 1)]
                self.assertEqual(view[name]["lines"], [t for t in shown if t and not set(t) <= views.FILLER], name)
                self.assertIn(view[name]["masthead"], text)
        self.assertEqual(seen[0][1]["middle"]["lines"], ["DENMARK", "APPOINT A NEW", "MANAGER"])
        self.assertEqual(seen[1][1]["middle"]["lines"][0], "GROUPS ARE ANNOUNCED")
        self.assertEqual(views.desk(driver.wait.state)["manager"], "B Ob")
        # The browser: its list in the screen's right column, the browsed country's card in its panel.
        from goal2.core import Core
        wait = Core.start(cache(E038.format("country-select")), goal_dat=requires.CACHE / "GOAL.DAT")
        browse = views.country_select(wait.state)
        self.assertEqual(sorted(c["country"] for c in browse["countries"]), list(range(1, 129)))
        column = [re.search(r"│([^│]+?)-*│$", row).group(1) for row in wait.text.splitlines()[7:23]]
        self.assertEqual(column, [c["name"] for c in browse["countries"][:16]])
        self.assertEqual((browse["country"], wait.view["country"]), (DENMARK, DENMARK))
        self.assertEqual((browse["start_year"], browse["stage"]), (2028, 2))       # E038 at DOS 2026 (F033)
        card = views.country_card(wait.state, DENMARK)
        rows = wait.text.splitlines()
        self.assertIn(f"│{card['name']}", rows[7])
        self.assertIn(f"│{card['manager']:<15}", rows[9])
        self.assertIn(f"formation  {card['formation']}", rows[11])
        self.assertIn(f"World    {card['world']}", rows[11])
        for name, word in card["team_tactics"] + card["player_defaults"]:
            self.assertTrue(any(word in r and name.split()[0] in r for r in rows), (name, word))


@requires.need(**NEEDS, slow=True)
class Determinism(unittest.TestCase):
    def test_the_dos_time_is_an_input_and_a_game_replays(self):
        from goal2.core import Core
        other = e038_game(dos_time=(11, 30, 5, 0)).core
        self.assertNotEqual(ds_word(other, SEED), 0xEE42)       # another time, another seed
        self.assertEqual(ds_word(other, SEED2), 0x0500)
        runs = [e038_game().core.memory_sha256() for _ in range(2)]
        self.assertEqual(runs[0], runs[1])                       # the same time twice, the same memory
        # Saved and loaded midway (at the country browser, with the name queued): the same final memory.
        from goal2.core.driver import Driver
        driver = Driver(e038_core())
        driver.press("n", expect=("title-player-count",))
        driver.press(ENTER, expect=("country-select",))
        for ch in "bob\r":
            driver.queue("country-select-name-entry", ch)
        blob = driver.core.save()
        resumed = Core.load(blob, goal_dat=requires.CACHE / "GOAL.DAT")
        self.assertEqual(resumed.dos_time, E038_TIME)
        for _ in range(3):
            resumed.press(ENTER)
        self.assertEqual(resumed.wait.kind, "manager-menu")
        self.assertEqual(resumed.memory_sha256(), runs[0])


@requires.need(**NEEDS, slow=True)
class Refusals(unittest.TestCase):
    def test_other_requests_stop_naming_the_vector_and_ah(self):
        from goal2.core import Core, InterruptError
        core = e038_core()
        with self.assertRaises(InterruptError) as caught:
            core.press("y")                     # load a saved game: DOS's current drive, through MsDos (F032)
        e = caught.exception
        self.assertEqual((e.number, e.ah, e.via), (0x21, 0x19, "MsDos"))
        self.assertIn("INT 21h AH=19h", str(e))
        self.assertIsNotNone(core.stopped)
        core = Core.start(cache(E038.format("title-keywait"))).core       # no GOAL.DAT given
        with self.assertRaises(InterruptError) as caught:
            core.press("n")
        self.assertEqual((caught.exception.number, caught.exception.ah), (0x21, 0x3D))
        self.assertIn("GOAL.DAT", str(caught.exception))
        core = Core.start(cache(E038.format("manager-menu"))).core       # quit: F10, Y, N; then the video BIOS
        core.press(F10)
        core.press("y")
        with self.assertRaises(InterruptError) as caught:
            core.press("n")
        e = caught.exception
        self.assertEqual((e.number, e.ah, e.via), (0x10, 0x02, "int"))
        self.assertIn("INT 10h AH=02h", str(e))

    def test_boot_refuses_a_state_not_at_the_date_call(self):
        from goal2.core import Core, CoreError
        with self.assertRaises(CoreError):
            Core.boot(cache(E038.format("title-keywait")), (1990, 10, 4))
        with self.assertRaises(ValueError):
            Core.boot(cache(DATE_CALL), (1979, 10, 4))


@requires.need(**NEEDS, slow=True)
class StartYear(unittest.TestCase):
    """E039's two dates from the date call, each through the whole title tune (about a minute each under Unicorn)."""

    @classmethod
    def setUpClass(cls):
        from goal2.core import Core
        from goal2.core.driver import Driver
        cls.title, cls.games = {}, {}
        for run, (date, _, _) in E039.items():
            wait = Core.boot(cache(DATE_CALL), date, dos_time=E038_TIME, goal_dat=requires.CACHE / "GOAL.DAT")
            cls.title[run] = wait
            driver = Driver(wait.core)
            driver.new_game(DENMARK, "bob")
            cls.games[run] = driver

    def test_the_title_read_holds_e039s_year_and_screen(self):
        for run, (date, _, _) in E039.items():
            rec, wait = record(run), self.title[run]
            self.assertEqual((wait.site, wait.kind), ("1771:085F", "title-load-prompt"), run)
            self.assertEqual([(p.kind, p.polls) for p in wait.passed], [("title-tune", 333)], run)    # NG-10
            self.assertEqual(hashlib.sha256(wait.screen).hexdigest(),
                             observed(rec, "title-load-prompt", "sha256"), run)
            self.assertEqual(wait.text, observed(rec, "title-load-prompt", "CP437"), run)
            year = wait.core.m.rd(0xA9FD)
            self.assertEqual(year, date[0], run)
            self.assertEqual(f"{year:04x}", observed(rec, "title-load-prompt", "DS:A9FD"), run)
            self.assertEqual(wait.core.date, date)

    def test_a_new_game_has_ng9s_start_year_and_stage(self):
        for run, (_, start, stage) in E039.items():
            core, rec = self.games[run].core, record(run)
            self.assertEqual(self.games[run].wait.kind, "manager-menu", run)
            self.assertEqual((game_word(core, 0x3A), game_word(core, 0x3C, 1)), (start, stage), run)
            self.assertEqual(core.m.read(core.m.far(GAME) + 0x38, 10).hex(),
                             observed(rec, "manager-menu", "+0x38..+0x41"), run)
        # The core save keeps the date and the time.
        from goal2.core import Core
        loaded = Core.load(self.games["E039-r0001"].core.save())
        self.assertEqual((loaded.date, loaded.dos_time), ((1990, 10, 4), E038_TIME))

    def test_launch_1990_is_dos_1989_and_a_key_in_the_tune_changes_only_its_counters(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        from goal2.desktop.core_model import BOOT_MONTH_DAY, dos_year
        wait = Core.boot(cache(DATE_CALL), (dos_year(1990),) + BOOT_MONTH_DAY, goal_dat=requires.CACHE / "GOAL.DAT",
                         title_key="n")
        self.assertEqual(wait.kind, "title-player-count")
        self.assertEqual([(p.kind, p.polls, p.keys) for p in wait.passed], [("title-tune", 1, (ord("n"),))])
        wait = wait.core.press(ENTER)                 # one manager: 1771:9B85 has set the game record (E039's records)
        self.assertEqual(wait.kind, "country-select")
        self.assertEqual((game_word(wait.core, 0x3A), game_word(wait.core, 0x3C, 1)), (1990, 5))
        # The desktop's boot (N pressed during the tune) against the whole tune at the same date and time.
        quick = Driver(Core.boot(cache(DATE_CALL), E039["E039-r0001"][0], dos_time=E038_TIME,
                                 goal_dat=requires.CACHE / "GOAL.DAT", title_key="n").core)
        quick.new_game(DENMARK, "bob")
        full = self.games["E039-r0001"].core
        ds = full.m.DS * 16
        self.assertEqual(ranges(full.memory(), quick.core.memory()),
                         [f"{ds + off:05X}-{ds + off + 1:05X}" for off in TUNE_COUNTERS])


@requires.need(**DESKTOP, slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_new_career_on_the_core_route_reaches_the_main_window(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.__main__ import main
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        from goal2.desktop.launch import LaunchWindow
        app, found, out = self.app, [], {}

        def fits(window, what, margin=True):
            for size in SIZES:
                window.resize(*size);app.processEvents()
                found.extend(f"{what} at {size}: {p}" for p in problems(window))
                page = window.pages.currentWidget();need = page.minimumSizeHint()
                # [designed: T105's margin] the new pages ask for at most 90 % of their room; the browser is the
                # Python route's page (T89, T101) with the core's data, checked by problems() as it always was.
                if margin and (need.width() > 0.9 * page.width() or need.height() > 0.9 * page.height()):
                    found.append(f"{what} at {size}: needs {need.width()}x{need.height()} of {page.width()}x"
                                 f"{page.height()}, more than 90 %")

        def drive():
            try:
                launch = next(w for w in QApplication.topLevelWidgets() if isinstance(w, LaunchWindow))
                launch.show_page(1);app.processEvents()
                out["list"] = [launch.country_list.item(r).data(0x0100) for r in range(launch.country_list.count())]
                row = out["list"].index(20)                                # Holland
                launch.country_list.setCurrentRow(row);launch.preview();app.processEvents()
                out["card"] = launch.country_card.card["name"]
                fits(launch, "browse", margin=False)
                launch.review();app.processEvents()
                out["campaign"] = launch.review_fields["campaign"].text()
                fits(launch, "review")
                launch.manager_name.setText("J Smith");launch.do_start();app.processEvents()
                out["bulletins"] = []
                for _ in range(len(launch.bulletins)):
                    self.assertEqual(launch.pages.currentIndex(), 4)
                    out["bulletins"].append(launch.bulletin_panels["middle"][1].text())
                    fits(launch, f"bulletin {len(out['bulletins'])}")
                    launch.bulletin_next.click();app.processEvents()
                QTimer.singleShot(0, look)
            except Exception as exc:                                       # reported by the test, not lost in Qt
                out["error"] = repr(exc);app.quit()

        def look():
            windows = [w for w in QApplication.topLevelWidgets() if isinstance(w, CoreWindow) and w.isVisible()]
            if windows:
                desk = windows[0].model.desk()
                out["window"] = (windows[0].core_team_name.text(), desk["team"]["country"], desk["manager"],
                                 desk["year"])
            app.quit()
        QTimer.singleShot(0, drive)
        argv = ["--core-boot", str(requires.CACHE / DATE_CALL), "--data", str(requires.CACHE / "GOAL.DAT"),
                "--save", str(Path(self.tmp.name) / "career.g2core")]
        self.assertEqual(main(argv), 0)
        self.assertNotIn("error", out)
        self.assertEqual(sorted(out["list"]), list(range(1, 129)))
        self.assertEqual(out["card"], "Holland")
        self.assertIn("1990, stage 5", out["campaign"])                   # Launch's first year: DOS 1989 (NG-9)
        self.assertEqual(len(out["bulletins"]), 2)
        self.assertTrue(out["bulletins"][0].startswith("HOLLAND\nAPPOINT A NEW"))
        self.assertEqual(out["window"], ("Holland", 20, "J Smith", 1990))
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
