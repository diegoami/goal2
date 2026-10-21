"""[designed: T92; owner, 2026-10-21] Renamed players and the manager's name.

[confirmed: goal2-archaeology docs/play-guide.md at 53d7ef5, E031 C30/C30b] F2 on a player's card
renames him, "maximum 12" characters; [confirmed: same, C15] the manager name takes "maximum 14".
[inferred: archaeology spec/customisation.md C-ALT-07] a rename lives in the saved game, never in
GOAL.DAT. The rebuild keeps both in the session state (state.player_renames, state.manager_name)
and resolves every displayed name here, so no view holds a second copy that can go stale.
"""
from dataclasses import replace

PLAYER_MAX, MANAGER_MAX = 12, 14




def clean(text, maximum):
    """The name as stored: stripped, 1..maximum printable CP437 characters, or ValueError."""
    if not isinstance(text, str):
        raise ValueError('a name must be text')
    name = text.strip()
    if not name:
        raise ValueError('a name cannot be empty')
    if len(name) > maximum:
        raise ValueError(f'a name has at most {maximum} characters')
    try:
        encoded = name.encode('cp437')
    except UnicodeEncodeError:
        raise ValueError('a name uses only characters the original can show') from None
    if any(b < 0x20 or b == 0x7F for b in encoded):
        raise ValueError('a name cannot hold control characters')
    return name


def rename_player(state, goaldat, word, text):
    """Rename player `word`; a name equal to the original removes the rename. Returns the name."""
    if type(word) is not int or not 1 <= word < len(goaldat.player_names):
        raise ValueError('no such player')
    name = clean(text, PLAYER_MAX)
    renames = dict(state.player_renames)
    if name == goaldat.player_names[word]:
        renames.pop(word, None)
    else:
        renames[word] = name
    state.player_renames = renames
    return name


def rename_manager(state, text):
    state.manager_name = clean(text, MANAGER_MAX)
    return state.manager_name


def named(goaldat, state):
    """GOAL.DAT's names with this session's renames applied; the same object when there are none."""
    renames = getattr(state, 'player_renames', None) if state is not None else None
    if not renames:
        return goaldat
    names = list(goaldat.player_names)
    for word, name in renames.items():
        names[word] = name
    return replace(goaldat, player_names=names)


def to_data(state):
    """The save's `identities` object, or None when nothing is renamed."""
    if not state.player_renames and not state.manager_name:
        return None
    data = {'players': {str(w): n for w, n in sorted(state.player_renames.items())}}
    if state.manager_name:
        data['manager'] = state.manager_name
    return data


def from_data(value, n_players):
    """(player_renames, manager_name) from a save's `identities` object; ValueError if malformed."""
    if not isinstance(value, dict) or not set(value) <= {'players', 'manager'} or 'players' not in value:
        raise ValueError('identities must hold players and optionally manager')
    players = value['players']
    if not isinstance(players, dict):
        raise ValueError('identities.players must be an object')
    renames = {}
    for key, name in players.items():
        if not key.isdigit() or str(int(key)) != key or not 1 <= int(key) < n_players:
            raise ValueError(f'identities.players: bad player number {key!r}')
        if clean(name, PLAYER_MAX) != name:
            raise ValueError(f'identities.players[{key}]: name is not in stored form')
        renames[int(key)] = name
    manager = ''
    if 'manager' in value:
        manager = value['manager']
        if clean(manager, MANAGER_MAX) != manager:
            raise ValueError('identities.manager: name is not in stored form')
    if not renames and not manager:
        raise ValueError('identities present but empty')
    return renames, manager
