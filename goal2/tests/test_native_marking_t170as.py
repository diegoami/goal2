"""[designed: T170as] Live marking through verified stopped decisions."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_scoped_worker_admits_one_exact_current_mark(self):
        for context, flag in (('half_time', 'half_time_edit'), ('substitution', 'substitution_edit')):
            worker = SeasonWorker()
            match = Mock(waiting=dict(context=context, substitutions_now=True, eleven=[11, 12], bench=[13]))
            worker.session = SimpleNamespace(pending_match=match)
            worker.decision = 7
            request = dict(op='season', action='answer', request=1, decision=7, **{flag: True})
            with patch('goal2.game.live_marking.worker_marking_targets',
                       side_effect=lambda _, word: (0, 21) if word == 12 else ()):
                for marking in ({11: 21}, {13: 0}, {12: None}, {12: False}, {12: '21'},
                                {12: 99}, {True: 0}, {'012': 21}, {11: 0, 12: 21}):
                    with self.assertRaises(SeasonRequestError):
                        worker.dispatch(dict(request, answer={'edit_only': True, 'marking': marking}))
                    self.assertEqual(worker.decision, 7)
                match.answer.assert_not_called()
                worker.dispatch(dict(request, answer={'edit_only': True, 'marking': {'12': 21}}))
                match.answer.assert_called_once_with(edit_only=True, marking={12: 21})
                self.assertIsNone(worker.decision)


def actual_marking(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game.live_marking import worker_marking_targets
    from goal2.game.stopped_view import StoppedMatchView
    from goal2.tests.test_native_opportunity_t170am import reach_requested_opportunity

    assert sys.implementation.name == 'pypy' and Uc is None
    worker, ask, stop, _ = reach_requested_opportunity(raw)
    match = worker.session.pending_match
    ask('answer', decision=stop, answer={'opportunity': 'accept'}, choice_answer=True)
    batch = ask('next', count=32)
    data = batch['events'][-1]['data']
    assert data['context'] == 'substitution'
    word = next(w for w in data['eleven'][1:] if len(worker_marking_targets(match, w)) > 1)
    target = worker_marking_targets(match, word)[1]
    keeper = data['eleven'][0]
    baseline = Match.load(match.save())
    direct = iter(baseline.events())
    for player, chosen, scoped in ((word, target, True), (word, 0, True), (keeper, target, False)):
        number = batch['decision']
        saved = match.save()
        answer = {'edit_only': True, 'marking': {player: chosen}}
        for decision, invalid in ((number - 1, answer), (number, dict(answer, marking={keeper: target})),
                                  (number, dict(answer, marking={player: None}))):
            try:
                ask('answer', decision=decision, answer=invalid, substitution_edit=True)
            except SeasonRequestError:
                assert worker.decision == number and match.save() == saved
            else:
                raise AssertionError('Invalid live mark consumed the stop')
        baseline.answer(**answer)
        ask('answer', decision=number, answer=answer, **({'substitution_edit': True} if scoped else {}))
        batch = ask('next', count=32)
        events = []
        for event in direct:
            events.append(asdict(event))
            if event.kind == 'decision':
                break
        assert batch['events'] == events and not batch['frames'] and batch['decision'] > number
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        packet = ask('stopped_preview', decision=batch['decision'])
        view = StoppedMatchView.from_packet(packet, request=packet['request'], decision=batch['decision'],
                                            managed_country=match.opts['managed'], data=events[-1]['data'])
        if scoped:
            assert view.marking_word(player) == chosen and view.record(player)[16] & 0x40
        else:
            assert view.marking_word(player) == 0
            assert any(event['kind'] == 'refused' for event in events)
    return True


class Actual(unittest.TestCase):
    def test_named_zone_and_real_keeper_refusal_match_direct_sdk(self):
        self.assertTrue(pypy_engine.call(__name__ + ':actual_marking', reference_raw()))


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_confirmed_named_and_zone_choices_at_both_legal_benches(self):
        for context, flag in (('half_time', 'half_time_edit'), ('substitution', 'substitution_edit')):
            with self.subTest(context=context):
                self.exercise(context, flag)

    def exercise(self, context, flag):
        from PySide6.QtCore import Qt
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import Image, PLAYERS_PTR, PLAYER_SIZE
        from goal2.engine.original_match.screens import MARKING
        from goal2.game import engine_tables
        from goal2.game.season import canonical_hash
        from goal2.tests.test_native_driver_t170ac import event
        from goal2.tests.test_native_opportunity_t170am import sample
        from goal2.tests.test_native_pitch_t170ad import WindowControls
        from goal2.tests.test_stopped_view_t170af import respond
        from goal2.tests.ui_assertions import assert_fits
        from goal2.ui.s22_help import HelpScreen
        from goal2.ui.squad_card import full_name

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
        ds = image.DS * 16
        image.memory[ds + 0xC1E] = 1
        players_at = image.far(PLAYERS_PTR)
        data = packet['data']
        word = next(w for w, position in data['positions'] if position >= 2 and w in data['eleven'])
        offset = players_at + PLAYER_SIZE * word
        image.memory[offset + 14:offset + 17] = bytes((100, 0, 0))
        opposing = image.squad(19)
        target = opposing[1]
        for opponent in opposing[1:11]:
            if opponent:
                at = players_at + PLAYER_SIZE * opponent
                image.memory[at + 14] = int(opponent == target) * 100
                image.memory[at + 16] = 0

        def stage(number, mark):
            at = ds + MARKING + 2 * data['eleven'].index(word)
            image.memory[at:at + 2] = mark.to_bytes(2, 'little')
            image.memory[offset + 16] = 64 if number > 3 else 0
            players = image.players()
            data.update(context=context, edited=number > 3,
                        team_context=dict(data['team_context'], match_set_up=1),
                        player_records=[[w, players[w].hex()] for w in data['eleven'] + data['bench'] if w])
            packet['state'] = image.state(tables)
            packet['preview'].update(decision=number, state_hash=canonical_hash(packet['state']),
                                      data_hash=canonical_hash(data))
            case.owner.batch(events=[event('decision', data)], decision=number, total=number + 1)
            case.tick()
            respond(case.owner, packet)
            case.tick()

        case.tick()
        stage(3, 0)
        bench = case.win.current()
        case.key(Qt.Key.Key_T)
        self.assertEqual(len(case.win.current().rows), 4)
        case.key(Qt.Key.Key_Escape)
        bench.select_player(bench.players.index(word))
        case.key(Qt.Key.Key_T)
        editor = case.win.current()
        self.assertEqual(len(editor.rows), 5)
        assert_fits(self, case.win)
        editor.choose(4)
        for number, wanted, display in ((3, target, full_name(editor.model, target)), (4, 0, 'Protect zone P')):
            case.key(Qt.Key.Key_Return)
            case.key(Qt.Key.Key_Return)
            self.assertEqual(case.owner.sent[-1], ('answer', {
                'decision': number, flag: True, 'answer': {'edit_only': True, 'marking': {word: wanted}}}))
            self.assertEqual(sum(operation == 'answer' for operation, _ in case.owner.sent), number - 2)
            case.key(Qt.Key.Key_F1)
            case.owner.reply('answer')
            case.tick()
            stage(number + 1, wanted)
            self.assertIsInstance(case.win.current(), HelpScreen)
            self.assertEqual(editor.lines()[4][1], display)
            case.key(Qt.Key.Key_Escape)
        case.key(Qt.Key.Key_Escape)
        self.assertIs(case.win.current(), bench)
        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 5, 'answer': {}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.failures, [])
