"""[designed: T35] Country API behavior over synthetic runtime records."""
from __future__ import annotations

import contextlib
import io
import json
import threading
import unittest
from http.server import HTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from goal2.data.goaldat import GoalDat
from goal2.web import server


def make_session() -> server.WebSession:
    names = [""] + [f"Nation {n:03}" for n in range(1, 129)]
    player_names = [""] + [f"Player {n:04}" for n in range(1, 2561)]
    player_initials = [""] + [f"P" for _ in range(1, 2561)]
    countries = [bytes(0xBF)]
    for country in range(1, 129):
        first = (country - 1) * 20 + 1
        countries.append(b"".join(n.to_bytes(2, "little") for n in range(first, first + 20)) + bytes(0xBF - 40))
    players = [bytes(20)]
    for number in range(1, 2561):
        record = bytearray(20)
        record[4] = number % 256
        record[7] = number % 14
        record[12] = number % 31 + 1  # [designed: T43] Distinct confidence fixture.
        record[14] = number % 26
        players.append(bytes(record))
    state = SimpleNamespace(
        players=players, countries=countries, managed_country=1,
        managed_squad=list(range(1, 21)), starting_eleven=list(range(1, 12)),
        captain=11, country_tactics=37,
    )
    data = GoalDat(country_names=names, player_names=player_names, player_initials=player_initials)
    return server.WebSession(state, data, object())


