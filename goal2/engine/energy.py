"""Q015 instruction-path model, using player words rather than player names.

These routines accept complete 20-byte player records. Recovery consumes the
ordered results of 214B:06B1/06D0, not a guessed average recovery. The cap table
is supplied from DS:0E84. Callers must supply the actual engine activity counter
and draw transcript; this module does not simulate movement, substitutions or
the RNG consumers that precede recovery.

Listing basis: E017 notes, 0791:8C35–8C5D, DA8D–DAC1, CBFC–CC14,
1771:366E–3774. +0xC changes other than CBFC belong to Q016/Q017.
"""

RECORD_SIZE = 20  # player stride, 0791:DAA3
FORM, FITNESS, ENERGY = 12, 13, 14  # 0791:CBFC, CC0D, CC14
QUICK_PERIOD = 5  # 0791:DA92
ACTIVITY_THRESHOLD = 180  # 0791:8C3F, unsigned strict greater
DECREMENT = 1  # 0791:8C54 / DAC1
FLOOR = 1  # signed gate, 0791:8C4A / DAB7; recovery clamp 1771:36E0
REST_THRESHOLD = 16  # 1771:36D7
REST_BONUS = 1  # 1771:36DD
AGE_MARGIN = 3  # 1771:36F6
SMALL_DRAW = 2  # 1771:3680,36A3,36C8
LARGE_DRAW = 8  # 1771:368A,36AD
REST_DRAW = 3  # 1771:36BE
HEAL_DRAW = 3  # 1771:375D
FORM_MAX = 255  # 0791:7CFA; existing F012 instruction, not a morale-outcome rule


def signed(value):
    return value if value < 128 else value - 256


def _record(record):
    if len(record) != RECORD_SIZE:
        raise ValueError('a player record must be 20 bytes')
    return bytearray(record)


def quick_tick(record, minute):
    """One DA8D slot visit; preserves +0xC/+0xD and all other bytes."""
    out = _record(record)
    if minute % QUICK_PERIOD == 0 and signed(out[ENERGY]) > FLOOR:
        out[ENERGY] -= DECREMENT
    return bytes(out)


def watched_step(record, counter, enabled):
    """8C35 tail, after the activity increment and intervening engine calls."""
    out = _record(record)
    if not 0 <= counter <= 65535:
        raise ValueError('activity counter must be an unsigned word')
    if enabled and counter > ACTIVITY_THRESHOLD:
        if signed(out[ENERGY]) > FLOOR:
            out[ENERGY] -= DECREMENT
        counter = 0
    return bytes(out), counter


def restore(record, match_form):
    """CB7D's per-player post-match copy; no invented full-energy refill."""
    out = _record(record)
    out[FORM] = match_form
    if signed(out[ENERGY]) > 0:
        out[ENERGY] = out[FITNESS]
    return bytes(out)


def form_delta(record, delta):
    """The already-established F012 7CC5 store, for whole-half byte accounting."""
    out = _record(record)
    value = (signed(out[FORM]) + delta) & 65535
    if value >= 32768:
        value -= 65536
    out[FORM] = min(FORM_MAX, max(FLOOR, value))
    return bytes(out)


def injure(record):
    """7D9B's store only; does not model or infer injury causes."""
    out = _record(record)
    out[ENERGY] = 0
    return bytes(out)


def recover(record, flag, draws, caps):
    """1771:3651, draws in guest call order; rejects missing/extra draws.

    For 06D0 the transcript supplies its underlying 1..3 draw, whose value 1
    makes the returned boolean true. caps is the two bytes at DS:0E84/0E85.
    """
    out = _record(record)
    draws = iter(draws)

    def draw(bound):
        try:
            value = next(draws)
        except StopIteration as exc:
            raise ValueError('missing recovery draw') from exc
        if not 1 <= value <= bound:
            raise ValueError(f'draw {value} outside 1..{bound}')
        return value

    value = signed(out[FITNESS])
    if out[ENERGY] == 0:
        value += draw(SMALL_DRAW) - draw(LARGE_DRAW)
    elif flag:
        first = draw(SMALL_DRAW)
        value += draw(LARGE_DRAW) - first
    else:
        first = draw(REST_DRAW)
        value += draw(SMALL_DRAW) - first
        if value < REST_THRESHOLD:
            value += REST_BONUS
    if value < FLOOR:
        value = FLOOR
    else:
        cap = caps[out[1] > out[2] + AGE_MARGIN]
        value = min(value, cap)
    out[FITNESS] = value
    if signed(out[ENERGY]) > 0 or draw(HEAL_DRAW) == 1:
        out[ENERGY] = out[FITNESS]
    if next(draws, None) is not None:
        raise ValueError('unused recovery draw')
    return bytes(out)
