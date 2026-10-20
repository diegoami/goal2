"""Stage-2 continental qualifying: final tables and the group winners who reach the finals.

[derived: F023 §§3-4 and §8, goal2-archaeology 3656a2d26e0f57a410d648edeaa6cd9eb7d1f607]
Stage 2 draws 32 groups of four, eight per continent, each a double round robin (kind 2).
The A table is re-sorted after every stage-2 fixture, so once the stage has been played
slot 1 of each group is its winner; the 8 winners of a continent are its qualifiers for
the stage-3 finals (§4: "Qualifiers per continent: 8 (the group winners of stage 2)").
Building stage 3 (hosts, B groups, finals fixtures) is T52's.

[designed: T50] The outcome is read from the persisted world schedule and results: the
draw is recovered from the saved rows (standings.opening_groups), never drawn again, and
no RNG is used. Qualifiers exist only once every scheduled fixture of the stage has a
result; before that, positions are provisional.
"""
from goal2.game.standings import TableFixture, group_table, opening_groups

STAGE = 2


def tables(campaign, template):
    """[derived: F023 §8] Every group's current table, in source continent/group order.
    None unless the campaign holds a complete cycle-one stage-2 schedule."""
    if campaign is None or campaign.stage != STAGE:
        return None
    groups = opening_groups(campaign, template)
    if groups is None:
        return None
    world = campaign.world
    fixtures = tuple(TableFixture(f.fixture_id, f.kind, f.side_a, f.side_b) for f in world.fixtures)
    return tuple({'continent': continent, 'group': group, 'slots': slots,
                  'rows': group_table(slots, fixtures, world.results, stage=STAGE, places=1)}
                 for continent, group, slots in groups)


def outcome(campaign, template, managed_country):
    """[derived: F023 §4; designed: T50] The stage-2 outcome for one managed country.

    Returns None outside a complete cycle-one stage-2 schedule, else a dict:
    `complete` (every scheduled fixture has a result), `groups` (each table),
    `qualifiers` ({continent: the 8 group winners in group order}, only when complete),
    and `managed` (its continent, group, current rank and status: 'in progress',
    'qualified' or 'eliminated').
    """
    groups = tables(campaign, template)
    if groups is None:
        return None
    world = campaign.world
    complete = len(world.results) == len(world.fixtures)
    qualifiers = None
    if complete:
        qualifiers = {continent: tuple(g['rows'][0].country for g in groups if g['continent'] == continent)
                      for continent in range(1, 5)}
        if (any(len(winners) != 8 for winners in qualifiers.values())
                or len({c for winners in qualifiers.values() for c in winners}) != 32):
            raise ValueError('stage 2 must send eight distinct group winners per continent')
    own = next((g for g in groups if managed_country in g['slots']), None)
    if own is None:
        raise ValueError('managed country is absent from the saved qualifying groups')
    rank = next(row.rank for row in own['rows'] if row.country == managed_country)
    status = 'in progress' if not complete else 'qualified' if rank == 1 else 'eliminated'
    return {'complete': complete, 'groups': groups, 'qualifiers': qualifiers,
            'managed': {'continent': own['continent'], 'group': own['group'], 'rank': rank, 'status': status}}
