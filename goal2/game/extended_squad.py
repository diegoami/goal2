"""[designed: owner2026-11-18, #777/T231] Optional22/24-player squad metadata.

The original recommended twenty remains authoritative. Extra choices balance
outfield lines using supplied original-strength scores, never a new rating.
Match eligibility/wiring is a separate native-engine capability.
"""
from copy import deepcopy

CAPACITIES=(20,22,24)


def validate(state):
    capacity=getattr(state,'squad_capacity',20)
    slots=getattr(state,'extra_squad',[])
    if type(capacity) is not int or capacity not in CAPACITIES:
        raise ValueError('squad capacity must be20,22or24')
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
        raise ValueError('squad capacity must be20,22or24')
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
    candidate=deepcopy(state)
    candidate.squad_capacity=data['capacity']
    candidate.extra_squad=deepcopy(data['players'])
    validate(candidate)
    return candidate


def balanced_extras(candidates,places):
    """Return2/4nullable places; line0 keeper,1 defence,2 midfield,3 attack.

    Scores are supplied by original1771:377E; this function only selects a
    balanced additional group. Stable input order breaks equal-score ties.
    """
    if type(places) is not int or places not in (0,2,4):
        raise ValueError('additional places must be0,2or4')
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
