"""[designed: T170ab/#808] Bounded completed-tick batches on the season pipe.

[derived: T81/T82] Samples keep their accepted signed fields; watermarks count
canonical non-tick events over this one configured Match.
"""
from goal2.game.watched_pitch import validate,FRAME_POLL_BUDGET


def validate_batch(value,sequence,watermark,event_count,limit):
    keys={'request','action','events','decision','over','exhausted','frames','event_count'}
    if (not isinstance(value,dict) or set(value)!=keys or value['action']!='next'
            or type(limit) is not int or not 1<=limit<=FRAME_POLL_BUDGET
            or type(value['over']) is not bool or type(value['exhausted']) is not bool
            or not isinstance(value['events'],list) or not isinstance(value['frames'],list)
            or len(value['events'])+len(value['frames'])>limit):
        raise ValueError('invalid native pitch batch')
    events,frames=value['events'],value['frames']
    if any(not isinstance(e,dict) or not isinstance(e.get('kind'),str) or e['kind']=='tick' for e in events):
        raise ValueError('invalid native canonical events')
    number=value['decision'];decisions=[e for e in events if e['kind']=='decision']
    if ((number is None and decisions) or (number is not None and
            (type(number) is not int or number<1 or len(decisions)!=1 or events[-1]['kind']!='decision'))):
        raise ValueError('invalid native pitch decision')
    total=event_count+len(events)
    if type(value['event_count']) is not int or value['event_count']!=total:
        raise ValueError('invalid native pitch event counter')
    for frame in frames:
        validate(frame,sequence,watermark)
        if not event_count<=frame['watermark']<=total:
            raise ValueError('native pitch watermark exceeds its event interval')
        sequence+=1;watermark=frame['watermark']
    return sequence,watermark,total
