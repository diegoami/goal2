"""Q016 result-relative player confidence, transcribed from GOAL.EXE.

Listing: 0791:B71C/B364/B7FA (E018 notes). This module models the
post-fixture operations, not temporary in-match morale, injuries, cards,
or the separate effect of arranging a friendly. Callers must preserve
operation order (pool, result, bench draw, and silent-route scorer bonuses).
"""

BYTE_BITS = 8
WORD_BITS = 16
LOWER = 1
UPPER = 32
EXPECTED_DIVISOR = 32
CONTINENT_BASE = 5
CONTINENT_RANK_BASE = 33
WORLD_RANK_BASE = 129
RATING_DIVISOR = 2
DOUBLE = 2
SMALL_DRAW = 2
UNUSED_DRAW = 4
LIVE_UPPER = 255


def _signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _idiv(numerator, denominator):
    return (abs(numerator) // denominator) * (-1 if numerator < 0 else 1)


def change(before, delta):
    """0791:B364: signed byte plus signed word, then clip each call."""
    total = _signed(_signed(before, BYTE_BITS) + _signed(delta, WORD_BITS), WORD_BITS)
    return min(UPPER, max(LOWER, total))


def country_rating(continent, continent_rank, world_rank):
    """1771:10E7, country +2C/+2A/+2B (seg_1771_02.asm:697–738)."""
    numerator = _signed((CONTINENT_BASE - continent) * (CONTINENT_RANK_BASE - continent_rank) + WORLD_RANK_BASE - world_rank, WORD_BITS)
    return _idiv(numerator, RATING_DIVISOR)


def match_form(live, saved, delta, persist):
    """0791:7CC5: transient byte plus optional DS:9B07 snapshot update."""
    total = _signed(_signed(live, BYTE_BITS) + _signed(delta, WORD_BITS), WORD_BITS)
    live = min(LIVE_UPPER, max(LOWER, total))
    if persist:
        saved = min(UPPER, _signed(live, BYTE_BITS)) & 255
    return live, saved


def result_delta(own_rating, opponent_rating, scores, winner, side, special_kind):
    """0791:B71C; special_kind is the *observed* 1771:5A03 result.

    Ratings are the 1771:10E7 outputs, not line-strength sums. The winner
    byte controls draws and wins, including the shoot-out's winner byte.
    """
    if side not in (0, 1) or winner not in (0, 1, 2) or len(scores) != 2:
        raise ValueError('invalid fixture')
    delta = _idiv(_signed(opponent_rating - own_rating, WORD_BITS), EXPECTED_DIVISOR)
    if winner != 2:
        margin = abs(_signed(scores[1], BYTE_BITS) - _signed(scores[0], BYTE_BITS))
        delta = _signed(delta + (margin if winner == side else -margin), WORD_BITS)
        if (winner == side) == (side == 0 or bool(special_kind)):
            delta = _signed(delta * DOUBLE, WORD_BITS)
    return delta


def participant_values(before, delta, role, draws=None):
    """B7FA exact possible bytes, or singleton with literal bounded draws.

    Draws are in execution order: subtracted draw, then added draw.
    Random draws consumed by fitness/energy are not represented here.
    """
    if role == 'starter':
        if draws is not None:
            raise ValueError('starter has no bench-confidence draws')
        return (change(before, delta),)
    if role not in ('substitute', 'unused'):
        raise ValueError('unknown participation role')
    bound = SMALL_DRAW if role == 'substitute' else UNUSED_DRAW
    base = change(before, delta) if role == 'substitute' else before
    if draws is None:
        pairs = ((a, b) for a in range(1, bound + 1) for b in range(1, SMALL_DRAW + 1))
    else:
        if len(draws) != 2 or not 1 <= draws[0] <= bound or not 1 <= draws[1] <= SMALL_DRAW:
            raise ValueError('invalid bench-confidence draws')
        pairs = (draws,)
    return tuple(sorted({change(base, b - a) for a, b in pairs}))
