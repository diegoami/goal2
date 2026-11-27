"""[designed: owner2026-11-18, #777/T231] Optional22-player squad metadata.

[designed: owner, 2026-11-27, #862/T240] Twenty-four places are withdrawn: 22 is the largest. A save
that says capacity 24 is read as 22 (see `from_data`), so no career is refused.

The original recommended twenty remains authoritative. Extra choices balance
outfield lines using supplied original-strength scores, never a new rating.
Match eligibility/wiring is a separate native-engine capability.
"""
from copy import deepcopy

CAPACITIES=(20,22)


def validate(state):
    capacity=getattr(state,'squad_capacity',20)
    slots=getattr(state,'extra_squad',[])
    if type(capacity) is not int or capacity not in CAPACITIES:
        raise ValueError('squad capacity must be20or22')
    if not isinstance(slots,list) or len(slots)!=capacity-20:
        raise ValueError('extra squad places differ from capacity')
    filled=[w for w in slots if w is not None]
    if (any(type(w) is not int or not 1<=w<=3060 for w in filled)
            or len(set(filled))!=len(filled)
            or set(filled)&set(state.managed_squad)):
        raise ValueError('extra squad words must be distinct and outside the native twenty')
    if filled:
        from goal2.game.campaign_pool import validate as pool_words
        if not set(filled)<=set(pool_words(state)):
            raise ValueError('extra squad players must belong to the current made pool')
    return tuple(slots)


def resized(state,capacity):
    current=validate(state)
    if type(capacity) is not int or capacity not in CAPACITIES:
        raise ValueError('squad capacity must be20or22')
    candidate=deepcopy(state)
    candidate.squad_capacity=capacity
    count=capacity-20
    candidate.extra_squad=list(current[:count])+[None]*max(0,count-len(current))
    validate(candidate)
    return candidate


def squad_slots(state):
    return tuple(state.managed_squad)+validate(state)


def visible_pool(state):
    selected={w for w in validate(state) if w is not None}
    from goal2.game.campaign_pool import validate as pool_words
    return [w for w in pool_words(state) if w not in selected]


def to_data(state):
    slots=validate(state)
    if state.squad_capacity==20:
        return None
    return {'capacity':state.squad_capacity,'players':list(slots)}


def from_data(state,data):
    if not isinstance(data,dict) or set(data)!={'capacity','players'}:
        raise ValueError('extended squad has missing or unknown fields')
    if type(data['capacity']) is not int or data['capacity'] not in (22,24):
        raise ValueError('extended squad data requires22or24places')
    players=data['players']
    if not isinstance(players,list):
        raise ValueError('extended squad players must be a list')
    if data['capacity']==24:
        # [designed: owner, 2026-11-27, #862/T240] Twenty-four places are withdrawn. The career keeps 22:
        # empty places are dropped first, then the last filled ones, and those players fall back to the
        # pool they were recruited from, so nothing is lost and no save is refused.
        players=[w for w in players if w is not None][:2]
        players=players+[None]*(2-len(players))
    candidate=deepcopy(state)
    candidate.squad_capacity=22
    candidate.extra_squad=deepcopy(players)
    validate(candidate)
    return candidate


def balanced_extras(candidates,places):
    """Return2nullable places; line0 keeper,1 defence,2 midfield,3 attack.

    Scores are supplied by original1771:377E; this function only selects a
    balanced additional group. Stable input order breaks equal-score ties.
    """
    if type(places) is not int or places not in (0,2):
        raise ValueError('additional places must be0or2')
    if not isinstance(candidates,(list,tuple)) or len(candidates)>80:
        raise ValueError('additional candidates need the bounded made pool')
    eligible=[];seen=set()
    for index,row in enumerate(candidates):
        if (not isinstance(row,dict) or set(row)!={'id','line','strength','available'}
                or type(row['id']) is not int or not 1<=row['id']<=3060
                or row['id'] in seen or type(row['line']) is not int or not 0<=row['line']<=3
                or type(row['strength']) is not int or not 0<=row['strength']<=256
                or type(row['available']) is not bool):
            raise ValueError('invalid additional candidate')
        seen.add(row['id'])
        if row['line'] and row['available']:
            eligible.append((index,row))
    chosen=[];counts={1:0,2:0,3:0}
    while eligible and len(chosen)<places:
        best=min(eligible,key=lambda pair:(counts[pair[1]['line']],-pair[1]['strength'],pair[0]))
        eligible.remove(best);row=best[1]
        chosen.append(row['id']);counts[row['line']]+=1
    return chosen+[None]*(places-len(chosen))


def _require_recruitment(state,incoming):
    from goal2.game import campaign_pool,eligibility
    pool=campaign_pool.validate(state)
    if type(incoming) is not int or incoming not in pool or incoming in validate(state):
        raise ValueError('Choose an unselected player of the current pool')
    window=campaign_pool.window(state)
    if not window['allowed']:
        raise ValueError(window['reason'])
    eligibility.require_available(state.players,[incoming])


def filled(state,slot,incoming):
    """[designed: T233] Fill a vacant extra place under current recruitment rules."""
    slots=validate(state)
    if type(slot) is not int or not 0<=slot<len(slots) or slots[slot] is not None:
        raise ValueError('Choose an empty additional squad place')
    _require_recruitment(state,incoming)
    candidate=deepcopy(state);candidate.extra_squad[slot]=incoming
    validate(candidate)
    return candidate


def exchanged(state,outgoing,incoming):
    """Outside recruitment; selected extras remain ordinary selected members."""
    slots=validate(state);_require_recruitment(state,incoming)
    if type(outgoing) is not int:
        raise ValueError('Choose a selected squad player')
    candidate=deepcopy(state)
    if outgoing in slots:
        candidate.extra_squad[slots.index(outgoing)]=incoming
    else:
        from goal2.game import campaign_pool
        campaign_pool.exchange(candidate,outgoing,incoming)
    validate(candidate)
    return candidate


def promoted(state,incoming,outgoing):
    """[designed: T233] Swap selected members across the physical20/80 boundary.

    This changes canonical GameState records, never a live engine. Outside
    recruitment rules do not apply to two already-selected squad members.
    """
    from goal2.game import campaign_pool
    slots=validate(state);pool=campaign_pool.validate(state)
    if (type(incoming) is not int or type(outgoing) is not int
            or incoming not in slots or outgoing not in state.managed_squad):
        raise ValueError('Choose a native squad member and selected extra')
    candidate=deepcopy(state)
    candidate.managed_squad=[incoming if w==outgoing else w for w in state.managed_squad]
    candidate.campaign.reserve_ids=[outgoing if w==incoming else w for w in pool]
    candidate.extra_squad[slots.index(incoming)]=outgoing
    candidate.starting_eleven=[incoming if w==outgoing else w for w in state.starting_eleven]
    if candidate.captain==outgoing:candidate.captain=incoming
    country=bytearray(candidate.countries[state.managed_country])
    country[:40]=b''.join(w.to_bytes(2,'little') for w in candidate.managed_squad)
    candidate.countries[state.managed_country]=bytes(country)
    campaign_pool.validate(candidate);validate(candidate)
    return candidate
