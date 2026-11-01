"""[designed: T64] Transport-neutral private watched jobs and once-only atomic publication.
[confirmed: E033 at3656a2d26e0f57a410d648edeaa6cd9eb7d1f607] result() follows the original tail.
Workers/UI integration is T65/T66; no process or widget owns this active-state swap.
"""
import copy
import secrets
from dataclasses import dataclass
from goal2.engine.original_match import Image, Fixture
from goal2.game import campaign_rounds
from goal2.game.watched_match import prepare_watched, sealed, WatchedOutcome
from goal2.game.watched_schema import ENGINE_ID, RESULT_SCHEMA, COMPETITIVE_SCHEMA, validate_result, validate_saved_watched, resolution


@dataclass(frozen=True)
class WatchedJob:
    token: str
    state: object
    fixture: Fixture


def completed_candidate(state,fixture,outcome,template,*,competitive=False):
    """[designed] Build every returned field and ledger privately, never quick Python effects."""
    if not isinstance(outcome,WatchedOutcome):raise ValueError('completed watched outcome required')
    result=outcome.result;engine=validate_result(result,competitive=competitive)
    schema=COMPETITIVE_SCHEMA if competitive else RESULT_SCHEMA
    if competitive and (result['kind']!=fixture.kind or result['substitution_budget']!=[5,5]):
        raise ValueError('completed kind or budget differs from competitive job')
    kinds=[getattr(event,'kind',None) for event in outcome.events]
    if (not kinds or kinds[-1]!='end' or kinds.count('end')!=1 or kinds.count('full_time')!=1
            or (result['first'],result['second'],result['index'],result['managed'])!=
                (fixture.first,fixture.second,fixture.index,state.managed_country)):
        raise ValueError('watched completion differs from the pending fixture or is incomplete')
    if competitive:
        from goal2.game.competitive_match import prepare_competitive
        expected_image=prepare_competitive(state,template,fixture)
    else:expected_image=prepare_watched(state,template,fixture)
    # [designed: T151] The engine's input is the sealed form of the prepared image.
    if result['image_sha256'] != sealed(expected_image).sha256():
        raise ValueError('watched completion differs from the declared input image')
    expected_year=expected_image.year()
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
    # [confirmed: F029; A-WATCH-8; E015-r0007 state 215] The original keeps a substitute in the
    # eleven: its squad words hold the swap into the next match. [designed: T102, as T47's quick
    # halftime] The managed side's substitutions, in the order made, replace the player taken off
    # in the selection, and a substituted captain by the incoming player; no swap, no change.
    side=int(state.managed_country==fixture.second)
    for swap in result.get('substitutions',()):
        if swap.get('team')==side and swap['off'] in candidate.starting_eleven:
            candidate.starting_eleven[candidate.starting_eleven.index(swap['off'])]=swap['on']
            if candidate.captain==swap['off']:candidate.captain=swap['on']
    candidate.country_tactics=candidate.countries[state.managed_country][0x2D]
    candidate.rng_seed_7b62,candidate.rng_seed_8336=outcome.seeds
    candidate.match_count+=1
    candidate.last_match={'engine':engine,'schema':schema,'original':copy.deepcopy(result),
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
                'score':score,'winner':result['winner'] if competitive else 2 if score[0]==score[1] else int(score[1]>score[0]),'mode':'watched',
                'engine':engine,'schema':schema,'seed_before':state.rng_seed_7b62,
                'seed_after':outcome.seeds[0],'secondary_after':outcome.seeds[1],
                'engine_year':outcome.engine_year,'index':fixture.index,
                'setup_seed':fixture.index*(outcome.engine_year+1)&65535})
        compact=resolution(result) if competitive else None
        if competitive and campaign.world is not None:world.results[-1]['resolution']=copy.deepcopy(compact)
        campaign.complete_fixture(pending.fixture_id,resolution=compact)
        campaign.results.append({'fixture_id':pending.fixture_id,'teams':[fixture.first,fixture.second],
            'score':list(result['score']),'engine':engine,'schema':schema})
        if competitive:campaign.results[-1]['resolution']=copy.deepcopy(compact)
        if campaign.world is not None:
            campaign_rounds.silent_until_managed(candidate,template,campaign_rounds.SilentResolver)
            campaign_rounds.validate_state(candidate)
        pending=campaign.next_fixture
        if pending is not None and pending.stage!=campaign.stage and pending.kind==1:campaign.advance_calendar()
    validate_saved_watched(candidate)
    return candidate


