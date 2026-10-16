"""[designed: T26, A-MATCH-1] A complete friendly on the vendored quick engine.

The template supplies tables, players and seeds. Its half-time match state is
not a kick-off state; setup and first-half play here are an explicit stand-in.
E010 "Match clock & loop" at archaeology 1b694ed confirms D733 timing and
kick-off side selection, but no whole-match seed-exact claim follows.
"""
from __future__ import annotations

import sys
from pathlib import Path

from goal2.ai.cpu import get_computer_tactics, pick_computer_eleven

# [designed: T01 vendored import layout] quick_engine imports sibling players.
_ENGINE_DIR = str(Path(__file__).resolve().parents[1] / "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from goal2.engine.quick_engine import QuickMatch  # noqa: E402


def resolve_full_matchup(template, game_state) -> tuple[tuple[int, int], int, int]:
    """[designed: T29] Resolve the actual engine teams for a full friendly.

    Returns ``(teams, managed_side, opponent)`` using the same replacement
    rule consumed by both the preview and the runner. This reads template
    setup but does not simulate the match. [designed: T41] Campaign mode instead
    uses the exact next scheduled pair and refuses unsupported fixtures.
    """
    qm = QuickMatch(template)
    if qm.ninea3d != 0 or qm.eight319 != 0x2D:
        raise ValueError("full friendly needs a normal friendly template")
    if qm.eight31a not in (0, 1):
        raise ValueError("invalid kick-off side in template")

    selected = game_state.managed_country
    if not 1 <= selected <= 128:
        raise ValueError("managed country must be 1..128")
    # [designed: T41] Campaign rows override both inherited template endpoints.
    # [derived: F023 at 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
    # Preserve source A/B order without inferring a home venue.
    if getattr(game_state, "campaign", None) is not None:
        campaign = game_state.campaign
        fixture = campaign.next_fixture
        if fixture is None:
            raise ValueError("unsupported next stage: no fixture builder is available")
        if fixture.kind != 1:
            raise ValueError(f"unsupported fixture kind {fixture.kind}; competitive play is unavailable")
        if (fixture.cycle, fixture.year, fixture.stage) != (campaign.cycle, campaign.year, campaign.stage):
            raise ValueError("unsupported next stage: calendar transition is required")
        teams = (fixture.side_a, fixture.side_b)
        if selected not in teams:
            raise ValueError("scheduled fixture does not include the managed country")
        managed_side = teams.index(selected)
        return teams, managed_side, teams[1 - managed_side]
    original_teams = tuple(qm.teams)
    managed_side = original_teams.index(selected) if selected in original_teams else 0
    opponent_side = 1 - managed_side
    opponent = original_teams[opponent_side]
    if opponent == selected:
        raise ValueError("template needs a distinct opponent")
    teams = list(original_teams)
    teams[managed_side] = selected
    return tuple(teams), managed_side, opponent


def _snapshot(qm: QuickMatch, start: int) -> dict:
    """[designed] Copy cumulative fields before the next half mutates them."""
    return {
        "score": tuple(qm.score),
        "goals": [dict(goal) for goal in qm.goals[start:]],
        "seed_DS7B62": qm.rng.seed,
        "seed_DS8336": qm.seed2,
        "draws": qm.rng.draws,
    }


def run_full_match(template, game_state, *, retain_state: bool = False) -> dict:
    """Run an assumed full friendly from a normal friendly template.

    [confirmed: E010 notes, "Match clock & loop" at 1b694ed] D733 receives
    minute 0..45 then 46..91, with countdown 91-minute; 998C uses the first
    kick-off side and 9A32 the opposite side. [designed: T26] We keep one
    QuickMatch instance so
    its RNG, score, goals, and mutable player/pitch/country state continue.
    [designed: T32] `retain_state=True` commits the final RNG words and
    engine-mutated player records to `game_state` after both halves finish.
    The default preserves the prior stateless API.
    """
    # [designed: T29] Resolve through the same rule the preview displays.
    teams, managed_side, opponent = resolve_full_matchup(template, game_state)
    qm = QuickMatch(template)  # Preserves the vendored extra-time refusal.
    qm.teams[:] = teams
    selected = game_state.managed_country
    opponent_side = 1 - managed_side

    # [designed: T26] The selected eleven and top-ability computer eleven
    # replace the inherited half-time pitch; remaining squad members stay
    # available for substitution. Keep the template's player energy.
    selected_squad = list(game_state.managed_squad)
    eleven = list(game_state.starting_eleven or selected_squad[:11])
    if len(selected_squad) != 20 or len(eleven) != 11 or len(set(eleven)) != 11:
        raise ValueError("friendly needs a 20-player squad and distinct eleven")
    if not set(eleven).issubset(selected_squad):
        raise ValueError("starting eleven must be in the managed squad")
    own_country = qm._country(selected)
    own_country["squad"] = eleven + [p for p in selected_squad if p not in eleven]
    own_country["tactics"] = game_state.country_tactics & 0xFF
    # [confirmed: E010 notes, "Match clock & loop" at 1b694ed; vendored
    # QuickMatch at 8760df9, 1771:0B77] A byte above 0x80 marks the
    # human side for the quick engine's automatic tactics/subs gates.
    # [designed] 0xFF is our marker when the chosen country came from a
    # template where it was a computer country.
    if own_country["managed"] <= 0x80:
        own_country["managed"] = 0xFF
    opponent_country = qm._country(opponent)
    computer_eleven = pick_computer_eleven(game_state.players, opponent_country["squad"])
    opponent_country["squad"] = computer_eleven + [
        p for p in opponent_country["squad"] if p not in computer_eleven
    ]
    opponent_country["tactics"] = get_computer_tactics(game_state.countries[opponent])
    if opponent_country["managed"] > 0x80:
        opponent_country["managed"] = opponent
    for side, lineup in ((managed_side, eleven), (opponent_side, computer_eleven)):
        for index, player in enumerate(lineup, 1):
            slot = qm.side_base[side] + index
            qm.pitch[slot]["slot_no"] = slot
            qm.pitch[slot]["player"] = player
            qm._player(player)

    # [designed: T26 friendly setup] These are match-initial fields. The
    # original setup also changes other fields and half-time energy; those
    # unmodelled steps are not inferred from a half-time template.
    qm.score = [0, 0]
    qm.goals = []
    qm.sub_budget = [5, 5]
    qm.once_8332 = [0, 0]
    qm.once_8334 = [0, 0]
    qm.eight30b = (qm.side_base[qm.eight31a] + 10) & 0xFF
    first_kickoff = qm.eight30b

    for minute in range(46):
        qm.d733(minute, 91 - minute)
    first = _snapshot(qm, 0)

    # [confirmed: E010 notes, "Match clock & loop", 9A32 at 1b694ed]
    # The second-half kick-off uses the inverted first-half side.
    # There is no RNG reset or new QuickMatch.
    qm.eight30b = (qm.side_base[1 - qm.eight31a] + 10) & 0xFF
    second_kickoff = qm.eight30b
    for minute in range(46, 92):
        qm.d733(minute, 91 - minute)
    second = _snapshot(qm, len(first["goals"]))
    result = {
        "score": second["score"],
        "goals": first["goals"] + second["goals"],
        "seed_DS7B62": second["seed_DS7B62"],
        "seed_DS8336": second["seed_DS8336"],
        "draws": second["draws"],
        "halves": (first, second),
        "teams": tuple(qm.teams),
        "managed_side": managed_side,
        "kickoffs": (first_kickoff, second_kickoff),
    }
    if retain_state:
        # Prepare a complete candidate before changing GameState, so engine
        # refusals and any failure above leave retained state untouched.
        players = list(game_state.players)
        for number, record in qm.playerrec.items():
            players[number] = bytes(record)
        retained_result = {
            "score": tuple(result["score"]),
            "goals": [dict(goal) for goal in result["goals"]],
            "teams": tuple(result["teams"]),
            "seed_DS7B62": result["seed_DS7B62"],
            "seed_DS8336": result["seed_DS8336"],
            "draws": result["draws"],
            "halves": tuple({
                "score": tuple(half["score"]),
                "goals": [dict(goal) for goal in half["goals"]],
                "seed_DS7B62": half["seed_DS7B62"],
                "seed_DS8336": half["seed_DS8336"],
                "draws": half["draws"],
            } for half in result["halves"]),
        }
        game_state.players = players
        game_state.rng_seed_7b62 = result["seed_DS7B62"]
        game_state.rng_seed_8336 = result["seed_DS8336"]
        game_state.match_count = getattr(game_state, "match_count", 0) + 1
        game_state.last_match = retained_result
    return result
