"""Versioned rebuild session saves with explicit JSON data. [designed: T33]

The save carries the complete adapted state and the compressed halftime template
needed to reconstruct the next friendly. It makes no claim of compatibility
with DOSBox-X savestates or any original save format. [designed: T33]
"""
from __future__ import annotations

import base64
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from goal2.game.state import (
    COUNTRY_SIZE, N_COUNTRIES, N_PLAYERS, PLAYER_SIZE, GameState,
)


FORMAT = "goal2-session"
VERSION = 3
_CAMPAIGN_VERSION = 2
_FRIENDLY_VERSION = 1
_TUPLE_TAG = "__goal2_session_tuple__"


class SessionSaveError(ValueError):
    """A session save is malformed, unsupported, or could not be written."""


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _json_value(value: Any) -> Any:
    """Encode JSON data while retaining tuple values used in GameState."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return value
    if isinstance(value, tuple):
        return {_TUPLE_TAG: [_json_value(item) for item in value]}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if _TUPLE_TAG in value or any(not isinstance(key, str) for key in value):
            raise TypeError("state dictionaries need string keys and cannot use the reserved tuple tag")
        return {key: _json_value(item) for key, item in value.items()}
    raise TypeError(f"unsupported session value: {type(value).__name__}")


def _restore_json_value(value: Any, field: str) -> Any:
    if isinstance(value, list):
        return [_restore_json_value(item, field) for item in value]
    if isinstance(value, dict):
        if _TUPLE_TAG in value:
            if set(value) != {_TUPLE_TAG} or not isinstance(value[_TUPLE_TAG], list):
                raise SessionSaveError(f"{field}: malformed tuple value")
            return tuple(_restore_json_value(item, field) for item in value[_TUPLE_TAG])
        return {key: _restore_json_value(item, field) for key, item in value.items()}
    return value


def _unb64(value: Any, field: str) -> bytes:
    if not isinstance(value, str):
        raise SessionSaveError(f"{field}: expected base64 text")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise SessionSaveError(f"{field}: invalid base64 data") from exc


def _state_data(state: GameState, version: int) -> dict[str, Any]:
    data = {
        "players": [_b64(bytes(record)) for record in state.players],
        "countries": [_b64(bytes(record)) for record in state.countries],
        "managed_country": state.managed_country,
        "managed_squad": list(state.managed_squad),
        "starting_eleven": list(state.starting_eleven),
        "captain": state.captain,
        "country_tactics": state.country_tactics,
        "rng_seed_7b62": state.rng_seed_7b62,
        "rng_seed_8336": state.rng_seed_8336,
        "match_state": _json_value(state.match_state),
        "vga": _b64(bytes(state.vga)),
        "mem": _b64(bytes(state.mem)),
        "match_count": state.match_count,
        "last_match": _json_value(state.last_match),
    }
    if state.campaign is not None:
        from goal2.game.campaign_pool import validate
        from goal2.game.campaign_rounds import validate_state
        validate_state(state)
        data["campaign"] = state.campaign.to_data()
        data["campaign"]["reserve_ids"] = validate(state)
    return data


def encode(state: GameState, template: bytes) -> bytes:
    """Return a validated explicit-data save document. [designed: T33]"""
    try:
        from goal2.game.watched_schema import needs_version3, validate_saved_watched
        validate_saved_watched(state)
        version = VERSION if needs_version3(state) else (_CAMPAIGN_VERSION if state.campaign is not None else _FRIENDLY_VERSION)
        document = {
            "format": FORMAT,
            "version": version,
            "template": _b64(bytes(template)),
            "state": _state_data(state, version),
        }
        raw = json.dumps(document, ensure_ascii=True, allow_nan=False,
                         separators=(",", ":")).encode("ascii")
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise SessionSaveError(f"cannot serialize session: {exc}") from exc
    # Decode our own document before it can be written; this catches invalid
    # record shapes and ranges without constructing unsafe Python objects.
    decode(raw)
    return raw


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise SessionSaveError(f"{field}: expected integer in {minimum}..{maximum}")
    return value


def _records(value: Any, field: str, count: int, size: int) -> list[bytes]:
    if not isinstance(value, list) or len(value) != count:
        raise SessionSaveError(f"{field}: expected {count} records")
    records = [_unb64(item, f"{field}[{i}]") for i, item in enumerate(value)]
    for i, record in enumerate(records):
        if len(record) != size:
            raise SessionSaveError(f"{field}[{i}]: expected {size} bytes, got {len(record)}")
    return records


def _numbers(value: Any, field: str, count: int, minimum: int, maximum: int) -> list[int]:
    if not isinstance(value, list) or len(value) != count:
        raise SessionSaveError(f"{field}: expected {count} player numbers")
    return [_integer(n, f"{field}[{i}]", minimum, maximum) for i, n in enumerate(value)]


def decode(raw: bytes) -> tuple[GameState, bytes]:
    """Load a save only after checking its complete versioned data shape."""
    try:
        doc = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"invalid number {value}")))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SessionSaveError(f"invalid session save JSON: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise SessionSaveError("not a goal2 session save")
    version = doc.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version not in (_FRIENDLY_VERSION, _CAMPAIGN_VERSION, VERSION):
        raise SessionSaveError(f"unsupported session save version: {doc.get('version')!r}")
    if set(doc) != {"format", "version", "template", "state"}:
        raise SessionSaveError("session save has missing or unknown top-level fields")
    template = _unb64(doc["template"], "template")
    data = doc["state"]
    required = {
        "players", "countries", "managed_country", "managed_squad", "starting_eleven",
        "captain", "country_tactics", "rng_seed_7b62", "rng_seed_8336", "match_state",
        "vga", "mem", "match_count", "last_match",
    }
    if version == _CAMPAIGN_VERSION or (version == VERSION and isinstance(data,dict) and "campaign" in data):
        required.add("campaign")
    if not isinstance(data, dict) or set(data) != required:
        raise SessionSaveError("session state has missing or unknown fields")
    players = _records(data["players"], "players", N_PLAYERS, PLAYER_SIZE)
    countries = _records(data["countries"], "countries", N_COUNTRIES, COUNTRY_SIZE)
    country = _integer(data["managed_country"], "managed_country", 1, 128)
    squad = _numbers(data["managed_squad"], "managed_squad", 20, 1, N_PLAYERS - 1)
    eleven = _numbers(data["starting_eleven"], "starting_eleven", 11, 1, N_PLAYERS - 1)
    if len(set(squad)) != 20 or len(set(eleven)) != 11 or not set(eleven).issubset(squad):
        raise SessionSaveError("managed squad and starting eleven must contain distinct valid players")
    captain = _integer(data["captain"], "captain", 0, N_PLAYERS - 1)
    tactics = _integer(data["country_tactics"], "country_tactics", 0, 255)
    seed_a = _integer(data["rng_seed_7b62"], "rng_seed_7b62", 0, 65535)
    seed_b = _integer(data["rng_seed_8336"], "rng_seed_8336", 0, 65535)
    match_count = _integer(data["match_count"], "match_count", 0, 2**31 - 1)
    match_state = _restore_json_value(data["match_state"], "match_state")
    last_match = _restore_json_value(data["last_match"], "last_match")
    if not isinstance(match_state, dict) or (last_match is not None and not isinstance(last_match, dict)):
        raise SessionSaveError("match_state and last_match must be objects (last_match may be null)")
    try:
        vga = _unb64(data["vga"], "vga")
        mem = _unb64(data["mem"], "mem")
    except SessionSaveError:
        raise
    campaign = None
    if "campaign" in required:
        try:
            from goal2.game.campaign import CampaignError, CampaignState
            campaign = CampaignState.from_data(data["campaign"])
        except CampaignError as exc:
            raise SessionSaveError(f"invalid campaign metadata: {exc}") from exc
    state = GameState(
        players=players, countries=countries, managed_country=country,
        managed_squad=squad, rng_seed_7b62=seed_a, rng_seed_8336=seed_b,
        match_state=match_state, vga=vga, mem=bytearray(mem),
        starting_eleven=eleven, captain=captain, country_tactics=tactics,
        match_count=match_count, last_match=last_match,
        campaign=campaign,
    )
    if campaign is not None:
        try:
            from goal2.game.campaign_pool import validate
            campaign.reserve_ids = validate(state)
            from goal2.game.campaign_rounds import validate_state
            validate_state(state)
        except ValueError as exc:
            raise SessionSaveError(f'invalid campaign pool: {exc}') from exc
    try:
        from goal2.game.watched_schema import needs_version3, validate_saved_watched
        validate_saved_watched(state)
        if needs_version3(state) and version != VERSION:
            raise ValueError("watched results require session version 3")
    except (ValueError, IndexError, KeyError, TypeError) as exc:
        raise SessionSaveError(f"invalid watched data: {exc}") from exc
    return state, template


def load(path: str | os.PathLike[str]) -> tuple[GameState, bytes]:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise SessionSaveError(f"cannot read session save: {exc}") from exc
    return decode(raw)


def save(path: str | os.PathLike[str], state: GameState, template: bytes) -> None:
    """Atomically replace a save; failures leave any previous save intact."""
    target = Path(path)
    raw = encode(state, template)
    temp_name: str | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".tmp",
                                         delete=False) as stream:
            temp_name = stream.name
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
        temp_name = None
    except OSError as exc:
        raise SessionSaveError(f"cannot write session save {target}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
