"""[designed: T170d/#566] The Core oracle for the sealed season route: one round, one terminal step, and proof that it can fail.

The claim: for the same career, the same keys and the same match answers, one sealed round and the terminal step
leave the game in the state the original Core leaves it in, field by field (countries, players, fixtures, the game
block, DS:A91F, 7B62, 8336). The comparison is goal2/tests/season_oracle.py, which T170e and T170f import.

Fast controls (always run, no Unicorn, no PyPy): the comparator names the field and the round for every field, the
fields are read through the far pointers, and the route's key policy and the Core's are accounted for site by site.
Slow cases (GOAL2_SLOW=1; Unicorn, PyPy and the T111 checkpoints in .cache): the original's play_round against the
sealed SeasonSession on real careers, and the same comparison failing on a deliberately altered sealed input.
"""
from dataclasses import dataclass
import functools
import hashlib
import json
import unittest

from goal2.tests import requires, season_oracle as so

MANIFEST = json.loads((requires.ROOT / "docs/evidence/T111/artifacts.json").read_text())
ARTIFACTS = MANIFEST["artifacts"]
NEEDS = dict(modules=("unicorn",), files=tuple(a["name"] for a in ARTIFACTS) + ("GOAL.DAT",))
GOAL_DAT = requires.CACHE / "GOAL.DAT"


def fake_fields():
    """Seven fields of the right sizes with distinct, non-uniform bytes."""
    out = {name: bytes((i * 7 + len(name)) % 251 for i in range(size)) for name, _, size, _, _ in so.FIELD_SPECS}
    out.update({"7B62": 0x1234, "8336": 0xBEEF})
    return out


