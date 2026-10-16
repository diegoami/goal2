"""[derived: F019/F020, archaeology0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
Campaign quick-runner confidence and the transient team-panel aggregate.

[designed: T43] Integrate current squads and actual quick scorer events only.
National-pool callers and competitive event production remain later tasks;
current B27F status belongs to eligibility.py. No full
original fixture-tail RNG parity or synthetic incident sequence is claimed.
"""
from goal2.engine import confidence, morale


def result_deltas(countries, teams, scores, kind, kind_set):
    """[derived: F019, B71C/1771:10E7/5A03] Country ranks and actual kind bit."""
    if not 0 <= kind <= 255 or kind // 8 >= len(kind_set):
        raise ValueError('missing fixture-kind membership byte')
    ratings = [confidence.country_rating(countries[c][0x2C], countries[c][0x2A],
                                         countries[c][0x2B]) for c in teams]
    winner = 2 if scores[0] == scores[1] else int(scores[1] > scores[0])
    special = bool(kind_set[kind // 8] & (1 << (kind % 8)))
    return tuple(confidence.result_delta(ratings[side], ratings[1-side], scores,
                                        winner, side, special) for side in (0, 1))


def participant(record, delta, role, rng):
    """[derived: F019, B7FA] Result clip then optional bounded bench delta."""
    if len(record) != 20:
        raise ValueError('confidence needs a 20-byte player record')
    draws = None if role == 'starter' else (rng.rand(2 if role == 'substitute' else 4), rng.rand(2))
    out = bytearray(record)
    out[12], = confidence.participant_values(record[12], delta, role, draws)
    return bytes(out)


def begin(qm):
    """[derived: F019/F020, F1F6/6443/7CC5] Capture scorer writes in event order.

    [designed: T43] Wrap the existing quick scorer method without editing the
    vendored engine. Team reactions remain live during play, but only flag-one
    scorer writes replace the saved shadow. No unobserved incident is invented.
    """
    if hasattr(qm, '_campaign_confidence_shadow'):
        raise ValueError('campaign confidence already initialized')
    shadow = {w: qm._player(w)[12] for side in (0, 1) for w in qm._squad(side) if w}
    original = qm.record_goal_scorer_effects
    def scorer(word):
        original(word)
        if word not in shadow:
            raise ValueError('campaign scorer is outside match squads')
        # [derived: 7CC5] Saved value uses signed new live C, capped only above.
        live = qm._player(word)[12]
        shadow[word] = min(32, live - 256 if live >= 128 else live) & 255
    qm._campaign_confidence_shadow = shadow
    qm.record_goal_scorer_effects = scorer


def restore(qm):
    """[derived: F019, CB7D] Remove transient reactions before fixture updates."""
    for word, value in qm._campaign_confidence_shadow.items():
        qm._player(word)[12] = value


def team_morale(players, eleven):
    """[derived: F020, 1771:13D0/3216] Available confirmed XI, fixed divisor11.

    [derived: 214B:0C57] Availability elements8/6/3 mean masks80/20/04;
    energy is a signed byte. Element5 booking alone is not this predicate.
    """
    if len(eleven) != 11 or len(set(eleven)) != 11:
        raise ValueError('team morale needs eleven distinct starters')
    values = []
    for word in eleven:
        if not 1 <= word < len(players) or len(players[word]) != 20:
            raise ValueError('team morale needs valid player records')
        r = players[word]
        if 0 < r[14] < 128 and not r[16] & 0xA4:
            values.append(r[12])
    return morale.team_panel_morale(values)
