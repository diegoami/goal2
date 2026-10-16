"""Campaign calendar, fresh state and strict save integration. [designed: T40]"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.data.goaldat import load as load_goaldat
from goal2.game.campaign import (
    CampaignError, CampaignState, Fixture, UnsupportedCampaignTransition,
    opening_calendar, start_campaign,
)
from goal2.game.new_game import country_rank, make_all_players, rating
from goal2.game.session_save import SessionSaveError, decode, encode
from goal2.game.state import GameState, SQUAD, _wrap_raw, from_savestate, to_savestate


ROOT = Path(__file__).resolve().parents[2]
DAT_PATH = ROOT / ".cache" / "GOAL.DAT"
TEMPLATE_PATH = ROOT / ".cache" / "e010-r0001-halftime.sav"


def _save_state(campaign=None):
    return GameState(
        players=[bytes(20) for _ in range(3061)],
        countries=[bytes(0xBF) for _ in range(129)],
        managed_country=7, managed_squad=list(range(121, 141)),
        rng_seed_7b62=0x1234, rng_seed_8336=0xABCD,
        match_state={"clock": 0, "score": (0, 0), "minute": 0, "half": 0},
        vga=b"synthetic VGA", mem=bytearray(b"synthetic Memory"),
        starting_eleven=list(range(121, 132)), campaign=campaign,
    )


def _fixtures():
    return (
        Fixture("stage2-a", 1, 1, 2, 1, 7, 8),
        Fixture("stage2-b", 1, 1, 2, 1, 7, 9),
        Fixture("stage3", 1, 2, 3, 1, 7, 10),
    )


class CampaignCalendar(unittest.TestCase):
    def campaign(self):
        return CampaignState(1992, 1, 1, 2, 0x1234, 0xABCD, _fixtures())

    def test_source_year_selects_ordinal_opening_stage(self):
        self.assertEqual(opening_calendar(1992), (1, 2))
        self.assertEqual(opening_calendar(1996), (1, 2))
        self.assertEqual(opening_calendar(1990), (3, 5))
        self.assertEqual(opening_calendar(1994), (3, 5))
        for unsupported in (1991, 1993, True):
            with self.assertRaises(CampaignError):
                opening_calendar(unsupported)

    def test_fixture_identity_order_and_competitive_boundary(self):
        campaign = self.campaign()
        campaign.complete_fixture("stage2-a")
        with self.assertRaisesRegex(CampaignError, "already completed"):
            campaign.complete_fixture("stage2-a")
        with self.assertRaisesRegex(CampaignError, "expected next fixture"):
            campaign.complete_fixture("stage3")

        competitive = CampaignState(
            1992, 1, 1, 2, 0, 0,
            (Fixture("qualifier", 1, 1, 2, 2, 7, 8),),
        )
        with self.assertRaisesRegex(UnsupportedCampaignTransition, "competitive result handler"):
            competitive.complete_fixture("qualifier")
        cross_stage = CampaignState(1992, 1, 1, 2, 0, 0, (
            Fixture("friendly", 1, 1, 2, 1, 7, 8),
            Fixture("competition", 1, 2, 3, 3, 7, 9),
        ))
        cross_stage.complete_fixture("friendly")
        with self.assertRaisesRegex(UnsupportedCampaignTransition, "begins with unsupported"):
            cross_stage.advance_calendar()
        with self.assertRaisesRegex(UnsupportedCampaignTransition, "builder"):
            CampaignState(1992, 1, 1, 2, 0, 0).advance_calendar()

    def test_ledger_requires_exact_prefix_and_calendar_cannot_skip(self):
        with self.assertRaisesRegex(CampaignError, "prefix"):
            CampaignState(1992, 1, 1, 2, 0, 0, _fixtures(), ["stage2-b"])
        with self.assertRaisesRegex(CampaignError, "skips"):
            CampaignState(1992, 1, 1, 2, 0, 0, (
                _fixtures()[0], Fixture("stage4", 1, 2, 4, 1, 7, 11),
            ))
        with self.assertRaisesRegex(CampaignError, "duplicate fixture ID"):
            CampaignState(1992, 1, 1, 2, 0, 0, (
                _fixtures()[0], Fixture("stage2-a", 1, 1, 2, 1, 7, 9),
            ))

    def test_competitive_fixture_cannot_enter_completed_ledger(self):
        queue = (
            Fixture("qualifier", 1, 1, 2, 2, 13, 14),
            Fixture("friendly", 1, 1, 2, 1, 13, 15),
        )
        with self.assertRaisesRegex(CampaignError, "unsupported competitive fixture"):
            CampaignState(1992, 1, 1, 2, 123, 456, queue, ["qualifier"])
        invalid = {
            "start_year": 1992, "cycle": 1, "year": 1, "stage": 2,
            "seed_7b62": 123, "seed_8336": 456,
            "fixtures": [fixture.__dict__ for fixture in queue],
            "completed_fixture_ids": ["qualifier"],
        }
        with self.assertRaisesRegex(CampaignError, "unsupported competitive fixture"):
            CampaignState.from_data(invalid)

    def test_campaign_save_roundtrips_at_stage_boundary_and_after_advance(self):
        state = _save_state(self.campaign())
        state.campaign.complete_fixture("stage2-a")
        before_advance = encode(state, b"template")
        resumed, template = decode(before_advance)
        self.assertEqual(template, b"template")
        self.assertEqual(resumed.campaign.completed_fixture_ids, ["stage2-a"])
        self.assertEqual(encode(resumed, template), before_advance)

        resumed.campaign.complete_fixture("stage2-b")
        boundary = encode(resumed, template)
        pending, _ = decode(boundary)
        self.assertEqual((pending.campaign.year, pending.campaign.stage), (1, 2))
        pending.campaign.advance_calendar()
        self.assertEqual((pending.campaign.year, pending.campaign.stage), (2, 3))
        advanced = encode(pending, template)
        loaded, loaded_template = decode(advanced)
        self.assertEqual((loaded.campaign.cycle, loaded.campaign.year, loaded.campaign.stage), (1, 2, 3))
        self.assertEqual(loaded.campaign.completed_fixture_ids, ["stage2-a", "stage2-b"])
        self.assertEqual(loaded.campaign.seed_7b62, 0x1234)
        self.assertEqual(loaded.campaign.seed_8336, 0xABCD)
        self.assertEqual(encode(loaded, loaded_template), advanced)

    def test_campaign_save_is_strict_and_friendly_save_stays_version_one(self):
        legacy = encode(_save_state(), b"friendly template")
        legacy_doc = json.loads(legacy)
        self.assertEqual(legacy_doc["version"], 1)
        self.assertNotIn("campaign", legacy_doc["state"])
        self.assertIsNone(decode(legacy)[0].campaign)

        campaign = encode(_save_state(self.campaign()), b"campaign template")
        document = json.loads(campaign)
        self.assertEqual(document["version"], 2)
        document["state"]["campaign"]["unexpected"] = True
        with self.assertRaisesRegex(SessionSaveError, "invalid campaign metadata"):
            decode(json.dumps(document).encode())
        document = json.loads(campaign)
        document["state"]["campaign"]["fixtures"][0]["home_country"] = True
        with self.assertRaisesRegex(SessionSaveError, "invalid campaign metadata"):
            decode(json.dumps(document).encode())

    def test_terminal_resume_refuses_campaign_before_entering_interactive_loop(self):
        from goal2 import loop

        campaign = _save_state(CampaignState(1992, 1, 1, 2, 10, 20, _fixtures()))
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.g2save"
            goaldat_path = Path(directory) / "GOAL.DAT"
            save_path.write_bytes(encode(campaign, b"template"))
            goaldat_path.write_bytes(b"placeholder GOAL.DAT")
            with patch.object(loop, "load_goaldat", return_value=object()), \
                 patch.object(loop, "load_session", return_value=(campaign, b"template")), \
                 patch.object(loop, "terminal_input") as terminal, \
                 patch.object(loop, "run_main_loop") as main_loop:
                self.assertEqual(loop.main(["loop", "--resume", str(save_path), str(goaldat_path)]), 2)
            terminal.assert_not_called()
            main_loop.assert_not_called()


class FreshCampaign(unittest.TestCase):
    def fixtures_or_skip(self):
        if not DAT_PATH.is_file() or not TEMPLATE_PATH.is_file():
            self.skipTest("local GOAL.DAT and engine-template savestate are required")
        return load_goaldat(DAT_PATH.read_bytes()), TEMPLATE_PATH.read_bytes()

    def _manager_address(self, state):
        raw = _wrap_raw(state.vga, bytearray(state.mem))
        pointer = raw.ds_bytes(0xA91F, 4)
        offset, segment = int.from_bytes(pointer[:2], "little"), int.from_bytes(pointer[2:], "little")
        return raw, segment * 16 + offset

    def test_fresh_state_rebuilds_players_countries_managers_and_resets_match_data(self):
        goaldat, pristine_template = self.fixtures_or_skip()
        dirty = from_savestate(pristine_template)
        dirty.players[1] = bytes([0xEE]) * 20
        dirty.countries[1] = bytes([0xD1]) * 0xBF
        dirty.countries[13] = bytes([0xD7]) * 0xBF
        dirty.match_state = {"clock": 91, "score": (8, 6), "minute": 91, "half": 2}
        dirty.match_count = 12
        dirty.last_match = {"score": (8, 6)}
        raw, manager_address = self._manager_address(dirty)
        raw.mem_write(manager_address + 3 + 1, b"\xFF")
        raw.mem_write(manager_address + 3 * 129 + 1, b"\xEE")
        raw.mem_write(manager_address + 135 * 3, b"\xA7")
        dirty.mem = raw.mem
        dirty_template = to_savestate(dirty, pristine_template)

        first = start_campaign(
            goaldat, dirty_template, managed_country=13, start_year=1992,
            seed_7b62=0xCAFE, seed_8336=0xBEEF,
        )
        second = start_campaign(
            goaldat, dirty_template, managed_country=13, start_year=1992,
            seed_7b62=0xCAFE, seed_8336=0xBEEF,
        )
        self.assertEqual(first.players, second.players)
        self.assertEqual(first.players, make_all_players(goaldat, 13))
        self.assertEqual((first.rng_seed_7b62, first.rng_seed_8336), (0xCAFE, 0xBEEF))
        self.assertEqual((first.campaign.seed_7b62, first.campaign.seed_8336), (0xCAFE, 0xBEEF))
        self.assertEqual(first.match_state, {"clock": 0, "score": (0, 0), "minute": 0, "half": 0})
        self.assertEqual((first.match_count, first.last_match), (0, None))
        self.assertEqual(first.players[1][0x12:0x14], b"\xff\x7f")

        world, continent, within = country_rank(goaldat, 1)
        country = first.countries[1]
        self.assertEqual([int.from_bytes(country[i:i + 2], "little") for i in range(0, 40, 2)],
                         list(range(1, SQUAD + 1)))
        self.assertEqual((country[0x28], country[0x29], country[0x2A], country[0x2B], country[0x2C]),
                         (within, world, within, world, continent))
        self.assertEqual(country[0x2D], goaldat.per_country_a[1])
        self.assertEqual(country[0x2E], 1)
        self.assertEqual(country[0x30:], bytes(0xBF - 0x30))
        managed = first.countries[13]
        self.assertEqual(managed[0x2D], goaldat.per_country_a[13])
        self.assertEqual(managed[0x2E], 0x81)
        self.assertEqual(first.country_tactics, goaldat.per_country_a[13])
        self.assertEqual(first.managed_squad, list(range(241, 261)))
        self.assertEqual(first.captain, 0)

        fresh_raw, fresh_manager_address = self._manager_address(first)
        self.assertEqual(fresh_raw.memory(fresh_manager_address + 3 + 1, 1), bytes([rating(goaldat, 1)]))
        self.assertEqual(fresh_raw.memory(fresh_manager_address + 3 * 129 + 1, 1),
                         bytes([rating(goaldat, 13)]))
        self.assertEqual(fresh_raw.memory(fresh_manager_address + 135 * 3, 1), b"\xA7")

        first.captain = 260
        saved, template = decode(encode(first, dirty_template))
        self.assertEqual(saved, first)
        self.assertGreater(saved.captain, 255)
        self.assertEqual(template, dirty_template)


if __name__ == "__main__":
    unittest.main()
