"""[designed: #619] Read-only UI projections of T196 decision snapshots.
No career, archived event, engine record or original table is changed here.
"""
import copy
from types import MappingProxyType
from goal2.game.watched_schema import validate_player_records


def player_snapshot(data):
    """Reuse the accepted wire validator; copy bytes into an immutable map."""
    validate_player_records(data)
    return MappingProxyType({word: bytes.fromhex(raw) for word, raw in data.get("player_records", ())})


def card_state(state, records, team_tactics=None):
    """Shallow view with copied player sequence, never an opaque model mutation."""
    view = copy.copy(state)
    players = list(state.players)
    for word, record in records.items():
        if word >= len(players):
            raise ValueError("live player is outside the career records")
        players[word] = record
    view.players = players
    if team_tactics is not None:
        view.country_tactics = team_tactics
    return view
