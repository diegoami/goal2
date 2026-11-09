"""[designed: T170e/#566] The 1992/stage 2 season on the sealed route, round by round, against the original's Core.

The claim [confirmed: T170 Done-when 1 and 2]: a career starting 1992/stage 2 plays all its fixtures and rounds to the
terminal boundary on the sealed route (goal2/game/season.py) exactly as the original plays them, every completed round
equal to Core `play_round` under Unicorn on the seven fields of goal2/tests/season_oracle.py (countries, players,
fixtures, the game block, DS:A91F, 7B62, 8336), the terminal step equal at its oracle site with the original paused
there, and the same season repeated from the same start giving the same final results and news.

The start [designed: owner, 2026-11-09, after T170e stopped on its first wording]: "1992/stage 2" names the cycle
position, not the calendar year. By NG-9 a start year divisible by four begins at stage 2; the original is booted at the
DOS date 10/04/1990 (E039-r0001: start year 1992, stage 2) and its own new game is played by its own keys to the
first manager menu, cursor 1 of 769. No guest-memory edit, no stored artifact: the start is rebuilt each run (about a
fifth of a second).

The oracle is imported unchanged (T170d, #691). The one addition to goal2/tests/season_oracle.py is `sealed_season`,
the sealed half again with the news and the fixtures each round published, for the repeat.

Fast controls (always run; need Unicorn and the date-call state in .cache/): the start is the cursor-1 stage-2 manager
menu of 1992, and the season test's own accounting (which round is 2 to 3, what a mismatch report holds) fails on
altered data. The season itself is slow (GOAL2_SLOW=1): tens of minutes of Unicorn rounds, played once.
"""
import contextlib
import dataclasses
import functools
import sys
import time
import unittest

from goal2.tests import requires, season_oracle as so

DATE_CALL = "e039-r0005-date-call.sav"
GOAL_DAT = requires.CACHE / "GOAL.DAT"
# [confirmed: goal2/tests/test_core_new_game_t106.py E039, E038_TIME] DOS 10/04/1990 gives start year 1992, stage 2
BOOT_DATE, BOOT_TIME = (1990, 10, 4), (10, 0, 20, 95)
DENMARK, MANAGER = 7, "bob"                 # [confirmed: T106] the country the traced new game chose, the name typed
START = dict(stage=2, cursor=1, count=769, rounds=1)       # [confirmed: F023 §9; T111's stage-2 count 769]
START_YEAR = 1992
BOUND = 400                                 # rounds asked of each side: far more than the season has; it stops at the terminal
NEEDS = dict(modules=("unicorn",), files=(DATE_CALL, "GOAL.DAT"))
LABEL = "1992/stage 2, round {}"
TIMES = {}


def say(text):
    print(f"[T170e] {text}", file=sys.stderr, flush=True)


def build_start():
    """(blob, start facts): the original's own new game, from the DOS date call to the first manager menu, saved.
    [confirmed: docs/core.md 'Booting at the DOS date call', NG-9, NG-10] `title_key="n"` is the desktop's boot: N
    pressed during the title tune."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    began = time.monotonic()
    wait = Core.boot((requires.CACHE / DATE_CALL).read_bytes(), BOOT_DATE, dos_time=BOOT_TIME, goal_dat=GOAL_DAT,
                     title_key="n")
    booted = time.monotonic()
    driver = Driver(wait.core)
    driver.new_game(DENMARK, MANAGER)
    TIMES["boot"], TIMES["new_game"] = booted - began, time.monotonic() - booted
    core = driver.core
    ds = core.m.DS * 16
    facts = so.game_facts(core.m.read, ds)
    game = int.from_bytes(core.m.read(ds + 0xA923 + 2, 2), "little") * 16 + int.from_bytes(core.m.read(ds + 0xA923, 2), "little")
    facts.update(kind=driver.wait.kind, year=int.from_bytes(core.m.read(game + 0x3A, 2), "little"))
    return core.save(), facts


@functools.lru_cache(maxsize=None)
def start():
    return build_start()


@requires.need(**NEEDS)
class TheStart(unittest.TestCase):
    def test_the_start_is_a_1992_stage_2_manager_menu_at_cursor_1(self):
        blob, facts = start()
        say(f"start: {facts}; boot {TIMES['boot']:.2f}s, new game {TIMES['new_game']:.2f}s")
        self.assertEqual(facts["kind"], "manager-menu")
        self.assertEqual({k: facts[k] for k in START}, START)
        self.assertEqual(facts["year"], START_YEAR)
        self.assertFalse(so.at_terminal(facts))

    def test_the_start_is_rebuilt_identically(self):
        """The original is deterministic from the same date and keys: two builds are one start, so no stored
        artifact is needed and none can drift."""
        self.assertEqual(build_start()[0], start()[0])

    def test_the_component_the_sealed_side_starts_from_is_the_same_memory(self):
        blob, _ = start()
        component = so.component_of(blob, GOAL_DAT)
        from goal2.core import Core
        self.assertEqual(Core.load(blob, goal_dat=GOAL_DAT).memory_component(), component)


# --- the Core's season: one round at a time, with the player's own repair of an eleven the original refuses --------

REPAIR_BOUND = 8                            # the driver's own bound on a refusing eleven (Driver.play_round)


@contextlib.contextmanager
def capturing_core():
    """Collect the Core each `core_rounds` call builds, so the saved state after its round is at hand. It wraps the
    oracle's own constructor for the duration and changes nothing it does."""
    original = so._core_driver
    cores = []

    def wrapped(blob, goal_dat):
        core, driver = original(blob, goal_dat)
        cores.append(core)
        return core, driver
    so._core_driver = wrapped
    try:
        yield cores
    finally:
        so._core_driver = original


