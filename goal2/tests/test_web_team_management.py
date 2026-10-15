"""[designed: T36] Atomic browser confirmation for Python-owned team choices."""
from __future__ import annotations

import unittest
import json
from http.server import HTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from goal2.game.state import GameState
from goal2.web.server import Handler, WebSession


def make_session() -> WebSession:
    squad = list(range(280, 300))  # Includes full player IDs above 255.
    players = [bytes(0x14) for _ in range(3061)]
    state = GameState(
        players=players,
        countries=[bytes(0xBF) for _ in range(129)],
        managed_country=7,
        managed_squad=squad,
        rng_seed_7b62=1,
        rng_seed_8336=2,
        match_state={},
        vga=b"",
        mem=b"",
        starting_eleven=squad[:11],
        captain=squad[2],
        country_tactics=0x08,
    )
    goaldat = type("GoalDatStub", (), {
        "country_names": ["" if i == 0 else f"Country {i}" for i in range(129)],
        "player_names": ["" if i == 0 else f"Player {i}" for i in range(3061)],
        "player_initials": ["" for _ in range(3061)],
    })()
    session = WebSession(state, goaldat, object())
    return session


class TeamManagementTests(unittest.TestCase):
    def setUp(self):
        self.session = make_session()
        self.initial = {
            "starting_eleven": list(self.session.state.starting_eleven),
            "captain": self.session.state.captain,
            "tactics": self.session.state.country_tactics,
        }
        self.resolver = patch("goal2.web.server.resolve_full_matchup", return_value=((7, 1), 0, 1))
        self.resolver.start()

    def tearDown(self):
        self.resolver.stop()
        # Keep this synthetic test's fixture values isolated even if an
        # assertion interrupts a case.
        self.session.state.starting_eleven = list(self.initial["starting_eleven"])
        self.session.state.captain = self.initial["captain"]
        self.session.state.country_tactics = self.initial["tactics"]

    def payload(self, **changes):
        data = {
            "country": 7,
            "starting_eleven": list(range(281, 292)),
            "captain": 290,
            "tactics": 0xA5,
        }
        data.update(changes)
        return data

    def snapshot(self):
        return (list(self.session.state.starting_eleven), self.session.state.captain,
                self.session.state.country_tactics)

    def test_confirms_non_default_choices_and_preview(self):
        result = self.session.confirm_management(self.payload())
        self.assertEqual(self.session.state.starting_eleven, list(range(281, 292)))
        self.assertEqual(self.session.state.captain, 290)
        self.assertGreater(self.session.state.captain, 255)
        self.assertEqual(self.session.state.country_tactics, 0xA5)
        self.assertEqual(result["confirmed"], {
            "starting_eleven": list(range(281, 292)), "captain": 290, "tactics": 0xA5,
        })
        self.assertEqual(result["matchup"]["opponent"], {"id": 1, "name": "Country 1"})

    def test_accepts_every_eight_bit_tactics_value(self):
        try:
            for tactics in range(256):
                with self.subTest(tactics=tactics):
                    self.session.confirm_management(self.payload(tactics=tactics))
                    self.assertEqual(self.session.state.country_tactics, tactics)
        finally:
            self.session.state.starting_eleven = list(self.initial["starting_eleven"])
            self.session.state.captain = self.initial["captain"]
            self.session.state.country_tactics = self.initial["tactics"]

    def test_invalid_drafts_are_rejected_atomically(self):
        valid = self.payload()
        invalid = [
            ("count", {"starting_eleven": valid["starting_eleven"][:10]}),
            ("count_type", {"starting_eleven": "eleven"}),
            ("duplicate", {"starting_eleven": [281] * 11, "captain": 281}),
            ("foreign", {"starting_eleven": [*range(281, 291), 999]}),
            ("player_string", {"starting_eleven": [*range(281, 291), "291"]}),
            ("player_float", {"starting_eleven": [*range(281, 291), 291.0]}),
            ("player_bool", {"starting_eleven": [*range(281, 291), True]}),
            ("captain", {"captain": 280}),
            ("captain_bool", {"captain": True}),
            ("captain_string", {"captain": "290"}),
            ("captain_float", {"captain": 290.0}),
            ("tactics_low", {"tactics": -1}),
            ("tactics_high", {"tactics": 256}),
            ("tactics_bool", {"tactics": True}),
            ("tactics_string", {"tactics": "165"}),
            ("tactics_float", {"tactics": 165.0}),
            ("tactics_list", {"tactics": [1, 0, 1]}),
            ("stale_country", {"country": 6}),
        ]
        try:
            for name, changes in invalid:
                with self.subTest(name=name):
                    before = self.snapshot()
                    with self.assertRaises(ValueError):
                        self.session.confirm_management(self.payload(**changes))
                    self.assertEqual(self.snapshot(), before)
        finally:
            self.session.state.starting_eleven = list(self.initial["starting_eleven"])
            self.session.state.captain = self.initial["captain"]
            self.session.state.country_tactics = self.initial["tactics"]

    def test_response_failure_does_not_partially_confirm(self):
        before = self.snapshot()
        with patch.object(self.session, "_view_for", side_effect=ValueError("preview failed")):
            with self.assertRaisesRegex(ValueError, "preview failed"):
                self.session.confirm_management(self.payload())
        self.assertEqual(self.snapshot(), before)

    def test_http_management_confirmation_and_reload_readback(self):
        handler = type("TestHandler", (Handler,), {"session": self.session})
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        before = self.snapshot()
        try:
            # Reading the session, as the browser does when restoring a
            # canceled draft, leaves the confirmed choices untouched.
            with urlopen(base + "/api/session") as response:
                initial_view = json.load(response)
            self.assertEqual(initial_view["confirmed"], {
                "starting_eleven": before[0], "captain": before[1], "tactics": before[2],
            })
            self.assertEqual(self.snapshot(), before)

            def post(payload):
                request = Request(base + "/api/management", data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urlopen(request) as response:
                        return response.status, json.load(response)
                except HTTPError as error:
                    try:
                        return error.code, json.load(error)
                    finally:
                        error.close()

            status, confirmed = post(self.payload())
            self.assertEqual(status, 200)
            self.assertEqual(confirmed["confirmed"]["captain"], 290)
            with urlopen(base + "/api/session") as response:
                self.assertEqual(json.load(response)["confirmed"], confirmed["confirmed"])
            invalid = self.payload(tactics=256)
            status, _ = post(invalid)
            self.assertEqual(status, 400)
            with urlopen(base + "/api/session") as response:
                self.assertEqual(json.load(response)["confirmed"], confirmed["confirmed"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            self.session.state.starting_eleven = list(self.initial["starting_eleven"])
            self.session.state.captain = self.initial["captain"]
            self.session.state.country_tactics = self.initial["tactics"]


if __name__ == "__main__":
    unittest.main()
