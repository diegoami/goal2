"""Browser session save/load validation and complete metadata retention. [designed: T38]"""
from __future__ import annotations

import json
import copy
import tempfile
import unittest
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from goal2.engine.savestate import Savestate
from goal2.game.quick_match import run_full_match
from goal2.game.campaign import CampaignState, Fixture, UnsupportedCampaignTransition
from goal2.game.session_save import SessionSaveError, decode, encode, save as save_session_save
from goal2.game.state import from_savestate, to_savestate
from goal2.web.server import Handler, WebSession, main
from goal2.tests.test_web_team_management import make_session


FIXTURE = Path(__file__).resolve().parents[2] / ".cache" / "e010-r0001-halftime.sav"
GOALDAT = Path(__file__).resolve().parents[2] / ".cache" / "GOAL.DAT"


class WebSessionSaveTests(unittest.TestCase):
    def setUp(self):
        self.session = make_session()
        self.session.template_bytes = b"validated-template"
        self.temp = tempfile.TemporaryDirectory()
        self.session.save_path = Path(self.temp.name) / "session.g2save"
        self.server = HTTPServer(("127.0.0.1", 0), type("TestHandler", (Handler,), {"session": self.session}))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.continuation = patch("goal2.web.server.Savestate", side_effect=lambda raw: raw)
        self.adapter = patch("goal2.web.server.to_savestate", return_value=b"validated-continuation")
        self.state_reader = patch("goal2.web.server.from_savestate", return_value=self.session.state)
        self.matchup = patch("goal2.web.server.resolve_full_matchup", return_value=((7, 1), 0, 1))
        self.continuation.start()
        self.adapter.start()
        self.state_reader.start()
        self.matchup.start()

    def tearDown(self):
        self.continuation.stop()
        self.adapter.stop()
        self.state_reader.stop()
        self.matchup.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, endpoint, payload=None):
        data = json.dumps(payload or {}).encode()
        request = Request(self.base + endpoint, data=data,
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            try:
                return error.code, json.load(error)
            finally:
                error.close()

    def test_save_load_roundtrip_retains_full_browser_state_and_metadata(self):
        self.session.state.starting_eleven = list(range(281, 292))
        self.session.state.captain = 290
        self.session.state.country_tactics = 0xA5
        self.session.state.managed_country = 7
        self.session.state.match_count = 1
        self.session.state.rng_seed_7b62 = 0x1234
        self.session.state.rng_seed_8336 = 0xABCD
        self.session.state.last_match = {
            "teams": [1, 7], "score": [2, 1], "goals": [], "draws": 0,
            "halves": [{"score": [1, 0]}, {"score": [2, 1]}],
            "seed_DS7B62": 0x1234, "seed_DS8336": 0xABCD, "match_count": 1,
        }
        saved_snapshot = (list(self.session.state.starting_eleven), self.session.state.captain,
                          self.session.state.country_tactics, self.session.state.match_count,
                          self.session.state.rng_seed_7b62, self.session.state.rng_seed_8336,
                          json.loads(json.dumps(self.session.state.last_match)))
        status, result = self.request("/api/save")
        self.assertEqual((status, result), (200, {"saved": True}))
        saved_bytes = self.session.save_path.read_bytes()
        self.assertIn(b'"format":"goal2-session"', saved_bytes)
        decoded, decoded_template = decode(saved_bytes)
        self.assertEqual(encode(decoded, decoded_template), saved_bytes,
                         "canonical re-encoding covers every saved GameState field and template")

        self.session.state.managed_country = 8
        self.session.state.starting_eleven = list(range(280, 291))
        self.session.state.captain = 280
        self.session.state.country_tactics = 0
        self.session.state.match_count = 9
        status, loaded = self.request("/api/load")
        self.assertEqual(status, 200)
        self.assertEqual(self.session.save_path.read_bytes(), saved_bytes)
        self.assertEqual((self.session.state.starting_eleven, self.session.state.captain,
                          self.session.state.country_tactics, self.session.state.match_count,
                          self.session.state.rng_seed_7b62, self.session.state.rng_seed_8336,
                          self.session.state.last_match), saved_snapshot)
        self.assertEqual(loaded["country"]["id"], 7)
        self.assertEqual(loaded["confirmed"]["captain"], 290)
        self.assertGreater(loaded["confirmed"]["captain"], 255)
        self.assertEqual(loaded["last_match"]["score"], [2, 1])
        self.assertEqual(loaded["last_match"]["match_count"], 1)
        self.assertEqual(loaded["last_match"]["managed_side"], 1,
                         "legacy result derives the managed side from its saved country and teams")

    def test_corrupt_or_original_savestate_input_is_rejected_without_replacement(self):
        self.session.save_path.write_bytes(b"original-live-save")
        before = self.session.state
        try:
            for content in (b"\xff\xfe\x00\x01binary original savestate", b'{"format":"goal2-session","version":99}'):
                self.session.save_path.write_bytes(content)
                saved = self.session.save_path.read_bytes()
                status, result = self.request("/api/load")
                self.assertEqual(status, 400)
                self.assertIn("Could not load session", result["error"])
                self.assertIs(self.session.state, before)
                self.assertEqual(self.session.save_path.read_bytes(), saved)
        finally:
            self.session.save_path.write_bytes(b"original-live-save")

    def test_unusable_continuation_is_rejected_before_state_publication(self):
        self.session.save_path.write_bytes(encode(self.session.state, self.session.template_bytes))
        before = self.session.state
        with patch("goal2.web.server.to_savestate", side_effect=ValueError("invalid continuation")):
            status, result = self.request("/api/load")
        self.assertEqual(status, 400)
        self.assertIn("invalid continuation", result["error"])
        self.assertIs(self.session.state, before)

    def test_invalid_template_is_rejected_during_preload_validation(self):
        self.session.save_path.write_bytes(encode(self.session.state, self.session.template_bytes))
        before = self.session.state
        with patch("goal2.web.server.from_savestate", side_effect=ValueError("invalid saved template")) as validate:
            status, result = self.request("/api/load")
        self.assertEqual(status, 400)
        self.assertIn("invalid saved template", result["error"])
        self.assertIs(self.session.state, before)
        validate.assert_called_once_with(self.session.template_bytes)

    def test_campaign_save_is_refused_without_replacing_active_friendly_session(self):
        candidate = copy.deepcopy(self.session.state)
        candidate.campaign = CampaignState(
            start_year=1992, cycle=1, year=1, stage=2, seed_7b62=123, seed_8336=456,
            fixtures=(Fixture("friendly-1", 1, 1, 2, 1, 7, 8),),
        )
        campaign_bytes = encode(candidate, b"campaign-template")
        self.session.save_path.write_bytes(campaign_bytes)
        previous_state = self.session.state
        previous_template = self.session.template
        previous_template_bytes = self.session.template_bytes
        previous_token = self.session._play_token

        with self.assertRaisesRegex(UnsupportedCampaignTransition, "campaign sessions need"):
            self.session.load_from_configured_path()
        self.assertIs(self.session.state, previous_state)
        self.assertIs(self.session.template, previous_template)
        self.assertEqual(self.session.template_bytes, previous_template_bytes)
        self.assertEqual(self.session._play_token, previous_token)
        self.assertEqual(self.session.save_path.read_bytes(), campaign_bytes)

    def test_malformed_campaign_candidate_preserves_active_state_and_save_bytes(self):
        candidate = copy.deepcopy(self.session.state)
        candidate.campaign = CampaignState(1992, 1, 1, 2, 123, 456,
                                           (Fixture("friendly-1", 1, 1, 2, 1, 7, 8),))
        document = json.loads(encode(candidate, b"candidate template"))
        document["state"]["campaign"]["unexpected"] = True
        malformed = json.dumps(document).encode()
        self.session.save_path.write_bytes(malformed)
        before = (self.session.state, self.session.template, self.session.template_bytes,
                  self.session._play_token)

        with self.assertRaisesRegex(SessionSaveError, "invalid campaign metadata"):
            self.session.load_from_configured_path()
        self.assertIs(self.session.state, before[0])
        self.assertIs(self.session.template, before[1])
        self.assertEqual(self.session.template_bytes, before[2])
        self.assertEqual(self.session._play_token, before[3])
        self.assertEqual(self.session.save_path.read_bytes(), malformed)

    def test_malformed_last_result_is_rejected_before_state_publication(self):
        invalid = self.session.state
        invalid.last_match = {
            "teams": [7, 1], "score": [-1, 0], "goals": [], "draws": 0,
            "halves": [{"score": [0, 0]}, {"score": [0, 0]}],
            "seed_DS7B62": 1, "seed_DS8336": 2,
        }
        self.session.save_path.write_bytes(encode(invalid, self.session.template_bytes))
        before = self.session.state
        status, result = self.request("/api/load")
        self.assertEqual(status, 400)
        self.assertIn("last match score is invalid", result["error"])
        self.assertIs(self.session.state, before)

    def test_resume_cli_needs_no_original_savestate_path(self):
        save = self.session.save_path
        goaldat = save.parent / "GOAL.DAT"
        with patch.object(WebSession, "resume", return_value=self.session) as resume, \
             patch("goal2.web.server.serve") as serve:
            self.assertEqual(main(["--resume", str(save), str(goaldat), "--port", "0"]), 0)
        resume.assert_called_once_with(save, goaldat)
        serve.assert_called_once()
        self.assertEqual(self.session.save_path, save)

    def test_failed_save_reports_retry_and_keeps_previous_bytes(self):
        self.session.save_path.write_bytes(b"previous-valid-save")
        previous = self.session.save_path.read_bytes()
        with patch("goal2.game.session_save.os.fsync", side_effect=OSError("disk full")):
            status, result = self.request("/api/save")
        self.assertEqual(status, 500)
        self.assertIn("previous save is safe", result["error"])
        self.assertEqual(self.session.save_path.read_bytes(), previous)
        status, result = self.request("/api/save")
        self.assertEqual((status, result), (200, {"saved": True}))
        self.assertNotEqual(self.session.save_path.read_bytes(), previous)


@unittest.skipUnless(FIXTURE.is_file() and GOALDAT.is_file(),
                     "cached E010 savestate and GOAL.DAT are not staged")
class E010WebSaveContinuation(unittest.TestCase):
    def test_cached_e010_resumed_browser_session_matches_uninterrupted_continuation(self):
        with tempfile.TemporaryDirectory() as temporary:
            template_bytes = FIXTURE.read_bytes()
            uninterrupted = from_savestate(template_bytes)
            country = 13  # The staged roster has eligible captain IDs above 255.
            squad = [int.from_bytes(uninterrupted.countries[country][offset:offset + 2], "little")
                     for offset in range(0, 40, 2)]
            uninterrupted.managed_country = country
            uninterrupted.managed_squad = squad
            uninterrupted.starting_eleven = squad[:11]
            uninterrupted.captain = squad[-1]
            uninterrupted.country_tactics = 0xA5
            self.assertGreater(uninterrupted.captain, 255)

            first_template = to_savestate(uninterrupted, original=template_bytes)
            first = run_full_match(Savestate(first_template), uninterrupted, retain_state=True)
            uninterrupted.last_match["managed_side"] = first["managed_side"]
            uninterrupted.last_match["match_count"] = uninterrupted.match_count
            save_path = Path(temporary) / "session.g2save"
            save_session_save(save_path, uninterrupted, template_bytes)

            resumed_session = WebSession.resume(save_path, GOALDAT)
            resumed = resumed_session.state
            self.assertEqual(resumed.managed_country, country)
            self.assertEqual(resumed.managed_squad, squad)
            self.assertEqual(resumed.starting_eleven, squad[:11])
            self.assertEqual(resumed.captain, squad[-1])
            self.assertEqual(resumed.country_tactics, 0xA5)
            self.assertEqual(resumed.last_match["managed_side"], first["managed_side"])

            resumed_next = to_savestate(resumed, original=resumed_session.template_bytes)
            resumed_result = run_full_match(Savestate(resumed_next), resumed, retain_state=True)
            uninterrupted_next = to_savestate(uninterrupted, original=template_bytes)
            uninterrupted_result = run_full_match(Savestate(uninterrupted_next), uninterrupted, retain_state=True)
            self.assertEqual(resumed_result, uninterrupted_result)
            self.assertEqual(resumed, uninterrupted)


if __name__ == "__main__":
    unittest.main()
