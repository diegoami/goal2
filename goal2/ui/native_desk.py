"""[designed: T170bb] The shared S06 presentation for a loaded native owner."""

from goal2.desktop.model import CHAMPIONSHIPS, CONTINENTS, MANAGER, PHASES, STAGES, WORLD_CUP
from goal2.ui.s06_desk import DeskScreen
from goal2.ui.s12_tournament import banner_text


_CONTINENT_CHAMPIONSHIPS = {name.casefold(): CHAMPIONSHIPS[number] for number, name in CONTINENTS.items()}


class NativeDeskScreen(DeskScreen):
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

    def _unavailable(self, *_):
        self.say('This action is unavailable for the native campaign.')

    # [designed: T170bb/#817] Keep S06's controls and focus order while each action gets its native owner.
    play_next_game = team_info = fixture_list = tournament = history = _unavailable
    select_squad = team_tactics = recordings = rename = _unavailable
