"""T236/#826: explicit selected-bench validation, never legacy profile widening."""
from dataclasses import dataclass
import re

from goal2.game import extended_squad
from goal2.game.watched_schema import (
    RESULT_KEYS, KIT2_KEYS, FRIENDLY_BUDGETS, ENGINE_ID, PORT_ENGINE_ID,
    integer, pair, _details, _competitive_kit2, validate_result,
    validate_player_records, validate_substitution_decision,
)

PROFILE = 'selected-bench:1'


@dataclass(frozen=True)
class ExtendedSelection:
    first: int
    second: int
    managed: int
    index: int
    kind: int
    capacity: int
    image_sha256: str
    core: tuple
    opponent: tuple
    extras: tuple
    before: tuple

    def __post_init__(self):
        if (not all(integer(v,1,128) for v in (self.first,self.second,self.managed))
                or self.first==self.second or self.managed not in (self.first,self.second)
                or not integer(self.index,1,2400) or type(self.kind) is not int
                or self.kind not in (1,2,3,5,6,7,8,101,102,103,200,201,202,203)
                or type(self.capacity) is not int or self.capacity not in (22,24)
                or type(self.image_sha256) is not str
                or re.fullmatch('[0-9a-f]{64}',self.image_sha256) is None):
            raise ValueError('invalid extended selection identity')
        for words,count in ((self.core,20),(self.opponent,20)):
            if (type(words) is not tuple or len(words)!=count
                    or any(not integer(w,1,3060) for w in words) or len(set(words))!=count):
                raise ValueError('invalid extended native twenty')
        if (type(self.extras) is not tuple or len(self.extras)>self.capacity-20
                or any(not integer(w,1,3060) for w in self.extras)
                or len(set(self.core+self.opponent+self.extras))!=40+len(self.extras)):
            raise ValueError('invalid extended selected membership')
        expected={w:self.side for w in self.core}|{w:1-self.side for w in self.opponent}
        if type(self.before) is not tuple or len(self.before)!=40:
            raise ValueError('invalid initial physical consequence snapshot')
        seen=set()
        for row in self.before:
            if (type(row) is not tuple or len(row)!=3 or not integer(row[0],1,3060)
                    or row[0] in seen or row[0] not in expected
                    or not integer(row[1],0,1) or row[1]!=expected[row[0]]
                    or type(row[2]) is not bytes or len(row[2])!=3):
                raise ValueError('invalid initial physical consequence snapshot')
            seen.add(row[0])
        if seen!=set(expected):raise ValueError('incomplete initial consequence snapshot')

    @property
    def side(self):return int(self.managed==self.second)

    @property
    def selected(self):return self.core+self.extras

    @classmethod
    def from_prepared(cls,state,fixture,image):
        slots=extended_squad.validate(state)
        if state.squad_capacity==20:raise ValueError('extended selection needs capacity22or24')
        core=tuple(state.starting_eleven)+tuple(w for w in state.managed_squad if w not in state.starting_eleven)
        if tuple(image.squad(state.managed_country))!=core or image.players()!=state.players:
            raise ValueError('prepared selection differs from current canonical records')
        other=fixture.second if state.managed_country==fixture.first else fixture.first
        opponent=tuple(image.squad(other));side=int(state.managed_country==fixture.second)
        if len(opponent)!=20 or any(not integer(w,1,3060) for w in opponent):
            raise ValueError('invalid prepared opponent twenty')
        records=image.players()
        before=tuple((w,team,bytes(records[w][i] for i in (12,14,16)))
                     for team,words in ((side,core),(1-side,opponent)) for w in words)
        return cls(fixture.first,fixture.second,state.managed_country,fixture.index,fixture.kind,
                   state.squad_capacity,image.sha256(),core,opponent,
                   tuple(w for w in slots if w is not None),before)


def _selection(selection):
    if type(selection) is not ExtendedSelection:raise ValueError('bound extended selection required')


def _national(value,native,selection):
    expected=list(native)+[w for w in selection.selected if w not in native]
    if (type(value) is not list or any(not integer(w,1,3060) for w in value)
            or value!=expected or set(native)-set(selection.selected)):
        raise ValueError('extended selected membership or order differs')


@dataclass(frozen=True)
class ExtendedDecision:
    context: str
    eleven: tuple
    bench: tuple
    native: tuple
    national: tuple
    records: tuple
    team_context: tuple
    substitutions_left: int
    tactics: int
    positions: tuple


