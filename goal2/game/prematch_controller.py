"""[designed: T170y/#770] Confirmed edits over an already-owned season pipe.

[confirmed: T170o/T170s/T170w] EngineProcess checks request/action correlation;
the owner marshals replies here. This coordinator neither opens a career nor
owns/discards the transport. Detach is presentation cleanup, not cancellation.
"""
from copy import deepcopy
import threading

from goal2.game.prematch_view import PrematchView

_OMITTED = object()
_EDITS = {'tactics','substitutions','positions','own_tactics','marking'}


class PrematchController:
    def __init__(self, send, managed_country):
        self._send=send
        self.managed_country=managed_country
        self._thread=threading.get_ident()
        self._status='new';self._view=None;self._message=''
        self._expected=None;self._last_request=0;self._mode=None
        self._candidate=None;self._handoff=None;self._events=[];self._play_refused=False

    @property
    def status(self):return self._status

    @property
    def view(self):return self._view

    @property
    def message(self):return self._message

    @property
    def pending(self):return self._expected is not None

    @property
    def handoff(self):return deepcopy(self._handoff)

    def _owner(self):
        if threading.get_ident()!=self._thread:
            raise RuntimeError('pre-match coordination belongs to the owner thread')

    def attach(self, packet, data, *, decision):
        self._owner()
        if self._status!='new':raise ValueError('create a new coordinator for an explicit new attachment')
        request=packet.get('request') if isinstance(packet,dict) else None
        if type(request) is not int or request<1:raise ValueError('preview has no request identity')
        view=PrematchView.from_preview(packet,data,decision=decision,managed_country=self.managed_country)
        self._view=view;self._last_request=request;self._status='ready'
        return view

    def _ready(self):
        self._owner()
        if self._status!='ready' or self.pending:raise ValueError('wait for the confirmed pre-match view')

    def _request(self, action, **values):
        # Set the phase first: a test/owner may deliver a reply synchronously.
        self._expected=action
        try:self._send(action,**deepcopy(values))
        except Exception as exc:self._lose(f'{type(exc).__name__}: {exc}')

    def edit(self, **fields):
        self._ready()
        if not fields or set(fields)-_EDITS:raise ValueError('unsupported pre-match edit fields')
        self._mode='edit';self._status='answering';self._message='';self._play_refused=False
        self._request('answer',decision=self._view.decision,answer=dict(edit_only=True,**fields))

    def set_team_tactic(self,element,value):
        if type(element) is not int or not 1<=element<=8 or type(value) is not bool:
            raise ValueError('team tactic needs element1..8 and a boolean')
        self.edit(tactics={element:value})

    def swap(self,first,second):self.edit(substitutions=[[first,second]])

    def exchange(self,outgoing,incoming):self.edit(substitutions=[[outgoing,incoming]])

    def set_position(self,word,code):
        if type(code) is not int or not 0<=code<=13:raise ValueError('position must be code0..13')
        self.edit(positions={word:code})

    def club_position(self,word):self.edit(positions={word:'club'})

    def set_own_tactic(self,word,element,value):
        if (type(element) is not int or not 1<=element<=4
                or (value is not None and type(value) is not bool)):
            raise ValueError('own tactic needs element1..4 and False/True/None')
        self.edit(own_tactics={word:{element:value}})

    def set_marking(self,word,target):
        if target is not None and type(target) is not int:
            raise ValueError('marking needs None/zone0/opponent word')
        self.edit(marking={word:target})

    def play(self, *, captain=_OMITTED):
        self._ready()
        self._mode='play';self._status='answering';self._message='';self._play_refused=False
        answer={} if captain is _OMITTED else {'captain':captain}
        self._request('answer',decision=self._view.decision,answer=answer)

    def _lose(self, message):
        self._status='lost';self._message=message;self._view=None
        self._expected=self._candidate=self._handoff=None
        self._events=[]

    def detach(self):
        self._owner()
        self._status='detached';self._view=None;self._expected=self._candidate=self._handoff=None
        self._events=[]

    def take_events(self):
        """Drain pre-match events. First play events belong only to handoff."""
        self._owner()
        events=deepcopy(self._events);self._events=[]
        return events

    def receive(self, kind, value):
        """Owner-thread delivery only. Existing process owner keeps its lease."""
        self._owner()
        if self._status in ('detached','lost'):return
        if kind in ('death','error'):
            self._lose(str(value));return
        try:self._receive(kind,value)
        except (KeyError,TypeError,IndexError,ValueError) as exc:
            self._lose(f'invalid pre-match reply: {exc}')

    def _receive(self, kind, value):
        if (kind not in ('season','season_error') or not isinstance(value,dict)
                or type(value.get('request')) is not int or value['request']<=self._last_request
                or self._expected is None):
            raise ValueError('stale or unexpected reply')
        self._last_request=value['request']
        if kind=='season_error':
            if type(value.get('lost')) is not bool or not isinstance(value.get('error'),str):
                raise ValueError('malformed refusal')
            if value['lost'] or self._expected!='answer':
                self._lose(value['error']);return
            self._message=value['error'];self._status='ready';self._expected=None
            return
        action=self._expected
        if value.get('action')!=action:raise ValueError('reply is for another operation')
        self._expected=None
        if action=='answer':
            self._status='reading'
            self._request('next',count=1 if self._mode=='play' else 32)
        elif action=='next':
            events=value.get('events')
            if not isinstance(events,list) or any(not isinstance(e,dict) or not isinstance(e.get('kind'),str) for e in events):
                raise ValueError('invalid event batch')
            if self._mode=='edit' and any(e['kind'] in ('minute','tick','frame','sample','goal','shot') for e in events):
                raise ValueError('edit unexpectedly played on')
            decisions=[e.get('data') for e in events if e['kind']=='decision']
            number=value.get('decision')
            if (number is None and decisions) or (number is not None and
                    (len(decisions)!=1 or events[-1]['kind']!='decision')):
                raise ValueError('decision identity/event mismatch')
            self._events.extend(deepcopy(events))
            for event in events:
                if event['kind']=='refused':
                    self._message=str(event.get('data',{}).get('reason','The original refused the action'))
                    self._play_refused=True
            if number is not None:
                if type(number) is not int or number<=self._view.decision:raise ValueError('old decision')
                if not decisions or not isinstance(decisions[-1],dict):raise ValueError('missing decision event')
                data=decisions[-1]
                if data.get('context')=='pre_match':
                    self._candidate=(number,deepcopy(data));self._status='previewing'
                    self._request('preview',decision=number)
                    return
                if self._mode!='play':raise ValueError('edit left pre-match context')
            elif self._mode=='edit' or self._play_refused:
                if value.get('exhausted') or value.get('over'):raise ValueError('pre-match edit/refusal ended its stream')
                if any(e['kind'] in ('minute','tick','frame','sample') for e in events):raise ValueError('edit unexpectedly played on')
                self._request('next',count=1 if self._mode=='play' else 32)
                return
            # The next driver owns this packet; don't duplicate its events in
            # the pre-match presentation queue as well.
            if events:del self._events[-len(events):]
            self._handoff=deepcopy(value);self._status='handoff'
        elif action=='preview':
            number,data=self._candidate
            view=PrematchView.from_preview(value,data,decision=number,managed_country=self.managed_country)
            self._view=view;self._candidate=None;self._status='ready'
        else:raise ValueError('unexpected operation')
