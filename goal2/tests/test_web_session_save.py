"""Browser session save/load validation and complete metadata retention. [designed: T38]"""
from __future__ import annotations

import json
import tempfile
import unittest
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from goal2.game.session_save import encode
from goal2.web.server import Handler, WebSession, main
from goal2.tests.test_web_team_management import make_session


class WebSessionSaveTests(unittest.TestCase):
    def setUp(self):
        self.session = make_session()
        self.session.template_bytes = b"validated-template"
        self.session.save_path = Path(tempfile.mkdtemp()) / "session.g2save"
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
            for content in (b"not json", b'{"format":"goal2-session","version":99}'):
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


if __name__ == "__main__":
    unittest.main()
