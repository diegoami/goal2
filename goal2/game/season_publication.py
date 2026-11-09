"""[designed: T170c2/#566] Atomic, once-only publication of a completed sealed round into a campaign.

[confirmed: goal2/game/watched_publication.py, T64/#254] The watched path publishes in two phases: a private
preparation that builds the whole candidate, then one owner-checked swap that installs it; a token, a cancel
and an owner staleness check bound the pair. This module keeps that shape and those method names for the
sealed season, and writes no second rule for it. It cannot reuse the watched classes themselves: those are
typed to a watched fixture and WatchedOutcome, which a SeasonObservation is not.

[designed] The campaign of the sealed route is the accepted state/2 the SeasonSession produced, plus the ledger
of calls it has accepted. Results, records, tables, calendars, ordered news and RNG are inside that state:
the session computed them, publication only moves them. Publication reads the session's public, detached
`observe()` and `state`; it never touches the Match, the continuation or the backend, and never calls the route.
No UI, wire or watched job is involved.
"""
import copy
import secrets
from dataclasses import dataclass

from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.season import canonical_hash

# [derived: T170b season.py; T170 "stage_end" note] 'complete' and 'deferred-rollover' are the two statuses of a
# finished original call: the second finished the season's final fixtures and stopped before annual
# advancement. 'ready' (no call yet) and 'match' (a call suspended on its Match) are not finished.
PUBLISHABLE = ('complete', 'deferred-rollover')
_COMPARED = ('call_number', 'status', 'input_hash', 'output_hash', 'rng_words')


@dataclass(frozen=True)
class PublishedCall:
    """One ledger row: what the campaign accepted, identified by call number and both canonical hashes."""
    call_number: int
    status: str
    input_hash: str
    output_hash: str


@dataclass(frozen=True)
class SeasonJob:
    token: str
    call_number: int


@dataclass(frozen=True)
class _Candidate:
    state: dict
    record: PublishedCall


class SeasonCampaign:
    """[designed] Holds one accepted state/2 and the ledger of the calls published into it.

    `view(candidate)` is the owner's validating hook, as `owner.view` is for WatchedPublication: it runs on the
    finished candidate immediately before the swap and refuses by raising. It is the single production seam
    between preparation and installation, and the one the atomicity test uses to inject a failure there.
    """

    def __init__(self, state, view=None):
        value = copy.deepcopy(state)
        Image.from_state(value, engine_tables.load())  # Validate before retaining anything.
        self._view = view
        self._held = (value, (), 0)  # state, ledger, revision: replaced as one unit, never edited in place.

    @property
    def state(self):
        return copy.deepcopy(self._held[0])

    @property
    def canonical_hash(self):
        return canonical_hash(self._held[0])

    @property
    def published(self):
        return self._held[1]

    @property
    def revision(self):
        return self._held[2]

    def has_published(self, call_number, input_hash, output_hash):
        return any((row.call_number, row.input_hash, row.output_hash) == (call_number, input_hash, output_hash)
                   for row in self._held[1])

    def _view_candidate(self, candidate):
        if self._view is not None:
            self._view(candidate)

    def _install(self, candidate):
        """Single assignment of the whole new holding; everything that can fail is computed first."""
        _, ledger, revision = self._held
        row = candidate.record
        if self.has_published(row.call_number, row.input_hash, row.output_hash):
            raise ValueError(f'season call {row.call_number} is already published')
        self._held = (candidate.state, ledger + (row,), revision + 1)


class _SeasonPreparation:
    """[designed: as watched_publication._CompletionPreparation] Private computation only; no campaign reference."""

    def __init__(self, observation, observed, state):
        self.inputs = observation, observed, state
        self.candidate = None
        self.error = None
        self.ready = False

    def run(self):
        try:
            self.candidate = _build_candidate(*self.inputs)
        except BaseException as exc:
            self.error = exc
        finally:
            self.ready = True


def _name(observation):
    return f'season call {observation.call_number}'


def _build_candidate(observation, observed, state):
    """[designed] The complete candidate, built and checked before any campaign is touched."""
    if tuple(getattr(observed, k) for k in _COMPARED) != tuple(getattr(observation, k) for k in _COMPARED):
        raise ValueError(f'{_name(observation)} changed since it was begun; the session is at '
                         f'call {observed.call_number} ({observed.status})')
    if canonical_hash(state) != observation.output_hash:
        raise ValueError(f"{_name(observation)}: the session's state differs from the observation's output hash")
    Image.from_state(state, engine_tables.load())
    return _Candidate(state, PublishedCall(observation.call_number, observation.status,
                                           observation.input_hash, observation.output_hash))


class SeasonPublication:
    """[designed] begin / prepare_completion / publish_prepared / complete / cancel, as WatchedPublication."""

    def __init__(self, campaign):
        self.campaign = campaign
        self._pending = None
        self._preparation = None

    def begin(self, observation):
        if self._pending is not None:
            raise ValueError('a season publication is already pending')
        if observation.status not in PUBLISHABLE:
            raise ValueError(f'{_name(observation)} is {observation.status}, not complete; nothing to publish')
        campaign = self.campaign
        if campaign.has_published(observation.call_number, observation.input_hash, observation.output_hash):
            raise ValueError(f'{_name(observation)} is already published')
        if observation.input_hash != campaign.canonical_hash:
            raise ValueError(f"{_name(observation)} does not start from the campaign's state")
        observation = copy.deepcopy(observation)
        job = SeasonJob(secrets.token_hex(24), observation.call_number)
        self._pending = (job.token, observation, campaign.revision, campaign.canonical_hash)
        return job

    def _pending_for(self, token):
        if self._pending is None or token != self._pending[0]:
            raise ValueError('unknown or consumed season publication token')
        return self._pending

    def _check_owner(self, pending):
        _, _, revision, digest = pending
        if self.campaign.revision != revision or self.campaign.canonical_hash != digest:
            raise ValueError('season publication is stale; the campaign changed')

    def prepare_completion(self, token, session):
        """Bind private computation: the session's detached observation and state are read here, once."""
        pending = self._pending_for(token)
        if self._preparation is not None:
            raise ValueError('season publication is already preparing')
        try:
            self._check_owner(pending)
        except Exception:
            self.cancel()
            raise
        self._preparation = _SeasonPreparation(pending[1], session.observe(), session.state)
        return self._preparation

    def publish_prepared(self, token, preparation):
        """Only the bound, ready preparation may install; a failure anywhere leaves the campaign unchanged."""
        pending = self._pending_for(token)
        if self._preparation is None or preparation is not self._preparation:
            raise ValueError('unknown or consumed season publication preparation')
        if not preparation.ready:
            raise ValueError('season publication is still preparing')
        self.cancel()
        if preparation.error is not None:
            raise preparation.error
        self._check_owner(pending)
        self.campaign._view_candidate(preparation.candidate)
        self.campaign._install(preparation.candidate)
        return preparation.candidate.record

    def complete(self, token, session):
        preparation = self.prepare_completion(token, session)
        preparation.run()
        return self.publish_prepared(token, preparation)

    def cancel(self):
        """Invalidate both token and preparation without publishing."""
        self._pending = None
        self._preparation = None
