"""T100 (G8, #310): the core runs the original's own main loop from E006-r0001 and yields at each key it reads.

Evidence (goal2-archaeology at 53d7ef5): the template E006-r0001 and its run record runs/E006/E006-r0001.json
(step 11, the main screen: its text and its chars+attributes digest); the screen kinds static/screens/kinds.tsv
(docs/screens.md); the play guide docs/play-guide.md (E031) and its claims experiments/E031-play-the-game/out/
claims.md (C03, C26, C26b); F030 (the captain prompt waits 1000 polls of "key pressed?"); the listing
static/goal-exe/code/ (the read sites). Nothing of the original is in this file: it reads .cache/ and skips without.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest

from goal2.engine.original_match.assets import REFERENCE
from goal2.engine.original_match.screens import DOWN, ENTER, ESC
from goal2.tests import requires

TEMPLATE = "e006-r0001-main.sav"
NEEDS = {"modules": ("unicorn",), "files": (TEMPLATE,), "archaeology": True}
F10 = 0x44 + 0x64     # [confirmed: seg_214B_02.asm 0917-0941] 08DD: an extended key's scan code + 0x64 (F10 0x44)
# [confirmed: the listing] the sites, each the return address of a call far 214B:08DD:
SITE_TEAM_INFO = "1771:28F5"   # 1771:28F0, in the country browser 1771:26B9 that main_menu_loop calls at 000E:767D
SITE_MENU = "000E:75D1"        # 000E:75CC, in main_menu_loop 000E:7439 (annotations/routines.tsv)
SITE_YES_NO = "214B:09C4"      # 214B:09BF, in u214b_wait_key_in_set 09A7, read by u214b_ask_yes_no 0566 (F030)
SITE_BOARD = "0791:041A"       # 0791:0415, the match board 0791:0106 (the kit's SITE_BOARD)
CAPTAIN_WAIT_POLL = "0791:CC54"  # wait_or_key 0791:CC2E's poll (the kit's KP_WAIT)


def template():
    requires.require(**NEEDS)
    data = (requires.CACHE / TEMPLATE).read_bytes()
    if hashlib.sha256(data).hexdigest() != REFERENCE["sha256"]:
        raise AssertionError(f".cache/{TEMPLATE} is not E006-r0001 (release E006, {REFERENCE['sha256'][:12]}...)")
    return data


def record_main_screen():
    """E006-r0001's record of the main screen (step 11): the text and the 4000-byte screen's SHA-256."""
    rec = json.loads((requires.archaeology() / "runs/E006/E006-r0001.json").read_text())
    obs = [o for o in rec["observations"] if o["step"] == 11]
    text = next(o["value"] for o in obs if o["source"] == "ui-text")
    digest = next(o["value"] for o in obs if o["source"] == "screen")
    return text, digest


def kind_rule(kind):
    """docs/screens.md: a kind's rule `+phrase ;; -phrase`, every + phrase in the text and no - phrase, runs of
    whitespace as one space."""
    for line in (requires.archaeology() / "static/screens/kinds.tsv").read_text().splitlines()[1:]:
        name, rule, _ = line.split("\t")
        if name == kind:
            return [(p[0], " ".join(p[1:].split())) for p in rule.split(" ;; ")]
    raise KeyError(kind)


def is_kind(text, kind):
    flat = " ".join(text.split())
    return all((phrase in flat) == (sign == "+") for sign, phrase in kind_rule(kind))


def claim_row(claim):
    """The screen row E031's claims.md quotes for a claim."""
    for line in (requires.archaeology() / "experiments/E031-play-the-game/out/claims.md").read_text().splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4 and cells[1] == claim:
            return cells[4].strip("`")
    raise KeyError(claim)


