"""[designed: T183c] Explicit assistant jobs on the owner's existing engine.

Preparation and private candidate work run off the owner thread. Only poll()
validates and publishes; cancellation/refusal/staleness/failure publish nothing.
"""
from copy import deepcopy
import queue
import threading

from goal2.game.best_twenty_state import prepare, candidate
from goal2.game.watched_jobs import MatchEngine


class AssistantStale(ValueError):
    """The requested career changed before publication."""


class _Reply:
    TERMINAL={'assistant','assistant_error','assistant_cancelled','death','error'}

    def __init__(self,shared):
        self.shared=shared
        self.queue=queue.Queue()
        self.ended=threading.Event()

    def put(self,kind,value):
        if kind in ('ready','opened'):
            return
        # [designed: #896] A terminal reply ends the handle and frees the shared engine before it is queued, so
        # the worker that reads it already sees `ended` and no caller who reads the result finds the engine claimed.
        if kind in self.TERMINAL:
            self.ended.set()
            self.shared.release(self)
        self.queue.put((kind,value))


class AssistantJobs:
    """One explicit request at a time; the model owns this bridge across visits."""
    def __init__(self,owner):
        self.owner=owner
        self.shared=MatchEngine.join(owner,self)
        self.closed=False
        self._owner_thread=threading.get_ident()
        self._publication=threading.RLock()
        self._active=False
        self._counter=0
        self.token=None
        # [designed: #896] Accepted requests, counted. `token` is only the request that is still pending,
        # so a caller who reads it after a fast reply cannot tell a refusal from a request that has ended.
        self.starts=0
        self._request=None
        self._handle=None
        self._before=self._identity=None
        self._cancelled=threading.Event()
        self._results=queue.Queue()

    @property
    def busy(self):
        return self._active

    def start(self):
        self._check_owner()
        if self.closed:
            raise ValueError('assistant bridge is closed')
        if self._active:
            self.poll(self.token)
        if self._active:
            raise ValueError('The assistant is still finishing the previous request')
        if getattr(self.owner,'match_pending',False):
            raise ValueError('Finish the current match first')
        identity=self.owner.state
        before=deepcopy(identity)
        handle=_Reply(self.shared)
        self.shared.claim(handle)
        self._counter+=1;self.token=self._counter
        self.starts+=1
        self._identity,self._before=identity,before
        self._handle,self._request=handle,None
        self._cancelled=threading.Event()
        self._results=queue.Queue()
        self._active=True
        threading.Thread(target=self._work,args=(self.token,before,handle,self._cancelled,self._results),
                         name='goal2-assistant',daemon=True).start()
        return self.token

    def _work(self,token,before,handle,cancelled,results):
        # [designed: #896] The result is posted only after the shared engine is released, so a caller who
        # has read it can start the next request at once (before: put, then release in `finally`).
        sent=False;outcome=[]
        try:
            try:
                prepared=prepare(before)
            except ValueError as exc:
                outcome.append((token,{'status':'error','reason':'unavailable','message':str(exc)}))
                return
            if cancelled.is_set():
                outcome.append((token,{'status':'cancelled'}));return
            places=before.squad_capacity-20
            number=(self.shared.engine.assistant(prepared.native,extra_places=places) if places
                    else self.shared.engine.assistant(prepared.native))
            sent=True
            self._request=number
            if cancelled.is_set():
                self.shared.engine.cancel_assistant(number)
            while True:
                try:
                    kind,value=handle.queue.get(timeout=.1)
                    break
                except queue.Empty:
                    if self.closed:
                        outcome.append((token,{'status':'cancelled'}));return
            if cancelled.is_set():
                outcome.append((token,{'status':'cancelled'}));return
            if kind=='assistant_cancelled':
                outcome.append((token,{'status':'cancelled'}));return
            if kind!='assistant':
                message=value.get('error',str(value)) if isinstance(value,dict) else str(value)
                outcome.append((token,{'status':'error','reason':'failed','message':message}));return
            if value['request']!=number or value['input_hash']!=prepared.input_hash:
                raise ValueError('assistant reply differs from the requested snapshot')
            answer=value['result']
            if not answer['allowed']:
                outcome.append((token,{'status':'refused','reason':answer['refusal']}));return
            proposed=candidate(prepared,answer)
            if cancelled.is_set():
                outcome.append((token,{'status':'cancelled'}));return
            recruits=[w for w in proposed.managed_squad if w not in before.managed_squad]
            additional={}
            if places:
                filled={w for w in proposed.extra_squad if w is not None}
                previous={w for w in before.extra_squad if w is not None}
                additional=dict(extra_filled=len(filled),extra_added=len(filled-previous),capacity=before.squad_capacity)
            outcome.append((token,{'status':'complete','candidate':proposed,'recruited':len(recruits),**additional}))
        except Exception as exc:
            outcome.append((token,{'status':'error','reason':'failed','message':f'{type(exc).__name__}: {exc}'}))
        finally:
            try:
                if not sent or handle.ended.is_set() or self.shared.engine.closed:
                    self.shared.release(handle)
            finally:
                if outcome:
                    results.put(outcome[0])

    def cancel(self,token=None):
        with self._publication:
            if not self._active or (token is not None and token!=self.token):
                return False
            self._cancelled.set()
            if self._request is not None:
                self.shared.engine.cancel_assistant(self._request)
            return True

    def poll(self,token=None):
        self._check_owner()
        if token is not None and token!=self.token:
            return None
        if self.closed:
            return {'status':'cancelled'}
        if not self._active:
            return None
        try:
            number,result=self._results.get_nowait()
        except queue.Empty:
            return None
        if number!=self.token:
            return None
        try:
            if self._cancelled.is_set():
                return {'status':'cancelled'}
            if result['status']!='complete':
                return result
            if (getattr(self.owner,'match_pending',False) or self.owner.state is not self._identity
                    or self.owner.state!=self._before):
                raise AssistantStale('Your career changed; ask the assistant again')
            proposed=result.pop('candidate')
            self.owner.view(proposed)
            with self._publication:
                if self._cancelled.is_set() or self.closed:
                    return {'status':'cancelled'}
                if (getattr(self.owner,'match_pending',False) or self.owner.state is not self._identity
                        or self.owner.state!=self._before):
                    raise AssistantStale('Your career changed; ask the assistant again')
                self.owner.state=proposed
                self._active=False
                return result
        finally:
            with self._publication:
                self._active=False
                self._before=self._identity=None

    def close(self):
        if self.closed:
            return
        self.cancel(self.token)
        self.closed=True
        self._active=False
        self._before=self._identity=None
        if getattr(self.owner,'_assistant_jobs',None) is self:
            del self.owner._assistant_jobs
        self.shared.leave(self.owner,self)
        if self._handle is not None and (self.shared.engine.closed or self._handle.ended.is_set()):
            self.shared.release(self._handle)

    def _check_owner(self):
        if threading.get_ident()!=self._owner_thread:
            raise RuntimeError('assistant publication must run on the owner thread')


def for_model(owner):
    jobs=getattr(owner,'_assistant_jobs',None)
    if jobs is None or jobs.closed:
        jobs=owner._assistant_jobs=AssistantJobs(owner)
    return jobs


def close_model(owner):
    jobs=getattr(owner,'_assistant_jobs',None)
    if jobs is not None:
        jobs.close()