def validate_extended_decision(data,selection,*,substitution_control=False):
    _selection(selection)
    if type(substitution_control) is not bool or not isinstance(data,dict):
        raise ValueError('invalid extended decision envelope')
    context=data.get('context')
    if context not in ('half_time','substitution','pause','extra_time','shootout_order',
                        'set_piece','substitution_opportunity'):
        raise ValueError('invalid extended watched decision context')
    eleven,bench=data.get('eleven'),data.get('bench')
    if (type(eleven) is not list or len(eleven)!=11 or type(bench) is not list
            or len(bench)!=9+len(selection.extras)
            or any(not integer(w,1,3060) for w in eleven+bench)
            or len(set(eleven+bench))!=20+len(selection.extras)
            or set(eleven+bench)!=set(selection.selected)):
        raise ValueError('invalid extended XI/bench membership')
    native=eleven+bench[:9]
    if selection.extras:
        _national(data.get('national_squad'),native,selection)
        if data['national_squad']!=eleven+bench:raise ValueError('extended bench order differs')
    elif 'national_squad' in data:
        raise ValueError('empty extras must keep the normal decision profile')
    # Reuse the unchanged legacy TEAM/card guard on the exact physical twenty.
    # Every selected card is separately validated below; no missing values are fabricated.
    rows=data.get('player_records')
    if type(rows) is not list or len(rows)!=len(eleven+bench):
        raise ValueError('missing complete extended live records')
    for word,row in zip(eleven+bench,rows):
        if (type(row) not in (list,tuple) or len(row)!=2 or not integer(row[0],1,3060)
                or row[0]!=word or type(row[1]) is not str
                or re.fullmatch('[0-9a-f]{40}',row[1]) is None):
            raise ValueError('invalid extended live record order or bytes')
    physical=dict(data,bench=bench[:9],player_records=rows[:20])
    validate_player_records(physical,required=True)
    positions=data.get('positions')
    if (type(positions) is not list or len(positions)!=len(rows)
            or any(type(p) not in (list,tuple) or len(p)!=2
                   or not integer(p[0],1,3060) or p[0]!=row[0]
                   or not integer(p[1],0,255) or p[1]!=bytes.fromhex(row[1])[6]
                   for p,row in zip(positions,rows))
            or not integer(data.get('substitutions_left'),0,255)
            or not integer(data.get('tactics'),0,255)):
        raise ValueError('extended positions/budget/tactics differ from current native data')
    team=data.get('team_context')
    if type(team) is not dict:raise ValueError('missing extended live TEAM context')
    if team['sides']!=[selection.first,selection.second]:
        raise ValueError('extended live TEAM sides differ')
    validate_substitution_decision(data,required=substitution_control)
    frozen_team=(team['match_set_up'],team['in_match_menu_used'],tuple(team['sides']))
    return ExtendedDecision(context,tuple(eleven),tuple(bench),tuple(native),tuple(eleven+bench),
                            tuple((row[0],bytes.fromhex(row[1])) for row in rows),frozen_team,
                            data['substitutions_left'],data['tactics'],tuple(tuple(p) for p in positions))


@dataclass(frozen=True)
class ExtendedResult:
    profile: str
    engine: str
    native: tuple
    national: tuple
    consequence_words: tuple


def _consequences(result,selection,native,opponent):
    before={w:(side,values) for w,side,values in selection.before}
    after={w:selection.side for w in native}|{w:1-selection.side for w in opponent}
    expected=set(before)|set(after);rows=result.get('players')
    if type(rows) is not list or len(rows)!=len(expected):
        raise ValueError('invalid extended physical consequence union')
    seen=set()
    keys={'player','team','confidence','energy','status','suspended','carried_booking','injured'}
    for row in rows:
        if type(row) is not dict or set(row)!=keys:raise ValueError('invalid extended consequence fields')
        w=row['player']
        if (not integer(w,1,3060) or w in seen or w not in expected
                or not integer(row['team'],0,1) or row['team']!=(after[w] if w in after else before[w][0])):
            raise ValueError('invalid extended consequence player/side')
        for i,key in enumerate(('confidence','energy','status')):
            values=row[key]
            if not isinstance(values,(list,tuple)) or len(values)!=2:
                raise ValueError('invalid extended consequence pair')
            b,a=values
            if ((w in before and (not integer(b,0,255) or b!=before[w][1][i]))
                    or (w not in before and b is not None)
                    or (w in after and not integer(a,0,255))
                    or (w not in after and a is not None)):
                raise ValueError('extended consequence presence or prepared bytes differ')
        status=row['status'][1];energy=row['energy'][1]
        flags=(bool(status is not None and status&0x80),bool(status is not None and status&8),energy==0)
        if any(type(row[k]) is not bool or row[k]!=v for k,v in zip(('suspended','carried_booking','injured'),flags)):
            raise ValueError('extended consequence derived flags differ')
        seen.add(w)
    if seen!=expected:raise ValueError('missing extended consequence player')
    return tuple(row['player'] for row in rows)