class Comparator(unittest.TestCase):
    def test_equal_fields_pass_and_the_field_set_is_the_tasks(self):
        self.assertEqual(so.FIELDS, ("countries", "players", "fixtures", "game", "A91F", "7B62", "8336"))
        fields = fake_fields()
        self.assertIsNone(so.check("r", fields, dict(fields)))
        # [confirmed: upstream E040 runner.py BLOCKS] 129 countries, 3061 players, 2409 fixtures, the game block, 0x195.
        self.assertEqual([len(fields[n]) for n in ("countries", "players", "fixtures", "game", "A91F")],
                         [129 * 0xBF, 3061 * 0x14, 2409 * 8, 0x10E, 0x195])

    def test_a_difference_in_any_one_field_names_that_field_and_the_round(self):
        fields = fake_fields()
        for name in so.FIELDS:
            with self.subTest(field=name):
                label = "1992 stage 2, round 3"
                with self.assertRaises(so.OracleMismatch) as caught:
                    so.check(label, fields, so.corrupt(fields, name))
                error = caught.exception
                self.assertEqual(error.fields, (name,))
                self.assertEqual(error.round, label)
                self.assertIn(f"round {label}: field {name}:", str(error))
                self.assertEqual(len(error.details), 1)
                # The other way round reports the same field: the check is symmetric in what it finds.
                with self.assertRaises(so.OracleMismatch) as other:
                    so.check(label, so.corrupt(fields, name), fields)
                self.assertEqual(other.exception.fields, (name,))

    def test_the_record_and_byte_are_named(self):
        fields = fake_fields()
        cases = {"players": f"player {(3061 * 0x14 // 2) // 0x14} +0x{(3061 * 0x14 // 2) % 0x14:02X}",
                 "fixtures": f"fixture {(2409 * 8 // 2) // 8 + 1} +0x{(2409 * 8 // 2) % 8:02X}",
                 "countries": f"country {(129 * 0xBF // 2) // 0xBF} +0x{(129 * 0xBF // 2) % 0xBF:02X}",
                 "game": f"game-block byte +0x{0x10E // 2:02X}", "A91F": f"manager slot {0x195 // 2 // 3} +0x{0x195 // 2 % 3:02X}"}
        for name, where in cases.items():
            with self.subTest(field=name), self.assertRaises(so.OracleMismatch) as caught:
                so.check("r", fields, so.corrupt(fields, name))
            self.assertIn(where, str(caught.exception))
            self.assertIn("core=0x", str(caught.exception))
            self.assertIn("sealed=0x", str(caught.exception))
        with self.assertRaises(so.OracleMismatch) as caught:
            so.check("r", fields, so.corrupt(fields, "7B62"))
        self.assertIn("core=0x1234 sealed=0x1235", str(caught.exception))

    def test_several_differing_fields_are_all_named_and_equal_ones_are_not(self):
        fields = fake_fields()
        bad = so.corrupt(so.corrupt(so.corrupt(fields, "players"), "fixtures"), "8336")
        with self.assertRaises(so.OracleMismatch) as caught:
            so.check("r", fields, bad)
        self.assertEqual(caught.exception.fields, ("players", "fixtures", "8336"))
        self.assertNotIn("countries", str(caught.exception))
        self.assertNotIn("7B62", str(caught.exception))

    def test_a_side_that_lacks_a_field_or_holds_an_extra_one_cannot_pass(self):
        fields = fake_fields()
        for name in so.FIELDS:
            short = {k: v for k, v in fields.items() if k != name}
            with self.subTest(missing=name):
                for args in ((short, fields), (fields, short)):
                    with self.assertRaises(so.OracleMismatch):
                        so.check("r", *args)
        with self.assertRaises(so.OracleMismatch):
            so.check("r", fields, dict(fields, extra=b""))
        with self.assertRaises(so.OracleMismatch):
            so.check("r", {}, {})

    def test_a_length_difference_is_reported_not_compared_byte_wise(self):
        fields = fake_fields()
        with self.assertRaises(so.OracleMismatch) as caught:
            so.check("r", fields, dict(fields, players=fields["players"][:-1]))
        self.assertEqual(caught.exception.fields, ("players",))
        self.assertIn("length", str(caught.exception))

    def test_observe_reads_each_field_through_its_far_pointer(self):
        memory = bytearray(0x60000)
        ds = 0x10000
        regions = {"countries": 0x20000, "players": 0x30000, "fixtures": 0x40000, "game": 0x50000, "A91F": 0x51000}
        for (name, _, size, _, _), other in zip(so.FIELD_SPECS, list(so.FIELD_SPECS)[1:]):
            self.assertLessEqual(regions[name] + size, regions[other[0]])     # the regions do not overlap
        for name, ptr, size, _, _ in so.FIELD_SPECS:
            base = regions[name]
            memory[ds + ptr:ds + ptr + 2] = (base & 15).to_bytes(2, "little")
            memory[ds + ptr + 2:ds + ptr + 4] = (base >> 4).to_bytes(2, "little")
            memory[base:base + size] = bytes((i + len(name)) % 256 for i in range(size))
        memory[ds + 0x7B62:ds + 0x7B64] = (0x1111).to_bytes(2, "little")
        memory[ds + 0x8336:ds + 0x8338] = (0x2222).to_bytes(2, "little")
        seen = []
        got = so.observe(lambda linear, size: seen.append((linear, size)) or bytes(memory[linear:linear + size]), ds)
        for name, ptr, size, _, _ in so.FIELD_SPECS:
            self.assertEqual(got[name], bytes(memory[regions[name]:regions[name] + size]), name)
        self.assertEqual((got["7B62"], got["8336"]), (0x1111, 0x2222))
        self.assertTrue(all(isinstance(got[n], bytes) for n in ("countries", "players", "fixtures", "game", "A91F")))
        # a read is a pointer word or a whole allocated block, nothing else
        self.assertEqual(sorted({size for _, size in seen}), sorted({2} | {spec[2] for spec in so.FIELD_SPECS}))

    def test_the_terminal_predicate_is_the_routes_own(self):
        good = dict(stage=4, cursor=1361, count=1361, rounds=1)
        self.assertTrue(so.at_terminal(good))
        self.assertTrue(so.at_terminal(dict(good, stage=8)))
        for change in (dict(stage=3), dict(stage=5), dict(cursor=1360), dict(rounds=2), dict(rounds=0)):
            self.assertFalse(so.at_terminal(dict(good, **change)), change)
        # the same predicate as the vendored route's deferral, on a real Image
        from goal2.engine.original_match import route
        from goal2.engine.original_match.image import Image
        from goal2.engine.original_match.machine import MEM_SIZE
        from goal2.game import engine_tables
        tables = engine_tables.load()
        image = Image.__new__(Image)
        image.header = bytes(0x78); image.load = 0x100; image.DS = image.load + 0x2581
        image.memory = bytearray(MEM_SIZE); image.tables = tables
        tables.place(image.memory, image.load)
        ds = image.DS * 16
        image.memory[ds + 0xA923:ds + 0xA925] = (0).to_bytes(2, "little")
        image.memory[ds + 0xA925:ds + 0xA927] = (0x3000).to_bytes(2, "little")
        game = 0x30000
        for cursor, count, rounds, stage in ((1361, 1361, 1, 4), (1361, 1361, 1, 8), (1361, 1361, 1, 5),
                                              (1360, 1361, 1, 4), (1361, 1361, 2, 4)):
            image.memory[game + 0x26:game + 0x28] = cursor.to_bytes(2, "little")
            image.memory[game + 0x28:game + 0x2A] = count.to_bytes(2, "little")
            image.memory[game + 0x3D] = rounds
            image.memory[game + 0x3C] = stage
            facts = so.game_facts(lambda linear, size: bytes(image.memory[linear:linear + size]), ds)
            self.assertEqual(facts, dict(stage=stage, cursor=cursor, count=count, rounds=rounds))
            self.assertEqual(so.at_terminal(facts), route._deferred_image(image), facts)


