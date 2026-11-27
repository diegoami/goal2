"""[designed: T170az] The explicit native campaign's named-save owner."""

from goal2.core.views import desk
from goal2.desktop.model import MANAGER, STAGES
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
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

    def summary(self):
        """[derived: Core desk reader, 000E:724A and 1771:5AC4] Read the committed manager boundary."""
        try:
            image = Image.from_state(self.campaign.state, engine_tables.load())
            managed, = image.managed_countries()
            view = desk(image)
            if view['team']['country'] != managed:
                raise ValueError('The current manager differs from the saved country.')
        except (ValueError, TypeError, IndexError, KeyError) as exc:
            raise ValueError(f'Cannot read the native manager boundary: {exc}') from exc
        opponent = view['opponent']
        stage = STAGES.get(view['stage'], view['stage_word'])
        return {'country': view['team']['name'], 'manager': view['manager'].strip() or MANAGER,
                'year_stage': f"{view['year']} · {stage}" if stage else str(view['year']),
                'next': opponent['name'] if opponent is not None else 'No scheduled match'}