class WebCountryTests(unittest.TestCase):
    def test_tactics_labels_match_confirmed_f010_elements_and_rebuild_choices(self):
        labels = {row["element"]: (row["clear"], row["set"], row["evidence"])
                  for row in make_session().view()["tactics_options"]}
        self.assertEqual(labels[6], ("sag back to box", "stand ground", "confirmed"))
        self.assertEqual(labels[7], ("play safe", "offside trap", "confirmed"))
        self.assertEqual(labels[1], ("stay back", "push forward", "confirmed"))
        self.assertEqual(labels[5][2], "designed")
        self.assertEqual(labels[8][2], "designed")

    def test_countries_lists_all_128_real_names_and_current_id(self):
        session = make_session()
        result = session.countries_view()
        self.assertEqual(len(result["countries"]), 128)
        self.assertEqual(result["countries"][0], {"id": 1, "name": "Nation 001"})
        self.assertEqual(result["countries"][-1], {"id": 128, "name": "Nation 128"})
        self.assertEqual(result["selected"], 1)

    def test_every_country_can_be_selected_from_its_runtime_record(self):
        session = make_session()
        for country in range(1, 129):
            with self.subTest(country=country):
                result = session.select_country(country)
                self.assertEqual(result["country"]["id"], country)
                self.assertEqual(len(result["players"]), 20)

    def test_switching_uses_runtime_player_ids_and_exact_record_fields(self):
        session = make_session()
        with patch.object(server, "resolve_full_matchup", return_value=((56, 7), 0, 7)) as resolver:
            result = session.select_country(56)
        resolver.assert_called_once_with(session.template, session.state)
        self.assertEqual(result["country"], {"id": 56, "name": "Nation 056"})
        self.assertEqual(session.state.managed_squad, list(range(1101, 1121)))
        self.assertEqual([p["id"] for p in result["players"]], list(range(1101, 1121)))
        player = result["players"][0]
        self.assertEqual(player, {"id": 1101, "name": "Player 1101", "initials": "P", "number": 1,
                                 "ability": 1101 % 256, "position": 1101 % 14,
                                 "energy": 1101 % 26, "confidence": 17})
        self.assertEqual(result["matchup"]["opponent"], {"id": 7, "name": "Nation 007"})

    def test_same_country_preserves_choices_and_valid_captain(self):
        session = make_session()
        session.state.starting_eleven = list(range(2, 13))
        session.state.captain = 8
        session.state.country_tactics = 219
        result = session.select_country(1)
        self.assertEqual(result["starting_eleven"], list(range(2, 13)))
        self.assertEqual(result["captain"], 8)
        self.assertEqual(result["tactics"], 219)

    def test_ineligible_legacy_captain_is_not_exposed(self):
        session = make_session()
        session.state.captain = 99
        result = session.view()
        self.assertEqual(result["captain"], 0)
        self.assertEqual(result["starting_eleven"], list(range(1, 12)))

    def test_country_change_resets_country_specific_choices(self):
        session = make_session()
        result = session.select_country(2)
        self.assertEqual(result["starting_eleven"], list(range(21, 32)))
        self.assertEqual(result["captain"], 0)
        self.assertEqual(result["tactics"], 0)

    def test_country_change_uses_the_new_country_tactics_byte(self):
        session = make_session()
        record = bytearray(session.state.countries[2])
        record[0x2D] = 91
        session.state.countries[2] = bytes(record)
        session.state.country_tactics = 219
        result = session.select_country(2)
        self.assertEqual(result["tactics"], 91)

    def test_invalid_candidate_player_data_is_atomic(self):
        session = make_session()
        session.state.players[21] = b"short"
        before = (session.state.managed_country, list(session.state.managed_squad),
                  list(session.state.starting_eleven), session.state.captain, session.state.country_tactics)
        with self.assertRaisesRegex(ValueError, "record is too short"):
            session.select_country(2)
        after = (session.state.managed_country, list(session.state.managed_squad),
                 list(session.state.starting_eleven), session.state.captain, session.state.country_tactics)
        self.assertEqual(after, before)

    def test_invalid_country_or_runtime_record_does_not_partially_mutate(self):
        session = make_session()
        before = (session.state.managed_country, list(session.state.managed_squad),
                  list(session.state.starting_eleven), session.state.captain, session.state.country_tactics)
        for invalid in (0, 129, True, "2", 2.0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                session.select_country(invalid)
        session.state.countries[2] = bytes(0xBF)
        with self.assertRaises(ValueError):
            session.select_country(2)
        after = (session.state.managed_country, list(session.state.managed_squad),
                 list(session.state.starting_eleven), session.state.captain, session.state.country_tactics)
        self.assertEqual(after, before)

    def test_unsupported_template_is_reported_without_fake_opponent(self):
        session = make_session()
        with patch.object(server, "resolve_full_matchup", side_effect=ValueError("extra time template")):
            result = session.view()
        self.assertFalse(result["matchup"]["available"])
        self.assertIsNone(result["matchup"]["opponent"])
        self.assertIn("extra time template", result["matchup"]["message"])

    def test_startup_missing_input_is_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "savestate"):
            server.WebSession.load(__import__("pathlib").Path("missing.sav"),
                                   __import__("pathlib").Path("missing.dat"))

    def test_http_json_country_update_and_static_allowlist(self):
        session = make_session()
        handler = type("TestHandler", (server.Handler,), {"session": session})
        httpd = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            with urlopen(base + "/api/countries") as response:
                countries = json.load(response)
                self.assertEqual(len(countries["countries"]), 128)
            with patch.object(server, "resolve_full_matchup", return_value=((1, 2), 0, 2)):
                with urlopen(base + "/api/session") as response:
                    current = json.load(response)
                    self.assertEqual(current["country"]["id"], 1)
                    self.assertEqual(current["matchup"]["opponent"]["id"], 2)
            request = Request(base + "/api/country", data=b'{"country":2}',
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request) as response:
                selected = json.load(response)
                self.assertEqual(selected["country"]["id"], 2)
            with urlopen(base + "/") as response:
                homepage = response.read()
                self.assertIn(b"Draft choices", homepage)
                self.assertIn("Elements 1–4, 6 and 7 use labels confirmed by F010".encode(), homepage)
                self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")
            for path, media_type in (("/app.mjs", "text/javascript; charset=utf-8"),
                                     ("/styles.css", "text/css; charset=utf-8")):
                with urlopen(base + path) as response:
                    self.assertEqual(response.headers["Content-Type"], media_type)
                    self.assertGreater(len(response.read()), 0)
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/../../pyproject.toml")
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
            request = Request(base + "/api/country", data=b'{"country":129}',
                              headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
            self.assertEqual(session.state.managed_country, 2)
        finally:
            httpd.shutdown()
            thread.join()
            httpd.server_close()

    def test_cli_load_failure_exits_cleanly_without_server(self):
        stderr = io.StringIO()
        with patch.object(server.WebSession, "load", side_effect=ValueError("invalid GOAL.DAT")), \
                contextlib.redirect_stderr(stderr):
            code = server.main(["state.sav", "GOAL.DAT", "--port", "8001"])
        self.assertEqual(code, 2)
        self.assertIn("error: invalid GOAL.DAT", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
