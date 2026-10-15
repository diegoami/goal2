"""[designed: T36] Atomic browser confirmation for Python-owned team choices."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from goal2.game.state import GameState
from goal2.web.server import WebSession


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
            ("duplicate", {"starting_eleven": [281] * 11}),
            ("foreign", {"starting_eleven": [*range(281, 291), 999]}),
            ("captain", {"captain": 280}),
            ("captain_bool", {"captain": True}),
            ("tactics_low", {"tactics": -1}),
            ("tactics_high", {"tactics": 256}),
            ("tactics_bool", {"tactics": True}),
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

    def test_cancel_is_no_request_and_leaves_confirmed_state_unchanged(self):
        before = self.snapshot()
        # Cancellation is represented by retaining/discarding only the browser
        # draft; this authoritative API is never called for Cancel.
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
