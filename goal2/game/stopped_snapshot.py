"""[designed: T170ae/#818] Verified current read, never campaign publication.

[confirmed: archaeology87d92501, Match._decide/records_after; F008/F010/F037]
The stopped Match owns its current records, flags, budgets and prompt domains.
Reading them grants no edit permission. The owner must bind the expected
request and decision to its existing lease, and explicitly answer separately.
"""
from dataclasses import dataclass, field
import json
from zlib import error as ZlibError

from goal2.engine.original_match.image import Image
from goal2.engine.original_match import screens as S
from goal2.game import engine_tables
from goal2.game.prematch_view import _words
from goal2.game.season import canonical_hash


CONTEXTS=frozenset(('pause','half_time','extra_time','substitution',
                    'substitution_opportunity','set_piece','shootout_order','post_match'))


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')


@dataclass(frozen=True)
class StoppedMatchSnapshot:
    request: int
    decision: int
    managed_country: int
    context: str
    state_hash: str
    data_hash: str
    _state: bytes=field(repr=False)
    _data: bytes=field(repr=False)

    @property
    def state(self):return json.loads(self._state)

    @property
    def data(self):return json.loads(self._data)

    @classmethod
    def from_packet(cls,packet,*,request,decision,managed_country,data):
        """Verify against the caller's waiting operation and original decision."""
        if (type(request) is not int or request<1 or type(decision) is not int or decision<1
                or type(managed_country) is not int or not 1<=managed_country<129
                or not isinstance(data,dict) or type(data.get('context')) is not str
                or data['context'] not in CONTEXTS):
            raise ValueError('invalid expected stopped-match identity')
        if (not isinstance(packet,dict) or set(packet)!={'request','action','preview','state','data'}
                or type(packet['request']) is not int or packet['request']!=request
                or packet['action']!='stopped_preview'):
            raise ValueError('invalid stopped-match reply')
        meta=packet['preview'];native=packet['state'];current=packet['data']
        if (not isinstance(meta,dict)
                or set(meta)!={'schema','decision','managed_country','state_hash','data_hash'}
                or meta['schema']!='goal2/stopped-preview/1'
                or type(meta['decision']) is not int or meta['decision']!=decision
                or type(meta['managed_country']) is not int or meta['managed_country']!=managed_country
                or not isinstance(native,dict) or native.get('schema')!='original_match.state/2'
                or not isinstance(current,dict) or meta['state_hash']!=canonical_hash(native)
                or meta['data_hash']!=canonical_hash(current)
                or meta['data_hash']!=canonical_hash(data)):
            raise ValueError('stopped-match identity/hash mismatch')
        try:
            image=Image.from_state(native,engine_tables.load())
            players=tuple(image.players());countries=tuple(image.countries())
            squad=_words(current.get('eleven'),11,zero=True)+_words(current.get('bench'),9,zero=True)
            _words(list(squad),20,zero=True)
            sides=(image.rd(0x9B34),image.rd(0x9B36))
            if (any(len(p)!=20 for p in players) or any(len(c)!=191 for c in countries)
                    or sides[0]==sides[1] or any(not 1<=c<129 for c in sides)
                    or managed_country not in sides or tuple(image.squad(managed_country))!=squad):
                raise ValueError('invalid stopped native records/roster/sides')
            _words(image.squad(sides[1-sides.index(managed_country)]),20,zero=True)
            expected=dict(positions=[[w,players[w][6]] for w in squad if w],
                player_records=[[w,players[w].hex()] for w in squad if w],
                tactics=countries[managed_country][0x2D],
                substitutions_left=image.rd(S.SUBS_LEFT+sides.index(managed_country),1),
                team_context=dict(match_set_up=image.rd(0xC1E,1),in_match_menu_used=image.rd(0xC1F,1),
                                  sides=list(sides)))
            # Canonical comparison distinguishes bool from int in every nested field.
            if any(k not in current or canonical_hash(current[k])!=canonical_hash(v) for k,v in expected.items()):
                raise ValueError('stopped decision differs from native records/context/budget')
            for name,offset in (('substitutions_now',S.SUBS_ALLOWED),('request_substitution',S.SUBS_REQUEST)):
                if name in current and (type(current[name]) is not bool or current[name]!=bool(image.rd(offset,1))):
                    raise ValueError('stopped decision differs from native substitution flags')
            if current['context'] == 'substitution_opportunity':
                from goal2.game.native_choice import opportunity_duration
                opportunity_duration(current)
                if type(current.get('substitutions_now')) is not bool:
                    raise ValueError('stopped opportunity lacks native substitution status')
            if current['context'] in ('set_piece','shootout_order'):
                available=[w for w in squad[:11] if w and 0<players[w][14]<128 and not players[w][16]&0xA4]
                if canonical_hash(current.get('available'))!=canonical_hash(available):
                    raise ValueError('stopped prompt domain differs from native availability')
                if current['context']=='set_piece':
                    if type(current.get('role')) is not int or current['role'] not in (2,3,4,5):
                        raise ValueError('invalid stopped taker role')
                elif type(current.get('takers')) is not int or not 0<=current['takers']<=len(available):
                    raise ValueError('invalid stopped shoot-out count')
            state_json,data_json=_json(native),_json(current)
        except (KeyError,TypeError,IndexError,ValueError,OverflowError,ZlibError) as exc:
            raise ValueError('invalid current stopped-match snapshot') from exc
        return cls(request,decision,managed_country,current['context'],meta['state_hash'],meta['data_hash'],
                   state_json,data_json)
