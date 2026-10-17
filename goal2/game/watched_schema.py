"""[designed: T64] Explicit completed watched result/save identity, independent of quick play."""
import re

LEGACY_ENGINE_ID = 'original-match:3656a2d26e0f57a410d648edeaa6cd9eb7d1f607:1'
ENGINE_ID = 'original-match:424d5998076da1e4efc399c2715689ddb44d3e1a:2'
ENGINE_IDS = (LEGACY_ENGINE_ID, ENGINE_ID)
RESULT_SCHEMA = 1
RESULT_KEYS = {'first','second','managed','index','score','half_time_score','goals',
    'goals_disallowed','goal_counts','bookings','sendings_off','injuries','substitutions',
    'man_of_the_match','man_of_the_match_name','board','commentary','decisions','inputs',
    'ticks','kickoff_seed','seed_after','image_sha256','kit','draws','draws_digest','squads_after'}

KIT2_KEYS = {'kind','winner','score_90','extra_time','substitution_budget','shootout','players'}

def integer(value,low,high):
    return type(value) is int and low<=value<=high


def pair(value,low,high):
    return isinstance(value,(list,tuple)) and len(value)==2 and all(integer(v,low,high) for v in value)


def validate_result(result):
    """[designed] Refuse incompatible kit results before state publication or save loading."""
    # [designed: T51a] Recognize both exact profiles; never relabel historical results.
    if not isinstance(result,dict):raise ValueError('invalid watched original result schema')
    kit=result.get('kit')
    keys=RESULT_KEYS if kit=='1' else RESULT_KEYS|KIT2_KEYS if kit=='2' else None
    if keys is None or set(result)!=keys:raise ValueError('invalid watched original result schema')
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
    _details(result)
    if kit=='2':_friendly_kit2(result)
    return LEGACY_ENGINE_ID if kit=='1' else ENGINE_ID


def _friendly_kit2(result):
    """[designed: T51a; confirmed: PR255 _competitive] Current app accepts default-budget friendlies only.
    T51 owns competitive routing and the owner's substitution policy.
    """
    score=result['score'];winner=2 if score[0]==score[1] else int(score[1]>score[0])
    if (type(result['kind']) is not int or result['kind']!=1
            or not integer(result['winner'],0,2) or result['winner']!=winner
            or result['score_90'] is not None or result['extra_time'] is not False
            or result['shootout'] is not None or result['substitution_budget']!=[5,5]
            or any(type(v) is not int for v in result['substitution_budget'])):
        raise ValueError('unsupported watched kit2 friendly resolution or budget')
    players=result['players']
    if not isinstance(players,list) or len(players)!=40:raise ValueError('invalid watched player consequences')
    expected={word:team for team,country in enumerate((result['first'],result['second']))
              for word in result['squads_after'][str(country)]}
    seen=set()
    for row in players:
        _object(row,{'player','team','confidence','energy','status','suspended','carried_booking','injured'})
        word=row['player']
        if (not integer(word,1,3060) or word in seen or word not in expected
                or not integer(row['team'],0,1) or row['team']!=expected[word]
                or any(not pair(row[key],0,255) for key in ('confidence','energy','status'))
                or any(type(row[key]) is not bool for key in ('suspended','carried_booking','injured'))
                or row['suspended']!=bool(row['status'][1]&0x80)
                or row['carried_booking']!=bool(row['status'][1]&0x08)
                or row['injured']!=(row['energy'][1]==0)):
            raise ValueError('invalid watched player consequences')
        seen.add(word)
    if seen!=set(expected):raise ValueError('invalid watched player consequences')


def _object(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys):raise ValueError('invalid watched result record fields')


def _number(value,low=0,high=65535):
    if not integer(value,low,high):raise ValueError('invalid watched result number')


def _text(value):
    if not isinstance(value,str):raise ValueError('invalid watched result text')


def _hash(value):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('invalid watched result digest')


