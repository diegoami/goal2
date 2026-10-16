"""[derived: F027 sections2/6/7/9, archaeology0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
Availability and B27F for current quick campaign squads.

[designed: T44] Existing player bytes carry all state. No calendar-day counter,
new injury event producer or duplicate transition over original watched results.
"""

def reasons(record):
    """[derived: 1771:3216/214B:0C57] Signed energy; elements8/6/3."""
    if len(record) != 20:
        raise ValueError('availability needs a 20-byte player record')
    out = []
    if record[14] == 0:
        out.append('Injured')
    elif record[14] >= 128:
        out.append('Unavailable energy')
    for mask, label in ((0x80, 'Suspended'), (0x20, 'Sent off'), (0x04, 'Substituted off')):
        if record[16] & mask:
            out.append(label)
    return tuple(out)


def info(record):
    """[designed: T44] Explain current record availability in campaign views."""
    why = reasons(record)
    return {'available': not why, 'reasons': list(why),
            'carried_bookings': int(bool(record[16] & 0x08)),
            'ban_fixtures': int(bool(record[16] & 0x80))}


def available_words(players, squad):
    """[derived: 3216; designed: T44] Preserve order while filtering eligibility."""
    return [word for word in squad if not reasons(players[word])]


def require_available(players, eleven):
    """[designed: T44] Refuse kickoff/confirmation and retain human repair."""
    failures = [f'{word}: {", ".join(reasons(players[word]))}' for word in eleven if reasons(players[word])]
    if failures:
        raise ValueError('unavailable starters: ' + '; '.join(failures))


def validate_teams(state, teams, managed_side):
    """[designed: T44] Gate both preview and the actual quick campaign runner."""
    own = list(state.starting_eleven or state.managed_squad[:11])
    require_available(state.players, own)
    opponent = teams[1 - managed_side]
    country = state.countries[opponent]
    squad = [int.from_bytes(country[i:i+2], 'little') for i in range(0, 40, 2)]
    if len(available_words(state.players, squad)) < 11:
        raise ValueError('opponent has fewer than eleven available players')


def after_fixture(record, kind):
    """[derived: F027/B27F/B7FA] Serve old ban, then red/two-booking transition.

    Kind0 never plays through B7FA; no ban is served. Elements3 and7 and
    unrelated bytes pass through. Injury recovery belongs to the energy adapter.
    """
    if len(record) != 20 or not 0 <= kind <= 255:
        raise ValueError('invalid discipline record or fixture kind')
    if kind == 0:
        return bytes(record)
    out = bytearray(record)
    status = out[16] & ~0x80
    if status & 0x20:
        status |= 0x80
    status &= ~0x20
    if status & 0x10:
        if status & 0x08:
            status = (status | 0x80) & ~0x08
        else:
            status |= 0x08
    out[16] = status & ~0x10
    return bytes(out)


def finish(qm, state):
    """[derived: B9FA; designed: T44] Complete each current squad word once.

    B27F consumes no draws and touches only this player's status; applying it
    after all energy/confidence calls commutes with other players' operations.
    Original national-pool callers remain T45. Candidate publication is atomic.
    """
    if getattr(qm, '_campaign_eligibility_complete', False):
        raise ValueError('campaign eligibility was already applied')
    fixture = state.campaign.next_fixture
    words = [w for side in (0, 1) for w in qm._squad(side) if w]
    updated = {word: bytearray(after_fixture(qm._player(word), fixture.kind)) for word in words}
    qm.playerrec.update(updated)
    qm._campaign_eligibility_complete = True
    return {'fixture_id': fixture.fixture_id, 'kind': fixture.kind}
