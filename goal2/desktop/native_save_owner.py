"""[designed: T170az] The explicit native campaign's named-save owner."""

from goal2.desktop.model import MANAGER, STAGES
from goal2.desktop.native_desk_view import NativeDeskView, read
from goal2.game.season_publication import SeasonCampaign


class NativeSaveOwner:
    def __init__(self, campaign):
        if not isinstance(campaign, SeasonCampaign):
            raise ValueError('A native save needs a committed season campaign.')
        self.campaign = campaign
        self.save_name = None
        self.save_path = None
        self.saved = None

    @property
    def unsaved(self):
        return self.saved != self.campaign.revision

    def desk_view(self) -> NativeDeskView:
        return read(self.campaign)

    def summary(self):
        view = self.desk_view()
        stage = STAGES.get(view.stage, view.stage_word)
        return {'country': view.team.name, 'manager': view.manager.name.strip() or MANAGER,
                'year_stage': f'{view.year} · {stage}' if stage else str(view.year),
                'next': view.fixture.opponent.name if view.fixture is not None else 'No scheduled match'}
