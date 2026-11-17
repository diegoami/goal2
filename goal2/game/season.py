"""[designed: T170b/#652] Transient ownership of the accepted sealed route.

[confirmed: archaeology 0f9f, original_match/route.py] One play_round call may
hold an ordinary Match; only its own completed Match may resume that call.
This module adds detached observations, not a calendar or match decision policy.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

from goal2.engine.original_match import route
from goal2.engine.original_match.image import Image
from goal2.engine.original_match.port.tables import from_record,to_record,TablesError
from goal2.game import engine_tables


def canonical_hash(state):
    """[designed: T170b] Hash the canonical JSON form of an accepted state/2."""
    return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                                     allow_nan=False).encode('ascii')).hexdigest()


@dataclass(frozen=True)
class SeasonObservation:
    """Detached boundary data; mutable nested values never alias the session.

    Deltas belong only to the advance/resume return that first exposes them.
    observe() is a pure snapshot with empty deltas. Match results retain their
    own pre-tail seeds; rng_words here are the current route boundary's words.
    """
    call_number: int
    status: str
    input_hash: str
    output_hash: str
    played_fixtures: tuple
    news_pages: tuple
    rng_words: tuple


class SeasonSession:
    """Own state/2, verified tables, persistent keys and a live continuation.

    advance() starts exactly one original call. While it holds a match, the
    caller drives pending_match normally and passes that same object to resume.
    No active-session serialization, automatic team choice or annual advance.
    """
    def __init__(self,state,tables=None,keys=None):
        accepted=engine_tables.load()
        # A caller's mutable Tables object is neither trusted nor retained.
        checked=from_record(to_record(accepted if tables is None else tables))
        if (checked.sha256,checked.ds,checked.code_data)!=(accepted.sha256,accepted.ds,accepted.code_data):
            raise TablesError('season tables differ from the accepted engine tables')
        value=deepcopy(state)
        Image.from_state(value,checked)  # Validate before retaining any state.
        self._tables=checked
        self._state=value
        self._keys=keys if isinstance(keys,route.Keys) else route.Keys(route.DEFAULT_KEYS if keys is None else keys)
        self._pending=None
        self._continuation=None
        self._status='ready'
        self._call_number=0
        self._input_hash=canonical_hash(value)
        self._fixture_cursor=self._news_cursor=0

    @property
    def state(self):
        return deepcopy(self._state)

    @property
    def pending_match(self):
        """The actual ordinary Match, intentionally retained within this process."""
        return self._pending

    def _observation(self,fixtures=(),pages=(),*,state=None):
        value=self._state if state is None else state
        image=Image.from_state(value,self._tables)
        memory=image.memory;ds=image.DS*16
        words=tuple(int.from_bytes(memory[ds+off:ds+off+2],'little') for off in route.SEEDS.values())
        return SeasonObservation(self._call_number,self._status,self._input_hash,canonical_hash(value),
                                 deepcopy(tuple(fixtures)),deepcopy(tuple(pages)),words)

    def observe(self):
        """Read detached current boundary data without delivering deltas again."""
        return self._observation()

    def select_twenty(self):
        """[designed: T183e/#773] Explicit assistant at a completed manager boundary.

        [confirmed: T183a/F031 and #771] Use the original preparation/selection
        on private native state. A refusal never publishes its prepared state.
        This synchronous owner operation consumes no round or persistent key;
        worker cancellation and window delivery belong to their own contract.
        """
        if (self._status not in ('ready','complete') or self._pending is not None
                or self._continuation is not None):
            raise ValueError('the assistant needs a completed manager boundary without a held match')
        from goal2.game.best_twenty import recommend
        answer=recommend(deepcopy(self._state))
        allowed=answer['allowed']
        if type(allowed) is not bool:
            raise ValueError('invalid assistant completion')
        selection=deepcopy(dict(allowed=allowed,refusal=answer['refusal'],
                                country=answer['country'],manager=answer['manager'],
                                changed=answer['changed'] if allowed else False,
                                recruited=answer['recruited'] if allowed else []))
        value=deepcopy(answer['state']) if allowed else self._state
        # Validate and construct all return data before the single commit.
        # Round identity, key policy and delta cursors deliberately stay put.
        observed=self._observation(state=value)
        if allowed:
            self._state=value
        return dict(selection=selection,observation=observed)

    def _accept(self,step,new_call=False,input_hash=None):
        # Upstream observations are shallow. Copy every nested published value.
        value=deepcopy(step.state)
        fixtures=deepcopy(step.played_fixtures)
        pages=deepcopy(step.news_pages)
        fixture_start=0 if new_call else self._fixture_cursor
        page_start=0 if new_call else self._news_cursor
        if new_call:
            self._call_number+=1
            self._input_hash=input_hash
        self._state=value
        self._status=step.status
        self._pending=step.match
        self._continuation=step.continuation
        self._fixture_cursor=len(fixtures)
        self._news_cursor=len(pages)
        return self._observation(fixtures[fixture_start:],pages[page_start:])

    def advance(self):
        if self._status=='deferred-rollover':
            return self.observe()
        if self._status not in ('ready','complete'):
            raise ValueError('complete the pending match and resume its original call first')
        value=deepcopy(self._state)
        input_hash=canonical_hash(value)
        step=route.play_round(value,self._tables,self._keys)
        return self._accept(step,new_call=True,input_hash=input_hash)

    def resume(self,match):
        # Reject before entering the backend, changing counters or consuming keys.
        if self._status!='match' or self._pending is None or match is not self._pending:
            raise ValueError('foreign or already consumed season match')
        if not match.over:
            raise ValueError('season match is incomplete')
        step=route.resume_round(self._continuation,match)
        return self._accept(step)
