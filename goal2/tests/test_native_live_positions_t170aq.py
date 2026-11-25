"""[designed: T170aq] Position edits at the verified retained bench."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_numeric_single_position_belongs_to_the_current_legal_roster(self):
        for context, flag in (('half_time', 'half_time_edit'), ('substitution', 'substitution_edit')):
            with self.subTest(context=context):
                worker = SeasonWorker()
                data = dict(context=context, substitutions_now=True, eleven=[11], bench=[12, 0])
                match = Mock(waiting=data)
                worker.session = SimpleNamespace(pending_match=match)
                worker.decision = 7
                request = dict(op='season', action='answer', request=1, decision=7, **{flag: True})
                valid = {'edit_only': True, 'positions': {'12': 8}}
                for bad in ({'12': True}, {'12': 'club'}, {'12': '8'}, {'12': 14}, {'12': -1},
                            {'13': 8}, {'0': 8}, {True: 8}, {'012': 8}, {'11': 8, '12': 1}):
                    with self.subTest(bad=bad), self.assertRaises(SeasonRequestError):
                        worker.dispatch(dict(request, answer=dict(valid, positions=bad)))
                    self.assertEqual(worker.decision, 7)
                for fields in ({'context': 'pause'}, {'context': 'extra_time'}, {'substitutions_now': False}):
                    match.waiting = dict(data, **fields)
                    with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                        worker.dispatch(dict(request, answer=valid))
                match.waiting = data
                with self.assertRaises(SeasonRequestError):
                    worker.dispatch(dict(request, answer=dict(valid, substitutions=[[11, 12]])))
                with self.assertRaises(SeasonRequestError):
                    worker.dispatch(dict(request, decision=6, answer=valid))
                match.answer.assert_not_called()
                worker.dispatch(dict(request, answer=valid))
                match.answer.assert_called_once_with(edit_only=True, positions={12: 8})
                self.assertIsNone(worker.decision)


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_both_benches_hold_r_and_c_and_preserve_the_selected_word(self):
        for context, flag in (('half_time', 'half_time_edit'), ('substitution', 'substitution_edit')):
            with self.subTest(context=context):
                self.exercise(context, flag)

    def exercise(self, context, flag):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import COUNTRIES_PTR, COUNTRY_SIZE, Image, PLAYERS_PTR, PLAYER_SIZE
        from goal2.engine.original_match.screens import SUBS_LEFT
        from goal2.game import engine_tables
        from goal2.game.season import canonical_hash
        from goal2.tests.test_native_driver_t170ac import event
        from goal2.tests.test_native_opportunity_t170am import sample
        from goal2.tests.test_native_pitch_t170ad import WindowControls
        from goal2.tests.test_stopped_view_t170af import respond
        from goal2.tests.ui_assertions import assert_fits
        from goal2.ui.s22_help import HelpScreen

        WindowControls.setUpClass()
        case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        case.half_time_controls = context == 'half_time'
        case.substitution_controls = context == 'substitution'
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        case.owner.managed_country = 7

        packet = sample(False)
        tables = engine_tables.load()
        image = Image.from_state(packet['state'], tables)
        image.memory[image.DS * 16 + SUBS_LEFT] = 0
        words = image.squad(7)
        word = words[1]
        record = image.far(PLAYERS_PTR) + PLAYER_SIZE * word
        image.memory[record + 7] = 6
        roster = image.far(COUNTRIES_PTR) + COUNTRY_SIZE * 7
        data = packet['data']

        def stage(number, position, edited=False):
            image.memory[record + 6] = position
            image.memory[roster:roster + 40] = b''.join(w.to_bytes(2, 'little') for w in words)
            players = image.players()
            data.update(context=context, eleven=words[:11], bench=words[11:], substitutions_left=0, edited=edited,
                        positions=[[w, players[w][6]] for w in words if w],
                        player_records=[[w, players[w].hex()] for w in words if w])
            state = image.state(tables)
            packet['state'] = state
            packet['preview'].update(decision=number, state_hash=canonical_hash(state),
                                     data_hash=canonical_hash(data))
            case.owner.batch(events=[event('decision', data)], decision=number, total=number + 1)
            case.tick()

        case.tick()
        stage(3, 13)
        page = case.win.current()
        respond(case.owner, packet)
        case.tick()
        self.assertEqual(case.failures, [])
        self.assertIn('Club position:', page.details.text())
        assert_fits(self, case.win)
        case.key(Qt.Key.Key_Right)
        self.assertFalse(page.next_position.isEnabled())
        case.key(Qt.Key.Key_R)
        self.assertFalse(any(operation == 'answer' for operation, _ in case.owner.sent))
        case.key(Qt.Key.Key_Left)
        case.key(Qt.Key.Key_Down)
        self.assertEqual(page.players[page.row], word)
        self.assertTrue(page.next_position.isEnabled())
        self.assertFalse(page.substitute.isEnabled())

        case.key(Qt.Key.Key_R)
        case.key(Qt.Key.Key_C)
        case.key(Qt.Key.Key_Return)
        expected = ('answer', {'decision': 3, flag: True,
                               'answer': {'edit_only': True, 'positions': {word: 0}}})
        self.assertEqual(case.owner.sent[-1], expected)
        self.assertEqual(sum(operation == 'answer' for operation, _ in case.owner.sent), 1)
        case.key(Qt.Key.Key_F1)
        case.owner.reply('answer')
        case.tick()
        words.insert(4, words.pop(1))
        stage(4, 0, edited=True)
        respond(case.owner, packet)
        case.tick()
        self.assertIsInstance(case.win.current(), HelpScreen)
        self.assertEqual(page.row, 4)
        self.assertEqual(page.players[page.row], word)
        self.assertEqual(page.state.players[word][6], 0)
        case.key(Qt.Key.Key_Escape)

        QTest.mouseClick(page.club_position, Qt.MouseButton.LeftButton)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 4, flag: True,
                             'answer': {'edit_only': True, 'positions': {word: 6}}}))
        case.owner.reply('answer')
        case.tick()
        stage(5, 6, edited=True)
        respond(case.owner, packet)
        case.tick()
        self.assertEqual(page.players[page.row], word)
        self.assertEqual(page.state.players[word][6], 6)
        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 5, 'answer': {}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.failures, [])
        self.assertEqual(case.decisions, [])


def actual_positions(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot
    from goal2.game.watched_pitch import snapshot
    from goal2.tests.test_native_opportunity_t170am import reach_requested_opportunity

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    worker, ask, opportunity, _ = reach_requested_opportunity(raw)
    match = worker.session.pending_match
    ask('answer', decision=opportunity, answer={'opportunity': 'accept'}, choice_answer=True)
    batch = ask('next', count=32)
    starting = batch['events'][-1]['data']
    assert starting['context'] == 'substitution' and starting['substitutions_now'] is True
    records = {word: bytes.fromhex(record) for word, record in starting['player_records']}
    word = next(word for word in starting['eleven'] if word and 2 <= records[word][6] < 13
                and records[word][6] == records[word][7])
    club = records[word][7]
    baseline = Match.load(match.save())
    direct = iter(baseline.events())

    def compare_next():
        sequence, watermark = worker.frame_sequence, worker.event_count
        packet = ask('next', count=32)
        events, frames = [], []
        for index, event in enumerate(direct, 1):
            if event.kind == 'tick':
                frames.append(snapshot(baseline, event, sequence + len(frames), watermark + len(events)))
            else:
                events.append(asdict(event))
            if event.kind == 'decision' or index == 32:
                break
        assert packet['events'] == events and packet['frames'] == frames
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        assert worker.session.pending_match is match
        return packet

    def read(current):
        number = current['decision']
        packet = ask('stopped_preview', decision=number)
        return StoppedMatchSnapshot.from_packet(packet, request=packet['request'], decision=number,
                                                managed_country=match.opts['managed'], data=current['events'][-1]['data'])

    positions = []
    for target in (club + 1, club):
        decision = batch['decision']
        saved = match.save()
        before = read(batch)
        assert match.save() == saved
        answer = {'edit_only': True, 'positions': {word: target}}
        for number, invalid in ((decision - 1, answer), (decision, dict(answer, positions={word: 'club'})),
                                (decision, dict(answer, positions={word: True})),
                                (decision, dict(answer, tactics={5: True}))):
            try:
                ask('answer', decision=number, answer=invalid, substitution_edit=True)
            except SeasonRequestError:
                assert worker.decision == decision and match.save() == saved
            else:
                raise AssertionError('Invalid position input consumed the stop')

        baseline.answer(**answer)
        ask('answer', decision=decision, answer=answer, substitution_edit=True)
        batch = compare_next()
        assert batch['decision'] > decision and not batch['frames']
        after = read(batch)
        assert after.context == 'substitution' and after.data['edited'] is True
        position = dict(after.data['positions'])[word]
        assert position == target
        assert sorted(after.data['eleven']) == sorted(before.data['eleven'])
        assert sorted(after.data['bench']) == sorted(before.data['bench'])
        assert after.data['substitutions_left'] == before.data['substitutions_left']
        assert any(row['kind'] == 'position' and row['data']['player'] == word
                   and row['data']['position'] == target for row in batch['events'])
        positions.append(position)

    baseline.answer()
    ask('answer', decision=batch['decision'], answer={})
    assert compare_next()['frames']
    return dict(club=club, positions=positions)


class Actual(unittest.TestCase):
    def test_live_next_and_club_positions_match_direct_sdk(self):
        result = pypy_engine.call(__name__ + ':actual_positions', reference_raw())
        self.assertEqual(result['positions'], [result['club'] + 1, result['club']])
