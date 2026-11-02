"""[designed: T80] Original competitive Play, independent of friendly Watch/Quick.

[derived: T65] Reuse the bounded JSON journal decoder and owned-child lifecycle.
[confirmed: T51/E034 at424d599] CompetitivePublication validates the full original
result, returned Memory, input image and post-match completion before publication.
"""
import sys
import zipfile
import zlib
import struct
from goal2.engine.original_match import Fixture
from goal2.game.watched_jobs import WatchedJobs
from goal2.game.watched_publication import CompetitivePublication


def pending_fixture(state):
    """[designed] Bind Play to the supplied calendar identity; never invent a draw."""
    from goal2.engine.original_match.match import KINDS
    pending = state.campaign.next_fixture if state.campaign else None
    if pending is None or pending.kind == 1 or pending.kind not in KINDS:
        raise ValueError('No supported pending competitive fixture; use Quick or friendly Watch')
    try:
        index = int(pending.fixture_id.removeprefix('original:'))
    except ValueError as exc:
        raise ValueError('Competitive Play needs an original:<number> scheduled fixture') from exc
    if pending.fixture_id != f'original:{index}':
        raise ValueError('Competitive Play needs an original:<number> scheduled fixture')
    return Fixture(pending.side_a, pending.side_b, index, pending.kind)


def require_runtime():
    """[designed] Refuse before launch with the install command, preserving management."""
    try:
        import unicorn  # noqa: F401 — optional dependency, loaded only on Play
    except ImportError as exc:
        raise ValueError("Competitive Play needs the original runtime: install with python3 -m pip install '.[desktop,watched]'") from exc


class CompetitiveJobs(WatchedJobs):
    """[designed] Separate bridge/token; parent owns state and match-pending exclusion."""
    WORKER = 'goal2.desktop.competitive_worker'   # under PyPy 3.11, chosen at the start (WatchedJobs.start, #496)

    def __init__(self, owner, *, command=None):
        if getattr(owner, '_competitive_jobs', None) is not None:
            raise ValueError('active game already has a competitive bridge')
        owner._competitive_jobs = self
        self.owner = owner
        self.publication = CompetitivePublication(owner)
        self.command = None if command is None else list(command)
        self.process = None
        self.token = None
        self.outcome = None
        self.events = []
        self.closed = False
        self._owns_pending = False

    def start(self, *, reference_seed=None, delay_byte=None, record_draws=False):
        if self.closed or self.busy:
            raise ValueError('competitive bridge is closed or a match is already running')
        if getattr(self.owner, 'match_pending', False):
            raise ValueError('Another match is already running; finish or cancel it first')
        require_runtime()
        fixture = pending_fixture(self.owner.state)
        try:
            token = super().start(fixture, reference_seed=reference_seed,
                                  delay_byte=delay_byte, record_draws=record_draws)
        except (ValueError, OSError, zipfile.BadZipFile, zlib.error, struct.error, IndexError, KeyError) as exc:
            raise ValueError(f'Cannot start competitive Play: {exc}. Check the local game resources and runtime') from exc
        self._owns_pending = True
        self.owner.match_pending = True
        return token

    def poll(self, token):
        try:
            return super().poll(token)
        except ValueError as exc:
            raise ValueError(f'Competitive Play failed: {exc}') from exc

    def _release(self):
        try:
            super()._release()
        finally:
            if self._owns_pending:
                self.owner.match_pending = False
                self._owns_pending = False

    def close(self):
        if self.busy:
            self.cancel(self.token)
        self.closed = True
        if getattr(self.owner, '_competitive_jobs', None) is self:
            del self.owner._competitive_jobs