class KeyPolicy(unittest.TestCase):
    def test_every_route_key_site_has_a_core_counterpart_and_the_same_key(self):
        self.assertEqual(so.policy_problems(), [])

    def test_drift_between_the_two_policies_is_reported(self):
        from goal2.engine.original_match import route
        policy = so.route_keys()
        self.assertEqual(policy, dict(route.DEFAULT_KEYS))
        site = "000E:6B89"
        gone = {k: v for k, v in policy.items() if k != site}
        self.assertIn(f"route key site", " ".join(so.policy_problems(dict(policy, **{"000E:7777": 13}))))
        self.assertIn(f"CORE_KEYS names {site}", " ".join(so.policy_problems(gone)))
        self.assertIn(f"{site}: route key", " ".join(so.policy_problems(dict(policy, **{site: 0x20}))))
        watch = "214B:157C<0791:E86E"
        self.assertIn(f"{watch}: route key", " ".join(so.policy_problems(dict(policy, **{watch: route.ENTER}))))

    def test_the_core_polls_named_are_the_routes_polls_and_polled_sites_of_its_table(self):
        from goal2.core import screens
        from goal2.engine.original_match import route
        self.assertEqual(sorted(so.POLL_SITES), sorted(route.POLLS))
        for site in so.POLL_SITES:
            with self.subTest(site=site):
                self.assertTrue(screens.SITES[site].poll)
        self.assertEqual(screens.SITES["000E:6B89"].kind(None), "round-playing")
        self.assertEqual(screens.SITES["000E:6BF7"].kind(None), "round-playing")
        # The catalogue lists Space and Left/Right for round-playing and refuses Return: Core.queue could not give
        # the route's key there, which is why the oracle answers these polls itself (season_oracle.RouteKeyCore).
        self.assertFalse(screens.KINDS["round-playing"].accepts(13))

    def test_the_drivers_own_keys_are_checked_against_the_policy(self):
        self.assertEqual(so.driver_keys_problems([("bulletin", 13), ("match-watch-prompt", ord("n")),
                                                   ("manager-menu", 0x50), ("match-menu", 13)]), [])
        self.assertEqual(len(so.driver_keys_problems([("bulletin", 0x20)])), 1)
        self.assertEqual(len(so.driver_keys_problems([("match-watch-prompt", ord("y"))])), 1)

    def test_every_driver_key_is_one_the_drivers_round_really_presses(self):
        from goal2.core import screens
        from goal2.core.driver import Driver
        for site, (kind, how, name) in so.CORE_KEYS.items():
            if how != "driver":
                continue
            with self.subTest(site=site):
                self.assertIn(kind, screens.KINDS)
                key = {"Return": 13, "n": ord("n")}[name]
                if kind == "match-watch-prompt":
                    self.assertTrue(screens.KINDS[kind].accepts(key))
                elif kind.startswith("bulletin-"):
                    # Driver.round_continue presses Return at the first poll of these (#395/#409)
                    self.assertIn(kind, (screens.BULLETIN_ACHIEVEMENT, screens.BULLETIN_CONGRATULATIONS))
                    self.assertTrue(screens.KINDS[kind].polled and screens.KINDS[kind].accepts(key))
                else:
                    self.assertIn(kind, Driver.PASSING)       # _pass presses Return on every one of them
                    self.assertTrue(screens.KINDS[kind].accepts(key))


