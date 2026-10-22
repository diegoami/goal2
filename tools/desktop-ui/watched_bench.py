#!/usr/bin/env python3
"""[designed: T102] A half-time swap end to end: the real window, the real SDL pitch view, the
worker; the bench opens at half time, the keyboard alone makes the swap, and the published game and
the match equal the vendored Match called directly with the same answer.

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/watched_bench.py
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2];sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop.window import ManagementWindow
from goal2.desktop.bench_page import VIEW
from goal2.desktop.fixed_page import problems
from goal2.engine.original_match import Match
from goal2.game import campaign_rounds
from goal2.tests.test_pygame_match_view import model, pump
from goal2.tests.test_watched_adapter import direct_image
from goal2.tests.test_watched_bench_t102 import fixture_of


def direct(state, template, fixture, pair):
    """The vendored Match on an independently written image: `pair` at half time, play on elsewhere."""
    state = campaign_rounds.prepare(state, template, competitive=False)
    match = Match(direct_image(state), fixture, managed=state.managed_country, captain=state.captain or None,
                  record_draws=True, delay_byte=0)
    events = []
    for ev in match.events():
        events.append(asdict(ev))
        if ev.kind == 'decision':
            match.answer(substitutions=[pair]) if ev.data['context'] == 'half_time' else match.answer()
    return match.result(), hashlib.sha256(match.memory_component()).hexdigest(), events


def main():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        m = model(Path(folder) / 'bench.g2save');w = ManagementWindow(m);w.show();app.processEvents()
        try:
            w.confirm_draft();app.processEvents()
            before = m.state;fixture = fixture_of(before)
            eleven = list(before.starting_eleven);bench = [x for x in before.managed_squad if x not in eleven]
            # Fastest, so the scenario is short; the pacing and the bench are the same at every speed.
            start = w.watched.start;w.watched.start = lambda **kw: start(**{**kw, 'playback_rate': 240})
            w.start_watched();assert w.watched.busy, w.status.text()
            seen = []
            def at_half_time():
                decision = w.bench.decision
                if decision is not None and decision.data['context'] != 'half_time':
                    seen.append(decision.data['context']);w.bench.escape()
                return decision is not None and decision.data['context'] == 'half_time'
            pump(at_half_time, app=app, timeout=300)
            assert w.watched.display.board() == 'HALF TIME', w.watched.display.board()
            assert w.fixture_views.currentIndex() == VIEW and w.bench.roster.hasFocus()
            assert w.bench.counter.text() == 'substitutions left 5', w.bench.counter.text()
            assert problems(w) == [], problems(w)
            # The keyboard alone: select, Enter, select, Enter, Play.
            roster = w.bench.roster
            QTest.keyClick(roster, Qt.Key.Key_Down);QTest.keyClick(roster, Qt.Key.Key_Down)
            QTest.keyClick(roster, Qt.Key.Key_Return)
            for _ in range(11):QTest.keyClick(roster, Qt.Key.Key_Down)
            QTest.keyClick(roster, Qt.Key.Key_Return)
            pair = [eleven[2], bench[2]];assert w.bench.chosen == [pair], w.bench.chosen
            QTest.keyClick(roster, Qt.Key.Key_Tab);QTest.keyClick(w.bench.play, Qt.Key.Key_Return)
            def done():
                if w.bench.decision is not None:
                    seen.append(w.bench.decision.data['context']);w.bench.escape()
                return not w.watched.busy
            pump(done, app=app, timeout=600)
            report = w.watched.reports[0]
            assert report['made'] == [pair] and report['refused'] == [] and report['substitutions_left'] == 4, report
            outcome = w.watched.engine.outcome
            result, memory, events = direct(before, m.template_bytes, fixture, pair)
            assert [asdict(e) for e in outcome.events] == events, 'events differ from the vendored Match'
            assert outcome.result == result and hashlib.sha256(outcome.memory).hexdigest() == memory
            assert pair[1] in m.state.starting_eleven and pair[0] not in m.state.starting_eleven
            assert pair[1] in m.state.managed_squad[:11]
            print(json.dumps({'pair': pair, 'score': outcome.result['score'], 'other_decisions': seen,
                              'memory_sha256': memory, 'report': report}, indent=2))
            print('PASS T102 half-time swap: bench by keyboard, seed-exact, substitute kept in the eleven')
        finally:
            w.close();w.deleteLater();app.processEvents()


if __name__ == '__main__':
    main()
