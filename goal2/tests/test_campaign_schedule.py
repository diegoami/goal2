"""T41a opening draws, source loops and managed projection."""
from __future__ import annotations

import collections
import unittest
from pathlib import Path

from goal2.data.goaldat import load as load_goaldat
from goal2.engine.savestate import Savestate, with_memory
from goal2.game.campaign import CampaignError, UnsupportedCampaignTransition
from goal2.game.campaign_schedule import build_opening_campaign, start_opening_campaign
from goal2.game.session_save import decode, encode


ROOT = Path(__file__).resolve().parents[2]
GOAL_DAT = ROOT / ".cache" / "GOAL.DAT"
TEMPLATE = ROOT / ".cache" / "e010-r0008-halftime.sav"


def _required_inputs(test: unittest.TestCase):
    if not GOAL_DAT.is_file() or not TEMPLATE.is_file():
        test.skipTest("local GOAL.DAT and E010 template are required")
    return load_goaldat(GOAL_DAT.read_bytes()), TEMPLATE.read_bytes()


def _source_loop_oracle(goaldat, template: bytes, *, start_year: int, seed: int):
    """Independent F023 loop transcription using raw LCG arithmetic and local DS bytes."""
    state = Savestate(template)
    stage = 2 if start_year % 4 == 0 else 5
    year = 1 if stage == 2 else 3
    slot_bytes = state.ds_bytes(0x0F76, 16)
    slot_rows = [tuple(slot_bytes[i:i + 4]) for i in range(0, 16, 4)]
    pair_bytes = state.ds_bytes(0x0F54, 0x13A)
    partner_bytes = state.ds_bytes(0x1087, 55)
    thresholds = state.ds_bytes(0x1106, 2)
    number = int.from_bytes(state.ds_bytes(0x6936 + (0 if stage == 2 else 2), 2), "little")

    continental = tuple(goaldat.per_country_c[1:])
    world = tuple(goaldat.per_country_b[1:])
    where = {country: position for position, country in enumerate(continental)}
    continent = {country: position // 32 + 1 for country, position in where.items()}
    order = list(continental) if stage == 2 else [
        country for cont in range(1, 5) for country in world if continent[country] == cont
    ]

    seed_word = seed

    def rand(n):
        nonlocal seed_word
        seed_word = (seed_word * 0x7ABD + 0x1B0F) & 0xFFFF
        return ((seed_word * n) >> 16) + 1

    pots = []
    for block in range(16):
        row = order[8 * block:8 * block + 8]
        for _ in range(4):
            a, b = rand(8) - 1, rand(8) - 1
            row[a], row[b] = row[b], row[a]
        pots.append(row)

    groups = []
    by_group = {}
    for cont in range(1, 5):
        for group in range(1, 9):
            permutation = slot_rows[rand(4) - 1]
            assigned = [None] * 4
            for pot in range(4):
                assigned[permutation[pot] - 1] = pots[(cont - 1) * 4 + pot][group - 1]
            assigned = tuple(assigned)
            groups.append((cont, group, assigned))
            by_group[(cont, group)] = assigned

    rows = []
    for rnd in range(1, 13):
        for cont in range(1, 5):
            for group in range(1, 9):
                partner = partner_bytes[6 * group + rnd] if rnd < (thresholds[1] if stage == 2 else thresholds[0]) else 0
                if partner:
                    for slot in range(4):
                        rows.append((number, rnd, cont, 0, group, partner, 1,
                                     by_group[(cont, partner)][slot], by_group[(cont, group)][slot]))
                        number += 1
                offset = 0x18 * (group + cont) + 2 * rnd
                pair_a, pair_b = pair_bytes[offset], pair_bytes[offset + 1]
                group_teams = by_group[(cont, group)]
                rows.append((number, rnd, cont, group, group, None, stage,
                             group_teams[pair_a - 1], group_teams[pair_b - 1]))
                number += 1
    return year, stage, tuple(groups), tuple(rows), seed_word


@unittest.skipUnless(GOAL_DAT.is_file() and TEMPLATE.is_file(),
                     "local GOAL.DAT and E010 template are required")
class OpeningCampaignSchedule(unittest.TestCase):
    def test_source_loop_oracle_matches_both_opening_draws_and_final_rng(self):
        goaldat, template = _required_inputs(self)
        for start_year, managed, expected_first in (
            (1992, 13, ("original:14", "original:117", "original:213")),
            (1990, 4, ("original:1378", "original:1471", "original:1475")),
        ):
            with self.subTest(start_year=start_year):
                result = build_opening_campaign(
                    goaldat, template, start_year=start_year,
                    seed_7b62=0x1234, seed_8336=0x8336,
                )
                year, stage, groups, rows, final_seed = _source_loop_oracle(
                    goaldat, template, start_year=start_year, seed=0x1234,
                )
                self.assertEqual((result.year, result.stage), (year, stage))
                self.assertEqual(
                    tuple((group.continent, group.group, group.countries_by_slot)
                          for group in result.groups), groups,
                )
                self.assertEqual(
                    tuple((row.fixture_number, row.round, row.continent, row.group,
                           row.draw_group, row.opponent_group, row.kind,
                           row.country_a, row.country_b) for row in result.fixtures), rows,
                )
                self.assertEqual(result.post_draw_seed_7b62, final_seed)
                self.assertEqual(result.post_draw_seed_7b62, 37972)
                self.assertEqual(result.post_draw_seed_8336, 0x8336)
                self.assertEqual(tuple(row.fixture_id for row in result.managed_fixtures(managed))[:3], expected_first)

    def test_groups_fixtures_counts_kinds_and_source_order(self):
        goaldat, template = _required_inputs(self)
        for start_year, expected_rows, appearances, friendly_count, competitive_kind in (
            (1992, 768, 12, 384, 2),
            (1990, 640, 10, 256, 5),
        ):
            with self.subTest(start_year=start_year):
                result = build_opening_campaign(
                    goaldat, template, start_year=start_year,
                    seed_7b62=0xBEEF, seed_8336=0x1234,
                )
                self.assertEqual(len(result.groups), 32)
                self.assertEqual([(g.continent, g.group) for g in result.groups],
                                 [(c, g) for c in range(1, 5) for g in range(1, 9)])
                drawn = [country for group in result.groups for country in group.countries_by_slot]
                self.assertEqual(set(drawn), set(range(1, 129)))
                self.assertEqual(len(drawn), 128)
                initial = list(goaldat.per_country_c[1:]) if result.stage == 2 else [
                    country for cont in range(1, 5) for country in goaldat.per_country_b[1:]
                    if (goaldat.per_country_c.index(country) - 1) // 32 + 1 == cont
                ]
                for group in result.groups:
                    pot_country_sets = [
                        set(initial[(group.continent - 1) * 32 + pot * 8:
                                    (group.continent - 1) * 32 + (pot + 1) * 8])
                        for pot in range(4)
                    ]
                    for pot in pot_country_sets:
                        self.assertEqual(sum(country in pot for country in group.countries_by_slot), 1)
                self.assertEqual(len(result.fixtures), expected_rows)
                self.assertEqual([row.fixture_number for row in result.fixtures],
                                 list(range(result.fixtures[0].fixture_number,
                                            result.fixtures[0].fixture_number + expected_rows)))
                self.assertEqual(len({row.fixture_id for row in result.fixtures}), expected_rows)
                self.assertTrue(all(row.fixture_id == f"original:{row.fixture_number}"
                                    for row in result.fixtures))
                self.assertEqual(collections.Counter(row.kind for row in result.fixtures),
                                 {1: friendly_count, competitive_kind: expected_rows - friendly_count})
                appearances_by_country = collections.Counter(
                    country for row in result.fixtures for country in (row.country_a, row.country_b)
                )
                self.assertEqual(set(appearances_by_country.values()), {appearances})
                self.assertTrue(all(row.country_a != row.country_b for row in result.fixtures))
                self.assertEqual(
                    [(row.round, row.continent, row.draw_group) for row in result.fixtures],
                    sorted((row.round, row.continent, row.draw_group) for row in result.fixtures),
                )
                self.assertTrue(all(row.group == 0 for row in result.fixtures if row.kind == 1))
                self.assertTrue(all(row.group == row.draw_group for row in result.fixtures if row.kind != 1))

    def test_managed_projection_keeps_friendly_prefix_and_qualifier_barrier_through_save(self):
        goaldat, template = _required_inputs(self)
        state, opening = start_opening_campaign(
            goaldat, template, managed_country=4, start_year=1990,
            seed_7b62=0x1234, seed_8336=0x8336,
        )
        queue = state.campaign.fixtures
        self.assertGreaterEqual(len(queue), 3)
        self.assertEqual([fixture.fixture_id for fixture in queue[:3]],
                         ["original:1378", "original:1471", "original:1475"])
        self.assertEqual([fixture.kind for fixture in queue[:3]], [1, 1, 5])
        self.assertEqual([(fixture.side_a, fixture.side_b) for fixture in queue[:3]],
                         [(4, 1), (9, 4), (4, 26)])
        state.campaign.complete_fixture(queue[0].fixture_id)
        state.campaign.complete_fixture(queue[1].fixture_id)
        with self.assertRaises(UnsupportedCampaignTransition):
            state.campaign.complete_fixture(queue[2].fixture_id)
        with self.assertRaises(CampaignError):
            state.campaign.advance_calendar()
        saved = encode(state, template)
        resumed, _ = decode(saved)
        self.assertEqual([f.fixture_id for f in resumed.campaign.fixtures],
                         [f.fixture_id for f in state.campaign.fixtures])
        self.assertEqual(resumed.campaign.completed_fixture_ids,
                         state.campaign.completed_fixture_ids)
        self.assertEqual((resumed.rng_seed_7b62, resumed.rng_seed_8336),
                         (opening.post_draw_seed_7b62, opening.post_draw_seed_8336))
        self.assertEqual((resumed.campaign.seed_7b62, resumed.campaign.seed_8336),
                         (0x1234, 0x8336))

    def test_invalid_template_tables_reject_without_mutating_inputs(self):
        goaldat, template = _required_inputs(self)
        before = (list(goaldat.per_country_b), list(goaldat.per_country_c), template)
        with self.assertRaises(CampaignError):
            build_opening_campaign(goaldat, b"not a local savestate", start_year=1992,
                                   seed_7b62=1, seed_8336=2)
        state = Savestate(template)
        bad_pair_address = state.program().ds_base + 0x0F86
        invalid = with_memory(template, bad_pair_address, b"\0")
        with self.assertRaisesRegex(CampaignError, "schedule row"):
            build_opening_campaign(goaldat, invalid, start_year=1992,
                                   seed_7b62=1, seed_8336=2)
        self.assertEqual((goaldat.per_country_b, goaldat.per_country_c, template), before)

    def test_invalid_goal_orders_and_managed_country_reject(self):
        goaldat, template = _required_inputs(self)
        broken = type("BadGoalDat", (), {})()
        broken.per_country_b = list(goaldat.per_country_b)
        broken.per_country_c = list(goaldat.per_country_c)
        broken.per_country_b[1] = broken.per_country_b[2]
        with self.assertRaisesRegex(CampaignError, "world order"):
            build_opening_campaign(broken, template, start_year=1992,
                                   seed_7b62=1, seed_8336=2)
        result = build_opening_campaign(goaldat, template, start_year=1992,
                                        seed_7b62=1, seed_8336=2)
        for value in (True, 0, 129, "13"):
            with self.subTest(managed_country=value):
                with self.assertRaises(CampaignError):
                    result.managed_fixtures(value)


if __name__ == "__main__":
    unittest.main()
