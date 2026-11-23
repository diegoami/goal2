"""[designed: T170ac/#810] Paced pull consumer of one retained native Match.

No Match factory, guessed selection, default answer or legacy publication.
The season owner retains its lease; only explicit resume adopts a new boundary.
"""
from collections import deque
from copy import deepcopy
import math
import queue
import threading

from goal2.desktop.match_view import SPEEDS
from goal2.game.season_pitch import validate_batch
from goal2.game.season_worker import ANSWER_FIELDS


class NativeMatchDriver:
    def __init__(self,owner,connection=None):
        if not owner.frames_enabled:raise ValueError('native driver requires frames enabled before entry')
        self.owner=owner;self.connection=owner.handoff() if connection is None else connection
        self._thread=threading.get_ident();self._state='playing';self._expected=None
        self._request=0;self._limit=1;self._sequence=0;self._watermark=0;self._total=0
        self._events=[];self._frames=[];self._pending_frames=deque();self._decision=None
        self._stopped_view=None
        self._over=self._exhausted=False;self._handled=-1;self._presented=-1;self._painted=-1
        self._visible=0;self._frame=None;self._due=0.;self.speed=3;self.quick=False;self.held=False
        self._pause_wanted=False;self._pause_latched=False;self.pause_requests=0;self.dropped_pauses=0
        self.choices=[];self.message='';self.error=None;self.boundary_status=None
        first=self.connection.packet
        if (not isinstance(first,dict) or type(first.get('event_count')) is not int
                or not isinstance(first.get('events'),list)):
            self._fail('invalid native handoff');return
        self.event_base=first['event_count']-len(first['events'])
        if self.event_base<0:self._fail('invalid native handoff offset');return
        self._total=self.event_base
        try:self._batch(first,1)
        except (ValueError,KeyError,TypeError,IndexError) as exc:self._fail(str(exc))

    def _owner(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('native driver belongs to the owner thread')

    def _drained(self):return not self._pending_frames and self._handled==self._sequence-1

    @property
    def status(self):
        if self._state!='playing':return self._state
        if self._expected is not None:return 'pending'
        if self._drained():
            if self._decision is not None:return 'decision'
            if self._over and self._exhausted:return 'complete'
        return 'playing'

    @property
    def pending(self):return self._expected is not None

    @property
    def waiting(self):return deepcopy(self._decision) if self.status=='decision' else None

    @property
    def stopped_view(self):
        self._owner()
        return self._stopped_view if self.status=='decision' else None

    def request_view(self):
        """[designed: T170af] One explicit read, on this connection's decision."""
        self._owner()
        if self.status!='decision':raise ValueError('current view needs a ready native decision')
        self._stopped_view=None;self.message=''
        self._send('stopped_preview',decision=self._decision['decision'])

    @property
    def events(self):return deepcopy(self._events)

    def events_since(self, start):
        """[designed: T170ad/#814] Detached append-only suffix for UI cursors."""
        self._owner()
        if type(start) is not int or not 0 <= start <= len(self._events):
            raise ValueError('invalid native event cursor')
        return deepcopy(self._events[start:])

    @property
    def shown_count(self):return self._visible

    @property
    def frames(self):return deepcopy(self._frames)

    @property
    def frame(self):return deepcopy(self._frame)

    @property
    def painted_sequence(self):return self._painted

    def shown(self):return deepcopy(self._events[:self._visible])

    def _fail(self,message):
        self.error=message;self._state='lost';self._expected=None;self._stopped_view=None
        self.owner.close()

    def _send(self,action,**values):
        self._expected=action
        try:self.connection.send(action,**deepcopy(values))
        except Exception as exc:self._fail(f'{type(exc).__name__}: {exc}')

    def _batch(self,value,limit):
        if type(value.get('request')) is not int or value['request']<=self._request:
            raise ValueError('stale native batch')
        sequence,watermark,total=validate_batch(value,self._sequence,self._watermark,self._total,limit)
        for event in value['events']:
            if (set(event)!={'kind','minute','score','data'} or type(event['minute']) is not int or event['minute']<0
                    or not isinstance(event['score'],(list,tuple)) or len(event['score'])!=2
                    or any(type(n) is not int or n<0 for n in event['score']) or not isinstance(event['data'],dict)):
                raise ValueError('invalid native canonical event')
        if value['decision'] is not None and value['events'][-1]['data'].get('context')=='pre_match':
            raise ValueError('native driver received a pre-match decision')
        if value['exhausted'] and (not value['over'] or value['decision'] is not None):
            raise ValueError('native stream exhausted before completion')
        self._request=value['request'];self._sequence,self._watermark,self._total=sequence,watermark,total
        self._events.extend(deepcopy(value['events']));self._frames.extend(deepcopy(value['frames']))
        self._pending_frames.extend(deepcopy(value['frames']))
        if value['decision'] is not None:
            self._stopped_view=None
            self._decision=dict(decision=value['decision'],event=deepcopy(value['events'][-1]))
            if self._pause_wanted:self.dropped_pauses+=1
            self._pause_wanted=False;self._pause_latched=False
        self._over,self._exhausted=value['over'],value['exhausted']

    def _receive(self,kind,value):
        if kind in ('death','error'):raise ValueError(f'native worker ended: {value}')
        if (kind not in ('season','season_error') or not isinstance(value,dict)
                or self._expected is None or type(value.get('request')) is not int
                or value['request']<=self._request):raise ValueError('unexpected native driver reply')
        action=self._expected
        if kind=='season_error':
            if (type(value.get('lost')) is not bool or not isinstance(value.get('error'),str)
                    or value['lost']):raise ValueError(str(value.get('error','native request failed')))
            self._request=value['request'];self._expected=None;self.message=value['error']
            if action=='pause':self._pause_wanted=False;self._pause_latched=False;self.dropped_pauses+=1
            elif action=='resume':self._state='playing'
            elif action not in ('answer','stopped_preview'):raise ValueError('native stream could not advance')
            return
        if value.get('action')!=action:raise ValueError('native driver reply action mismatch')
        if action=='next':self._batch(value,self._limit)
        elif action=='stopped_preview':
            from goal2.game.stopped_view import StoppedMatchView
            if self._decision is None:raise ValueError('native stopped read lost its decision')
            self._stopped_view=StoppedMatchView.from_packet(value,request=self._request+1,
                decision=self._decision['decision'],managed_country=self.owner.managed_country,
                data=self._decision['event']['data'])
            self._request=value['request']
        elif action=='answer':
            self._request=value['request'];self._decision=None
        elif action=='pause':
            if (type(value.get('paused')) is not bool or (not value['paused'] and not isinstance(value.get('reason'),str))):
                raise ValueError('invalid native pause reply')
            self._request=value['request'];self._pause_wanted=False;self._pause_latched=value['paused']
            if not value['paused']:self.message=value['reason'];self.dropped_pauses+=1
        elif action=='resume':
            self.boundary_status=self.owner.adopt_resume(value,self.connection)
            if self.boundary_status=='lost':raise ValueError(self.owner.message)
            self._request=value['request'];self._state='resumed'
        self._expected=None

    def _pull(self):
        if self._state!='playing' or self.pending or not self._drained() or self._decision is not None:return
        if self._pause_wanted:
            if self._over:self._pause_wanted=False;self.dropped_pauses+=1
            else:self._send('pause');return
        if not self._exhausted:
            self._limit=32 if self.quick else 1;self._send('next',count=self._limit)

    def tick(self,now):
        self._owner()
        if type(now) not in (int,float) or not math.isfinite(now):raise ValueError('invalid native playback clock')
        if self._state in ('closed','lost','resumed'):return None
        # [designed: T170af] Covered menus may finish their pure stopped read.
        # Other held playback behavior, queued samples and deadlines stay intact.
        if self.held and self._state=='playing' and self._expected not in (None,'stopped_preview'):return None
        try:
            for _ in range(32):
                try:kind,value=self.connection.replies.get_nowait()
                except queue.Empty:break
                self._receive(kind,value)
                if self._state=='resumed':return None  # queue now belongs to the season owner again
            if self.held and self._state=='playing':return None
            if self.quick:
                if self._presented>self._handled:self._handled=self._presented
                while self._pending_frames:self._handled=self._pending_frames.popleft()['sequence']
                self._visible=len(self._events)
            elif self._pending_frames and self._presented==self._handled and now>=self._due:
                frame=self._pending_frames.popleft();self._frame=frame;self._presented=frame['sequence']
                self._visible=max(self._visible,frame['watermark']-self.event_base)
                self._due=now+1/SPEEDS[self.speed][1]
                return deepcopy(frame)
            if self._drained() and (self._decision is not None or self._exhausted):self._visible=len(self._events)
            self._pull()
        except (ValueError,KeyError,TypeError,IndexError) as exc:self._fail(str(exc))
        return None

    def painted(self,sequence):
        self._owner()
        if self._state in ('closed','lost','resumed'):return False
        if type(sequence) is not int:raise ValueError('invalid native painted sample')
        if sequence<=self._handled:return False
        if sequence!=self._presented or sequence!=self._handled+1:raise ValueError('sample was not delivered to paint')
        self._painted=sequence;self._handled=sequence;return True

    def step_speed(self,step):
        self._owner()
        if type(step) is not int:raise ValueError('speed step must be an integer')
        self.speed=max(0,min(len(SPEEDS)-1,self.speed+step));self._due=0

    def set_held(self,held):
        self._owner()
        if type(held) is not bool:raise ValueError('held must be boolean')
        self.held=held
        if not held:self._due=0

    def quick_result(self):self._owner();self.quick=True

    def request_pause(self):
        self._owner()
        if (self._state!='playing' or self._decision is not None or self._over
                or self._pause_wanted or self._pause_latched or self._expected=='pause'):return False
        self._pause_wanted=True;self.pause_requests+=1;return True

    def answer(self,values):
        self._owner()
        if self.status!='decision':raise ValueError('native decision is not ready for an answer')
        if not isinstance(values,dict) or set(values)-ANSWER_FIELDS or 'captain' in values:
            raise ValueError('invalid in-match native answer')
        self._stopped_view=None
        self.message='';self.choices.append((self._decision['event']['data'].get('context'),deepcopy(values)))
        self._send('answer',decision=self._decision['decision'],answer=values)

    def resume(self):
        self._owner()
        if self.status!='complete':raise ValueError('native resume needs actual completion and drained samples')
        self._stopped_view=None;self._state='resuming';self._send('resume')

    def close(self):
        self._owner()
        if self._state=='closed':return
        completed=self._state=='resumed';self._state='closed';self._expected=None;self._stopped_view=None
        if not completed:self.owner.close()