@dataclass(frozen=True)
class Case:
    """A real career position and how many rounds are compared from it."""
    name: str
    artifact: int               # index in docs/evidence/T111/artifacts.json (a manager-menu Core save)
    prepare: int                # rounds the Core plays first (T111's test policy for an eleven it refuses)
    rounds: int
    kinds: tuple                # the route's status for each compared round
    matches: tuple              # managed matches the sealed side holds in each
    why: str


# [designed: T170d] Every case starts from the original's own memory (the T111 saves, built by the original's keys);
# `prepare` plays whole rounds of the Core first, with T111's fix_eleven for an eleven the original refuses, because the
# sealed route chooses no eleven (T170: "Production chooses no legal eleven"). Those rounds are not compared.
CASES = (
    Case("ageing", 0, 0, 1, ("complete",), (0,),
         "[confirmed: T111 Continuation] the last silent round of the qualifying stage: stage_end, run_stage's builders "
         "and the in-season ageing at 2 to 3, with no managed match"),
    Case("managed-match", 1, 1, 1, ("complete",), (1,),
         "the second round of the continental groups: 59 silent fixtures and the managed side's match, whose eleven "
         "the original accepts, played with the default answers"),
    Case("terminal", 2, 0, 2, ("complete", "deferred-rollover"), (0, 0),
         "[derived: T170 scope, 000E:70E6] the knockout stage 4 from its second round: a completed round, then "
         "the explicit rollover boundary before stage_end, the Core stopped there"),
)


