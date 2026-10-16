"""[designed: T48] Atomic source-ordered CPU/managed turns and explicit RNG ledger.
[derived: proposed F023/F024 at0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb]
Source draw rounds are metadata; a playable turn stops before the next managed row.
"""
import copy
from dataclasses import dataclass,asdict
from goal2.game.silent_results import SilentResolver


def integer(value,low,high):return type(value) is int and low<=value<=high


def advance(seed,count):
    """[derived: F004] Affine LCG exponentiation, same steps without replay cost."""
    mul,add=0x7abd,0x1b0f
    while count:
        if count&1:seed=(seed*mul+add)&65535
        add=(add*(mul+1))&65535;mul=(mul*mul)&65535;count>>=1
    return seed


@dataclass(frozen=True)
class Scheduled:
    """[designed] Immutable original fixture identity/endpoints and draw-round tag."""
    fixture_id:str
    kind:int
    side_a:int
    side_b:int
    round_number:int


@dataclass
class World:
    """[designed] Full source schedule and an exactly-once result prefix."""
    managed_country:int
    initial_seed:int
    fixtures:tuple
    results:list

    def validate(self,campaign):
        if not integer(self.managed_country,1,128) or not integer(self.initial_seed,0,65535):
            raise ValueError('invalid world country or seed')
        if not isinstance(self.fixtures,tuple) or not self.fixtures or not isinstance(self.results,list):
            raise ValueError('invalid full fixture schedule')
        seen=set();previous=0
        for fixture in self.fixtures:
            if (not isinstance(fixture,Scheduled) or not isinstance(fixture.fixture_id,str) or not fixture.fixture_id
                    or fixture.fixture_id in seen or not integer(fixture.kind,1,255)
                    or not integer(fixture.side_a,1,128) or not integer(fixture.side_b,1,128)
                    or fixture.side_a==fixture.side_b or not integer(fixture.round_number,1,12)
                    or fixture.round_number<previous):raise ValueError('invalid/duplicate/out-of-order world fixture')
            seen.add(fixture.fixture_id);previous=fixture.round_number
        managed=[f for f in self.fixtures if self.managed_country in (f.side_a,f.side_b)]
        if [(f.fixture_id,f.kind,f.side_a,f.side_b) for f in managed]!=[(f.fixture_id,f.kind,f.side_a,f.side_b) for f in campaign.fixtures]:
            raise ValueError('world schedule differs from managed fixture projection')
        if len(self.results)>len(self.fixtures):raise ValueError('world result prefix is too long')
        seed=self.initial_seed;managed_ids=[]
        for fixture,row in zip(self.fixtures,self.results):
            keys={'fixture_id','teams','score','winner','mode','seed_before','seed_after','draws'}
            if (not isinstance(row,dict) or set(row)!=keys or row['fixture_id']!=fixture.fixture_id
                    or row['teams']!=[fixture.side_a,fixture.side_b]
                    or not isinstance(row['teams'],list) or any(type(t) is not int for t in row['teams'])
                    or not isinstance(row['score'],list) or len(row['score'])!=2
                    or any(not integer(g,0,255) for g in row['score'])
                    or not integer(row['winner'],0,2) or not integer(row['seed_before'],0,65535)
                    or not integer(row['seed_after'],0,65535) or not integer(row['draws'],1,2**31-1)
                    or row['seed_before']!=seed or advance(seed,row['draws'])!=row['seed_after']):
                raise ValueError('duplicate/out-of-order/invalid world result or RNG chain')
            expected='managed' if self.managed_country in (fixture.side_a,fixture.side_b) else 'silent'
            if row['mode']!=expected:raise ValueError('world result used the wrong match path')
            a,b=row['score'];winner=2 if a==b else int(b>a)
            decider=fixture.kind==4 or 8<=fixture.kind<=203
            if (a!=b or not decider) and row['winner']!=winner:raise ValueError('world result winner differs from score')
            if a==b and decider and row['winner']==2:raise ValueError('silent decider needs its winner coin')
            if expected=='managed':
                if fixture.kind!=1:raise ValueError('unsupported managed fixture completed')
                managed_ids.append(fixture.fixture_id)
            seed=row['seed_after']
        if managed_ids!=campaign.completed_fixture_ids:raise ValueError('world and managed completion ledgers differ')
        for row in campaign.results:
            match=next((r for r in self.results if r['fixture_id']==row['fixture_id']),None)
            if match is None or match['teams']!=row['teams'] or match['score']!=row['score']:
                raise ValueError('managed score differs from world result')
        return seed

    def to_data(self):
        return {'managed_country':self.managed_country,'initial_seed':self.initial_seed,
                'fixtures':[asdict(f) for f in self.fixtures],'results':copy.deepcopy(self.results)}

    @classmethod
    def from_data(cls,data):
        if not isinstance(data,dict) or set(data)!={'managed_country','initial_seed','fixtures','results'} or not isinstance(data['fixtures'],list):
            raise ValueError('invalid world metadata')
        try:return cls(data['managed_country'],data['initial_seed'],tuple(Scheduled(**r) for r in data['fixtures']),data['results'])
        except (TypeError,ValueError) as exc:raise ValueError(f'invalid scheduled fixture: {exc}') from exc


