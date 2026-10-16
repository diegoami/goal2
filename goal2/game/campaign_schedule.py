"""Static opening-campaign fixture metadata from GOAL.DAT and a local template.

[derived: F023, goal2-archaeology 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
The opening stage-2 and stage-5 draw and fixture loops are modeled from the
pinned listing. This is a static reconstruction, not original-runtime evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
import zipfile
import zlib

from goal2.game.campaign import CampaignError, Fixture, opening_calendar
from goal2.engine.quick_engine import LCG
from goal2.engine.savestate import Savestate

if TYPE_CHECKING:
    from goal2.game.state import GameState


@dataclass(frozen=True)
class GroupAssignment:
    """A drawn group in source continent/group order. [derived: F023]"""
    continent: int
    group: int
    countries_by_slot: tuple[int, int, int, int]


@dataclass(frozen=True)
class OpeningFixture:
    """One original row; A/B preserve listing operand order. [derived: F023]"""
    fixture_number: int
    fixture_id: str
    stage: int
    kind: int
    round: int
    continent: int
    group: int
    draw_group: int
    opponent_group: int | None
    country_a: int
    country_b: int

    @property
    def friendly(self) -> bool:
        """Whether this source kind is friendly kind 1. [derived: F023]"""
        return self.kind == 1


@dataclass(frozen=True)
class OpeningCampaign:
    """Validated opening draw and its source-ordered rows. [designed: T41a]"""
    start_year: int
    cycle: int
    year: int
    stage: int
    seed_7b62: int
    seed_8336: int
    post_draw_seed_7b62: int
    post_draw_seed_8336: int
    groups: tuple[GroupAssignment, ...]
    fixtures: tuple[OpeningFixture, ...]

    def managed_fixtures(self, managed_country: int) -> tuple[Fixture, ...]:
        """Project this country’s rows, retaining IDs, order and A/B endpoints. [designed: T41a]"""
        if isinstance(managed_country, bool) or not isinstance(managed_country, int) or not 1 <= managed_country <= 128:
            raise CampaignError("managed_country must be an integer in 1..128")
        ordinal, stage = opening_calendar(self.start_year)
        if (stage, ordinal) != (self.stage, self.year):
            raise CampaignError("opening metadata does not match its source start year")
        rows = tuple(
            Fixture(
                fixture_id=row.fixture_id, cycle=1, year=self.year, stage=self.stage,
                kind=row.kind, home_country=row.country_a, away_country=row.country_b,
            )
            for row in self.fixtures
            if managed_country in (row.country_a, row.country_b)
        )
        if not rows:
            raise CampaignError(f"country {managed_country} has no opening fixtures")
        return rows


def _read_tables(template: bytes) -> tuple[tuple[tuple[int, ...], ...], dict[tuple[int, int], tuple[int, int]], bytes, bytes, tuple[int, int]]:
    """Read and validate required immutable source tables before building output."""
    try:
        ds = Savestate(template)
        slots_raw = ds.ds_bytes(0x0F76, 16)
        schedule_raw = ds.ds_bytes(0x0F54, 0x13A)
        friendlies_raw = ds.ds_bytes(0x1087, 55)
        thresholds = ds.ds_bytes(0x1106, 2)
        fixture_starts = ds.ds_bytes(0x6936, 4)
    except (ValueError, KeyError, OSError, TypeError, zipfile.BadZipFile, zlib.error) as exc:
        raise CampaignError(f"local engine template is missing required campaign tables: {exc}") from exc

    slots = tuple(tuple(slots_raw[r * 4:r * 4 + 4]) for r in range(4))
    if any(sorted(row) != [1, 2, 3, 4] for row in slots):
        raise CampaignError("local slot permutation table is invalid")

    schedule: dict[tuple[int, int], tuple[int, int]] = {}
    for key in range(2, 13):
        base = 0x18 * key
        pairs = []
        for round_number in range(1, 13):
            offset = base + 2 * round_number
            pair = (schedule_raw[offset], schedule_raw[offset + 1])
            if pair[0] not in range(1, 5) or pair[1] not in range(1, 5) or pair[0] == pair[1]:
                raise CampaignError(f"local qualifying schedule row {key} has an invalid pair")
            pairs.append(pair)
        if len(set(pairs)) != 12 or any(sum(team in pair for pair in pairs) != 6 for team in range(1, 5)):
            raise CampaignError(f"local qualifying schedule row {key} is not a double round robin")
        schedule.update({(key, round_number): pairs[round_number - 1]
                         for round_number in range(1, 13)})

    partners = friendlies_raw
    for group in range(1, 9):
        row = partners[group * 6 + 1:group * 6 + 7]
        if any(value > 8 or value == group for value in row):
            raise CampaignError(f"local friendly partner row {group} is invalid")
    if not (1 < thresholds[0] <= 13 and 1 < thresholds[1] <= 13):
        raise CampaignError("local friendly round thresholds are invalid")
    starts = (int.from_bytes(fixture_starts[:2], "little"),
              int.from_bytes(fixture_starts[2:], "little"))
    if starts != (1, 1361):
        raise CampaignError("local opening fixture-number table is invalid")
    return slots, schedule, partners, thresholds, starts


def _validated_orders(goaldat: Any) -> tuple[tuple[int, ...], tuple[int, ...], dict[int, int]]:
    """Validate GOAL.DAT rank permutations and derive continent membership. [derived: F023]"""
    try:
        world = tuple(goaldat.per_country_b[1:])
        continental = tuple(goaldat.per_country_c[1:])
    except (AttributeError, TypeError) as exc:
        raise CampaignError(f"GOAL.DAT is missing campaign rank arrays: {exc}") from exc
    expected = set(range(1, 129))
    if (len(world) != 128 or any(isinstance(x, bool) or not isinstance(x, int) for x in world)
            or set(world) != expected):
        raise CampaignError("GOAL.DAT world order must contain each country once")
    if (len(continental) != 128 or any(isinstance(x, bool) or not isinstance(x, int) for x in continental)
            or set(continental) != expected):
        raise CampaignError("GOAL.DAT continental order must contain each country once")
    continent_for = {
        country: index // 32 + 1
        for index, country in enumerate(continental)
    }
    return world, continental, continent_for


def build_opening_campaign(
    goaldat: Any,
    engine_template: bytes,
    *,
    start_year: int,
    seed_7b62: int,
    seed_8336: int,
) -> OpeningCampaign:
    """Build cycle-one stage 2 or 5 metadata without mutating inputs.

    [derived: F023, goal2-archaeology 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
    The initial rank orders, 4-swap pot draw, slot row, friendly rows, group
    schedules and fixture numbering follow the pinned static builder listing.
    """
    year, stage = opening_calendar(start_year)
    for name, value in (("seed_7b62", seed_7b62), ("seed_8336", seed_8336)):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 65535:
            raise CampaignError(f"{name} must be an integer in 0..65535")
    slots, schedule, partners, thresholds, starts = _read_tables(engine_template)
    threshold = thresholds[1 if stage == 2 else 0]
    fixture_number = starts[0 if stage == 2 else 1]
    if not (1 < threshold <= 13) or fixture_number <= 0:
        raise CampaignError("local opening stage constants are invalid")
    world, continental, continent_for = _validated_orders(goaldat)

    # F023 1771:56FF copies continental order at stage 2; stage 5 filters
    # world order into four continent blocks. [derived: F023]
    initial = continental if stage == 2 else tuple(
        country for continent in range(1, 5)
        for country in world if continent_for[country] == continent
    )
    if len(initial) != 128 or any(
        sum(continent_for[country] == continent for country in initial[(continent - 1) * 32:continent * 32]) != 32
        for continent in range(1, 5)
    ):
        raise CampaignError("GOAL.DAT orders do not form four complete continent blocks")

    rng = LCG(seed_7b62)
    pots: list[list[int]] = []
    for block in range(16):
        pot = list(initial[block * 8:(block + 1) * 8])
        for _ in range(4):
            first, second = rng.rand(8) - 1, rng.rand(8) - 1
            pot[first], pot[second] = pot[second], pot[first]
        pots.append(pot)

    groups: list[GroupAssignment] = []
    slots_by_group: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    for continent in range(1, 5):
        for group in range(1, 9):
            slot_row = slots[rng.rand(4) - 1]
            assigned = [0, 0, 0, 0]
            group_index = group - 1
            for pot_index in range(4):
                country = pots[(continent - 1) * 4 + pot_index][group_index]
                assigned[slot_row[pot_index] - 1] = country
            if any(country == 0 for country in assigned):
                raise CampaignError("local slot assignment did not produce a group")
            assignment = tuple(assigned)
            slots_by_group[(continent, group)] = assignment
            groups.append(GroupAssignment(continent, group, assignment))

    fixtures: list[OpeningFixture] = []
    for round_number in range(1, 13):
        for continent in range(1, 5):
            for group in range(1, 9):
                partner = partners[group * 6 + round_number] if round_number < threshold else 0
                if partner:
                    for slot in range(1, 5):
                        a = slots_by_group[(continent, partner)][slot - 1]
                        b = slots_by_group[(continent, group)][slot - 1]
                        fixtures.append(_fixture(fixture_number, stage, 1, round_number,
                                                 continent, 0, group, partner, a, b))
                        fixture_number += 1
                pair_a, pair_b = schedule[(group + continent, round_number)]
                assigned = slots_by_group[(continent, group)]
                fixtures.append(_fixture(fixture_number, stage, stage, round_number,
                                         continent, group, group, None,
                                         assigned[pair_a - 1], assigned[pair_b - 1]))
                fixture_number += 1

    expected_rows = 768 if stage == 2 else 640
    expected_per_country = 12 if stage == 2 else 10
    appearances = {country: 0 for country in range(1, 129)}
    for row in fixtures:
        if row.country_a == row.country_b:
            raise CampaignError("opening fixture contains the same country twice")
        appearances[row.country_a] += 1
        appearances[row.country_b] += 1
    if len(fixtures) != expected_rows or set(appearances.values()) != {expected_per_country}:
        raise CampaignError("local tables produce an invalid opening fixture count")
    if len({row.fixture_number for row in fixtures}) != len(fixtures):
        raise CampaignError("opening fixture numbers are not unique")
    return OpeningCampaign(
        start_year=start_year, cycle=1, year=year, stage=stage,
        seed_7b62=seed_7b62, seed_8336=seed_8336,
        post_draw_seed_7b62=rng.seed, post_draw_seed_8336=seed_8336,
        groups=tuple(groups), fixtures=tuple(fixtures),
    )


def _fixture(number: int, stage: int, kind: int, round_number: int,
             continent: int, group: int, draw_group: int, opponent_group: int | None,
             country_a: int, country_b: int) -> OpeningFixture:
    return OpeningFixture(
        fixture_number=number, fixture_id=f"original:{number}", stage=stage,
        kind=kind, round=round_number, continent=continent, group=group,
        draw_group=draw_group, opponent_group=opponent_group, country_a=country_a, country_b=country_b,
    )


def start_opening_campaign(
    goaldat: Any,
    engine_template: bytes,
    *,
    managed_country: int,
    start_year: int,
    seed_7b62: int,
    seed_8336: int,
) -> tuple["GameState", OpeningCampaign]:
    """Build a T40 campaign candidate and continue live RNG after the opening draw.

    [designed: T41a] Draw RNG is explicit and separate from player-pool setup;
    the returned GameState starts after its 160 opening-draw calls.
    """
    from goal2.game.campaign import start_campaign

    opening = build_opening_campaign(
        goaldat, engine_template, start_year=start_year,
        seed_7b62=seed_7b62, seed_8336=seed_8336,
    )
    state = start_campaign(
        goaldat, engine_template, managed_country=managed_country,
        start_year=start_year, seed_7b62=seed_7b62, seed_8336=seed_8336,
        fixtures=opening.managed_fixtures(managed_country),
    )
    state.rng_seed_7b62 = opening.post_draw_seed_7b62
    state.rng_seed_8336 = opening.post_draw_seed_8336
    return state, opening
