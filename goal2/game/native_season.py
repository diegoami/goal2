"""[designed: T170aa/#783] Explicit native input and ownership on the shared pipe.

This is not a fresh-career generator. The caller supplies a native state/2 at a
route boundary; no legacy GameState or assistant projection is constructed here.
"""
from copy import deepcopy
from dataclasses import dataclass
import queue
import threading
import time
from zlib import error as ZlibError

from goal2.engine.original_match.image import Image, GAME_PTR, FIXTURES_PTR, FIXTURE_SIZE
from goal2.engine.original_match import route
from goal2.game import engine_tables
from goal2.game.prematch_controller import PrematchController
from goal2.game.season import canonical_hash
from goal2.game.watched_jobs import MatchEngine


def _native(value):
    if not isinstance(value,dict) or value.get('schema')!='original_match.state/2':
        raise ValueError('explicit native state/2 input is required')
    state=deepcopy(value)
    try:
        image=Image.from_state(state,engine_tables.load())
        countries=image.managed_countries()
    except (KeyError,TypeError,IndexError,ValueError,ZlibError) as exc:
        raise ValueError('invalid native state/2 input') from exc
    if len(countries)!=1:raise ValueError('native entry requires one managed country')
    return state,image,countries[0]


@dataclass(frozen=True)
class NativeFixture:
    """[confirmed: Image F023/F024/F030, route87d92501] Actual pending row."""
    index:int
    side_a:int
    side_b:int
    kind:int
    stage:int
    year:int
    state_hash:str

    @classmethod
    def from_boundary(cls,state,country):
        state,image,managed=_native(state)
        if managed!=country:raise ValueError('native manager changed')
        game=image.far(GAME_PTR);memory=image.memory
        if not 0<=game<=len(memory)-0x3E:raise ValueError('invalid native game span')
        index=image.fixture_index();count=image.rd_far(GAME_PTR,0x28)
        at=image.far(FIXTURES_PTR)+FIXTURE_SIZE*(index-1)
        if not 1<=index<count or not 0<=at<=len(memory)-FIXTURE_SIZE:
            raise ValueError('invalid pending native fixture span')
        raw=memory[at:at+FIXTURE_SIZE]
        a,b=(int.from_bytes(raw[off:off+2],'little') for off in (4,6))
        if a==b or any(not 1<=c<=128 for c in (a,b)) or country not in (a,b):
            raise ValueError('pending native fixture does not contain this manager')
        # [confirmed: route._deferred_image] game+3C is the native calendar stage.
        return cls(index,a,b,raw[2],memory[game+0x3C],image.year(),canonical_hash(state))


@dataclass(frozen=True)
class SeasonHandoff:
    """Next driver owns this queue/first packet; the season owner keeps its lease."""
    send:object
    replies:object
    packet:dict


