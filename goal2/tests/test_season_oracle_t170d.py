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
        memory = bytearray(0x40000)
        ds = 0x10000
        regions = {"countries": 0x20000, "players": 0x30000, "fixtures": 0x3A000, "game": 0x3F000, "A91F": 0x3F800}
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
        # nothing was written, and every read is bounded by the allocated sizes
        self.assertTrue(all(size in (2, 4) or size in {s[2] for s in so.FIELD_SPECS} for _, size in seen))

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

    def test_the_core_polls_named_are_polled_sites_of_its_own_table(self):
        from goal2.core import screens
        queued = [site for site, (kind, how, name) in so.CORE_KEYS.items() if how == "queued"]
        self.assertEqual(sorted(queued), ["000E:6B89", "000E:6B92", "000E:6BF7"])
        for site in ("000E:6B89", "000E:6BF7"):          # 6B92 is the read of the key 6B89's poll found: no Core site
            with self.subTest(site=site):
                self.assertTrue(screens.SITES[site].poll)
                self.assertEqual(screens.SITES[site].kind(None), "round-playing")
        self.assertEqual(so.QUEUED_KINDS, ("round-playing",))
        self.assertTrue(screens.KINDS["round-playing"].polled)
        # The catalogue lists Space and Left/Right for this kind and refuses Return: the reason the oracle puts
        # the route's Return into the queue itself.
        self.assertFalse(screens.KINDS["round-playing"].accepts(13))

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
