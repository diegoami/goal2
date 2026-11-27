"""[designed: T170c2/#566] Atomic, once-only publication of a completed sealed round into a campaign.

[confirmed: goal2/game/watched_publication.py, T64/#254] The watched path publishes in two phases: a private
preparation that builds the whole candidate, then one owner-checked swap that installs it; a token, a cancel
and an owner staleness check bound the pair. This module keeps that shape and those method names for the
sealed season, and writes no second rule for it. It cannot reuse the watched classes themselves: those are
typed to a watched fixture and WatchedOutcome, which a SeasonObservation is not.

[designed] The campaign of the sealed route is the accepted state/2 the SeasonSession produced, plus the ledger
of calls it has accepted. Results, records, tables, calendars, ordered news and RNG are inside that state:
the session computed them, publication only moves them. It reads either the session's detached
`observe()` and `state`, or the native owner's verified current completion (T170ax).
"""
import copy
import re
import secrets
from dataclasses import dataclass

from goal2.core.views import Memory
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.season import canonical_hash

# [derived: T170b season.py; T170 "stage_end" note] 'complete' and 'deferred-rollover' are the two statuses of a
# finished original call: the second finished the season's final fixtures and stopped before annual
# advancement. 'ready' (no call yet) and 'match' (a call suspended on its Match) are not finished.
PUBLISHABLE = ('complete', 'deferred-rollover')
_COMPARED = ('call_number', 'status', 'input_hash', 'output_hash', 'rng_words')
_INSTALLING = object()
_DIGEST = re.compile(r'[0-9a-f]{64}')
_MANAGEMENT_ACTIONS = ('select-twenty', 'player-position')


@dataclass(frozen=True)
class PublishedCall:
    """One ledger row: what the campaign accepted, identified by call number and both canonical hashes."""
    call_number: int
    status: str
    input_hash: str
    output_hash: str

    @property
    def identity(self):
        return self.call_number, self.input_hash, self.output_hash


@dataclass(frozen=True)
class PublishedManagementEdit:
    """[designed: T170be] An original manager-menu change between season calls."""

    action: str
    input_hash: str
    output_hash: str


@dataclass(frozen=True)
class SeasonJob:
    token: str
    call_number: int


@dataclass(frozen=True)
class _Candidate:
    state: dict
    record: PublishedCall | PublishedManagementEdit


