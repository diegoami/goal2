"""[designed: T80] Original competitive Play, independent of friendly Watch/Quick.

[derived: T65; T160] Reuse the watched bridge: its replies, publication and lifecycle, on the owner's one
engine process (goal2.game.watched_jobs.MatchEngine), which it shares with the watched bridge.
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


class CompetitiveJobs(WatchedJobs):
    """[designed] Separate bridge/token; parent owns state and match-pending exclusion."""
    KIND = 'competitive'   # [designed: T160] on the owner's engine process, under PyPy 3.11 (WatchedJobs.start, #496)

    def __init__(self, owner, *, command=None):
        if getattr(owner, '_competitive_jobs', None) is not None:
            raise ValueError('active game already has a competitive bridge')
        owner._competitive_jobs = self
        self._owns_pending = False
        self._setup(owner, CompetitivePublication(owner), command)

    def start(self, *, reference_seed=None, delay_byte=None, record_draws=False, frames=False, bench=False,
              prompts=False):
        """[designed: T80] Play the pending qualifier. [designed: T176] With `frames` and `bench` it is watched
        (WatchedController): the same `competitive` match on the engine process with the pitch samples and the
        bench, published by the same CompetitivePublication. [designed: T167, #541] `prompts` also asks the player
        prompts (the set-piece taker, the shoot-out order, the menu before extra time; WatchedJobs.start)."""
        if self.closed or self.busy:
            raise ValueError('competitive bridge is closed or a match is already running')
        if getattr(self.owner, 'match_pending', False):
            raise ValueError('Another match is already running; finish or cancel it first')
        fixture = pending_fixture(self.owner.state)
        try:
            token = super().start(fixture, reference_seed=reference_seed, delay_byte=delay_byte,
                                  record_draws=record_draws, frames=frames, bench=bench, prompts=prompts)
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
        self._leave()