def validate_extended_result(result,selection,*,competitive=False):
    _selection(selection)
    if type(competitive) is not bool or type(result) is not dict:
        raise ValueError('invalid extended result envelope')
    if (any(not integer(result.get(k),1,128) for k in ('first','second','managed'))
            or not integer(result.get('index'),1,2400) or type(result.get('kind')) is not int):
        raise ValueError('invalid extended result identity types')
    if (result.get('first'),result.get('second'),result.get('managed'),result.get('index'),result.get('kind'))!=(
            selection.first,selection.second,selection.managed,selection.index,selection.kind):
        raise ValueError('extended result fixture differs from prepared selection')
    if result.get('image_sha256')!=selection.image_sha256:
        raise ValueError('extended result differs from prepared image')
    if result.get('kit')!='4':raise ValueError('extended pending selection requires current kit4')
    if not selection.extras:
        engine=validate_result(result,competitive=competitive)
    else:
        keys=RESULT_KEYS|KIT2_KEYS|{'national_squad_after'}
        port='ports' in result
        if port:
            keys=keys|{'ports'};ports=result['ports']
            if (type(ports) is not dict or set(ports)!={'names','calls'}
                    or type(ports['names']) is not list or not ports['names'] or type(ports['calls']) is not dict):
                raise ValueError('invalid extended port record')
        if result.get('kit')!='4' or set(result)!=keys:
            raise ValueError('invalid exact extended kit4 result profile')
        if (not pair(result['score'],0,255) or not pair(result['half_time_score'],0,255)
                or not pair(result['goal_counts'],0,255)
                or any(not integer(result[k],0,65535) for k in ('seed_after','kickoff_seed'))
                or any(not integer(result[k],0,2**31-1) for k in ('ticks','draws'))
                or (result['draws_digest'] is not None and (type(result['draws_digest']) is not str
                    or re.fullmatch('[0-9a-f]{64}',result['draws_digest']) is None))
                or any(type(result[k]) is not list or any(type(r) is not dict for r in result[k])
                       for k in ('goals','goals_disallowed','bookings','sendings_off','injuries','substitutions','commentary','decisions','inputs'))):
            raise ValueError('invalid extended scores/RNG/transcript')
        if competitive:_competitive_kit2(result)
        else:
            score=result['score'];winner=2 if score[0]==score[1] else int(score[1]>score[0])
            if (not integer(result['winner'],0,2) or result['winner']!=winner or selection.kind!=1
                    or result['score_90'] is not None or result['extra_time'] is not False
                    or result['shootout'] is not None or result['substitution_budget'] not in FRIENDLY_BUDGETS
                    or any(type(v) is not int for v in result['substitution_budget'])):
                raise ValueError('invalid extended friendly resolution/budget')
        engine=PORT_ENGINE_ID if port else ENGINE_ID
    squads=result.get('squads_after')
    if type(squads) is not dict or set(squads)!={str(selection.first),str(selection.second)}:
        raise ValueError('invalid extended physical squad endpoints')
    for words in squads.values():
        if (type(words) is not list or len(words)!=20 or any(not integer(w,1,3060) for w in words)
                or len(set(words))!=20):raise ValueError('invalid extended physical twenty')
    native=squads[str(selection.managed)]
    other=selection.second if selection.managed==selection.first else selection.first
    opponent=squads[str(other)]
    if set(opponent)!=set(selection.opponent) or set(native)-set(selection.selected):
        raise ValueError('extended physical membership differs')
    if selection.extras:_national(result.get('national_squad_after'),native,selection)
    _details(result,competitive=competitive)
    words=_consequences(result,selection,native,opponent)
    national=tuple(native)+tuple(w for w in selection.selected if w not in native)
    return ExtendedResult(PROFILE,engine,tuple(native),national,words)
