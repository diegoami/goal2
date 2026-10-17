"""[designed: T64] Explicit completed watched result/save identity, independent of quick play."""
import re

ENGINE_ID = 'original-match:3656a2d26e0f57a410d648edeaa6cd9eb7d1f607:1'
RESULT_SCHEMA = 1
RESULT_KEYS = {'first','second','managed','index','score','half_time_score','goals',
    'goals_disallowed','goal_counts','bookings','sendings_off','injuries','substitutions',
    'man_of_the_match','man_of_the_match_name','board','commentary','decisions','inputs',
    'ticks','kickoff_seed','seed_after','image_sha256','kit','draws','draws_digest','squads_after'}


def integer(value,low,high):
    return type(value) is int and low<=value<=high


def pair(value,low,high):
    return isinstance(value,(list,tuple)) and len(value)==2 and all(integer(v,low,high) for v in value)


def validate_result(result):
    """[designed] Refuse incompatible kit results before state publication or save loading."""
    if not isinstance(result,dict) or set(result)!=RESULT_KEYS or result['kit']!='1':
        raise ValueError('invalid watched original result schema')
    if (any(not integer(result[k],1,128) for k in ('first','second','managed'))
            or result['first']==result['second'] or result['managed'] not in (result['first'],result['second'])
            or not integer(result['index'],1,2400) or not pair(result['score'],0,255)
            or not pair(result['half_time_score'],0,255) or not pair(result['goal_counts'],0,255)
            or any(not integer(result[k],0,65535) for k in ('seed_after','kickoff_seed'))
            or any(not integer(result[k],0,2**31-1) for k in ('ticks','draws'))
            or not isinstance(result['image_sha256'],str) or re.fullmatch('[0-9a-f]{64}',result['image_sha256']) is None
            or (result['draws_digest'] is not None and (not isinstance(result['draws_digest'],str)
                or re.fullmatch('[0-9a-f]{64}',result['draws_digest']) is None))):
        raise ValueError('invalid watched result identity, score or RNG metadata')
    for key in ('goals','goals_disallowed','bookings','sendings_off','injuries','substitutions','commentary','decisions','inputs'):
        if not isinstance(result[key],list) or any(not isinstance(row,dict) for row in result[key]):
            raise ValueError(f'invalid watched {key}')
    squads=result['squads_after']
    if not isinstance(squads,dict) or set(squads)!={str(result['first']),str(result['second'])}:
        raise ValueError('invalid watched squad endpoints')
    for words in squads.values():
        if (not isinstance(words,list) or len(words)!=20 or any(not integer(w,1,3060) for w in words)
                or len(set(words))!=20):raise ValueError('invalid watched squad words')
    if not isinstance(result['board'],dict):raise ValueError('invalid watched board')


def watched(row):
    """[designed] Legacy quick records have no engine field and retain that meaning."""
    if not isinstance(row,dict):return False
    if 'engine' not in row:return False
    if row['engine']!=ENGINE_ID:raise ValueError('unsupported result engine identity')
    return True


def validate_saved_watched(state):
    """[designed] Validate watched envelopes and their returned-memory continuation."""
    last=state.last_match
    if watched(last):
        keys={'engine','schema','original','teams','score','goals','managed_side','match_count','seeds','engine_year'}
        if set(last)!=keys or last['schema']!=RESULT_SCHEMA or type(last['schema']) is not int:
            raise ValueError('invalid watched result envelope')
        result=last['original'];validate_result(result)
        teams=[result['first'],result['second']]
        if (last['teams']!=teams or last['score']!=list(result['score']) or last['goals']!=result['goals']
                or last['managed_side']!=teams.index(state.managed_country)
                or not integer(last['managed_side'],0,1) or last['match_count']!=state.match_count
                or not integer(last['match_count'],1,2**31-1) or not pair(last['seeds'],0,65535)
                or last['seeds'][0]!=result['seed_after'] or not integer(last['engine_year'],0,65535)):
            raise ValueError('inconsistent watched result envelope')
        from goal2.engine.original_match import Image
        image=Image.from_memory_component(state.mem)
        # [designed] Management edits may change live fields after completion;
        # the retained returned memory still validates the original result independently.
        if (any(image.squad(int(country))!=words for country,words in result['squads_after'].items())
                or image.year()!=last['engine_year']
                or tuple(last['seeds'])!=(image.rd(0x7B62),image.rd(0x8336))
                or state.rng_seed_8336!=last['seeds'][1]):
            raise ValueError('watched returned memory differs from saved known fields')
        if state.campaign is None or state.campaign.world is None:
            if state.rng_seed_7b62!=last['seeds'][0]:raise ValueError('watched primary RNG differs from returned memory')
    if state.campaign is not None:
        for row in state.campaign.results:
            if watched(row) and (set(row)!={'fixture_id','teams','score','engine','schema'}
                    or type(row['schema']) is not int or row['schema']!=RESULT_SCHEMA):
                raise ValueError('invalid watched campaign result schema')


def needs_version3(state):
    return (watched(state.last_match) or (state.campaign is not None and
            any(watched(row) for row in state.campaign.results)))