def _details(result):
    """[derived: accepted E033 Match._finish/_board/_flush] Compatible result data shapes."""
    _number(result['man_of_the_match'],0,3060);_text(result['man_of_the_match_name'])
    board=result['board']
    _object(board,{'statistics','bars','man_of_the_match','final_score','screen_sha256','ticks','seed'})
    _object(board['statistics'],{'corners','free_kicks','penalties','shots','on_target','saves','fouls','bookings','red_cards','injuries'})
    if any(not pair(v,0,255) for v in board['statistics'].values()):raise ValueError('invalid watched statistics')
    if (not isinstance(board['bars'],list) or len(board['bars'])!=2
            or any(not pair(v,0,65535) for v in board['bars'])
            or not pair(board['final_score'],0,255) or board['final_score']!=result['score']
            or board['ticks']!=result['ticks'] or board['man_of_the_match']!=result['man_of_the_match']):
        raise ValueError('invalid watched final board')
    _number(board['ticks'],0,2**31-1);_number(board['man_of_the_match'],0,3060)
    _number(board['seed']);_hash(board['screen_sha256'])
    for key in ('goals','goals_disallowed','bookings','sendings_off','injuries','substitutions'):
        for row in result[key]:
            if key=='substitutions':
                _object(row,{'team','off','on','off_name','on_name','minute'})
                for word in ('off','on'):_number(row[word],0,3060)
                for name in ('off_name','on_name'):_text(row[name])
            else:
                keys={'team','player','name','minute'}
                if key in ('goals','goals_disallowed'):keys|={'country','minute_byte'}
                _object(row,keys);_number(row['team'],0,1);_number(row['player'],0,3060);_text(row['name'])
                if 'country' in row:
                    if row['country']!=result[('first','second')[row['team']]]:raise ValueError('invalid watched scorer country')
                    if row['minute_byte'] is not None:_number(row['minute_byte'],0,255)
            _number(row['team'],0,1);_number(row['minute'],0,65535)
    for row in result['commentary']:
        _object(row,{'minute','template','players','team','text'})
        _number(row['minute']);_number(row['template'],0,255);_number(row['team'],0,255);_text(row['text'])
        # [confirmed: accepted E033 _flush] The ring carries two raw words;
        # unused template arguments are not constrained to valid player IDs.
        if not pair(row['players'],0,65535):raise ValueError('invalid watched commentary words')
    for row in result['inputs']:
        _object(row,{'what','linear','old','new'});_text(row['what']);_number(row['linear'],0,0x10ffff)
        for key in ('old','new'):
            if not isinstance(row[key],str) or re.fullmatch('(?:[0-9a-f]{2})*',row[key]) is None:
                raise ValueError('invalid watched declared input')
        if len(row['old'])!=len(row['new']):raise ValueError('invalid watched input lengths')
    for row in result['decisions']:
        _object(row,{'context','minute','answer'});_text(row['context']);_number(row['minute'])
        answer=row['answer'];_object(answer,{'substitutions','tactics','positions','marking','own_tactics','quick','speed'})
        if type(answer['quick']) is not bool or (answer['speed'] is not None and not integer(answer['speed'],0,255)):
            raise ValueError('invalid watched decision policy')
        for key in ('substitutions','tactics','positions','marking','own_tactics'):
            if not isinstance(answer[key],list):raise ValueError('invalid watched decision entries')
            for entry in answer[key]:
                if not isinstance(entry,(list,tuple)) or len(entry)!=2:raise ValueError('invalid watched decision pair')
                _number(entry[0],1,3060)
                if key=='tactics':
                    if type(entry[1]) is not bool:raise ValueError('invalid watched tactics decision')
                elif key=='own_tactics':
                    if not isinstance(entry[1],(list,tuple)):raise ValueError('invalid watched own tactics decision')
                    for setting in entry[1]:
                        if (not isinstance(setting,(list,tuple)) or len(setting)!=2
                                or not integer(setting[0],1,4) or (setting[1] is not None and type(setting[1]) is not bool)):
                            raise ValueError('invalid watched own tactics setting')
                else:_number(entry[1],0,3060)


def watched(row):
    """[designed] Legacy quick records have no engine field and retain that meaning."""
    if not isinstance(row,dict):return False
    if 'engine' not in row:
        if 'schema' in row or 'original' in row:raise ValueError('missing watched engine identity')
        return False
    if row['engine'] not in ENGINE_IDS:raise ValueError('unsupported result engine identity')
    return True


