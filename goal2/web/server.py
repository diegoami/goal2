"""[designed: T35] A single-session, standard-library HTTP view of goal2 state.

Country names and player fields come from the confirmed GOAL.DAT and runtime
records (F002, F007, F008); country roster IDs come from the runtime country
record, never the GOAL.DAT squad-position pattern.
"""
from __future__ import annotations

import argparse
import copy
import json
import secrets
import sys
from threading import Lock
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from goal2.data.goaldat import GoalDat, load as load_goaldat
from goal2.engine.savestate import Savestate
from goal2.game.campaign_confidence import team_morale
from goal2.game import eligibility
from goal2.game.quick_match import resolve_full_matchup
from goal2.game.quick_match import run_full_match
from goal2.game.session_save import SessionSaveError, load as load_session_save, save as save_session_save
from goal2.game.campaign_schedule import start_opening_campaign
from goal2.game.state import GameState, from_savestate, to_savestate


STATIC_FILES = frozenset({"/", "/index.html", "/app.mjs", "/styles.css"})
MAX_BODY = 4096


class StalePlaySubmission(Exception):
    """The browser supplied a token that has already been consumed."""

# [confirmed: F010] Labels for tactics elements 1–4. [designed: F010] The
# labels for elements 5–8 are not read from the original screen; these retain
# the rebuild's existing terminal wording.
TACTICS = (
    {"element": 5, "clear": "half pitch", "set": "full pitch", "evidence": "designed"},
    {"element": 6, "clear": "short kicks", "set": "long kicks", "evidence": "designed"},
    {"element": 7, "clear": "stay back", "set": "push forward", "evidence": "designed"},
    {"element": 1, "clear": "stay back", "set": "push forward", "evidence": "confirmed"},
    {"element": 2, "clear": "keep ball", "set": "quick pass", "evidence": "confirmed"},
    {"element": 3, "clear": "short passes", "set": "long passes", "evidence": "confirmed"},
    {"element": 4, "clear": "avoid injury", "set": "go in hard", "evidence": "confirmed"},
    {"element": 8, "clear": "zone", "set": "man to man", "evidence": "designed"},
)


