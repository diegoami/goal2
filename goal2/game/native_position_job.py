"""[designed: T170bh] One detached edit on the native career owner's shared pipe."""

from queue import Empty, Queue
from threading import Event, Thread

from goal2.game.watched_jobs import MatchEngine


class NativePositionJob:
    """Hold the lease through terminal delivery, independent of the screen's lifetime."""

    def __init__(self, owner, state, revision, player, key):
        self.replies = Queue()
        self.results = Queue()
        self.cancelled = Event()
        self.owner = owner
        self.shared = MatchEngine.join(owner, self)
        try:
            self.shared.claim(self)
            Thread(target=self._run, args=(state, revision, player, key),
                   name='goal2-native-position', daemon=False).start()
        except Exception:
            self._release()
            raise

    def put(self, kind, value):
        if kind in ('position', 'position_error', 'position_cancelled', 'death'):
            self.replies.put((kind, value))

    def cancel(self):
        self.cancelled.set()

    def poll(self):
        try:
            return self.results.get_nowait()
        except Empty:
            return None

    def _release(self):
        self.shared.release(self)
        self.shared.leave(self.owner, self)

    def _run(self, state, revision, player, key):
        result = ('position_cancelled', None)
        try:
            if not self.cancelled.is_set():
                result = self._request(state, revision, player, key)
        except Exception as exc:
            result = ('position_error', {'error': str(exc)})
        finally:
            self._release()
        self.results.put(result)

    def _request(self, state, revision, player, key):
        engine = self.shared.engine
        try:
            request = engine.edit_position(state, revision=revision, player=player, key=key)
        except OSError:
            # A partial write makes the stream unusable. Retire the child before freeing the lease.
            process = engine.process
            if process is not None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                while self.replies.get()[0] != 'death':
                    pass
            raise
        cancelling = False
        while True:
            if not cancelling and self.cancelled.is_set():
                engine.cancel_position(request)
                cancelling = True
            try:
                kind, value = self.replies.get(timeout=.05)
            except Empty:
                continue
            if self.cancelled.is_set():
                return 'position_cancelled', None
            return kind, value