def repair_eleven(blob):
    """[designed: T111 test policy, test_core_continuation_t111.fix_eleven, on the manager menu] The player's answer to
    an eleven the original refuses: at the manager menu, by the original's own keys, swap the first eleven player who
    is not fit with a fit player of the same line from the bench (Driver.swap, the squad screen). The original decides
    the legality; nothing is written to guest memory. Returns (the saved Core, (off, on))."""
    from goal2.core import Core, views
    from goal2.core.driver import Driver
    driver = Driver(Core.load(blob, goal_dat=GOAL_DAT))
    wait = driver.wait
    memory = views.Memory(wait.state)
    rows = views.team(wait.state)["squad"]
    cards = {r["player"]: views.player_card(wait.state, r["player"]) for r in rows}
    fit, ready = memory.code_str(0x1771, 0x42A6), memory.code_str(0x1771, 0x42AF)
    off = next(r for r in rows if r["eleven"] and cards[r["player"]]["readiness"] != fit)
    on = next(r for r in reversed(rows) if not r["eleven"] and r["line"] == off["line"]
              and cards[r["player"]]["readiness"] == ready)
    driver.swap(off["player"], on["player"])
    return driver.core.save(), (off["player"], on["player"])


def core_season(blob):
    """The original's whole season, one round per `core_rounds` call (so the oracle's own function plays every round),
    each from the saved Core the one before left at its manager menu. [designed: T170e] When the original refuses the
    managed side's eleven at the kick-off (the round is not played), the player's repair is made on the saved menu of
    that round (`repair_eleven`) and the round is played again from there. Returns (rounds, repairs, menus): the
    oracle's Round per round, [(round, the original's message, (off, on))], and {round: the saved Core the round was
    played from} for the rounds that follow a repair. Stops after the terminal step."""
    from goal2.core.driver import DriverError
    rounds, repairs, menus = [], [], {}
    current = blob
    began = time.monotonic()
    for number in range(1, BOUND + 1):
        attempts = 0
        while True:
            with capturing_core() as cores:
                try:
                    got = so.core_rounds(current, GOAL_DAT, 1)
                except DriverError as error:
                    if "refuses the eleven" not in str(error) or attempts >= REPAIR_BOUND:
                        raise
                    refusal = str(error)
                else:
                    break
            attempts += 1
            current, swap = repair_eleven(current)
            repairs.append((number, refusal, swap))
            menus[number] = current
            say(f"round {number}: the original refused the eleven ({refusal}); swapped {swap} at the menu")
        rounds.append(got[0])
        say(f"round {number} ({got[0].kind}) stage {got[0].before['stage']}->{got[0].after['stage']} cursor "
            f"{got[0].before['cursor']}->{got[0].after['cursor']}/{got[0].after['count']} at {time.monotonic() - began:.0f}s")
        if got[0].kind == "deferred-rollover":
            break
        current = cores[-1].save()
    return rounds, repairs, menus


# --- the accounting of a played season, as functions of the rounds, so a test can feed them altered ones ------------

def round_changing_stage(rounds, before, after):
    """The numbers (1-based) of the rounds that took the stage from `before` to `after`."""
    return [n for n, r in enumerate(rounds, 1) if (r.before["stage"], r.after["stage"]) == (before, after)]


def aged(start, after):
    """Players whose age byte (+1) rose by one between two `players` fields."""
    return sum(1 for w in range(3061) if start[20 * w + 1] and after[20 * w + 1] == start[20 * w + 1] + 1)