class _CompletionPreparation:
    """[designed: #254] Private computation only; no owner reference or state swap."""
    def __init__(self, candidate, fixture, outcome, template, competitive):
        self.inputs = candidate, fixture, outcome, template
        self.competitive = competitive
        self.candidate = None
        self.error = None
        self.ready = False

    def run(self):
        try:
            self.candidate = completed_candidate(*self.inputs, competitive=self.competitive)
        except BaseException as exc:
            self.error = exc
        finally:
            self.ready = True


class WatchedPublication:
    """[designed] Owner supplies state/template_bytes and a validating view(candidate)."""
    _competitive=False

    def __init__(self,owner):
        self.owner=owner;self._pending=None;self._preparation=None

    def begin(self,fixture):
        if self._pending is not None:raise ValueError('a watched job is already pending')
        fixture=copy.deepcopy(fixture)
        original=self.owner.state;snapshot=copy.deepcopy(original)
        candidate=campaign_rounds.prepare(original,self.owner.template_bytes,competitive=self._competitive)
        if self._competitive:
            from goal2.game.competitive_match import prepare_competitive
            prepare_competitive(candidate,self.owner.template_bytes,fixture)
        else:prepare_watched(candidate,self.owner.template_bytes,fixture)
        job=WatchedJob(secrets.token_hex(24),copy.deepcopy(candidate),copy.deepcopy(fixture))
        self._pending=(job.token,original,snapshot,candidate,fixture,bytes(self.owner.template_bytes))
        return job

    def _pending_for(self,token):
        if self._pending is None or token!=self._pending[0]:
            raise ValueError('unknown or consumed watched completion token')
        return self._pending

    def _check_owner(self,pending):
        _,original,snapshot,_,_,template=pending
        if self.owner.state is not original or self.owner.state!=snapshot or self.owner.template_bytes!=template:
            raise ValueError('watched completion is stale; active state changed')

    def prepare_completion(self,token,outcome):
        """[designed: #254] Bind private computation before leaving the owner thread."""
        pending=self._pending_for(token)
        if self._preparation is not None:
            raise ValueError('watched completion is already preparing')
        try:
            self._check_owner(pending)
        except Exception:
            self.cancel()
            raise
        _,_,_,candidate,fixture,template=pending
        self._preparation=_CompletionPreparation(candidate,fixture,outcome,template,self._competitive)
        return self._preparation

    def publish_prepared(self,token,preparation):
        """[designed: #254] Only the bound prepared candidate may swap active state."""
        pending=self._pending_for(token)
        if self._preparation is None or preparation is not self._preparation:
            raise ValueError('unknown or consumed watched completion preparation')
        if not preparation.ready:
            raise ValueError('watched completion is still preparing')
        self.cancel()
        if preparation.error is not None:
            raise preparation.error
        self._check_owner(pending)
        self.owner.view(preparation.candidate)
        self.owner.state=preparation.candidate
        return preparation.candidate

    def complete(self,token,outcome):
        """[designed] Synchronous callers retain validated once-only publication."""
        preparation=self.prepare_completion(token,outcome)
        preparation.run()
        return self.publish_prepared(token,preparation)

    def cancel(self):
        """[designed] Invalidate both token and prepared result without publishing."""
        self._pending=None
        self._preparation=None


class CompetitivePublication(WatchedPublication):
    """[designed: T51] Explicit competitive jobs retain T64 once-only atomic publication."""
    _competitive=True
