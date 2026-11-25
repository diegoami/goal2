"""[designed: T170an] Legal retained substitution after the timed notice."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_worker_accepts_only_one_current_legal_pair(self):
        available = bytearray(20)
        available[14] = 10
        data = dict(context='substitution', eleven=[11], bench=[12, 13],
                    substitutions_now=True, substitutions_left=1,
                    player_records=[[12, available.hex()], [13, bytes(20).hex()]])
        worker = SeasonWorker()
        match = Mock(waiting=data)
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        request = dict(op='season', action='answer', request=1, decision=7, substitution_edit=True)
        valid = {'edit_only': True, 'substitutions': [[11, 12]]}
        for fields in ({'decision': 6}, {'substitution_edit': 1}, {'half_time_edit': True},
                       {'answer': dict(valid, substitutions=[[11, 13]])},
                       {'answer': dict(valid, substitutions=[[True, 12]])},
                       {'answer': dict(valid, substitutions=[[11, 12], [11, 12]])},
                       {'answer': dict(valid, positions={12: 7})}):
            with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=valid) | fields)
            self.assertEqual(worker.decision, 7)
        for fields in ({'context': 'half_time'}, {'context': 'substitution_opportunity'},
                       {'substitutions_left': 0}, {'substitutions_now': False}):
            match.waiting = dict(data, **fields)
            with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=valid))
            self.assertEqual(worker.decision, 7)
        match.answer.assert_not_called()
        match.waiting = data
        worker.dispatch(dict(request, answer=valid))
        self.assertIsNone(worker.decision)
        match.answer.assert_called_once_with(**valid)


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_a_verified_pair_refreshes_roster_and_budget_before_explicit_play(self):
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
        from goal2.ui.native_half_time import NativeSubstitutionScreen
        from goal2.ui.s22_help import HelpScreen

        WindowControls.setUpClass()
        case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        case.substitution_controls = True
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        case.owner.managed_country = 7

        packet = sample(False)
        data = packet['data']
        tables = engine_tables.load()
        image = Image.from_state(packet['state'], tables)
        budget_offset = image.DS * 16 + SUBS_LEFT
        image.memory[budget_offset] = 2
        starters, bench = data['eleven'], data['bench']
        outgoing = starters[1]
        players = image.players()
        available = [word for word in bench if word and 0 < players[word][14] < 128 and not players[word][16] & 0xA4]
        injured, incoming = available[:2]
        image.memory[image.far(PLAYERS_PTR) + PLAYER_SIZE * injured + 14] = 0
        data.update(context='substitution', substitutions_left=2)

        def refresh(number):
            words = data['eleven'] + data['bench']
            current = image.players()
            data['positions'] = [[word, current[word][6]] for word in words if word]
            data['player_records'] = [[word, current[word].hex()] for word in words if word]
            packet['state'] = image.state(tables)
            packet['preview'].update(decision=number, state_hash=canonical_hash(packet['state']),
                                     data_hash=canonical_hash(data))

        refresh(3)
        case.tick()
        case.owner.batch(events=[event('decision', data)], decision=3, total=4)
        case.tick()
        page = case.win.current()
        self.assertIsInstance(page, NativeSubstitutionScreen)
        respond(case.owner, packet)
        case.tick()
        self.assertEqual(case.failures, [])
        self.assertEqual(page.budget.text(), 'Substitutions left: 2')
        self.assertEqual(page.players, tuple(starters + bench))
        assert_fits(self, case.win)
        case.key(Qt.Key.Key_Right)
        self.assertFalse(page.substitute.isEnabled())
        case.key(Qt.Key.Key_Left)
        answer = {'edit_only': True, 'substitutions': [[outgoing, incoming]]}
        with self.assertRaises(ValueError):
            page.driver.answer_substitution(2, answer)

        case.key(Qt.Key.Key_Down)
        case.key(Qt.Key.Key_X)
        QTest.mouseClick(page.roster.rows[11 + bench.index(injured)], Qt.MouseButton.LeftButton)
        case.key(Qt.Key.Key_X)
        self.assertIn('unavailable', page.status.text())
        self.assertFalse(any(operation == 'answer' for operation, _ in case.owner.sent))
        QTest.mouseClick(page.roster.rows[11 + bench.index(incoming)], Qt.MouseButton.LeftButton)
        QTest.mouseClick(page.substitute, Qt.MouseButton.LeftButton)
        case.key(Qt.Key.Key_X)
        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 3, 'answer': answer, 'substitution_edit': True}))
        self.assertEqual(sum(operation == 'answer' for operation, _ in case.owner.sent), 1)

        case.key(Qt.Key.Key_F1)
        self.assertIsInstance(case.win.current(), HelpScreen)
        case.owner.reply('answer')
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('next', {'count': 32}))
        after = starters.copy(), bench.copy()
        after[0][1], after[1][bench.index(incoming)] = incoming, outgoing
        roster = image.far(COUNTRIES_PTR) + 7 * COUNTRY_SIZE
        words = after[0] + after[1]
        image.memory[roster:roster + 40] = b''.join(word.to_bytes(2, 'little') for word in words)
        image.memory[budget_offset] = 1
        data.update(eleven=after[0], bench=after[1], substitutions_left=1, edited=True)
        refresh(4)
        case.owner.batch(events=[event('decision', data)], decision=4, total=5)
        case.tick()
        respond(case.owner, packet)
        case.tick()
        self.assertIsInstance(case.win.current(), HelpScreen)
        case.key(Qt.Key.Key_Escape)
        self.assertIs(case.win.current(), page)
        self.assertEqual(page.players, tuple(words))
        self.assertEqual(page.budget.text(), 'Substitutions left: 1')

        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 4, 'answer': {}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.decisions, [])
        self.assertEqual(case.failures, [])

        case.tick()
        data.update(edited=False, refused='The original refused the eleven.')
        refresh(5)
        case.owner.batch(events=[event('decision', data)], decision=5, total=6)
        case.tick()
        retry = case.win.current()
        self.assertIsInstance(retry, NativeSubstitutionScreen)
        self.assertIsNot(retry, page)
        respond(case.owner, packet)
        case.tick()
        self.assertEqual(retry.status.text(), data['refused'])


def actual_substitution(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot
    from goal2.game.watched_pitch import snapshot
    from goal2.tests.test_native_opportunity_t170am import reach_requested_opportunity

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    worker, ask, number, _ = reach_requested_opportunity(raw)
    match = worker.session.pending_match
    ask('answer', decision=number, answer={'opportunity': 'accept'}, choice_answer=True)
    legal = ask('next', count=32)
    number = legal['decision']
    data = legal['events'][-1]['data']
    assert data['context'] == 'substitution' and data['substitutions_now'] is True

    def read(decision, expected):
        packet = ask('stopped_preview', decision=decision)
        return StoppedMatchSnapshot.from_packet(packet, request=packet['request'], decision=decision,
                                                managed_country=match.opts['managed'], data=expected)

    before = read(number, data)
    saved = match.save()
    records = {word: bytes.fromhex(record) for word, record in data['player_records']}
    outgoing = data['eleven'][1]
    assert records[outgoing][6] != 0
    incoming = next(word for word in data['bench'] if word and records[word][6] != 0
                    and 0 < records[word][14] < 128 and not records[word][16] & 0xA4)
    answer = {'edit_only': True, 'substitutions': [[outgoing, incoming]]}
    for decision, bad in ((number - 1, answer), (number, dict(answer, substitutions=[[incoming, outgoing]])),
                          (number, dict(answer, quick=True))):
        try:
            ask('answer', decision=decision, answer=bad, substitution_edit=True)
        except SeasonRequestError:
            assert worker.decision == number and match.save() == saved
        else:
            raise AssertionError('An invalid substitution consumed the stop')

    baseline = Match.load(saved)
    stream = iter(baseline.events())

    def compare_batch():
        seq, watermark = worker.frame_sequence, worker.event_count
        batch = ask('next', count=32)
        events, frames = [], []
        for index, event in enumerate(stream, 1):
            if event.kind == 'tick':
                frames.append(snapshot(baseline, event, seq + len(frames), watermark + len(events)))
            else:
                events.append(asdict(event))
            if event.kind == 'decision' or index == 32:
                break
        assert batch['events'] == events and batch['frames'] == frames
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        assert worker.session.pending_match is match
        return batch

    baseline.answer(**answer)
    ask('answer', decision=number, answer=answer, substitution_edit=True)
    edited = compare_batch()
    assert edited['decision'] > number and not edited['frames']
    after = read(edited['decision'], edited['events'][-1]['data'])
    assert after.data['edited'] is True and after.context == 'substitution'
    assert after.data['substitutions_left'] == before.data['substitutions_left'] - 1
    assert incoming in after.data['eleven'] and outgoing not in after.data['eleven']
    assert any(row['kind'] == 'substitution' and row['data']['off'] == outgoing and row['data']['on'] == incoming
               for row in edited['events'])

    baseline.answer()
    ask('answer', decision=edited['decision'], answer={})
    resumed = compare_batch()
    assert resumed['frames'], [(row['kind'], row['data'].get('context'), row['data'].get('refused'))
                               for row in resumed['events']]
    return dict(budget_before=before.data['substitutions_left'], budget_after=after.data['substitutions_left'])


class Actual(unittest.TestCase):
    def test_actual_opportunity_swap_and_play_match_direct_sdk(self):
        result = pypy_engine.call(__name__ + ':actual_substitution', reference_raw())
        self.assertEqual(result['budget_before'] - result['budget_after'], 1)
