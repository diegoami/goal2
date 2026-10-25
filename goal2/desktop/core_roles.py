"""[designed: owner #424; accepted #283/#286] Side-sensitive display codes, never guest edits.

The original DS:69A8 table uses B/B, M/M and W/W. The accepted presentation uses lower case
for left positions3/7/10; retain raw Core views as the original-screen oracle.
"""
from goal2.game.roles import LEFT


def role_code(row, *, club=False):
    position = row.get('club_position' if club else 'position')
    code = row['club_code' if club else 'code']
    return code.lower() if type(position) is int and position in LEFT else code


def pitch_identity(state, identity):
    """Adapt a detached viewer identity, using each actual player's original position field."""
    from goal2.core import views
    mem = views.Memory(state)
    base = mem.far(views.PLAYERS)
    roles = {}
    for word, code in identity['roles'].items():
        position = mem.byte(base + views.PLAYER_SIZE * int(word) + 6)
        roles[word] = role_code(dict(position=position, code=code))
    return {**identity, 'roles': roles}
