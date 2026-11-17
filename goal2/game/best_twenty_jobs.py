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
        self.queue.put((kind,value))
        if kind in self.TERMINAL:
            self.ended.set()
            self.shared.release(self)


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
        self._identity,self._before=identity,before
        self._handle,self._request=handle,None
        self._cancelled=threading.Event()
        self._results=queue.Queue()
        self._active=True
        threading.Thread(target=self._work,args=(self.token,before,handle,self._cancelled,self._results),
                         name='goal2-assistant',daemon=True).start()
        return self.token

    def _work(self,token,before,handle,cancelled,results):
        sent=False
        try:
            try:
                prepared=prepare(before)
            except ValueError as exc:
                results.put((token,{'status':'error','reason':'unavailable','message':str(exc)}))
                return
            if cancelled.is_set():
                results.put((token,{'status':'cancelled'}));return
            number=self.shared.engine.assistant(prepared.native)
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
                        results.put((token,{'status':'cancelled'}));return
            if cancelled.is_set():
                results.put((token,{'status':'cancelled'}));return
            if kind=='assistant_cancelled':
                results.put((token,{'status':'cancelled'}));return
            if kind!='assistant':
                message=value.get('error',str(value)) if isinstance(value,dict) else str(value)
                results.put((token,{'status':'error','reason':'failed','message':message}));return
            if value['request']!=number or value['input_hash']!=prepared.input_hash:
                raise ValueError('assistant reply differs from the requested snapshot')
            answer=value['result']
            if not answer['allowed']:
                results.put((token,{'status':'refused','reason':answer['refusal']}));return
            proposed=candidate(prepared,answer)
            if cancelled.is_set():
                results.put((token,{'status':'cancelled'}));return
            recruits=[w for w in proposed.managed_squad if w not in before.managed_squad]
            results.put((token,{'status':'complete','candidate':proposed,'recruited':len(recruits)}))
        except Exception as exc:
            results.put((token,{'status':'error','reason':'failed','message':f'{type(exc).__name__}: {exc}'}))
        finally:
            if not sent or handle.ended.is_set() or self.shared.engine.closed:
                self.shared.release(handle)

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