def _management_boundary(image):
    country, = image.managed_countries()
    memory = Memory(image)
    manager = memory.game(1)
    if memory.manager_country(0x80 + manager) != country or memory.game(0x47 + manager):
        raise ValueError('management edit requires the active native manager')
    # [derived: T170aa, Core Desk reader] Index/count, year, stage and rounds.
    calendar = tuple(memory.game(offset, width) for offset, width in
                     ((0x26, 2), (0x28, 2), (0x38, 2), (0x3A, 2), (0x3C, 1), (0x3D, 1)))
    return country, manager, calendar


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
        return tuple(row for row in self._held[1] if isinstance(row, PublishedCall))

    @property
    def revision(self):
        return self._held[2]

    def committed_snapshot(self):
        """[designed: T170ay/T170be] Read state and ordered history from one committed holding."""
        state, ledger, _ = self._held
        return copy.deepcopy(state), ledger

    @classmethod
    def from_committed(cls, state, records, view=None):
        """[designed: T170ay] Restore one checked holding without reapplying its call history."""
        campaign = cls(state, view)
        ledger = tuple(records)
        seen = set()
        previous = None
        for row in ledger:
            if (not isinstance(row, (PublishedCall, PublishedManagementEdit))
                    or any(not isinstance(digest, str) or not _DIGEST.fullmatch(digest)
                           for digest in (row.input_hash, row.output_hash))):
                raise ValueError('invalid native ledger record')
            if isinstance(row, PublishedCall):
                if type(row.call_number) is not int or row.call_number < 1 or row.status not in PUBLISHABLE:
                    raise ValueError('invalid native ledger record')
                if row.identity in seen:
                    raise ValueError('duplicate native ledger record')
                seen.add(row.identity)
            elif row.action not in _MANAGEMENT_ACTIONS or row.input_hash == row.output_hash:
                raise ValueError('invalid native ledger record')
            if previous is not None and previous != row.input_hash:
                raise ValueError('native ledger chain does not connect')
            previous = row.output_hash
        if ledger and previous != campaign.canonical_hash:
            raise ValueError('native ledger does not end at the saved state')
        campaign._held = (campaign._held[0], ledger, len(ledger))
        return campaign

    def has_published(self, call_number, input_hash, output_hash):
        identity = call_number, input_hash, output_hash
        return any(row.identity == identity for row in self.published)

    def publish_management(self, state, *, action, revision, input_hash, output_hash):
        """[designed: T170be] Install an already verified, detached native edit result."""
        if action not in _MANAGEMENT_ACTIONS:
            raise ValueError('unsupported native management action')
        held = self._held
        if type(revision) is not int or revision != held[2] or input_hash != canonical_hash(held[0]):
            raise ValueError('native management edit is stale; the campaign changed')
        rounds = self.published
        if rounds and rounds[-1].status == 'deferred-rollover':
            raise ValueError('native management edit is unavailable after deferred rollover')
        value = copy.deepcopy(state)
        if canonical_hash(value) != output_hash:
            raise ValueError('native management state differs from the declared output')
        tables = engine_tables.load()
        original = Image.from_state(held[0], tables)
        edited = Image.from_state(value, tables)
        if _management_boundary(original) != _management_boundary(edited):
            raise ValueError('native management edit changed the manager or calendar')
        if input_hash == output_hash:
            return None
        record = PublishedManagementEdit(action, input_hash, output_hash)
        candidate = _Candidate(value, record)
        self._view_candidate(candidate)
        if self._held is not held:
            raise ValueError('native management edit is stale; the campaign changed')
        self._install(candidate)
        return record

    def _view_candidate(self, candidate):
        if self._view is not None:
            self._view(copy.deepcopy(candidate))

    def _install(self, candidate):
        """Single assignment of the whole new holding; everything that can fail is computed first."""
        _, ledger, revision = self._held
        row = candidate.record
        if isinstance(row, PublishedCall) and self.has_published(row.call_number, row.input_hash, row.output_hash):
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
        return self._prepare(token, lambda: (session.observe(), session.state))

    def _prepare(self, token, read_boundary):
        pending = self._pending_for(token)
        if self._preparation is not None:
            raise ValueError('season publication is already preparing')
        try:
            self._check_owner(pending)
        except Exception:
            self.cancel()
            raise
        self._preparation = _SeasonPreparation(pending[1], *read_boundary())
        return self._preparation

    def publish_prepared(self, token, preparation):
        """Only the bound, ready preparation may install; a failure anywhere leaves the campaign unchanged."""
        pending = self._pending_for(token)
        if self._preparation in (None, _INSTALLING) or preparation is not self._preparation:
            raise ValueError('unknown or consumed season publication preparation')
        if not preparation.ready:
            raise ValueError('season publication is still preparing')
        self._preparation = _INSTALLING
        try:
            if preparation.error is not None:
                raise preparation.error
            self._check_owner(pending)
            self.campaign._view_candidate(preparation.candidate)
            # The owner callback can close the window or install another round.
            self._pending_for(token)
            self._check_owner(pending)
            self.campaign._install(preparation.candidate)
            return preparation.candidate.record
        finally:
            if self._pending is pending:
                self.cancel()

    def complete(self, token, session):
        preparation = self.prepare_completion(token, session)
        preparation.run()
        return self.publish_prepared(token, preparation)

    def complete_native(self, owner, packet):
        """[designed: T170ax] Install only the acknowledged completion from this owner."""
        observation, state = owner.completed_boundary(packet)
        job = self.begin(observation)
        preparation = self._prepare(job.token, lambda: (observation, state))
        preparation.run()
        return self.publish_prepared(job.token, preparation)

    def cancel(self):
        """Invalidate both token and preparation without publishing."""
        self._pending = None
        self._preparation = None
