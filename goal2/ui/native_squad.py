"""[designed: T170bd] Read the committed native squad and pool through S08."""

from types import SimpleNamespace

from PySide6.QtCore import Qt

from goal2.core.views import Memory, pool, squad
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.campaign_pool import fold
from goal2.ui.s08_squad import SquadScreen


_READ_ONLY = 'Browse the squad and pool. Edits are unavailable from this native view.'
_EDIT_KEYS = {
    Qt.Key.Key_A, Qt.Key.Key_Insert, Qt.Key.Key_R, Qt.Key.Key_C, Qt.Key.Key_T, Qt.Key.Key_F2,
}


def _row(source):
    return {'id': source['player'], 'role': source['code'], 'line': source['line'],
            'position': source['position']}


class _NativeSquadModel:
    """Detached original records for the existing player-card decoder."""

    def __init__(self, campaign):
        state, _ = campaign.committed_snapshot()
        image = Image.from_state(state, engine_tables.load())
        memory = Memory(image)
        managed, = image.managed_countries()
        if memory.manager_country(0x80 + memory.game(1)) != managed:
            raise ValueError('The current manager differs from the saved country.')
        roster = squad(memory, managed)
        words = tuple(row['player'] for row in roster)
        players = tuple(image.players())
        countries = tuple(image.countries())
        if len(set(words)) != 20 or any(not 1 <= word < len(players) for word in words):
            raise ValueError('The native squad does not contain twenty distinct players.')
        initial_and_surname = [('', '')]
        initial_and_surname.extend(memory.raw_player_name(word).split(' ', 1) for word in range(1, len(players)))
        self.goaldat = SimpleNamespace(
            player_initials=tuple(initial for initial, _ in initial_and_surname),
            player_names=tuple(surname for _, surname in initial_and_surname),
        )
        self.state = SimpleNamespace(
            players=players, countries=countries, managed_country=managed, managed_squad=words,
            starting_eleven=words[:11], country_tactics=countries[managed][0x2D],
            mem=image.memory_component(), vga=b'',
        )
        self._country_name = memory.country_name(managed)
        self._squad = tuple(roster)
        # [confirmed: F011, Core pool reader] Read the manager's actual A927 list.
        self._pool = tuple(row for row in pool(image)['rows'] if row['player'])
        if any(not 1 <= row['player'] < len(players) for row in self._pool):
            raise ValueError('The native pool contains an invalid player.')

    def view(self):
        return {'country_name': self._country_name, 'players': [_row(row) for row in self._squad]}

    def pool_view(self, *, query='', position=None):
        query = fold(query)
        return {'reserves': [_row(row) for row in self._pool
                             if (position is None or row['position'] == position)
                             and query in fold(self.goaldat.player_names[row['player']])]}


class NativeSquadScreen(SquadScreen):
    GRID = True  # [designed: T215] S08 keeps the same grid in the native read view.

    def __init__(self, window, campaign):
        super().__init__(window, _NativeSquadModel(campaign), back='desk')
        for binding in self.bindings:
            if _EDIT_KEYS.intersection(binding.keys):
                binding.shown = False
        self._refresh_bar()

    def refresh(self):
        super().refresh()
        self.note.setText(self.message or _READ_ONLY)

    def enter_hint_text(self):
        return super().enter_hint_text() if self.searching else ''

    def _unavailable(self, *_):
        self.say(_READ_ONLY)

    press_move = assistant = reposition = club_position = his_tactics = new_name = _unavailable