class NativeSeasonOwner:
    """Owner-thread entry/poll, reader-thread queue, asynchronous bounded disposal.

    At prematch the caller gives controller/fixture/replies to HeldPrematchFlow;
    only that flow consumes replies until handoff/close. Observation packets are
    detached native boundaries, never a legacy career publication.
    """
    def __init__(self,owner,state):
        native,_,country=_native(state)
        self.owner=owner;self.managed_country=country;self._thread=threading.get_ident()
        self._initial=native;self._input_hash=canonical_hash(native)
        self._boundary=None;self._observations=[];self._entry_events=[]
        self.replies=queue.Queue();self.controller=None;self.fixture=None
        self._phase='opening';self._expected='open';self._last_request=0
        self._call_number=0
        self._decision_data=None;self._decision=None;self.message=''
        self._closing=False;self._uncertain=False;self._disposed=threading.Event()
        self._terminal_received=threading.Event();self._discard_requested=threading.Event()
        self._never_started=False
        self.shared=MatchEngine.join(owner,self)
        try:
            self.shared.claim(self)
            if self.shared.engine.busy or self.shared.engine.season_active:
                raise ValueError('the shared engine already owns an operation or season')
        except Exception:
            self.shared.release(self);self.shared.leave(owner,self);raise
        engine=self.shared.engine;generation=engine.generation;process=engine.process
        try:engine.season_open(native)
        except Exception as exc:
            self._never_started=process is None and engine.generation==generation
            self._lose(f'{type(exc).__name__}: {exc}',uncertain=True)

    @property
    def status(self):
        if self._disposed.is_set():return 'closed'
        if self._phase=='prematch' and self.controller.status=='lost':return 'lost'
        return self._phase

    @property
    def disposed(self):return self._disposed.is_set()

    @property
    def input_hash(self):return self._input_hash

    @property
    def initial_state(self):return deepcopy(self._initial)

    @property
    def boundary_state(self):return deepcopy(self._boundary)

    @property
    def pid(self):return self.shared.engine.pid

    def _owner(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('native season belongs to the owner thread')

    def put(self,kind,value):
        self.replies.put((kind,value))
        # Keep the lease until delivery, not merely the parser's earlier state
        # update. Otherwise its final reply could reach the next shared client.
        if (kind=='death' or (self._discard_requested.is_set() and kind=='season'
                and isinstance(value,dict) and value.get('action')=='discard')):
            self._terminal_received.set()

    def _lose(self,message,uncertain=False):
        self.message=message;self._phase='lost';self._expected=None
        self._uncertain|=uncertain

    def _request(self,action,**values):
        self._expected=action
        try:self.shared.engine.season_request(action,**values)
        except Exception as exc:self._lose(f'{type(exc).__name__}: {exc}',uncertain=True)

    def advance(self):
        self._owner()
        if self.status!='boundary' or self._expected is not None:
            raise ValueError('advance requires a completed native boundary')
        self.message='';self._phase='advancing';self._request('advance')

    def take_observations(self):
        self._owner();result=deepcopy(self._observations);self._observations=[];return result

    def take_entry_events(self):
        self._owner();result=deepcopy(self._entry_events);self._entry_events=[];return result

    def _accept_boundary(self,value):
        state,image,country=_native(value['state']);obs=value['observation']
        fields={'call_number','status','input_hash','output_hash','played_fixtures','news_pages','rng_words'}
        if (country!=self.managed_country or not isinstance(obs,dict) or set(obs)!=fields
                or type(obs['call_number']) is not int or obs['call_number']<0
                or obs['status'] not in ('ready','complete','match','deferred-rollover')
                or obs['output_hash']!=canonical_hash(state)
                or not isinstance(obs['input_hash'],str) or len(obs['input_hash'])!=64
                or any(c not in '0123456789abcdef' for c in obs['input_hash'])
                or any(not isinstance(obs[k],(list,tuple)) for k in ('played_fixtures','news_pages','rng_words'))
                or len(obs['rng_words'])!=2 or any(type(n) is not int or not 0<=n<=65535 for n in obs['rng_words'])
                or tuple(obs['rng_words'])!=tuple(image.rd(off) for off in route.SEEDS.values())):
            raise ValueError('invalid native boundary observation')
        if value['action']=='open' and (obs['status']!='ready' or obs['call_number']!=0
                or obs['input_hash']!=self.input_hash or obs['output_hash']!=self.input_hash
                or obs['played_fixtures'] or obs['news_pages']):
            raise ValueError('native open differs from the explicit input')
        if value['action']=='advance' and (obs['call_number']!=self._call_number+1
                or obs['input_hash']!=canonical_hash(self._boundary)):
            raise ValueError('native round identity differs from its previous boundary')
        fixture=NativeFixture.from_boundary(state,self.managed_country) if obs['status']=='match' else None
        self._call_number=obs['call_number']
        if fixture is not None:self.fixture=fixture
        self._boundary=state;self._observations.append(deepcopy(value))
        return obs['status']

    def poll(self):
        self._owner()
        if self._closing or self._phase in ('lost','prematch','handed_off'):return self.status
        try:
            while True:
                try:kind,value=self.replies.get_nowait()
                except queue.Empty:break
                if kind=='ready':
                    if (not isinstance(value,dict) or value.get('implementation')!='PyPy'
                            or list(value.get('version',()))[:2]!=[3,11]):
                        raise ValueError('native worker must be PyPy3.11')
                    continue
                if kind in ('death','error'):
                    self._lose(str(value));break
                if (kind not in ('season','season_error') or not isinstance(value,dict)
                        or type(value.get('request')) is not int or value['request']<=self._last_request
                        or self._expected is None):raise ValueError('unexpected native reply')
                self._last_request=value['request']
                if kind=='season_error':
                    # Only advance's proven pure refusal can return to a boundary.
                    if (self._expected=='advance' and value.get('lost') is False
                            and isinstance(value.get('error'),str)):
                        self.message=value['error'];self._phase='boundary';self._expected=None;continue
                    self._lose(str(value.get('error','native operation failed')));break
                action=self._expected
                if value.get('action')!=action:raise ValueError('native reply action mismatch')
                self._expected=None
                if action in ('open','advance'):
                    status=self._accept_boundary(value)
                    if status=='match':
                        self._phase='configuring';self._request('configure')
                    else:self._phase='terminal' if status=='deferred-rollover' else 'boundary'
                elif action=='configure':
                    self._phase='preparing';self._request('next',count=32)
                elif action=='next':
                    events=value.get('events');number=value.get('decision')
                    if not isinstance(events,list) or any(not isinstance(e,dict) or not isinstance(e.get('kind'),str) for e in events):
                        raise ValueError('invalid native entry events')
                    if any(e['kind'] in ('minute','tick','frame','sample','shot','goal') for e in events):
                        raise ValueError('native entry played before pre-match handoff')
                    decisions=[e.get('data') for e in events if e['kind']=='decision']
                    self._entry_events.extend(deepcopy(events))
                    if number is not None:
                        if (type(number) is not int or number<1 or len(decisions)!=1
                                or events[-1]['kind']!='decision' or not isinstance(decisions[0],dict)
                                or decisions[0].get('context')!='pre_match'):
                            raise ValueError('native entry needs its pre-match decision')
                        self._decision,self._decision_data=number,deepcopy(decisions[0])
                        self._request('preview',decision=number)
                    elif decisions or value.get('over') or value.get('exhausted'):
                        raise ValueError('native entry ended without pre-match')
                    else:self._request('next',count=32)
                elif action=='preview':
                    controller=PrematchController(self._send_prematch,self.managed_country)
                    controller.attach(value,self._decision_data,decision=self._decision)
                    if controller.view.sides!=(self.fixture.side_a,self.fixture.side_b):
                        raise ValueError('native preview differs from pending fixture')
                    self.controller=controller;self._phase='prematch'
                    break  # the screen is now the sole consumer of this reply queue
        except (KeyError,TypeError,IndexError,ValueError) as exc:self._lose(f'invalid native reply: {exc}')
        return self.status

    def _send_prematch(self,action,**values):
        self._owner()
        if self._phase!='prematch' or self._closing:raise ValueError('native pre-match lease is not available')
        self.shared.engine.season_request(action,**values)

    def handoff(self):
        self._owner()
        if self._closing or self._phase!='prematch' or self.controller.status!='handoff':
            raise ValueError('no native first-packet handoff is available')
        self._phase='handed_off'
        return SeasonHandoff(self._send_handoff,self.replies,self.controller.handoff)

    def _send_handoff(self,action,**values):
        self._owner()
        if self._closing or self._phase!='handed_off' or action not in ('next','answer','resume','observe'):
            raise ValueError('operation is outside the native match handoff')
        self.shared.engine.season_request(action,**values)

    def close(self):
        self._owner()
        if self._closing:return
        self._closing=True;self._phase='closing'
        if self.controller is not None:self.controller.detach()
        threading.Thread(target=self._retire,name='goal2-native-season-close',daemon=True).start()

    def _retire(self):
        """No UI poll/window is needed to finish disposal; never release live work."""
        engine=self.shared.engine;deadline=time.monotonic()+engine.cancel_deadline
        sent=False;killed=None
        while not self._never_started and not self._terminal_received.is_set():
            process=engine.process
            if self._uncertain or time.monotonic()>=deadline:
                if process is not None and process is not killed:
                    try:process.kill()
                    except ProcessLookupError:pass
                    killed=process
            elif not engine.busy:
                if engine.season_active and not sent:
                    self._discard_requested.set()
                    try:engine.season_request('discard');sent=True
                    except Exception:self._uncertain=True
            try:self.replies.get(timeout=.05)
            except queue.Empty:pass
        self.shared.release(self)
        self.shared.leave(self.owner,self)
        self._disposed.set()