class ImportWithoutUnicorn(unittest.TestCase):
    def test_import_works_and_start_names_what_is_missing(self):
        code = ("import sys; sys.modules['unicorn'] = None\n"
                "import goal2.core\n"
                "try:\n    goal2.core.Core.start(b'')\n"
                "except ModuleNotFoundError as e:\n    print('MISSING', e)\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           cwd=str(requires.ROOT), env={**os.environ, "PYTHONPATH": str(requires.ROOT)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("MISSING", r.stdout)
        self.assertIn("unicorn", r.stdout)


@requires.need(**NEEDS)
class Start(unittest.TestCase):
    def test_start_yields_the_recorded_main_screen(self):
        from goal2.core import Core
        wait = Core.start(template())
        text, digest = record_main_screen()
        self.assertEqual(wait.site, SITE_TEAM_INFO)
        self.assertEqual(wait.text, text)                         # E006-r0001 step 11, the main screen
        self.assertEqual(hashlib.sha256(wait.screen).hexdigest(), digest)
        self.assertEqual(wait.state.managed, (7,))                # Denmark, the card on the screen
        self.assertIn("│Denmark-------- status major", wait.text)
        self.assertEqual(wait.state.year(), 0)                    # the game record's year word: a new game's first
        self.assertEqual(wait.polls, ())


@requires.need(**NEEDS)
class DocumentedKeys(unittest.TestCase):
    def test_escape_then_f10_y_n_quits_as_the_play_guide_records(self):
        from goal2.core import Core, CoreError, InterruptError
        core = Core.start(template()).core
        menu = core.press(ESC)                                    # the screen's own "Esc to exit"
        self.assertEqual(menu.site, SITE_MENU)
        self.assertTrue(is_kind(menu.text, "manager-menu"), menu.text)
        self.assertEqual(menu.state.managed, (7,))
        quit_ = core.press(F10)                                   # play guide section 4: F10 asks to quit [C03]
        self.assertEqual(quit_.site, SITE_YES_NO)
        self.assertTrue(is_kind(quit_.text, "quit-confirm"), quit_.text)
        self.assertEqual(quit_.text.splitlines()[-1], claim_row("C03"))
        save = core.press("Y")                                    # ... then whether to save [C26]
        self.assertEqual(save.site, SITE_YES_NO)
        self.assertTrue(is_kind(save.text, "save-game-prompt"), save.text)
        self.assertEqual(save.text.splitlines()[-1], claim_row("C26"))
        with self.assertRaises(InterruptError) as caught:         # after the answer GOAL exits [C26b]: the core
            core.press("N")                                       # serves no interrupt and stops at the first
        self.assertEqual(caught.exception.number, 0x10)
        self.assertRegex(caught.exception.pc, r"^[0-9A-F]{4}:[0-9A-F]{4} \(CS:IP [0-9A-F]{4}:[0-9A-F]{4}\)$")
        self.assertIn("F10quit", caught.exception.text)
        with self.assertRaises(CoreError):
            core.press(ENTER)


@requires.need(**NEEDS)
class SaveAndLoad(unittest.TestCase):
    # Esc to the menu, Down x5 to "play next game", Enter: the match menu (the round's set-up draws the RNG);
    # Down x4 to "match stats", Enter: the board; Enter back to the match menu.
    KEYS = [ESC] + [DOWN] * 5 + [ENTER] + [DOWN] * 4 + [ENTER, ENTER]
    MIDWAY = 7

    def test_straight_and_saved_midway_are_the_same_run(self):
        from goal2.core import Core
        data = template()
        core = Core.start(data).core
        straight = [core.wait] + [core.press(k) for k in self.KEYS]
        straight_sha = core.memory_sha256()
        self.assertEqual(straight[self.MIDWAY].site, "214B:157C")       # the match menu's reader 214B:1560
        self.assertIn("Hit INS to turn automatic action replay", straight[self.MIDWAY].text)
        self.assertEqual(straight[-2].site, SITE_BOARD)

        core = Core.start(data).core
        resumed = [core.wait] + [core.press(k) for k in self.KEYS[:self.MIDWAY]]
        blob = core.save()
        n = int.from_bytes(blob[4:8], "little")
        saved = json.loads(blob[8:8 + n])
        self.assertEqual(saved["keys"], self.KEYS[:self.MIDWAY])
        self.assertEqual(saved["seeds"]["7B62"], core.m.rd(0x7B62))
        self.assertNotEqual(saved["seeds"]["7B62"], 0xEE42)              # E006-r0001's seed, drawn since (F004)
        del core
        loaded = Core.load(blob)
        self.assertEqual(loaded.wait, resumed[-1])
        resumed[-1] = loaded.wait
        resumed += [loaded.press(k) for k in self.KEYS[self.MIDWAY:]]
        self.assertEqual([(w.site, w.text) for w in resumed], [(w.site, w.text) for w in straight])
        self.assertEqual(resumed, straight)
        self.assertEqual(loaded.memory_sha256(), straight_sha)


@requires.need(**NEEDS)
class TimedPromptAndBudget(unittest.TestCase):
    # ... the match menu, Down x5 to "play", Enter: the captain prompt, a timed prompt (10 s, F030).
    TO_PLAY = [ESC] + [DOWN] * 5 + [ENTER] + [DOWN] * 5

    def test_the_captain_prompt_times_out_by_itself(self):
        from goal2.core import Core
        core = Core.start(template()).core
        for k in self.TO_PLAY:
            core.press(k)
        wait = core.press(ENTER)                 # no key is given at the prompt: its 1000 polls run out (F030)
        self.assertEqual(wait.site, SITE_BOARD)
        self.assertIn("---- HALF TIME ----", wait.text)     # the first half played on: the half-time board
        self.assertIn("hit any key", wait.text)
        self.assertGreaterEqual(dict(wait.polls)[CAPTAIN_WAIT_POLL], 1000)

    def test_a_run_past_the_budget_stops_with_the_pc_and_the_text_page(self):
        from goal2.core import Core, CoreError, BudgetExceeded
        core = Core.start(template(), budget=50_000_000).core
        for k in self.TO_PLAY:
            core.press(k)
        with self.assertRaises(BudgetExceeded) as caught:
            core.press(ENTER)
        e = caught.exception
        self.assertTrue(re.match(r"^[0-9A-F]{4}:[0-9A-F]{4} \(CS:IP [0-9A-F]{4}:[0-9A-F]{4}\)$", e.pc), e.pc)
        self.assertIn("select  CAPTAIN", e.text)        # the prompt it was waiting in
        self.assertIn("C-computer select", e.text)
        self.assertIn(e.pc, str(e))
        self.assertIn(e.text, str(e))
        with self.assertRaises(CoreError):
            core.press(ENTER)


if __name__ == "__main__":
    unittest.main()