def validate_state(state):
    world=state.campaign.world if state.campaign else None
    if world is not None:
        seed=world.validate(state.campaign)
        if (world.managed_country!=state.managed_country or seed!=state.rng_seed_7b62
                or state.match_count!=len(state.campaign.completed_fixture_ids)):
            raise ValueError('world country or live RNG differs from saved continuation')


def append_result(state,fixture,outcome,mode):
    world=state.campaign.world;seed=state.rng_seed_7b62
    row={'fixture_id':fixture.fixture_id,'teams':[fixture.side_a,fixture.side_b],
         'score':list(outcome['score']),'winner':outcome['winner'],'mode':mode,
         'seed_before':seed,'seed_after':outcome['seed_after'],'draws':outcome['draws']}
    world.results.append(row);state.rng_seed_7b62=row['seed_after']


def silent_until_managed(state,template,resolver_factory):
    world=state.campaign.world
    resolver=None
    while len(world.results)<len(world.fixtures):
        fixture=world.fixtures[len(world.results)]
        if state.managed_country in (fixture.side_a,fixture.side_b):break
        if resolver is None:resolver=resolver_factory(state,template)
        append_result(state,fixture,resolver(fixture,state.rng_seed_7b62),'silent')


def prepare(state,template,*,resolver_factory=SilentResolver):
    """[designed] Pure atomic prefix; only caller-owned candidates leave this seam."""
    candidate = copy.deepcopy(state)
    validate_state(candidate)
    if candidate.campaign is not None and candidate.campaign.world is not None:
        pending=candidate.campaign.next_fixture
        if pending is None or pending.kind!=1:raise ValueError('unsupported managed fixture')
        silent_until_managed(candidate,template,resolver_factory)
        world=candidate.campaign.world
        if len(world.results)>=len(world.fixtures) or world.fixtures[len(world.results)].fixture_id!=pending.fixture_id:
            raise ValueError('world cursor differs from pending managed fixture')
        validate_state(candidate)
    return candidate


def complete(state,result,*,template=None,resolver_factory=SilentResolver):
    """[designed] Pure atomic result+suffix; failure cannot publish half a turn."""
    candidate=copy.deepcopy(state)
    if not isinstance(candidate.last_match,dict):raise ValueError('Friendly runner did not retain its result')
    candidate.last_match['managed_side']=result['managed_side'];candidate.last_match['match_count']=candidate.match_count
    campaign=candidate.campaign
    if campaign is not None:
        fixture=campaign.next_fixture
        if campaign.world is not None:
            world=campaign.world;world.validate(campaign)
            if candidate.match_count!=len(campaign.completed_fixture_ids)+1:raise ValueError('managed match was already completed')
            if tuple(result['teams'])!=(fixture.side_a,fixture.side_b):raise ValueError('managed result fixture changed')
            if len(world.results)>=len(world.fixtures) or world.fixtures[len(world.results)].fixture_id!=fixture.fixture_id:
                raise ValueError('round was not prepared or was already completed')
            seed_before=world.results[-1]['seed_after'] if world.results else world.initial_seed
            candidate.rng_seed_7b62=seed_before
            score=list(result['score']);winner=2 if score[0]==score[1] else int(score[1]>score[0])
            append_result(candidate,world.fixtures[len(world.results)],{'score':score,'winner':winner,
                          'seed_after':state.rng_seed_7b62,'draws':candidate.last_match['draws']},'managed')
        campaign.complete_fixture(fixture.fixture_id)
        campaign.results.append({'fixture_id':fixture.fixture_id,'teams':list(result['teams']),'score':list(result['score'])})
        if campaign.world is not None:
            if template is None:raise ValueError('world turn completion needs its local template')
            silent_until_managed(candidate,template,resolver_factory);validate_state(candidate)
        pending=campaign.next_fixture
        if pending is not None and pending.stage!=campaign.stage and pending.kind==1:campaign.advance_calendar()
    return candidate