def mismatches(core, sealed):
    """[(round number, OracleMismatch)] for every round whose seven fields differ: all of them, so one run reports
    the whole season's difference and not only its first."""
    found = []
    for number, (c, s) in enumerate(zip(core, sealed), 1):
        try:
            so.check(LABEL.format(number), c.fields, s.fields)
        except so.OracleMismatch as error:
            found.append((number, error))
    return found


@dataclasses.dataclass
class Played:
    core: list              # the oracle's Round for each round, from the original under Unicorn
    sealed: list            # the same, from the sealed route
    repairs: list           # [(round, message, (off, on))]: the player's repairs of the eleven, made on the Core
    first: dict             # sealed_season, first run (its "rounds" are `sealed`)
    second: dict            # sealed_season, the same season again from the same start


def played():
    """The season on both sides, played once, success or failure (a failed season is not replayed by each test)."""
    if "outcome" not in PLAYED:
        try:
            PLAYED["outcome"] = (True, play())
        except BaseException as error:             # reported by every test that asks, from the one run
            PLAYED["outcome"] = (False, error)
    ok, value = PLAYED["outcome"]
    if not ok:
        raise value
    return value


PLAYED = {}


def play():
    """The Core's season first (CPython, Unicorn: the long part), then the sealed season twice in PyPy children
    beside each other, the player's repairs handed to the sealed side as the menus the Core was in."""
    from goal2.tests import pypy_engine
    blob, _ = start()
    began = time.monotonic()
    core, repairs, menus = core_season(blob)
    TIMES["core"] = time.monotonic() - began
    component = so.component_of(blob, GOAL_DAT)
    rebase = {number: so.component_of(menu, GOAL_DAT) for number, menu in menus.items()}
    children = [pypy_engine.start("goal2.tests.season_oracle:sealed_season", component, BOUND, rebase) for _ in range(2)]
    first, second = (child.result() for child in children)
    TIMES["season"] = time.monotonic() - began
    say(f"season: {len(core)} rounds; Core {TIMES['core']:.0f}s, sealed twice {TIMES['season'] - TIMES['core']:.0f}s, "
        f"whole {TIMES['season']:.0f}s, start {TIMES['boot'] + TIMES['new_game']:.2f}s; repairs {len(repairs)}")
    return Played(core, first["rounds"], repairs, first, second)


