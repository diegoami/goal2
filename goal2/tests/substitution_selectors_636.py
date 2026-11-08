"""[designed: owner #636] Actual-UI selectors for the fresh-match acceptance.
Run with the composite live-player/substitution-control worker profile.
Uses existing real Window/BenchScreen/controller/PyPy bridge; never constructs a
fake stop, writes engine bytes, mutates the career, or supplies a pair early.
"""
import copy
import time
from pathlib import Path


def real_worker(controller):
    bridge = controller.bridge
    engine = bridge.shared.engine
    ready = engine.ready or {}
    assert str(ready.get('implementation', '')).lower() == 'pypy', ready
    assert ready.get('pid') == engine.pid and engine.pid is not None
    assert bridge._live_players is True
    assert bridge._substitution_control is True
    return copy.deepcopy(ready)


def stopped_identity(controller, answer):
    return dict(minute=answer.minute, score=list(answer.score), eleven=list(answer.eleven),
                bench=list(answer.bench), budget=answer.left,
                frame_count=controller.bridge._frame_sequence)


def drafts(answer):
    return copy.deepcopy(dict(positions=answer.positions, marking=answer.marking,
                              own=answer.own, first=answer.first))


def source_capture(window, folder, label, *, native=False):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if native:
        assert app.platformName() == 'windows', 'native Windows acceptance requires the real Windows Qt backend'
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (label + '.png')
    assert not path.exists(), 'never overwrite an existing capture'
    window.grab().save(str(path))
    return dict(path=str(path), qt_platform=app.platformName(),
                device_pixel_ratio=window.devicePixelRatioF(), screen=window.screen().name())


def pause_at_lead_boundary(window, pitch, *, wait=120):
    """Existing T190/610 pause selector: one real UI Esc at a recorded frame boundary."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from goal2.game.watched_jobs import LEAD
    from goal2.tests.test_ui_bench_t180 import key
    controller = pitch.controller
    real_worker(controller)
    assert controller.stop is None and not controller.held
    boundary = controller.acked + LEAD
    controller.commentary_paused = True
    deadline = time.monotonic() + wait
    try:
        while controller.bridge._match.received_frames - 1 < boundary:
            if any(kind == 'decision' for kind, value in controller.bridge._match.replies):
                return None  # handle the naturally arrived stop; retry on another running frame
            assert time.monotonic() < deadline, 'worker did not fill the bounded frame lead'
            QApplication.instance().processEvents()
            time.sleep(.001)
        assert controller.bridge._match.received_frames - 1 == boundary
    finally:
        controller.commentary_paused = False
    before = controller.requests
    key(window, Qt.Key.Key_Escape)
    assert controller.requests == before + 1
    return boundary


def request_from_bench(window, screen, desired, *, expected=None, capture=None):
    """Real UI Enter: no pair, one desired-state edit, authoritative stopped ack.

    Pending-operation lock tests separately send an autorepeat and assert it cannot
    consume the new decision or toggle the captured desired boolean again.
    """
    from PySide6.QtCore import Qt
    from goal2.tests.test_ui_bench_t180 import key, pump
    assert type(desired) is bool
    expected = desired if expected is None else expected
    controller = window.match_day.controller
    real_worker(controller)
    assert type(screen).__name__ == 'BenchScreen'
    assert screen.answer.context == 'pause' and not screen.answer.takes_substitutions
    assert screen.answer.chosen == [] and not screen.pending
    current = controller.stop.data['request_substitution']
    assert type(current) is bool
    assert current != desired, 'this UI action is a toggle, retries retain the already captured desired state'
    before = stopped_identity(controller, screen.answer)
    saved = drafts(screen.answer)
    count = len(controller.choices)
    key(window, Qt.Key.Key_Return)
    if capture: capture(window, 'request-pending' if desired else 'cancel-pending')
    pump(lambda: not screen.pending or controller.error, 120, 'request edit was not acknowledged')
    assert controller.error is None
    assert window.current() is screen and controller.stop is not None
    assert controller.stop.data['edited'] is True
    assert controller.stop.data['request_substitution'] is expected
    assert screen.answer.chosen == []
    assert stopped_identity(controller, screen.answer) == before
    assert drafts(screen.answer) == saved
    assert len(controller.choices) == count + 1
    context, body = controller.choices[-1]
    assert context == 'pause' and body['edit_only'] is True
    assert body['request_substitution'] is desired and not body.get('substitutions')
    assert not any(body.get(k) for k in ('positions', 'marking', 'own_tactics'))
    if capture: capture(window, 'request-confirmed' if desired else 'cancel-confirmed')
    return dict(before=before, desired=desired, acknowledged=expected,
                answer=copy.deepcopy(controller.choices[-1]))


def accept_opportunity_with_escape(window, pitch, *, capture=None):
    """Owner UI alias Esc -> accepting Enter; wait for the real legal stop before S19."""
    from PySide6.QtCore import Qt
    from goal2.tests.test_ui_bench_t180 import key, pump
    controller = pitch.controller
    real_worker(controller)
    assert controller.stop.data['context'] == 'substitution_opportunity'
    data = copy.deepcopy(controller.stop.data)
    assert data['timeout_polls'] == (1000 if data['keeper_unavailable'] else 400)
    assert data['poll_ms'] == 10
    count = len(controller.choices)
    if capture: capture(window, 'opportunity-visible')
    key(window, Qt.Key.Key_Escape)
    pump(lambda: (type(window.current()).__name__ == 'BenchScreen'
                  and controller.stop is not None
                  and controller.stop.data['context'] == 'substitution') or controller.error,
         120, 'accepted opportunity did not open the legal bench')
    assert controller.error is None
    screen = window.current()
    assert screen.answer.context == 'substitution' and screen.answer.takes_substitutions
    assert screen.answer.chosen == []
    assert len(controller.choices) == count + 1
    assert controller.choices[-1] == ('substitution_opportunity', {'opportunity':'accept'})
    return screen, data


def outfield_pair(answer, *, taken_off=()):
    """Existing outfield selector; the engine remains responsible for legal acceptance."""
    from goal2.tests.test_ui_bench_t180 import outfield
    assert answer.context == 'substitution' and answer.takes_substitutions and answer.left > 0
    starters = outfield(answer, [w for w in answer.eleven if w not in answer.injured])
    bench = outfield(answer, [w for w in answer.bench if w not in answer.injured and w not in taken_off])
    assert starters and bench
    return starters[0], bench[0]


def swap_immediately(window, screen, pair):
    from goal2.tests.test_ui_bench_t180 import enter_on
    controller = window.match_day.controller
    assert controller.stop.data['context'] == 'substitution'
    assert screen.answer.takes_substitutions and screen.answer.chosen == []
    off, on = pair
    before = stopped_identity(controller, screen.answer)
    count = len(controller.choices)
    enter_on(window, screen, off)
    assert len(controller.choices) == count, 'first player selection must not send a pair'
    enter_on(window, screen, on)
    assert controller.error is None and not screen.pending
    assert on in screen.answer.eleven and off in screen.answer.bench
    assert screen.answer.left == before['budget'] - 1
    assert screen.answer.minute == before['minute'] and screen.answer.score == before['score']
    assert screen.answer.chosen == []
    assert len(controller.choices) == count + 1
    assert controller.choices[-1][0] == 'substitution'
    assert controller.choices[-1][1]['substitutions'] == [[off,on]]
    assert controller.choices[-1][1]['edit_only'] is True
    return copy.deepcopy(controller.choices[-1])
