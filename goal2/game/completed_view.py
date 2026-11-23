"""[designed: T170ag/#828] Current data after actual F1F6 completion.

[confirmed: archaeology a492059d, Match._finish/_on_board/records_after]
The final board is the recorded whistle snapshot; these player records are
current after F1F6 restoration. Neither is an invented post-match decision.
This transient native result is not a historical watched save profile: its
unchanged SDK history includes held pre-match inputs. #829 owns the earlier
interactive post-match menu. No save/schema guard is broadened here.
"""
from dataclasses import dataclass,field
import re
from zlib import error as ZlibError

from goal2.engine.original_match.image import Image,GAME_PTR,FIXTURES_PTR,FIXTURE_SIZE
from goal2.game import engine_tables
from goal2.game.season import canonical_hash
from goal2.game.stopped_snapshot import _json
from goal2.game.stopped_view import NativeMatchView
from goal2.game.prematch_view import _words
from goal2.game.watched_schema import RESULT_KEYS,KIT2_KEYS,integer,pair
from goal2.game.session_save import _json_value,_restore_json_value


def _hash(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def completed_result_hash(value):
    """[designed: T170ag] Bind the SDK's tuple/list distinctions on this pipe."""
    return canonical_hash(_json_value(value))


def _native_result(result,image,country):
    """Validate current/rendered fields; preserve raw SDK histories hash-bound.

    [derived: Match._competitive] Player consequences include the before/after
    union, including removed pre-match pool members. It is not a fixed40 save.
    """
    if (not isinstance(result,dict) or set(result)!=RESULT_KEYS|KIT2_KEYS|{'ports'} or result['kit']!='4'
            or any(not integer(result[k],1,128) for k in ('first','second','managed'))
            or result['managed']!=country or not integer(result['index'],1,2400)
            or not integer(result['kind'],1,255) or not pair(result['score'],0,255)
            or (result['half_time_score'] is not None and not pair(result['half_time_score'],0,255))
            or not pair(result['goal_counts'],0,255) or not integer(result['winner'],0,2)
            or any(not integer(result[k],0,65535) for k in ('kickoff_seed','seed_after'))
            or result['seed_after']!=image.rd(0x7B62) or not _hash(result['image_sha256'])
            or any(not integer(result[k],0,2**31-1) for k in ('ticks','draws'))
            or (result['draws_digest'] is not None and not _hash(result['draws_digest']))):
        raise ValueError('invalid native completed result identity')
    sides=(image.rd(0x9B34),image.rd(0x9B36))
    if sides!=(result['first'],result['second']) or country not in sides or sides[0]==sides[1]:
        raise ValueError('completed result differs from native sides')
    game=image.far(GAME_PTR);fixtures=image.far(FIXTURES_PTR);index=result['index']
    at=fixtures+FIXTURE_SIZE*(index-1)
    if (game<=0 or fixtures<=0 or image.fixture_index()!=index
            or not 1<=index<image.rd_far(GAME_PTR,0x28) or not 0<=at<=len(image.memory)-FIXTURE_SIZE):
        raise ValueError('invalid completed fixture span')
    raw=image.memory[at:at+FIXTURE_SIZE]
    if (int.from_bytes(raw[4:6],'little'),int.from_bytes(raw[6:8],'little'),raw[2])!=(*sides,result['kind']):
        raise ValueError('completed result differs from native fixture')
    players=image.players();countries=image.countries()
    if any(len(p)!=20 for p in players) or any(len(c)!=191 for c in countries):
        raise ValueError('invalid completed record spans')
    squads={str(c):list(_words(image.squad(c),20,zero=True)) for c in sides}
    if canonical_hash(result['squads_after'])!=canonical_hash(squads):
        raise ValueError('completed squads differ from current native records')
    current={w:team for team,c in enumerate(sides) for w in squads[str(c)] if w}
    if len(current)!=sum(bool(w) for words in squads.values() for w in words):
        raise ValueError('duplicate completed side membership')
    rows=result['players'];seen=set()
    if not isinstance(rows,list):raise ValueError('invalid native completed consequences')
    for row in rows:
        if (not isinstance(row,dict) or set(row)!={'player','team','confidence','energy','status',
                'suspended','carried_booking','injured'} or not integer(row['player'],1,3060)
                or row['player'] in seen or not integer(row['team'],0,1)):
            raise ValueError('invalid native consequence row')
        word=row['player'];seen.add(word)
        for key,offset in (('confidence',12),('energy',14),('status',16)):
            values=row[key]
            if (not isinstance(values,list) or len(values)!=2
                    or any(v is not None and not integer(v,0,255) for v in values)
                    or (word in current and (row['team']!=current[word] or values[1]!=players[word][offset]))
                    or (word not in current and values[1] is not None)):
                raise ValueError('completed consequence differs from current records')
        status=row['status'][1]
        expected=dict(suspended=bool(status is not None and status&128),
            carried_booking=bool(status is not None and status&8),injured=row['energy'][1]==0)
        if any(type(row[k]) is not bool or row[k]!=v for k,v in expected.items()):
            raise ValueError('invalid completed consequence flags')
    if not set(current)<=seen:raise ValueError('missing completed current player')
    for key in ('goals','goals_disallowed','bookings','sendings_off','injuries','substitutions',
                'commentary','decisions','inputs'):
        if not isinstance(result[key],list) or any(not isinstance(r,dict) for r in result[key]):
            raise ValueError('invalid native completed history')
    for row in result['decisions']:
        if (set(row)!={'context','minute','answer'} or not isinstance(row['context'],str)
                or not integer(row['minute'],0,65535) or not isinstance(row['answer'],dict)):
            raise ValueError('invalid native decision history')
    if (type(result['extra_time']) is not bool or not pair(result['substitution_budget'],0,255)
            or (result['score_90'] is not None and not pair(result['score_90'],0,255))):
        raise ValueError('invalid native completed stages')
    penalties=[0,0];shoot=result['shootout']
    if shoot is not None:
        if (not isinstance(shoot,dict) or set(shoot)!={'score','kicks'} or not pair(shoot['score'],0,255)
                or not isinstance(shoot['kicks'],list) or any(not isinstance(k,dict) for k in shoot['kicks'])):
            raise ValueError('invalid native completed shootout')
        penalties=shoot['score']
    board=result['board'];keys={'statistics','bars','man_of_the_match','final_score','screen_sha256','ticks','seed'}
    stats={'corners','free_kicks','penalties','shots','on_target','saves','fouls','bookings','red_cards','injuries'}
    if (not isinstance(board,dict) or set(board)!=keys or not isinstance(board['statistics'],dict)
            or set(board['statistics'])!=stats or any(not pair(v,0,255) for v in board['statistics'].values())
            or not isinstance(board['bars'],list) or len(board['bars'])!=2
            or any(not pair(v,0,65535) for v in board['bars']) or not pair(board['final_score'],0,255)
            or board['final_score']!=[result['score'][i]+penalties[i] for i in (0,1)]
            or type(board['ticks']) is not int or board['ticks']!=result['ticks']
            or not integer(result['man_of_the_match'],0,3060) or type(board['man_of_the_match']) is not int
            or board['man_of_the_match']!=result['man_of_the_match'] or not isinstance(result['man_of_the_match_name'],str)
            or not integer(board['seed'],0,65535) or not _hash(board['screen_sha256'])):
        raise ValueError('invalid original completed board')
    ports=result['ports']
    if (not isinstance(ports,dict) or set(ports)!={'names','calls'} or not isinstance(ports['names'],list)
            or not ports['names'] or any(not isinstance(n,str) for n in ports['names'])
            or not isinstance(ports['calls'],dict) or any(not isinstance(k,str) or not integer(v,0,2**63-1)
                                                       for k,v in ports['calls'].items())):
        raise ValueError('invalid completed port provenance')


@dataclass(frozen=True)
class CompletedMatchSnapshot:
    request: int
    managed_country: int
    event_count: int
    frame_sequence: int
    state_hash: str
    result_hash: str
    _state: bytes=field(repr=False)
    _result: bytes=field(repr=False)

    @property
    def state(self):
        import json
        return json.loads(self._state)

    @property
    def result(self):
        import json
        return _restore_json_value(json.loads(self._result),'completed native result')

    @classmethod
    def from_packet(cls,packet,*,request,managed_country,event_count=None,frame_sequence=None,
                    fixture=None,score=None,board=None):
        if not integer(request,1,2**63-1) or not integer(managed_country,1,128):
            raise ValueError('invalid expected completion identity')
        if (not isinstance(packet,dict) or set(packet)!={'request','action','preview','state','result'}
                or type(packet['request']) is not int or packet['request']!=request
                or packet['action']!='completed_preview'):
            raise ValueError('invalid completed reply')
        meta=packet['preview'];native=packet['state'];result=packet['result']
        if (not isinstance(meta,dict) or set(meta)!={'schema','managed_country','event_count','frame_sequence',
                'state_hash','result_hash'} or meta['schema']!='goal2/completed-preview/1'
                or type(meta['managed_country']) is not int or meta['managed_country']!=managed_country
                or not integer(meta['event_count'],1,2**63-1) or not integer(meta['frame_sequence'],0,2**63-1)
                or not isinstance(native,dict) or native.get('schema')!='original_match.state/2'
                or meta['state_hash']!=canonical_hash(native) or meta['result_hash']!=completed_result_hash(result)):
            raise ValueError('completed identity/hash mismatch')
        for name,expected,low in (('event_count',event_count,1),('frame_sequence',frame_sequence,0)):
            if expected is not None and (not integer(expected,low,2**63-1) or meta[name]!=expected):
                raise ValueError('completed stream counter mismatch')
        try:
            image=Image.from_state(native,engine_tables.load());_native_result(result,image,managed_country)
            if fixture is not None and (not isinstance(fixture,(list,tuple)) or len(fixture)!=4
                    or canonical_hash(fixture)!=canonical_hash([result[k] for k in ('first','second','index','kind')])):
                raise ValueError('completed fixture mismatch')
            if score is not None and canonical_hash(score)!=canonical_hash(result['score']):
                raise ValueError('completed terminal score mismatch')
            if board is not None and canonical_hash(board)!=canonical_hash(result['board']):
                raise ValueError('completed canonical final-board mismatch')
            state_json,result_json=_json(native),_json(_json_value(result))
        except (KeyError,TypeError,IndexError,ValueError,OverflowError,ZlibError) as exc:
            raise ValueError('invalid native completed snapshot') from exc
        return cls(request,managed_country,meta['event_count'],meta['frame_sequence'],meta['state_hash'],
                   meta['result_hash'],state_json,result_json)


@dataclass(frozen=True)
class CompletedMatchView(NativeMatchView):
    @classmethod
    def from_packet(cls,packet,**expected):
        return cls._from_snapshot(CompletedMatchSnapshot.from_packet(packet,**expected))

    @property
    def result(self):return self.snapshot.result

    @property
    def board(self):return self.result['board']
