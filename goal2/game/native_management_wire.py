"""[designed: T170bj] Host validation of private standalone native edit replies."""

from goal2.engine.original_match import Image
from goal2.game import engine_tables
from goal2.game.native_position import position_codes, position_goal
from goal2.game.native_roster_move import move_context
from goal2.game.native_squad_menu import manager_roster


def position_check(source, player, key):
    position, club = position_codes(source, player)
    expected = position_goal(position, club, key), club

    def verify(state, fields):
        if (set(fields) != {'position', 'club_position'}
                or any(type(code) is not int for code in fields.values())
                or (fields['position'], fields['club_position']) != expected):
            raise ValueError('position codes differ')
        if position_codes(state, player) != expected:
            raise ValueError('saved position codes differ')

    return verify


def roster_check(source, first, second):
    tables = engine_tables.load()
    image = Image.from_state(source, tables)
    roster, squad, pool = move_context(image, (first, second))
    swapped = {first: second, second: first}
    expected = tuple(sorted(swapped.get(word, word) for word in block)
                     for block in (squad[:11], squad[11:], pool))
    exchange = first in pool or second in pool

    def verify(state, fields):
        if set(fields) != {'refusal'}:
            raise ValueError('invalid roster result fields')
        refusal = fields['refusal']
        if refusal is not None:
            if not exchange or refusal not in ('finals', 'tour') or state is not None:
                raise ValueError('invalid roster refusal')
            return
        image = Image.from_state(state, tables)
        if manager_roster(image) != roster:
            raise ValueError('roster manager context differs')
        actual_squad, actual_pool = roster.words(lambda at, size: image.memory[at:at + size])
        if tuple(sorted(block) for block in (actual_squad[:11], actual_squad[11:], actual_pool)) != expected:
            raise ValueError('returned roster membership differs from the requested move')

    return verify
