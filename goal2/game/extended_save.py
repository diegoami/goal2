"""T237/#830: explicit JSON selected-bench result profile and retained-memory proof."""
import re
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.game.extended_schema import ExtendedSelection, PROFILE, validate_extended_result
from goal2.game.watched_schema import integer

KEY = 'selected_bench'
SCALARS = ('first','second','managed','index','kind','capacity','image_sha256')
KEYS = {'profile','core','opponent','extras','before','slots',*SCALARS}


def needs_version6(state):
    return isinstance(state.last_match,dict) and KEY in state.last_match


def _slots(selection,slots):
    if (type(slots) not in (tuple,list) or len(slots)!=selection.capacity-20
            or any(w is not None and not integer(w,1,3060) for w in slots)
            or tuple(w for w in slots if w is not None)!=selection.extras):
        raise ValueError('selected-bench slots differ from the bound selection')
    return tuple(slots)


def _universe(country):
    return set(range((country-1)*20+1,country*20+1))|set(range(2561,2641))


def to_data(selection,slots):
    if type(selection) is not ExtendedSelection:raise ValueError('bound selected-bench profile required')
    _slots(selection,slots)
    if not set(selection.selected)<=_universe(selection.managed):
        raise ValueError('selected-bench profile contains a foreign managed player')
    return dict(profile=PROFILE,**{k:getattr(selection,k) for k in SCALARS},
                core=list(selection.core),opponent=list(selection.opponent),extras=list(selection.extras),
                before=[[w,side,values.hex()] for w,side,values in selection.before],slots=list(slots))


def from_data(data):
    if type(data) is not dict or set(data)!=KEYS or data.get('profile')!=PROFILE:
        raise ValueError('invalid exact selected-bench save profile')
    if (any(type(data[k]) is not list for k in ('core','opponent','extras','before','slots'))
            or len(data['core'])!=20 or len(data['opponent'])!=20
            or len(data['extras'])>4 or len(data['before'])!=40 or len(data['slots'])>4):
        raise ValueError('invalid selected-bench save counts')
    before=[]
    for row in data['before']:
        if (type(row) is not list or len(row)!=3 or type(row[2]) is not str
                or re.fullmatch('[0-9a-f]{6}',row[2]) is None):
            raise ValueError('invalid selected-bench before snapshot')
        before.append((row[0],row[1],bytes.fromhex(row[2])))
    selection=ExtendedSelection(**{k:data[k] for k in SCALARS},core=tuple(data['core']),
                                opponent=tuple(data['opponent']),extras=tuple(data['extras']),before=tuple(before))
    slots=_slots(selection,data['slots'])
    if not set(selection.selected)<=_universe(selection.managed):
        raise ValueError('selected-bench profile contains a foreign managed player')
    return selection,slots


def returned_pool(image,managed):
    if not integer(managed,1,128):raise ValueError('invalid returned managed country')
    manager=image.rd_far(0xA923,1,1)
    base=image.rd(0x6D1A)
    at=image.far(0xA927)+2*base
    if (manager!=1 or base<1 or image.far(0xA927)==0
            or image.rd(0xA927)+2*(base+80)>65536
            or at+160>min(len(image.memory),MEM_SIZE)):
        raise ValueError('invalid returned selected-bench manager/pool allocation')
    pool=tuple(int.from_bytes(image.memory[at+2*i:at+2*i+2],'little') for i in range(80))
    core=tuple(image.squad(managed));records=image.players()
    if (len(core)!=20 or len(set(core+pool))!=100 or set(core+pool)!=_universe(managed)
            or any(len(records[w])!=20 or records[w][0]!=managed for w in core+pool)):
        raise ValueError('returned selected-bench twenty/eighty membership differs')
    return pool


def validate_returned(selection,result,image,*,competitive=False):
    checked=validate_extended_result(result,selection,competitive=competitive)
    if tuple(image.squad(selection.managed))!=checked.native:
        raise ValueError('selected-bench native twenty differs from returned memory')
    pool=returned_pool(image,selection.managed)
    if not set(checked.national[20:])<=set(pool):
        raise ValueError('selected-bench extras differ from returned pool')
    records=image.players()
    for row in result['players']:
        for field,offset in (('confidence',12),('energy',14),('status',16)):
            value=row[field][1]
            if value is not None and records[row['player']][offset]!=value:
                raise ValueError('selected-bench consequences differ from returned memory')
    return checked,pool
