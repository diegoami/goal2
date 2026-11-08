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

    def _observation(self,fixtures=(),pages=()):
        image=Image.from_state(self._state,self._tables)
        memory=image.memory;ds=image.DS*16
        words=tuple(int.from_bytes(memory[ds+off:ds+off+2],'little') for off in route.SEEDS.values())
        return SeasonObservation(self._call_number,self._status,self._input_hash,canonical_hash(self._state),
                                 deepcopy(tuple(fixtures)),deepcopy(tuple(pages)),words)

    def observe(self):
        """Read detached current boundary data without delivering deltas again."""
        return self._observation()

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