def checkpoint(case):
    """The saved Core the case starts from: the T111 artifact, hash-checked, after `prepare` rounds."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    from goal2.tests.test_core_continuation_t111 import fix_eleven
    item = ARTIFACTS[case.artifact]
    raw = (requires.CACHE / item["name"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    if not case.prepare:
        return raw
    core = Core.load(raw, goal_dat=GOAL_DAT)
    driver = Driver(core)
    for _ in range(case.prepare):
        driver.play_round(fix_eleven=fix_eleven)
    return core.save()


@functools.lru_cache(maxsize=None)
def played(case):
    """(core rounds, sealed rounds) for the case: the sealed child runs beside the Core. Played once per case."""
    from goal2.tests import pypy_engine
    blob = checkpoint(case)
    component = so.component_of(blob, GOAL_DAT)
    child = pypy_engine.start("goal2.tests.season_oracle:sealed_rounds", component, case.rounds)
    core = so.core_rounds(blob, GOAL_DAT, case.rounds)
    return core, child.result()


def aged(start, after):
    """Players whose age byte (+1) rose by one between two `players` fields."""
    return sum(1 for w in range(3061) if start[20 * w + 1] and after[20 * w + 1] == start[20 * w + 1] + 1)


@requires.need(**NEEDS, slow=True)
class OriginalRounds(unittest.TestCase):
    def equal_rounds(self, case):
        """The case played on both sides: same kinds, same match counts, and every round equal on all seven fields."""
        core, sealed = played(case)
        self.assertEqual([r.kind for r in core], list(case.kinds))
        self.assertEqual([r.kind for r in sealed], list(case.kinds))
        self.assertEqual([r.facts["matches"] for r in sealed], list(case.matches))
        for number, (c, s) in enumerate(zip(core, sealed), 1):
            label = f"{case.name}/{number}"
            so.check(label, c.fields, s.fields)
            # the same position before, the same position after
            self.assertEqual((c.before, c.after), (s.before, s.after), label)
            # the press did nothing before play_round, so the menu and the route's own entry are one state
            self.assertEqual((c.facts["before_play_round"], c.facts["entry_changed"]), ([], []), label)
            # the round did something: a comparison of two unchanged states would prove nothing
            self.assertLess(c.before["cursor"], c.after["cursor"], label)
            changed = [n for n in so.FIELDS if c.start[n] != c.fields[n]]
            self.assertIn("fixtures", changed, label)
            self.assertIn("game", changed, label)
            # the key state after the call agrees: a waiting key on both sides or on neither
            self.assertEqual(c.facts["waiting"] is None, s.facts["waiting"] is None, label)
        return core, sealed

    def test_the_ageing_round_equals_the_original(self):
        core, sealed = self.equal_rounds(CASES[0])
        self.assertEqual((core[0].before["stage"], core[0].after["stage"]), (2, 3))
        # [confirmed: T111 Continuation] 100 players of the managed side and the pool age; the whole array does here
        self.assertGreaterEqual(aged(core[0].start["players"], core[0].fields["players"]), 100)
        self.assertEqual(aged(core[0].start["players"], core[0].fields["players"]),
                         aged(sealed[0].start["players"], sealed[0].fields["players"]))

    def test_the_round_with_a_managed_match_equals_the_original(self):
        core, sealed = self.equal_rounds(CASES[1])
        self.assertEqual(core[0].after["stage"], 3)
        self.assertEqual(sealed[0].facts["matches"], 1)         # 59 fixtures with the advance, the match's own with resume

    def test_the_terminal_step_equals_the_original_paused_at_the_same_site(self):
        core, sealed = self.equal_rounds(CASES[2])
        for side in (core[-1], sealed[-1]):
            self.assertTrue(so.at_terminal(side.after), side.after)   # cursor=count, rounds=1, stage 4: not advanced
        self.assertEqual((core[-1].after["stage"], sealed[-1].after["stage"]), (4, 4))
        self.assertEqual(sealed[-1].facts["call"], 2)
        self.assertTrue(core[-1].facts["paused"])
        self.assertFalse(core[0].facts["paused"])

    def test_the_comparison_names_the_field_and_the_round_on_the_real_runs_too(self):
        case = CASES[0]
        core, sealed = played(case)
        label = f"{case.name}/1"
        so.check(label, core[0].fields, sealed[0].fields)
        for name in so.FIELDS:
            with self.subTest(corrupted=name), self.assertRaises(so.OracleMismatch) as caught:
                so.check(label, so.corrupt(core[0].fields, name), sealed[0].fields)
            self.assertEqual(caught.exception.fields, (name,))
            self.assertIn(f"round {label}: field {name}:", str(caught.exception))

    def test_a_real_difference_in_the_sealed_run_is_reported_by_name(self):
        """The sealed side starts from one changed byte of one player; nothing else differs. The oracle must say so."""
        from goal2.tests import pypy_engine
        case = CASES[0]
        blob = checkpoint(case)
        component = bytearray(so.component_of(blob, GOAL_DAT))
        from goal2.engine.original_match.image import Image
        image = Image(bytes(component))
        player = 1 + 3060 // 2
        address = image.far(0xA91B) + 20 * player + 0x0A + 0x78
        component[address] ^= 0x01
        child = pypy_engine.start("goal2.tests.season_oracle:sealed_rounds", bytes(component), 1)
        core = so.core_rounds(blob, GOAL_DAT, 1)
        sealed = child.result()
        with self.assertRaises(so.OracleMismatch) as caught:
            so.check("ageing/1 (sealed input altered)", core[0].fields, sealed[0].fields)
        self.assertEqual(caught.exception.fields, ("players",))
        self.assertIn(f"player {player} +0x0A", str(caught.exception))
        self.assertIn("round ageing/1 (sealed input altered)", str(caught.exception))




# The third kind of position: a managed retiree an earlier ageing flagged. [confirmed: this oracle, 2026-11-09; the
# Core's hook at 000E:56F3 runs before 000E:70B9] "Play next game" first replaces the retiree
# (replace_retiree), then calls play_round. The route starts at play_round, so it cannot do the first part.
RETIREE = dict(name="g16-bdf6c0842365fb09-congratulations-before.g2core",
               sha256="bdf6c0842365fb09a2767f5710ce8f2ecbba3340a43b19bc7ad8aa14bac82901")
PLAYER_RETIRED, PLAYER_REPLACEMENT = 2603, 2729


@functools.lru_cache(maxsize=None)
def retiree_run():
    """(Core round with its entry memory, sealed round from the menu, sealed round from the entry)."""
    from goal2.tests import pypy_engine
    raw = (requires.CACHE / RETIREE["name"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RETIREE["sha256"]
    menu = so.component_of(raw, GOAL_DAT)
    first = pypy_engine.start("goal2.tests.season_oracle:sealed_rounds", menu, 1)
    core = so.core_rounds(raw, GOAL_DAT, 1, entry=True)[0]
    second = pypy_engine.start("goal2.tests.season_oracle:sealed_rounds", core.entry, 1)
    return core, first.result()[0], second.result()[0]


@requires.need(modules=("unicorn",), files=(RETIREE["name"], "GOAL.DAT"), slow=True)
class RetireeReplacement(unittest.TestCase):
    def test_the_routes_own_call_equals_the_original_at_the_6_to_7_ageing(self):
        """play_round from the state where the original enters it: stage 6 to 7 (ageing, run_stage's builders, the
        stage announcement with the congratulations animation under the poll policy), equal on all seven fields."""
        core, _, sealed = retiree_run()
        so.check("retiree/1 (route entry)", core.fields, sealed.fields)
        self.assertEqual((core.before["stage"], core.after["stage"], sealed.after["stage"]), (6, 7, 7))
        self.assertEqual((core.kind, sealed.kind), ("complete", "complete"))
        self.assertGreaterEqual(aged(core.start["players"], core.fields["players"]), 100)

    def test_the_plays_step_before_play_round_is_not_the_routes_and_the_oracle_says_so(self):
        """Characterisation of a finding, not a Done-when: from the manager menu the sealed route differs from the
        original in exactly the replacement the Play action makes before play_round (the retiree's record zeroed, a
        fresh record in the pool). T170's integration owes that step; when it lands, this test is to be replaced by
        the equality."""
        core, sealed, _ = retiree_run()
        self.assertEqual(core.facts["before_play_round"], ["000E:56F3"])
        self.assertEqual(core.facts["entry_changed"], ["players", "game", "7B62"])
        with self.assertRaises(so.OracleMismatch) as caught:
            so.check("retiree/1 (manager menu)", core.fields, sealed.fields)
        self.assertEqual(caught.exception.fields, ("players",))
        self.assertIn(f"player {PLAYER_RETIRED} +0x00", str(caught.exception))
        self.assertIn("2 players", str(caught.exception))
        players = lambda side, w: side.fields["players"][20 * w:20 * w + 20]
        self.assertEqual(players(core, PLAYER_RETIRED), bytes(20))               # replace_retiree zeroes the retiree
        self.assertNotEqual(players(sealed, PLAYER_RETIRED), bytes(20))          # the route aged him instead
        self.assertEqual(players(sealed, PLAYER_REPLACEMENT), bytes(20))         # and made no replacement
        self.assertNotEqual(players(core, PLAYER_REPLACEMENT), bytes(20))


if __name__ == "__main__":
    unittest.main()
