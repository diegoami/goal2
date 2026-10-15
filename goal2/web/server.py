"""[designed: T35] A single-session, standard-library HTTP view of goal2 state.

Country names and player fields come from the confirmed GOAL.DAT and runtime
records (F002, F007, F008); country roster IDs come from the runtime country
record, never the GOAL.DAT squad-position pattern.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from goal2.data.goaldat import GoalDat, load as load_goaldat
from goal2.engine.savestate import Savestate
from goal2.game.quick_match import resolve_full_matchup
from goal2.game.state import GameState, from_savestate


STATIC_FILES = frozenset({"/", "/index.html", "/app.mjs", "/styles.css"})
MAX_BODY = 4096


class WebSession:
    """[designed: T35] Keep one loaded session in memory for this process."""

    def __init__(self, state: GameState, goaldat: GoalDat, template: Savestate):
        self.state = state
        self.goaldat = goaldat
        self.template = template

    @classmethod
    def load(cls, savestate_path: Path, goaldat_path: Path) -> "WebSession":
        """[designed: T35] Read and validate each local input once at startup."""
        try:
            savestate_bytes = savestate_path.read_bytes()
        except OSError as exc:
            raise ValueError(f"savestate: {exc}") from exc
        try:
            state = from_savestate(savestate_bytes)
            template = Savestate(savestate_bytes)
        except Exception as exc:
            raise ValueError(f"invalid savestate {savestate_path}: {exc}") from exc
        try:
            goaldat_bytes = goaldat_path.read_bytes()
            goaldat = load_goaldat(goaldat_bytes)
        except (OSError, ValueError) as exc:
            raise ValueError(f"GOAL.DAT: {exc}") from exc
        if not 1 <= state.managed_country <= 128:
            raise ValueError("savestate managed country must be 1..128")
        return cls(state, goaldat, template)

    def countries_view(self) -> dict[str, Any]:
        return {
            "countries": [
                {"id": country, "name": self.goaldat.country_names[country]}
                for country in range(1, 129)
            ],
            "selected": self.state.managed_country,
        }

    def view(self) -> dict[str, Any]:
        return self._view_for(self.state, list(self.state.managed_squad))

    def _view_for(self, state: GameState, squad: list[int]) -> dict[str, Any]:
        country = state.managed_country
        if not 1 <= country <= 128 or country >= len(self.goaldat.country_names):
            raise ValueError(f"country {country} has no GOAL.DAT name")
        players = []
        for player_id in squad:
            if not 1 <= player_id < len(self.state.players):
                raise ValueError(f"country {country} contains invalid player ID {player_id}")
            record = self.state.players[player_id]
            if len(record) < 0x0F:
                raise ValueError(f"player {player_id} record is too short")
            if player_id >= len(self.goaldat.player_names):
                raise ValueError(f"player {player_id} has no GOAL.DAT name")
            players.append({
                "id": player_id,
                "name": self.goaldat.player_names[player_id],
                "initials": (self.goaldat.player_initials[player_id]
                             if player_id < len(self.goaldat.player_initials) else ""),
                "number": len(players) + 1,
                "ability": record[0x04],
                "position": record[0x07],
                "energy": record[0x0E],
            })
        try:
            teams, managed_side, opponent = resolve_full_matchup(self.template, state)
            matchup = {
                "available": True,
                "teams": list(teams),
                "managed_side": managed_side,
                "opponent": {"id": opponent, "name": self.goaldat.country_names[opponent]},
                "message": None,
            }
        except Exception as exc:
            matchup = {
                "available": False,
                "teams": None,
                "managed_side": None,
                "opponent": None,
                "message": f"Matchup unavailable: {exc}",
            }
        starting_eleven = list(state.starting_eleven)
        if (len(starting_eleven) != 11 or len(set(starting_eleven)) != 11
                or not set(starting_eleven).issubset(squad)):
            starting_eleven = squad[:11]
        captain = state.captain if state.captain in starting_eleven else 0
        return {
            "country": {"id": country, "name": self.goaldat.country_names[country]},
            "countries": self.countries_view()["countries"],
            "players": players,
            "starting_eleven": starting_eleven,
            # [derived: F007, T35] A legacy byte may name a player outside the
            # displayed eleven; only expose captain choices that are eligible.
            "captain": captain,
            "tactics": state.country_tactics,
            "matchup": matchup,
        }

    def select_country(self, raw_country: Any) -> dict[str, Any]:
        """[designed: T35] Validate a complete candidate before changing state."""
        if isinstance(raw_country, bool) or not isinstance(raw_country, int) or not 1 <= raw_country <= 128:
            raise ValueError("country must be an integer from 1 to 128")
        candidate = self.state.countries[raw_country]
        if raw_country >= len(self.goaldat.country_names):
            raise ValueError(f"country {raw_country} has no GOAL.DAT name")
        if len(candidate) < 0x2E:
            raise ValueError(f"country {raw_country} runtime record is shorter than 0x2E bytes")
        squad = [int.from_bytes(candidate[offset:offset + 2], "little") for offset in range(0, 40, 2)]
        if any(not 1 <= player_id < len(self.state.players) for player_id in squad):
            raise ValueError(f"country {raw_country} runtime record contains an invalid player ID")
        if len(set(squad)) != 20:
            raise ValueError(f"country {raw_country} runtime record contains duplicate player IDs")
        if raw_country != self.state.managed_country:
            candidate_state = copy.copy(self.state)
            candidate_state.managed_country = raw_country
            candidate_state.managed_squad = squad
            candidate_state.starting_eleven = squad[:11]
            candidate_state.captain = 0
            # [confirmed: F010] Keep this country's stored tactics byte; old
            # country tactics are not carried over during a country change.
            candidate_state.country_tactics = candidate[0x2D]
            result = self._view_for(candidate_state, squad)
            self.state.managed_country = candidate_state.managed_country
            self.state.managed_squad = candidate_state.managed_squad
            self.state.starting_eleven = candidate_state.starting_eleven
            self.state.captain = candidate_state.captain
            self.state.country_tactics = candidate_state.country_tactics
            return result
        return self.view()


class Handler(BaseHTTPRequestHandler):
    """[designed: T35] Serve an explicit static allowlist and JSON endpoints."""

    server_version = "goal2-web/1"
    session: WebSession

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path in ("/api/countries", "/api/session"):
            try:
                data = self.session.countries_view() if path.endswith("countries") else self.session.view()
                self._json(200, data)
            except (ValueError, IndexError) as exc:
                self._json(500, {"error": str(exc)})
            return
        if path not in STATIC_FILES:
            self._json(404, {"error": "not found"})
            return
        name = "/index.html" if path == "/" else path
        try:
            content = (Path(__file__).parent / "static" / name.lstrip("/")).read_bytes()
        except OSError:
            self._json(500, {"error": "static asset unavailable"})
            return
        content_type = "text/html; charset=utf-8" if name.endswith(".html") else (
            "text/javascript; charset=utf-8" if name.endswith(".mjs") else "text/css; charset=utf-8"
        )
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/country":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= length <= MAX_BODY:
                raise ValueError("request body is too large or missing")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {"country"}:
                raise ValueError("request must contain only a country field")
            result = self.session.select_country(body["country"])
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        except (IndexError, TypeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, result)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        print(f"goal2.web: {format % args}", file=sys.stderr)


def serve(session: WebSession, host: str = "127.0.0.1", port: int = 8000) -> None:
    """[designed: T35] Bind one local HTTP server and serve this session."""
    handler = type("SessionHandler", (Handler,), {"session": session})
    server = HTTPServer((host, port), handler)
    print(f"goal2 web view: http://{host}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m goal2.web", description="Serve a local browser view of a savestate.")
    parser.add_argument("savestate", type=Path)
    parser.add_argument("goaldat", type=Path)
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000; 0 chooses an available port)")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be from 0 to 65535")
    try:
        session = WebSession.load(args.savestate, args.goaldat)
        serve(session, args.host, args.port)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    return 0
