"""[designed: T37] Explicit, one-shot browser friendlies and retained results."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from http.server import HTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from goal2.game.state import GameState
from goal2.engine.savestate import Savestate
from goal2.game.quick_match import run_full_match
from goal2.game.state import from_savestate, to_savestate
from goal2.web.server import Handler, WebSession


def make_session() -> WebSession:
    squad = list(range(280, 300))
    players = [bytes(0x14) for _ in range(3061)]
    state = GameState(
        players=players, countries=[bytes(0xBF) for _ in range(129)],
        managed_country=7, managed_squad=squad, rng_seed_7b62=11,
        rng_seed_8336=22, match_state={}, vga=b"", mem=b"",
        starting_eleven=squad[:11], captain=squad[3], country_tactics=0xA5,
    )
    goaldat = type("GoalDatStub", (), {
        "country_names": ["" if i == 0 else f"Country {i}" for i in range(129)],
        "player_names": ["" if i == 0 else f"Player {i}" for i in range(3061)],
        "player_initials": ["" for _ in range(3061)],
    })()
    return WebSession(state, goaldat, object(), b"synthetic-original-savestate")


class BrowserMatchesTests(unittest.TestCase):
    def setUp(self):
        self.session = make_session()
        self.snapshot = copy.deepcopy(self.session.state)
        self.resolver = patch("goal2.web.server.resolve_full_matchup", return_value=((7, 1), 0, 1))
        self.resolver.start()

    def tearDown(self):
        self.resolver.stop()
        self.session.state = self.snapshot

    def serve(self):
        handler = type("TestHandler", (Handler,), {"session": self.session})
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://127.0.0.1:{server.server_port}"

    def http(self, url, payload=None, method="GET"):
        request = Request(url, method=method)
        if payload is not None:
            request = Request(url, data=json.dumps(payload).encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request) as response:
                content = response.read()
                return response.status, (json.loads(content) if "json" in response.headers.get("Content-Type", "") else content)
        except HTTPError as error:
            try:
                return error.code, json.load(error)
            finally:
                error.close()

    def test_explicit_play_retains_confirmed_state_named_result_and_seeds(self):
        confirmed = {
            "country": 7, "starting_eleven": list(range(281, 292)),
            "captain": 290, "tactics": 0x69,
        }
        self.session.confirm_management(confirmed)
        before = self.session.state

        adapted_template = object()

        def simulate(template, candidate, *, retain_state):
            self.assertIs(template, adapted_template)
            self.assertTrue(retain_state)
            self.assertEqual(candidate.managed_country, 7)
            self.assertEqual(candidate.starting_eleven, confirmed["starting_eleven"])
            self.assertEqual(candidate.captain, 290)
            self.assertEqual(candidate.country_tactics, 0x69)
            candidate.players[281] = bytes([0] * 14 + [19] + [0] * 5)
            candidate.rng_seed_7b62 = 1234
            candidate.rng_seed_8336 = 5678
            candidate.match_count += 1
            candidate.last_match = {
                "teams": (7, 1), "managed_side": 0, "score": (1, 0),
                "goals": [{"team": 0, "minute": 37, "player": 281}],
                "halves": ({"score": (0, 0)}, {"score": (1, 0)}),
                "seed_DS7B62": 1234, "seed_DS8336": 5678,
            }
            return {"score": (1, 0), "managed_side": 0}

        with patch("goal2.web.server.to_savestate", return_value=b"adapted") as adapt, \
             patch("goal2.web.server.Savestate", return_value=adapted_template), \
             patch("goal2.web.server.run_full_match", side_effect=simulate) as runner:
            result = self.session.play({"play_token": self.session.view()["play_token"]})
        adapt.assert_called_once()
        adapted_state = adapt.call_args.args[0]
        self.assertIsNot(adapted_state, before)
        self.assertEqual(adapted_state.starting_eleven, confirmed["starting_eleven"])
        self.assertEqual(adapt.call_args.kwargs, {"original": self.session.template_bytes})
        runner.assert_called_once()
        self.assertIsNot(self.session.state, before)
        self.assertEqual(self.session.state.players[281][0x0E], 19)
        self.assertEqual(next(player for player in result["players"] if player["id"] == 281)["energy"], 19,
                         "successful play response immediately shows retained player energy")
        self.assertEqual(self.session.state.match_count, 1)
        self.assertEqual(result["last_match"], {
            "teams": [{"id": 7, "name": "Country 7"}, {"id": 1, "name": "Country 1"}],
            "managed_side": 0, "score": [1, 0],
            "goals": [{"team": 7, "team_name": "Country 7", "minute": 37,
                       "player": 281, "player_name": "Player 281"}],
            "halftime_scores": [[0, 0], [1, 0]], "seeds": [1234, 5678],
            "match_count": 1,
        })

    def test_get_reload_navigation_and_duplicate_submission_do_not_play_again(self):
        server, thread, base = self.serve()
        initial = self.session.view()
        with patch("goal2.web.server.to_savestate", return_value=b"adapted"), \
             patch("goal2.web.server.Savestate", return_value=object()), \
             patch("goal2.web.server.run_full_match") as runner:
            try:
                # Session reads and ordinary navigation-shaped GETs have no play effect.
                self.assertEqual(self.http(base + "/api/session")[0], 200)
                self.assertEqual(self.http(base + "/")[0], 200)
                self.assertEqual(self.http(base + "/api/countries")[0], 200)
                self.assertEqual(self.session.state.match_count, 0)
                self.assertEqual(runner.call_count, 0)

                def retain(_template, candidate, *, retain_state):
                    candidate.match_count += 1
                    candidate.last_match = {
                        "teams": (7, 1), "score": (0, 0), "goals": [],
                        "halves": ({"score": (0, 0)}, {"score": (0, 0)}),
                        "seed_DS7B62": 3, "seed_DS8336": 4,
                    }
                    return {"score": (0, 0), "managed_side": 0}

                runner.side_effect = retain
                status, completed = self.http(base + "/api/play", {"play_token": initial["play_token"]}, "POST")
                self.assertEqual(status, 200)
                self.assertEqual(completed["match_count"], 1)
                status, duplicate = self.http(base + "/api/play", {"play_token": initial["play_token"]}, "POST")
                self.assertEqual(status, 409)
                self.assertIn("already used", duplicate["error"])
                self.assertEqual(self.session.state.match_count, 1)
                self.assertEqual(runner.call_count, 1)
                # A reload exposes the retained result and a fresh explicit action token.
                reloaded = self.http(base + "/api/session")[1]
                self.assertEqual(reloaded["last_match"]["match_count"], 1)
                self.assertNotEqual(reloaded["play_token"], initial["play_token"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_simulation_failure_discards_candidate_and_keeps_session_usable(self):
        before = copy.deepcopy(self.session.state)
        token = self.session.view()["play_token"]

        def fail(_template, candidate, *, retain_state):
            candidate.players[280] = b"changed"
            candidate.rng_seed_7b62 = 999
            candidate.match_count += 1
            raise RuntimeError("synthetic engine refusal")

        with patch("goal2.web.server.to_savestate", return_value=b"adapted"), \
             patch("goal2.web.server.Savestate", return_value=object()), \
             patch("goal2.web.server.run_full_match", side_effect=fail):
            server, thread, base = self.serve()
            try:
                status, payload = self.http(base + "/api/play", {"play_token": token}, "POST")
                self.assertEqual(status, 500)
                self.assertIn("synthetic engine refusal", payload["error"])
                self.assertEqual(self.session.state, before)
                self.assertNotEqual(payload["play_token"], token)
                current = self.http(base + "/api/session")[1]
                self.assertEqual(current["match_count"], 0)
                self.assertEqual(current["country"]["id"], 7)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_cached_e010_two_match_adapter_inputs_match_direct_runner(self):
        fixture = Path(__file__).resolve().parents[2] / ".cache" / "e010-r0001-halftime.sav"
        if not fixture.is_file():
            self.skipTest("cached E010-r0001 savestate unavailable")
        original = fixture.read_bytes()
        self.assertTrue(hashlib.sha256(original).hexdigest().startswith("e1dee7e2f5ad443e"))
        state = from_savestate(original)
        goaldat = type("GoalDatStub", (), {
            "country_names": ["" if i == 0 else f"Country {i}" for i in range(129)],
            "player_names": ["" if i == 0 else f"Player {i}" for i in range(3061)],
            "player_initials": ["" for _ in range(3061)],
        })()
        session = WebSession(state, goaldat, Savestate(original), original)
        direct = copy.deepcopy(state)
        for _ in range(2):
            direct_template = Savestate(to_savestate(direct, original=original))
            direct_result = run_full_match(direct_template, direct, retain_state=True)
            direct.last_match["managed_side"] = direct_result["managed_side"]
            direct.last_match["match_count"] = direct.match_count
            web_result = session.play({"play_token": session.view()["play_token"]})
            self.assertEqual(session.state.players, direct.players)
            self.assertEqual((session.state.rng_seed_7b62, session.state.rng_seed_8336),
                             (direct.rng_seed_7b62, direct.rng_seed_8336))
            self.assertEqual(session.state.match_count, direct.match_count)
            self.assertEqual(session.state.last_match, direct.last_match)
            self.assertEqual(web_result["last_match"]["seeds"], [
                direct.last_match["seed_DS7B62"], direct.last_match["seed_DS8336"]])
        self.assertEqual(session.state.match_count, 2)


if __name__ == "__main__":
    unittest.main()
