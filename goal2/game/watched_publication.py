"""[designed: T64] Transport-neutral private watched jobs and once-only atomic publication.
[confirmed: E033 at3656a2d26e0f57a410d648edeaa6cd9eb7d1f607] result() follows the original tail.
Workers/UI integration is T65/T66; no process or widget owns this active-state swap.
"""
import copy
import secrets
from dataclasses import dataclass
from goal2.engine.original_match import Image, Fixture
from goal2.game import campaign_rounds
from goal2.game.watched_match import prepare_watched, WatchedOutcome, engine_year
from goal2.game.watched_schema import ENGINE_ID, RESULT_SCHEMA, validate_result, validate_saved_watched


@dataclass(frozen=True)
class WatchedJob:
    token: str
    state: object
    fixture: Fixture


def completed_candidate(state,fixture,outcome,template):
    """[designed] Build every returned field and ledger privately, never quick Python effects."""
    if not isinstance(outcome,WatchedOutcome):raise ValueError('completed watched outcome required')
    result=outcome.result;validate_result(result)
    kinds=[getattr(event,'kind',None) for event in outcome.events]
    if (not kinds or kinds[-1]!='end' or kinds.count('end')!=1 or kinds.count('full_time')!=1
            or (result['first'],result['second'],result['index'],result['managed'])!=
                (fixture.first,fixture.second,fixture.index,state.managed_country)):
        raise ValueError('watched completion differs from the pending fixture or is incomplete')
    expected_year=engine_year(state.campaign) if state.campaign is not None else Image(state.mem).year()
    if type(outcome.engine_year) is not int or outcome.engine_year!=expected_year:
        raise ValueError("watched completion changed engine year")
    image=Image.from_memory_component(outcome.memory)
    if outcome.seeds!=(image.rd(0x7B62),image.rd(0x8336)) or result['seed_after']!=outcome.seeds[0]:
        raise ValueError('watched returned RNG differs from result')
    candidate=copy.deepcopy(state)
    candidate.mem=bytes(outcome.memory)
    candidate.players=image.players();candidate.countries=image.countries()
    candidate.managed_squad=image.squad(state.managed_country)
    # [designed] Selection and captain are manager choices; returned squad/tactics are engine fields.
    candidate.country_tactics=candidate.countries[state.managed_country][0x2D]
    candidate.rng_seed_7b62,candidate.rng_seed_8336=outcome.seeds
    candidate.match_count+=1
    candidate.last_match={'engine':ENGINE_ID,'schema':RESULT_SCHEMA,'original':copy.deepcopy(result),
        'teams':[fixture.first,fixture.second],'score':list(result['score']),'goals':copy.deepcopy(result['goals']),
        'managed_side':int(state.managed_country==fixture.second),'match_count':candidate.match_count,
        'seeds':list(outcome.seeds),'engine_year':outcome.engine_year}
    candidate.match_state['score']=tuple(result['score']);candidate.match_state['minute']=90;candidate.match_state['half']=2
    campaign=candidate.campaign
    if campaign is not None:
        pending=campaign.next_fixture
        if pending is None or pending.fixture_id!=f'original:{fixture.index}':
            raise ValueError('scheduled watched completion changed')
        if campaign.world is not None:
            world=campaign.world;world.validate(campaign)
            if len(world.results)>=len(world.fixtures) or world.fixtures[len(world.results)].fixture_id!=pending.fixture_id:
                raise ValueError('watched round was not prepared')
            score=list(result['score'])
            world.results.append({'fixture_id':pending.fixture_id,'teams':[fixture.first,fixture.second],
                'score':score,'winner':2 if score[0]==score[1] else int(score[1]>score[0]),'mode':'watched',
                'engine':ENGINE_ID,'schema':RESULT_SCHEMA,'seed_before':state.rng_seed_7b62,
                'seed_after':outcome.seeds[0],'secondary_after':outcome.seeds[1],
                'engine_year':outcome.engine_year,'index':fixture.index,
                'setup_seed':fixture.index*(outcome.engine_year+1)&65535})
        campaign.complete_fixture(pending.fixture_id)
        campaign.results.append({'fixture_id':pending.fixture_id,'teams':[fixture.first,fixture.second],
            'score':list(result['score']),'engine':ENGINE_ID,'schema':RESULT_SCHEMA})
        if campaign.world is not None:
            campaign_rounds.silent_until_managed(candidate,template,campaign_rounds.SilentResolver)
            campaign_rounds.validate_state(candidate)
        pending=campaign.next_fixture
        if pending is not None and pending.stage!=campaign.stage and pending.kind==1:campaign.advance_calendar()
    validate_saved_watched(candidate)
    return candidate


class WatchedPublication:
    """[designed] Owner supplies state/template_bytes and a validating view(candidate)."""
    def __init__(self,owner):
        self.owner=owner;self._pending=None

    def begin(self,fixture):
        if self._pending is not None:raise ValueError('a watched job is already pending')
        fixture=copy.deepcopy(fixture)
        original=self.owner.state;snapshot=copy.deepcopy(original)
        candidate=campaign_rounds.prepare(original,self.owner.template_bytes)
        prepare_watched(candidate,self.owner.template_bytes,fixture)
        job=WatchedJob(secrets.token_hex(24),copy.deepcopy(candidate),copy.deepcopy(fixture))
        self._pending=(job.token,original,snapshot,candidate,fixture,bytes(self.owner.template_bytes))
        return job

    def complete(self,token,outcome):
        if self._pending is None or token!=self._pending[0]:raise ValueError('unknown or consumed watched completion token')
        _,original,snapshot,candidate,fixture,template=self._pending
        self._pending=None
        if self.owner.state is not original or self.owner.state!=snapshot or self.owner.template_bytes!=template:
            raise ValueError('watched completion is stale; active state changed')
        candidate=completed_candidate(candidate,fixture,outcome,template)
        self.owner.view(candidate)
        self.owner.state=candidate
        return candidate

    def cancel(self):
        """[designed] Cancellation invalidates the token without publishing state."""
        self._pending=None
