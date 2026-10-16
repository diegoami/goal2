"""[derived: F018/F007/F027 at 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
Campaign quick-match energy boundaries. The vendored model owns 3651.

[designed: T42] This adapter orders energy operations. T43 optionally interleaves confidence; pool
and current status callers are integrated separately; no whole original fixture-tail RNG
parity is claimed. It is called by the quick runner, never on watched results.
"""
from goal2.engine import energy


def _record(record):
    if len(record) != 20:
        raise ValueError('energy needs a 20-byte player record')
    return bytearray(record)


def half_bonus(record):
    """[derived: F018, 0791:9A32] Add two only to energy 1..30."""
    out = _record(record)
    if 1 <= out[14] <= 30:
        out[14] += 2
    return bytes(out)


def restore_energy(record):
    """[derived: F018, CB7D] Copy fitness to signed-positive energy.

    [designed: T42] Preserve current form: original shadow-form restoration
    and confidence integration are not implemented by this energy-only task.
    """
    return energy.restore(record, record[12])


def recover_player(record, flag, rng, *, gradual, managed, caps, redraw_bases):
    """[derived: F018/F007] Consume 3651 or 3558 draws in call order."""
    out = _record(record)
    def draw(bound):
        value = rng.rand(bound)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= bound:
            raise ValueError('invalid recovery RNG output')
        return value
    if gradual:
        if out[14] == 0:
            draws = [draw(2), draw(8)]
        elif flag:
            draws = [draw(2), draw(8)]
        else:
            draws = [draw(3), draw(2)]
        if energy.signed(out[14]) <= 0:
            draws.append(draw(3))
        return energy.recover(out, flag, draws, caps)
    # [derived: F007/F018, 1771:3558] Copy to E precedes D's lower clamp.
    base = redraw_bases[out[1] > out[2] + 4]
    if managed:
        first = draw(base + 1)
        value = base + draw(3 * base) - first
    else:
        value = base + draw(2 * base)
    value &= 255
    if energy.signed(value) > 32:
        value = 32
    out[13] = out[14] = value
    if energy.signed(out[13]) < 1:
        out[13] = 1
    return bytes(out)


def ensure_pending(state):
    """[designed: T42] One energy transition per pending campaign fixture."""
    if state.campaign is None or state.campaign.next_fixture is None:
        raise ValueError('energy transition requires a pending campaign fixture')
    fixture = state.campaign.next_fixture
    prior = state.match_state.get('campaign_energy', {})
    if prior.get('fixture_id') == fixture.fixture_id:
        raise ValueError('campaign energy was already applied to this fixture')
    if fixture.kind != 1:
        raise ValueError('campaign energy supports friendly fixtures only')
    return fixture


def half_time(qm):
    """[derived: F018, 9A32] Visit the current pitch, not the unused bench."""
    for slot in range(1, 23):
        player = qm.pitch[slot]['player']
        qm.playerrec[player] = bytearray(half_bonus(qm._player(player)))


def finish(qm, state, *, with_confidence=False):
    """[designed: T42] Restore then recover this quick campaign candidate once.

    [derived: F018/F027, B7FA/5A8F] Side A then B, nonzero squad words in
    slot order; XI or status-set element 3 (mask 0x04) participants use flag 1, unused bench 0.
    Default energy-only calls exclude confidence; campaign quick calls interleave
    T43 confidence. T45 applies the disjoint reserve prefix before this current-squad tail.
    """
    fixture = ensure_pending(state)
    if tuple(qm.teams) != (fixture.side_a, fixture.side_b):
        raise ValueError('energy teams differ from the pending fixture')
    if getattr(qm, '_campaign_energy_complete', False):
        raise ValueError('campaign energy was already applied to this simulation')
    squads = [list(qm._squad(side)) for side in (0, 1)]
    words = [word for squad in squads for word in squad if word]
    if len(words) != len(set(words)) or any(not 1 <= word < len(state.players) for word in words):
        raise ValueError('campaign energy requires distinct valid squad words')
    pool_transition = None
    if with_confidence:
        from goal2.game import campaign_pool
        pool_transition = campaign_pool.finish(qm, state)
        from goal2.game import campaign_confidence
        campaign_confidence.restore(qm)
        deltas = campaign_confidence.result_deltas(
            state.countries, qm.teams, qm.score, fixture.kind, qm.state.ds_bytes(0x0F3E, 32))
    for word in words:
        qm.playerrec[word] = bytearray(restore_energy(qm._player(word)))
    bases = tuple(qm.state.ds_bytes(0x0E82, 2))
    caps = tuple(qm.state.ds_bytes(0x0E84, 2))
    in_set = bool(qm.state.ds_bytes(0x0F3E, 1)[0] & (1 << fixture.kind))
    host_continent = state.countries[fixture.side_b][0x2C]
    recovery_draws = confidence_draws = 0
    for side, squad in enumerate(squads):
        country = qm.teams[side]
        gradual = in_set or (state.countries[country][0x2C] != host_continent)
        for slot, word in enumerate(squad, 1):
            if not word:
                continue
            record = qm._player(word)
            flag = slot <= 11 or bool(record[0x10] & 0x04)
            role = 'starter' if slot <= 11 else ('substitute' if flag else 'unused')
            # [derived: F019/F018, B7FA] Unused bench changes C before recovery;
            # participants recover first, then result C and used-bench noise.
            def update_confidence(record):
                nonlocal confidence_draws
                before = qm.rng.draws
                record = campaign_confidence.participant(record, deltas[side], role, qm.rng)
                confidence_draws += qm.rng.draws - before
                return record
            if with_confidence and not flag:
                record = update_confidence(record)
            before = qm.rng.draws
            record = recover_player(record, flag, qm.rng, gradual=gradual,
                                    managed=record[0] == state.managed_country,
                                    caps=caps, redraw_bases=bases)
            recovery_draws += qm.rng.draws - before
            if with_confidence and flag:
                record = bytearray(update_confidence(record))
                if slot > 11:
                    # [derived: B957..B964] Consume the used-bench element3.
                    record[16] &= ~0x04
            qm.playerrec[word] = bytearray(record)
    qm._campaign_energy_complete = True
    return {'fixture_id': fixture.fixture_id, 'engine': 'quick-energy-v1',
            'recovery_draws': recovery_draws, 'confidence_draws': confidence_draws, **({'pool': pool_transition} if pool_transition is not None else {})}