def validate_saved_watched(state):
    """[designed] Validate watched envelopes and their returned-memory continuation."""
    last=state.last_match
    image=None
    if watched(last):
        keys={'engine','schema','original','teams','score','goals','managed_side','match_count','seeds','engine_year'}
        if set(last)!=keys or last['schema']!=RESULT_SCHEMA or type(last['schema']) is not int:
            raise ValueError('invalid watched result envelope')
        result=last['original'];engine=validate_result(result)
        if last['engine']!=engine:raise ValueError('watched engine differs from original result profile')
        teams=[result['first'],result['second']]
        if (result['managed']!=state.managed_country
                or not pair(last['teams'],1,128) or last['teams']!=teams
                or not pair(last['score'],0,255) or last['score']!=list(result['score']) or last['goals']!=result['goals']
                or last['managed_side']!=teams.index(state.managed_country)
                or not integer(last['managed_side'],0,1) or last['match_count']!=state.match_count
                or not integer(last['match_count'],1,2**31-1) or not pair(last['seeds'],0,65535)
                or last['seeds'][0]!=result['seed_after'] or not integer(last['engine_year'],0,65535)):
            raise ValueError('inconsistent watched result envelope')
        image=_returned_image(state.mem)
        # [designed] Management edits may change live fields after completion;
        # the retained returned memory still validates the original result independently.
        if (any(image.squad(int(country))!=words for country,words in result['squads_after'].items())
                or image.fixture_index()!=result['index'] or _fixture_teams(image,result['index'])!=teams
                or image.year()!=last['engine_year']
                or tuple(last['seeds'])!=(image.rd(0x7B62),image.rd(0x8336))
                or state.rng_seed_8336!=last['seeds'][1]):
            raise ValueError('watched returned memory differs from saved known fields')
        if state.campaign is None or state.campaign.world is None:
            if state.rng_seed_7b62!=last['seeds'][0]:raise ValueError('watched primary RNG differs from returned memory')
    if state.campaign is not None:
        world=state.campaign.world
        if world is not None:
            managed=[row for row in world.results if row['mode'] in ('managed','watched')]
            if managed and managed[-1]['mode']=='watched' and not watched(last):
                raise ValueError('watched completion lost its result engine identity')
            returned=[row for row in world.results if row['mode']=='watched']
            if returned:
                if image is None:image=_returned_image(state.mem)
                row=returned[-1]
                if (row['seed_after']!=image.rd(0x7B62) or row['secondary_after']!=image.rd(0x8336)
                        or row['engine_year']!=image.year() or row['index']!=image.fixture_index()
                        or row['teams']!=_fixture_teams(image,row['index'])):
                    raise ValueError('watched world RNG or fixture differs from retained returned memory')
        if watched(last):
            if (not state.campaign.results or state.campaign.results[-1]['fixture_id']!=f"original:{last['original']['index']}"
                    or state.campaign.results[-1].get('engine')!=last['engine']):
                raise ValueError('watched last result differs from campaign history')
            world=state.campaign.world
            if world is not None:
                row=next((r for r in world.results if r['fixture_id']==f"original:{last['original']['index']}"),None)
                if (row is None or row.get('mode')!='watched' or row.get('engine')!=last['engine'] or row['seed_after']!=last['seeds'][0]
                        or row['secondary_after']!=last['seeds'][1] or row['engine_year']!=last['engine_year']):
                    raise ValueError('watched result differs from world continuation')
        for row in state.campaign.results:
            if watched(row) and (set(row)!={'fixture_id','teams','score','engine','schema'}
                    or type(row['schema']) is not int or row['schema']!=RESULT_SCHEMA):
                raise ValueError('invalid watched campaign result schema')


def _fixture_teams(image,index):
    # [confirmed: E033 _write_fixture at the engine identity pin] Source row endpoints.
    return [image.rd_far(0xA92B,8*(index-1)+offset) for offset in (4,6)]


def _returned_image(memory):
    # [designed: T64; derived: accepted E033] The latest original Memory remains
    # retained through later quick results; live quick fields may differ from it.
    from goal2.engine.original_match import Image
    image=Image.from_memory_component(memory)
    if image.build_problems():raise ValueError('unsupported watched returned memory build')
    return image


def needs_version3(state):
    if watched(state.last_match):return True
    campaign=state.campaign
    if campaign is None:return False
    return (any(watched(row) for row in campaign.results) or (campaign.world is not None
            and any(isinstance(row,dict) and row.get('mode')=='watched' for row in campaign.world.results)))
