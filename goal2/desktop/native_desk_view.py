"""[designed: T170ba] Immutable Desk data from one committed native snapshot."""

from dataclasses import dataclass

from goal2.core.views import desk
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.season import canonical_hash


@dataclass(frozen=True, slots=True)
class DeskCountry:
    country: int
    name: str
    continent: str
    world_rank: int
    continent_rank: int


@dataclass(frozen=True, slots=True)
class DeskManager:
    number: int
    name: str
    country: int


@dataclass(frozen=True, slots=True)
class DeskFixture:
    index: int
    opponent: DeskCountry
    text: str


@dataclass(frozen=True, slots=True)
class DeskPlayer:
    player: int
    name: str
    position: int
    code: str
    line: str


@dataclass(frozen=True, slots=True)
class NativeDeskView:
    state_hash: str
    revision: int
    status: str | None
    manager: DeskManager
    rating: str
    team: DeskCountry
    managers: tuple[DeskManager, ...]
    year: int
    stage: int
    stage_word: str
    fixture: DeskFixture | None
    squad: tuple[DeskPlayer, ...]
    sacked: bool

    @property
    def starting_eleven(self):
        return self.squad[:11]

    @property
    def bench(self):
        return self.squad[11:]


def read(campaign):
    """[derived: Core Desk reader, 000E:724A and 1771:5AC4] Read the original manager boundary."""
    state, ledger = campaign.committed_snapshot()
    try:
        image = Image.from_state(state, engine_tables.load())
        managed, = image.managed_countries()
        view = desk(image)
        if view['team']['country'] != managed:
            raise ValueError('The current manager differs from the saved country.')
        fixture = (DeskFixture(view['fixture'], DeskCountry(**view['opponent']), view['fixture_kind'])
                   if view['fixture'] is not None else None)
        return NativeDeskView(
            state_hash=canonical_hash(state), revision=len(ledger), status=ledger[-1].status if ledger else None,
            manager=DeskManager(view['manager_number'], view['manager'], managed), rating=view['rating'],
            team=DeskCountry(**view['team']), managers=tuple(DeskManager(**row) for row in view['managers']),
            year=view['year'], stage=view['stage'], stage_word=view['stage_word'], fixture=fixture,
            squad=tuple(DeskPlayer(**row) for row in view['squad']), sacked=view['sacked'],
        )
    except (ValueError, TypeError, IndexError, KeyError) as exc:
        raise ValueError(f'Cannot read the native manager boundary: {exc}') from exc
