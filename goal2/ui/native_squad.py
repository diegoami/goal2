"""[designed: T170bd/T170bh] Browse and edit positions in the committed native squad and pool."""

from types import SimpleNamespace

from PySide6.QtCore import Qt, QTimer

from goal2.core.views import Memory, pool, squad
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.campaign_pool import fold
from goal2.game.native_position_job import NativePositionJob
from goal2.ui.s08_squad import SquadScreen


_DEFERRED_KEYS = {Qt.Key.Key_A, Qt.Key.Key_Insert, Qt.Key.Key_T, Qt.Key.Key_F2}


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

    def __init__(self, window, owner):
        self.owner = owner
        self.position_edit = None
        self.revision = owner.campaign.revision
        super().__init__(window, _NativeSquadModel(owner.campaign), back='desk')
        self.position_timer = QTimer(self)
        self.position_timer.setInterval(20)
        self.position_timer.timeout.connect(self._poll_position)
        for binding in self.bindings:
            if _DEFERRED_KEYS.intersection(binding.keys):
                binding.shown = False
        self._refresh_bar()

    def refresh(self):
        super().refresh()
        self.note.setText('Changing position…' if self.position_edit is not None else self.message)

    def enter_hint_text(self):
        return super().enter_hint_text() if self.searching else ''

    def _unavailable(self, *_):
        self.say('This squad action is unavailable.')

    press_move = assistant = his_tactics = new_name = _unavailable

    def reposition(self, step):
        if step == 1:
            return self._edit_position('R')
        self.say('Use R for the next position.')

    def club_position(self):
        return self._edit_position('C')

    def _edit_position(self, key):
        if (self.position_edit is not None or self.searching or self.window_.current() is not self
                or self.window_.career is not self.owner):
            return
        campaign = self.owner.campaign
        if self.revision != campaign.revision:
            self._reload()
            return self.say('The squad changed. Check the selected player and try again.')
        if (word := self.current()) is None:
            return
        try:
            self.position_edit = NativePositionJob(self.owner, campaign.state, self.revision, word, key)
        except (OSError, RuntimeError, ValueError) as exc:
            return self.say(str(exc))
        self.message = ''
        self.position_timer.start()
        self.refresh()

    def _poll_position(self):
        if self.window_.current() is not self:
            return
        if self.window_.career is not self.owner:
            self.cancel_position_edit()
            return
        result = self.position_edit.poll() if self.position_edit is not None else None
        if result is None:
            return
        self.position_timer.stop()
        self.position_edit = None
        kind, reply = result
        if kind != 'position':
            error = reply.get('error') if reply is not None else None
            return self.say(error or 'The position edit was not completed.')
        try:
            self.owner.campaign.publish_management(
                reply['state'], action='player-position', revision=reply['revision'],
                input_hash=reply['input_hash'], output_hash=reply['output_hash'])
        except (RuntimeError, ValueError) as exc:
            self._reload()
            return self.say(str(exc))
        self._reload()
        self.say('')

    def _reload(self):
        # [designed: T170bh] Keep the current word on each pane across native reordering.
        selected = {}
        for side, index in self.cursor.items():
            rows = self.rows(side)
            if index < len(rows):
                selected[side] = rows[index]['id']
        campaign = self.owner.campaign
        self.model = _NativeSquadModel(campaign)
        self.revision = campaign.revision
        for side, word in selected.items():
            self.cursor[side] = next((i for i, row in enumerate(self.rows(side)) if row['id'] == word), 0)

    def cancel_position_edit(self):
        if self.position_edit is not None:
            self.position_edit.cancel()
            self.position_edit = None
            self.position_timer.stop()
            self.message = ''
