"""[designed: T41] Scheduled pair routing and atomic browser transactions."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.web.server import WebSession, StalePlaySubmission
from goal2.game.session_save import encode, decode

ROOT = Path(__file__).resolve().parents[2]


class CampaignFriendlies(unittest.TestCase):
    def setUp(self):
        self.session = WebSession.load(ROOT / ".cache/e010-r0008-halftime.sav", ROOT / ".cache/GOAL.DAT")

    def start(self):
        return self.session.new_campaign({"country": 4, "start_year": 1990,
                                          "seed_7b62": 0x1234, "seed_8336": 0x8336})

    def play(self, view=None):
        view = view or self.session.view()
        return self.session.play({"play_token": view["play_token"],
                                  "fixture_id": view["campaign"]["next_fixture"]["fixture_id"]})

    def test_actual_runner_uses_both_scheduled_pairs_and_stops_at_qualifier(self):
        view = self.start()
        self.assertEqual(view["matchup"]["teams"], [4, 1])
        self.assertEqual(view["campaign"]["next_fixture"]["fixture_id"], "original:1378")
        first = self.play(view)
        self.assertEqual([t["id"] for t in first["last_match"]["teams"]], [4, 1])
        self.assertEqual(first["matchup"]["teams"], [9, 4])
        self.assertEqual(first["matchup"]["managed_side"], 1)
        second = self.play(first)
        self.assertEqual([t["id"] for t in second["last_match"]["teams"]], [9, 4])
        self.assertEqual(second["match_count"], 2)
        self.assertEqual([r["fixture_id"] for r in second["campaign"]["history"]],
                         ["original:1378", "original:1471"])
        self.assertEqual(second["campaign"]["next_fixture"]["kind"], 5)
        self.assertFalse(second["matchup"]["available"])
        self.assertIn("unsupported", second["matchup"]["message"])
        before = copy.deepcopy(self.session.state)
        with self.assertRaises(ValueError):
            self.play(second)
        self.assertEqual(self.session.state, before)

    def test_stale_duplicate_wrong_fixture_and_management_tokens(self):
        initial = self.start()
        with self.assertRaises(StalePlaySubmission):
            self.session.play({"play_token": initial["play_token"], "fixture_id": "original:1471"})
        self.assertEqual(self.session.state.match_count, 0)
        first = self.play(initial)
        with self.assertRaises(StalePlaySubmission):
            self.play(initial)
        self.assertEqual(self.session.state.match_count, 1)
        self.session.confirm_management({"country": 4, **first["confirmed"]})
        with self.assertRaises(StalePlaySubmission):
            self.play(first)
        self.assertEqual(self.session.state.match_count, 1)

    def test_failed_simulation_and_failed_response_never_publish(self):
        self.start()
        for target in ("goal2.web.server.run_full_match", "goal2.web.server.WebSession._session_view"):
            with self.subTest(target=target):
                view = self.session.view()
                before = copy.deepcopy(self.session.state)
                with patch(target, side_effect=RuntimeError("injected failure")):
                    with self.assertRaises(RuntimeError):
                        self.play(view)
                self.assertEqual(self.session.state, before)
                with self.assertRaises(StalePlaySubmission):
                    self.play(view)
        self.assertEqual(self.play()["match_count"], 1)

    def test_save_load_resume_and_reads_keep_history_without_play(self):
        self.start()
        self.play()
        self.play()
        with tempfile.TemporaryDirectory() as folder:
            self.session.save_path = Path(folder) / "campaign.g2save"
            before = copy.deepcopy(self.session.state)
            self.session.view()
            self.session.save_to_configured_path()
            self.session.load_from_configured_path()
            self.assertEqual(self.session.state, before)
            resumed = WebSession.resume(self.session.save_path, ROOT / ".cache/GOAL.DAT")
            self.assertEqual(resumed.state, before)
            self.assertEqual(len(resumed.view()["campaign"]["history"]), 2)
            self.assertFalse(resumed.view()["matchup"]["available"])

    def test_campaign_cannot_switch_manager_and_invalid_start_is_atomic(self):
        self.start()
        before = copy.deepcopy(self.session.state)
        with self.assertRaises(ValueError):
            self.session.select_country(13)
        for key, value in (("country", True), ("start_year", 1991), ("seed_7b62", -1), ("seed_8336", 65536)):
            data = {"country": 4, "start_year": 1990, "seed_7b62": 0x1234, "seed_8336": 0x8336}
            data[key] = value
            with self.assertRaises(ValueError):
                self.session.new_campaign(data)
            self.assertEqual(self.session.state, before)

    def test_history_roundtrip_and_tampered_history_rejection(self):
        self.start()
        self.play()
        state, _ = decode(encode(self.session.state, self.session.template_bytes))
        self.assertEqual(state.campaign.results, self.session.state.campaign.results)
        state.campaign.results[0]["teams"] = [4, 13]
        with self.assertRaises(ValueError):
            encode(state, self.session.template_bytes)

    def test_friendly_still_uses_token_only_and_new_campaign_invalidates_old_token(self):
        old = self.session.view()["play_token"]
        friendly = self.session.play({"play_token": old})
        self.assertEqual(friendly["match_count"], 1)
        self.assertIsNone(friendly["campaign"])
        self.start()
        with self.assertRaises(StalePlaySubmission):
            self.session.play({"play_token": friendly["play_token"], "fixture_id": "original:1378"})


if __name__ == "__main__":
    unittest.main()