@requires.need(**NEEDS, slow=True)
class Season(unittest.TestCase):
    def test_every_round_of_the_season_equals_the_original(self):
        run = played()
        core, sealed = run.core, run.sealed
        # the same rounds on both sides, to the same end: neither side skipped or added a round
        self.assertEqual(len(core), len(sealed))
        self.assertLess(len(core), BOUND, "the season did not reach its terminal boundary within the bound")
        self.assertEqual([r.kind for r in core], [r.kind for r in sealed])
        self.assertEqual({r.kind for r in core[:-1]}, {"complete"})
        self.assertEqual(core[-1].kind, "deferred-rollover")
        # every round, not a sample, equal on all seven fields; the failure lists every round that differs
        found = mismatches(core, sealed)
        self.assertEqual(found, [], "\n".join(f"{error}" for _, error in found))
        for number, (c, s) in enumerate(zip(core, sealed), 1):
            label = LABEL.format(number)
            self.assertEqual((c.before, c.after), (s.before, s.after), label)
            # both sides started the round from the same seven fields (a repair is on both)
            self.assertEqual(c.start, s.start, label)
            # the press did nothing before play_round, so the menu and the route's own entry are one state
            self.assertEqual((c.facts["before_play_round"], c.facts["entry_changed"]), ([], []), label)
            # the round did something: a comparison of two unchanged states would prove nothing
            changed = [n for n in so.FIELDS if c.start[n] != c.fields[n]]
            self.assertLess(c.before["cursor"], c.after["cursor"], label)
            self.assertIn("fixtures", changed, label)
            self.assertIn("game", changed, label)
            self.assertEqual(c.facts["waiting"] is None, s.facts["waiting"] is None, label)
        # the season is the whole of the calendar from cursor 1 to the end of stage 4's fixtures
        self.assertEqual(core[0].before, START)
        self.assertEqual((core[-1].after["stage"], core[-1].after["cursor"], core[-1].after["count"]), (4, 1353, 1353))
        say(f"every one of {len(core)} rounds equal on {len(so.FIELDS)} fields; managed matches "
            f"{sum(r.facts['matches'] for r in sealed)}; stages {sorted({r.after['stage'] for r in core})}")

    def test_the_rounds_are_one_chain_and_a_repair_is_the_only_thing_between_two(self):
        run = played()
        repaired = {n for n, _, _ in run.repairs}
        for number in range(2, len(run.core) + 1):
            before, after = run.core[number - 2], run.core[number - 1]
            between = [n for n in so.FIELDS if before.fields[n] != after.start[n]]
            if number in repaired:
                say(f"round {number}: the repair changed {between}")
                self.assertTrue(between, f"round {number} was repaired and nothing changed")
                self.assertLessEqual(set(between), {"players", "game", "A91F", "countries"}, between)
            else:
                self.assertEqual(between, [], LABEL.format(number))
        say(f"{len(run.repairs)} repairs of the eleven, in rounds {sorted(repaired)}")

    def test_the_round_crossing_2_to_3_is_identified_equal_and_ages_players(self):
        run = played()
        core, sealed = run.core, run.sealed
        crossing = round_changing_stage(core, 2, 3)
        self.assertEqual(crossing, round_changing_stage(sealed, 2, 3))
        self.assertEqual(len(crossing), 1, "exactly one round takes the career from stage 2 to stage 3")
        number = crossing[0]
        c, s = core[number - 1], sealed[number - 1]
        label = LABEL.format(number) + " (2 to 3)"
        say(f"the 2 to 3 round is round {number} of {len(core)}")
        so.check(label, c.fields, s.fields)
        self.assertEqual((c.before["stage"], c.after["stage"], s.before["stage"], s.after["stage"]), (2, 3, 2, 3))
        # [confirmed: T111 Continuation; assumptions.md ROUND-AGEING-1] the managed twenty and the pool age at 2 to 3
        self.assertGreaterEqual(aged(c.start["players"], c.fields["players"]), 100)
        self.assertEqual(aged(c.start["players"], c.fields["players"]), aged(s.start["players"], s.fields["players"]))

    def test_the_terminal_step_equals_the_original_paused_at_the_same_site(self):
        run = played()
        core, sealed = run.core, run.sealed
        for side in (core[-1], sealed[-1]):
            self.assertTrue(so.at_terminal(side.after), side.after)      # cursor=count, rounds=1: not advanced
            self.assertEqual(side.after["stage"], 4)
            self.assertEqual(side.after["rounds"], 1)
        so.check(LABEL.format(len(core)) + " (terminal)", core[-1].fields, sealed[-1].fields)
        self.assertEqual((core[-1].before["stage"], sealed[-1].before["stage"]), (4, 4))
        self.assertTrue(core[-1].facts["paused"])
        self.assertFalse(any(r.facts["paused"] for r in core[:-1]))
        self.assertEqual(sealed[-1].kind, "deferred-rollover")

    def test_the_season_repeated_from_the_same_start_gives_the_same_results_and_news(self):
        run = played()
        first, second = run.first, run.second
        self.assertEqual(second["rounds"], first["rounds"])
        # the news pages and the fixtures each round published, in order
        self.assertEqual(second["news"], first["news"])
        self.assertEqual(second["played"], first["played"])
        self.assertGreater(sum(len(pages) for pages in first["news"]), 0)
        self.assertGreater(sum(len(fixtures) for fixtures in first["played"]), 0)
        # the final results: the fixtures field at the boundary
        self.assertEqual(second["rounds"][-1].fields["fixtures"], first["rounds"][-1].fields["fixtures"])
        # the boundary retains its results and news and repeats unchanged: one more advance() is the same observation
        step, again = first["repeat"]
        self.assertEqual((again.status, again.call_number, again.output_hash),
                         (step.status, step.call_number, step.output_hash))
        self.assertEqual((again.played_fixtures, again.news_pages), ((), ()))     # deltas belong to the first return only
        self.assertEqual(second["repeat"][1], again)
        self.assertEqual(again.rng_words, step.rng_words)


@requires.need(**NEEDS, slow=True)
class TheAccountingCanFail(unittest.TestCase):
    """The checks above are not vacuous: fed a season altered in one place, they name that place."""

    def test_an_altered_round_is_reported_with_its_number_field_and_record(self):
        run = played()
        bad = list(run.sealed)
        target = len(bad) // 2
        bad[target] = dataclasses.replace(bad[target], fields=so.corrupt(bad[target].fields, "players"))
        found = mismatches(run.core, bad)
        self.assertEqual([n for n, _ in found], [target + 1])
        self.assertEqual(found[0][1].fields, ("players",))
        self.assertIn(f"round {LABEL.format(target + 1)}: field players:", str(found[0][1]))

    def test_the_stage_crossing_finder_sees_a_changed_stage(self):
        run = played()
        self.assertEqual(len(round_changing_stage(run.core, 2, 3)), 1)
        self.assertEqual(round_changing_stage(run.core, 3, 2), [])


if __name__ == "__main__":
    unittest.main()
