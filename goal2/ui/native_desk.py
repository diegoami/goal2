"""[designed: T170bb] The shared S06 presentation for a loaded native owner."""

from types import SimpleNamespace

from goal2.data.goaldat import load as load_goaldat
from goal2.desktop.model import CHAMPIONSHIPS, CONTINENTS, MANAGER, PHASES, STAGES, WORLD_CUP
from goal2.ui.native_match_day import NativeMatchDay
from goal2.ui.s06_desk import DeskScreen
from goal2.ui.s12_tournament import banner_text


_CONTINENT_CHAMPIONSHIPS = {name.casefold(): CHAMPIONSHIPS[number] for number, name in CONTINENTS.items()}


class _NativeRoundIdentity:
    """[designed: T170bc] Names and manager identity for the retained round's screens."""

    def __init__(self, data, view):
        self.goaldat = data
        self.state = SimpleNamespace(managed_country=view.team.country,
                                     manager_name=view.manager.name, player_renames={})

    def rename_player(self, *_):
        raise ValueError('Player renaming is unavailable during a native round.')


class NativeDeskScreen(DeskScreen):
    GRID = True  # [designed: T215] The concrete native Desk uses the shared cell layout.

    def __init__(self, window, model):
        self.native_round = None
        super().__init__(window, model)

    def refresh(self):
        view = self.model.desk_view()
        if view.stage in PHASES:
            name = (WORLD_CUP if view.stage >= 5
                    else _CONTINENT_CHAMPIONSHIPS.get(view.team.continent.casefold(), STAGES[view.stage]))
            phase = view.stage_word.strip()
        else:
            name, phase = STAGES.get(view.stage, view.stage_word), ''
        self.banner.setText(banner_text({'year': view.year, 'name': name, 'phase': phase}))

        manager = view.manager.name.strip() or MANAGER
        self.manager['name'].setText(manager)
        self.manager['rating'].setText(view.rating)
        self.team_name.setText(view.team.name)
        self._native_ranks(self.team_ranks, view.team)
        self.managers.show_manager(manager, view.team.name, view.manager.number)

        fixture = view.fixture
        if fixture is None:
            opponent = ''
            cue = 'No scheduled match'
            self.opponent_ranks['world'].setText('—')
            self.opponent_ranks['continent'].caption.setText('continent')
            self.opponent_ranks['continent'].setText('—')
        else:
            opponent = fixture.opponent.name
            cue = fixture.text
            self._native_ranks(self.opponent_ranks, fixture.opponent)
        self.opponent_name.setText(opponent or '—')
        self.opponent_kind.setText(cue)
        self.play_opponent.setText(opponent)
        self.play_kind.setText(cue)
        self.strip.show_rows(view.team.name, [(row.code, row.line, row.name) for row in view.squad])
        self.note.setText(self.message or ('The manager has been dismissed.' if view.sacked else ''))

    def _native_ranks(self, labels, country):
        self._ranks(labels, {'world': country.world_rank, 'continent': country.continent,
                             'continental': country.continent_rank})

    def play_next_game(self):
        """[designed: T170bc] Play an explicit committed round, then return to this Desk."""
        if self.window_.current() is not self or self.window_.career is not self.model:
            return None
        if self.native_round is not None:
            if not self.native_round.native.disposed:
                return self.say('The previous round is still closing.')
            self.native_round.deleteLater()
            self.native_round = None
        try:
            view = self.model.desk_view()
            if view.sacked:
                return self.say('The manager has been dismissed.')
            if view.status == 'deferred-rollover':
                return self.say('The season is complete. Annual rollover is unavailable.')
            identity = _NativeRoundIdentity(load_goaldat(self.window_.target.goal_dat.read_bytes()), view)
            self.native_round = NativeMatchDay(
                self.window_, identity, self.model.campaign.state,
                campaign=self.model.campaign, engine_owner=self.model,
                show_round_results=True, show_bulletins=True,
                on_boundary=self._round_published, on_failure=self._return_from_round,
                on_goal=self._goal, on_tournament=self._round_tournament, on_stats=self._round_stats,
            )
            self.native_round.setParent(self)
            return self.native_round
        except (OSError, KeyError, RuntimeError, TypeError, ValueError) as exc:
            return self.say(str(exc))

    def _round_published(self, day, packet):
        status = packet['observation']['status']
        message = ('The season is complete. Annual rollover is unavailable.'
                   if status == 'deferred-rollover' else 'Round complete.')
        self._return_from_round(day, message)

    def _return_from_round(self, day, message):
        day.close()
        if day is not self.native_round or self not in self.window_.stack or self.window_.career is not self.model:
            return
        while self.window_.current() is not self:
            self.window_.pop()
        self.say(message)

    @staticmethod
    def _goal(pitch, _):
        pitch.show_stop('goal', 'Goal', '', lambda _: pitch.release_goal())

    @staticmethod
    def _round_tournament(flow):
        flow.window.current().say('Tournament is unavailable during a native round.')

    @staticmethod
    def _round_stats(_, menu):
        menu.say('Match statistics are unavailable before the native match.')

    def close_native_round(self):
        if self.native_round is not None:
            self.native_round.close()

    def select_squad(self):
        if self.window_.current() is not self or self.window_.career is not self.model:
            return None
        from goal2.ui.native_squad import NativeSquadScreen
        try:
            screen = NativeSquadScreen(self.window_, self.model)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            return self.say(f'Cannot read the native squad: {exc}')
        return self.window_.push(screen)

    def closing(self):
        self.close_native_round()
        super().closing()

    def _unavailable(self, *_):
        self.say('This action is unavailable for the native campaign.')

    # [designed: T170bb/#817] Keep S06's controls and focus order while each action gets its native owner.
    team_info = fixture_list = tournament = history = _unavailable
    team_tactics = recordings = rename = _unavailable