class WebSession:
    """[designed: T35] Keep one loaded session in memory for this process."""

    def __init__(self, state: GameState, goaldat: GoalDat, template: Savestate,
                 template_bytes: bytes | None = None, save_path: Path | None = None):
        self.state = state
        self.goaldat = goaldat
        self.template = template
        self.template_bytes = template_bytes
        self.save_path = save_path
        self._play_lock = Lock()
        self._play_token = secrets.token_urlsafe(24)

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
        return cls(state, goaldat, template, savestate_bytes)

    @classmethod
    def resume(cls, save_path: Path, goaldat_path: Path) -> "WebSession":
        """[designed: T38] Rebuild a session from its versioned save and GOAL.DAT."""
        try:
            state, template_bytes = load_session_save(save_path)
            from_savestate(template_bytes)
            template = Savestate(template_bytes)
            # Check that this candidate can produce the next engine input before
            # publishing it as the active browser session.
            continuation = to_savestate(state, original=template_bytes)
            from_savestate(continuation)
            Savestate(continuation)
            goaldat = load_goaldat(goaldat_path.read_bytes())
            if not 1 <= state.managed_country <= 128:
                raise ValueError("managed country must be 1..128")
            session = cls(state, goaldat, template, template_bytes, save_path)
            session._session_view(state, list(state.managed_squad))
            return session
        except (OSError, SessionSaveError, ValueError, TypeError, IndexError, KeyError) as exc:
            raise ValueError(f"cannot resume session: {exc}") from exc

    def save_to_configured_path(self) -> None:
        """[designed: T38] Atomically save the complete live session."""
        if self.save_path is None or self.template_bytes is None:
            raise ValueError("session save location is not configured")
        with self._play_lock:
            save_session_save(self.save_path, self.state, self.template_bytes)

    def load_from_configured_path(self) -> dict[str, Any]:
        """[designed: T38] Validate a save and continuation before replacing state."""
        if self.save_path is None:
            raise ValueError("session save location is not configured")
        with self._play_lock:
            try:
                candidate, template_bytes = load_session_save(self.save_path)
            except SessionSaveError as exc:
                if str(exc).startswith("cannot read session save:"):
                    raise SessionSaveError("cannot read configured session save") from exc
                raise
            from_savestate(template_bytes)
            template = Savestate(template_bytes)
            continuation = to_savestate(candidate, original=template_bytes)
            from_savestate(continuation)
            Savestate(continuation)
            old_template = self.template
            self.template = template
            try:
                # Validate matchup, retained result and the complete dashboard
                # while the candidate template is active, before publication.
                self._view_for(candidate, list(candidate.managed_squad))
                self._named_match(candidate.last_match, candidate)
                response = self._session_view(candidate, list(candidate.managed_squad))
            finally:
                self.template = old_template
            self.state = candidate
            self.template = template
            self.template_bytes = template_bytes
            self._play_token = secrets.token_urlsafe(24)
            response["play_token"] = self._play_token
            response["match_count"] = getattr(candidate, "match_count", 0)
            return response

    def new_campaign(self, raw: Any) -> dict[str, Any]:
        """[designed: T41] Publish a fresh scheduled campaign only after validation."""
        if not isinstance(raw, dict) or set(raw) != {"country", "start_year", "seed_7b62", "seed_8336"}:
            raise ValueError("new campaign requires country, start_year, seed_7b62 and seed_8336")
        if self.template_bytes is None:
            raise ValueError("original template bytes are required to create a campaign")
        with self._play_lock:
            candidate, _ = start_opening_campaign(
                self.goaldat, self.template_bytes, managed_country=raw["country"],
                start_year=raw["start_year"], seed_7b62=raw["seed_7b62"], seed_8336=raw["seed_8336"],
            )
            response = self._session_view(candidate, list(candidate.managed_squad))
            self.state = candidate
            self._play_token = secrets.token_urlsafe(24)
            response["play_token"] = self._play_token
            return response

    def _campaign_view(self, state: GameState) -> dict[str, Any] | None:
        """[designed: T41] Display source identities, pending boundary and score history."""
        campaign = getattr(state, "campaign", None)
        if campaign is None:
            return None
        fixture = campaign.next_fixture
        def named(country):
            return {"id": country, "name": self.goaldat.country_names[country]}
        return {
            "start_year": campaign.start_year, "cycle": campaign.cycle,
            "year": campaign.year, "stage": campaign.stage,
            "next_fixture": ({"fixture_id": fixture.fixture_id, "kind": fixture.kind,
                              "stage": fixture.stage, "teams": [named(fixture.side_a), named(fixture.side_b)]}
                             if fixture else None),
            "history": [{"fixture_id": row["fixture_id"], "teams": [named(t) for t in row["teams"]],
                         "score": list(row["score"])} for row in campaign.results],
        }

    def countries_view(self) -> dict[str, Any]:
        return {
            "countries": [
                {"id": country, "name": self.goaldat.country_names[country]}
                for country in range(1, 129)
            ],
            "selected": self.state.managed_country,
        }

    def view(self) -> dict[str, Any]:
        return self._session_view(self.state, list(self.state.managed_squad))

    def _session_view(self, state: GameState, squad: list[int]) -> dict[str, Any]:
        view = self._view_for(state, squad)
        view["play_token"] = self._play_token
        view["match_count"] = getattr(state, "match_count", 0)
        view["campaign"] = self._campaign_view(state)
        view["last_match"] = self._named_match(getattr(state, "last_match", None), state)
        return view

    def _named_match(self, match: dict[str, Any] | None,
                     state: GameState | None = None) -> dict[str, Any] | None:
        if match is None:
            return None
        if not isinstance(match, dict):
            raise ValueError("saved last match must be an object")
        state = state or self.state
        required = {"teams", "score", "goals", "halves", "seed_DS7B62", "seed_DS8336"}
        optional = {"managed_side", "match_count", "draws"}
        if not required.issubset(match) or set(match) - required - optional:
            raise ValueError("saved last match has missing or unknown fields")
        teams = match["teams"]
        if (not isinstance(teams, (list, tuple)) or len(teams) != 2
                or any(isinstance(team, bool) or not isinstance(team, int) or not 1 <= team <= 128
                       for team in teams) or teams[0] == teams[1]):
            raise ValueError("saved last match teams are invalid")
        score = match["score"]
        if (not isinstance(score, (list, tuple)) or len(score) != 2
                or any(isinstance(goals, bool) or not isinstance(goals, int) or goals < 0
                       for goals in score)):
            raise ValueError("saved last match score is invalid")
        goals = match["goals"]
        if not isinstance(goals, list):
            raise ValueError("saved last match goals are invalid")
        for goal in goals:
            required_goal_fields = {"team", "minute", "player"}
            optional_goal_fields = {"squad_slot", "stored_byte"}
            if (not isinstance(goal, dict) or not required_goal_fields.issubset(goal)
                    or set(goal) - required_goal_fields - optional_goal_fields):
                raise ValueError("saved last match goal is invalid")
            if (isinstance(goal["team"], bool) or not isinstance(goal["team"], int)
                    or goal["team"] not in (0, 1)
                    or isinstance(goal["minute"], bool) or not isinstance(goal["minute"], int)
                    or goal["minute"] < 0
                    or isinstance(goal["player"], bool) or not isinstance(goal["player"], int)
                    or not 1 <= goal["player"] < len(state.players)):
                raise ValueError("saved last match goal fields are invalid")
            if "squad_slot" in goal and (isinstance(goal["squad_slot"], bool)
                    or not isinstance(goal["squad_slot"], int) or not 1 <= goal["squad_slot"] <= 20):
                raise ValueError("saved last match goal squad slot is invalid")
            if "stored_byte" in goal and (isinstance(goal["stored_byte"], bool)
                    or not isinstance(goal["stored_byte"], int) or not 0 <= goal["stored_byte"] <= 255):
                raise ValueError("saved last match goal stored byte is invalid")
        halves = match["halves"]
        if not isinstance(halves, (list, tuple)) or len(halves) != 2:
            raise ValueError("saved last match halves are invalid")
        halftime_scores = []
        for half in halves:
            if not isinstance(half, dict) or "score" not in half:
                raise ValueError("saved last match half is invalid")
            half_score = half["score"]
            if (not isinstance(half_score, (list, tuple)) or len(half_score) != 2
                    or any(isinstance(value, bool) or not isinstance(value, int) or value < 0
                           for value in half_score)):
                raise ValueError("saved last match half score is invalid")
            halftime_scores.append(list(half_score))
        seeds = (match["seed_DS7B62"], match["seed_DS8336"])
        if any(isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 65535
               for seed in seeds):
            raise ValueError("saved last match seeds are invalid")
        managed_side = match.get("managed_side")
        if managed_side is None:
            if state.managed_country not in teams:
                raise ValueError("saved last match does not identify the managed country")
            managed_side = teams.index(state.managed_country)
        if (isinstance(managed_side, bool) or not isinstance(managed_side, int)
                or managed_side not in (0, 1)):
            raise ValueError("saved last match managed side is invalid")
        match_count = match.get("match_count", getattr(state, "match_count", 0))
        if isinstance(match_count, bool) or not isinstance(match_count, int) or match_count < 1:
            raise ValueError("saved last match count is invalid")
        named_teams = [
            {"id": team, "name": self.goaldat.country_names[team]}
            for team in teams
        ]
        named_goals = []
        for goal in goals:
            team = teams[goal["team"]]
            player = goal["player"]
            named_goals.append({
                "team": team,
                "team_name": self.goaldat.country_names[team],
                "minute": goal["minute"],
                "player": player,
                "player_name": self.goaldat.player_names[player],
            })
        return {
            "teams": named_teams,
            "managed_side": managed_side,
            "score": list(score),
            "goals": named_goals,
            "halftime_scores": halftime_scores,
            "seeds": list(seeds),
            "match_count": match_count,
        }

    def play(self, raw: Any) -> dict[str, Any]:
        """[designed: T37] Consume one explicit browser submission atomically."""
        if not isinstance(raw, dict):
            raise ValueError("play request must be an object")
        with self._play_lock:
            campaign = getattr(self.state, "campaign", None)
            expected = {"play_token", "fixture_id"} if campaign is not None else {"play_token"}
            if set(raw) != expected:
                raise ValueError("play request must identify its token and scheduled fixture in campaign mode")
            if campaign is not None:
                pending = campaign.next_fixture
                if pending is None or raw["fixture_id"] != pending.fixture_id:
                    raise StalePlaySubmission("scheduled fixture changed or was already played")
            token = raw["play_token"]
            if not isinstance(token, str) or not secrets.compare_digest(token, self._play_token):
                raise StalePlaySubmission("play request was already used or is stale")
            # Rotate before simulation. A replay cannot submit this action
            # again, including while a long match is running.
            self._play_token = secrets.token_urlsafe(24)
            if self.template_bytes is None:
                raise ValueError("original savestate bytes are required to prepare a friendly")
            from goal2.game.campaign_rounds import prepare as prepare_round,complete as complete_round
            candidate = prepare_round(self.state,self.template_bytes)
            adapted = Savestate(to_savestate(candidate, original=self.template_bytes))
            result = run_full_match(adapted, candidate, retain_state=True)
            candidate = complete_round(candidate,result,template=self.template_bytes)
            # Validate the full next browser view before making candidate state authoritative.
            response = self._session_view(candidate, list(candidate.managed_squad))
            self.state = candidate
            return response

    def _view_for(self, state: GameState, squad: list[int]) -> dict[str, Any]:
        country = state.managed_country
        if not 1 <= country <= 128 or country >= len(self.goaldat.country_names):
            raise ValueError(f"country {country} has no GOAL.DAT name")
        players = []
        for player_id in squad:
            if not 1 <= player_id < len(state.players):
                raise ValueError(f"country {country} contains invalid player ID {player_id}")
            record = state.players[player_id]
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
                "confidence": record[0x0C],
                # [designed: T44] Campaign eligibility is authoritative at kickoff.
                **({"availability": eligibility.info(record)} if getattr(state, "campaign", None) is not None else {}),
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
            # [derived: F020; designed: T43] Recompute from confirmed starters.
            "team_morale": team_morale(state.players, starting_eleven),
            "starting_eleven": starting_eleven,
            # [derived: F007, T35] A legacy byte may name a player outside the
            # displayed eleven; only expose captain choices that are eligible.
            "captain": captain,
            "tactics": state.country_tactics,
            "tactics_options": list(TACTICS),
            "confirmed": {
                "starting_eleven": list(starting_eleven),
                "captain": captain,
                "tactics": state.country_tactics,
            },
            "matchup": matchup,
        }

    def confirm_management(self, raw: Any) -> dict[str, Any]:
        """[designed: T36] Validate a complete browser draft before assignment."""
        if not isinstance(raw, dict) or set(raw) != {"country", "starting_eleven", "captain", "tactics"}:
            raise ValueError("request must contain country, starting_eleven, captain, and tactics")
        country = raw["country"]
        if isinstance(country, bool) or not isinstance(country, int) or country != self.state.managed_country:
            raise ValueError("draft country changed; reload the current squad")
        eleven = raw["starting_eleven"]
        if not isinstance(eleven, list) or len(eleven) != 11:
            raise ValueError("starting eleven must contain exactly 11 players")
        if any(isinstance(player, bool) or not isinstance(player, int) for player in eleven):
            raise ValueError("starting eleven player IDs must be integers")
        if len(set(eleven)) != 11:
            raise ValueError("starting eleven must contain 11 distinct players")
        squad = set(self.state.managed_squad)
        if any(player not in squad for player in eleven):
            raise ValueError("starting eleven must use players from the managed squad")
        if getattr(self.state, "campaign", None) is not None:
            eligibility.require_available(self.state.players, eleven)
        captain = raw["captain"]
        if isinstance(captain, bool) or not isinstance(captain, int) or captain not in eleven:
            raise ValueError("captain must be one of the starting eleven")
        tactics = raw["tactics"]
        if isinstance(tactics, bool) or not isinstance(tactics, int) or not 0 <= tactics <= 0xFF:
            raise ValueError("tactics must be an eight-bit integer from 0 to 255")

        # Build the response against a detached candidate too, so a bad roster
        # record cannot leave a partly confirmed state. Keep Python integers
        # intact; player IDs can exceed the legacy one-byte captain adapter.
        candidate = copy.copy(self.state)
        candidate.starting_eleven = list(eleven)
        candidate.captain = captain
        candidate.country_tactics = tactics
        result = self._session_view(candidate, list(candidate.managed_squad))
        self.state.starting_eleven = candidate.starting_eleven
        self.state.captain = candidate.captain
        self.state.country_tactics = candidate.country_tactics
        self._play_token = secrets.token_urlsafe(24)
        result["play_token"] = self._play_token
        return result

    def select_country(self, raw_country: Any) -> dict[str, Any]:
        """[designed: T35] Validate a complete candidate before changing state."""
        if isinstance(raw_country, bool) or not isinstance(raw_country, int) or not 1 <= raw_country <= 128:
            raise ValueError("country must be an integer from 1 to 128")
        if getattr(self.state, "campaign", None) is not None and raw_country != self.state.managed_country:
            raise ValueError("campaign manager is fixed; use New campaign to choose another country")
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
            result = self._session_view(candidate_state, squad)
            self.state.managed_country = candidate_state.managed_country
            self.state.managed_squad = candidate_state.managed_squad
            self.state.starting_eleven = candidate_state.starting_eleven
            self.state.captain = candidate_state.captain
            self.state.country_tactics = candidate_state.country_tactics
            self._play_token = secrets.token_urlsafe(24)
            result["play_token"] = self._play_token
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
        path = urlsplit(self.path).path
        if path not in ("/api/country", "/api/management", "/api/play", "/api/save", "/api/load", "/api/campaign"):
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= length <= MAX_BODY:
                raise ValueError("request body is too large or missing")
            body = json.loads(self.rfile.read(length))
            if path in ("/api/save", "/api/load"):
                if body != {}:
                    raise ValueError("request body must be an empty object")
                if path == "/api/save":
                    self.session.save_to_configured_path()
                    result = {"saved": True}
                else:
                    result = self.session.load_from_configured_path()
            elif path == "/api/country":
                if not isinstance(body, dict) or set(body) != {"country"}:
                    raise ValueError("request must contain only a country field")
                result = self.session.select_country(body["country"])
            elif path == "/api/campaign":
                result = self.session.new_campaign(body)
            elif path == "/api/management":
                result = self.session.confirm_management(body)
            else:
                result = self.session.play(body)
        except StalePlaySubmission as exc:
            self._json(409, {"error": str(exc), "play_token": self.session.view()["play_token"]})
            return
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, SessionSaveError) as exc:
            if path == "/api/save":
                message = "Could not save session. The previous save is safe; try again."
            elif path == "/api/load" and isinstance(exc, SessionSaveError):
                message = f"Could not load session: {exc}"
            else:
                message = str(exc)
            payload = {"error": message}
            if path == "/api/play":
                payload["play_token"] = self.session.view()["play_token"]
            self._json(500 if path in ("/api/play", "/api/save") else 400, payload)
            return
        except (IndexError, TypeError) as exc:
            message = ("Could not save session. The previous save is safe; try again."
                       if path == "/api/save" else
                       f"Could not load session: {exc}" if path == "/api/load" else str(exc))
            payload = {"error": message}
            if path == "/api/play":
                payload["play_token"] = self.session.view()["play_token"]
            self._json(500 if path == "/api/play" else 400, payload)
            return
        except Exception as exc:
            message = ("Could not save session. The previous save is safe; try again."
                       if path == "/api/save" else
                       f"Could not load session: {exc}" if path == "/api/load" else str(exc))
            payload = {"error": message}
            if path == "/api/play":
                payload["play_token"] = self.session.view()["play_token"]
            self._json(500 if path in ("/api/play", "/api/save") else 400, payload)
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
    parser = argparse.ArgumentParser(prog="python -m goal2.web", description="Serve a local browser view of a game session.")
    parser.add_argument("paths", nargs="*", type=Path,
                        help="new game: SAVESTATE GOAL.DAT; resume: GOAL.DAT")
    parser.add_argument("--resume", type=Path, help="resume a .g2save without an original savestate")
    parser.add_argument("--save", type=Path, help="local .g2save location (default: .cache/session.g2save)")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000; 0 chooses an available port)")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be from 0 to 65535")
    if args.resume:
        if len(args.paths) != 1:
            parser.error("--resume requires exactly one positional GOAL.DAT path")
        goaldat_path = args.paths[0]
        save_path = args.save or args.resume
    else:
        if len(args.paths) != 2:
            parser.error("new game requires SAVESTATE and GOAL.DAT paths")
        savestate_path, goaldat_path = args.paths
        save_path = args.save or Path(".cache/session.g2save")
    try:
        session = (WebSession.resume(args.resume, goaldat_path) if args.resume
                   else WebSession.load(savestate_path, goaldat_path))
        session.save_path = save_path
        serve(session, args.host, args.port)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    return 0
