"""Synthetic packet/UI projection tests only; no original asset or engine run."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from goal2.tests import requires


def record(*,position=3,club=9,own=0,status=0,energy=5):
    value=bytearray(20);value[0]=7;value[1]=27;value[2]=26;value[3]=22;value[4]=18;value[5]=2
    value[6]=position;value[7]=club;value[8:10]=(99).to_bytes(2,'little');value[10:12]=(7).to_bytes(2,'little')
    value[12]=4;value[13]=12;value[14]=energy;value[15]=own;value[16]=status;value[18:20]=(155).to_bytes(2,'little')
    return bytes(value)


def fixture(**changes):
    old=bytearray(record(position=6,club=7,energy=31));old[1]=20;old[8:10]=(1).to_bytes(2,'little');old[18:20]=(55).to_bytes(2,'little')
    model=SimpleNamespace(state=SimpleNamespace(players=[bytes(old)]*41,country_tactics=1,managed_country=7,
        managed_squad=list(range(1,21)),starting_eleven=list(range(1,12))),
        goaldat=SimpleNamespace(player_names=['P'+str(i) for i in range(41)],player_initials=['']*41,country_names=['C'+str(i) for i in range(129)]))
    data=dict(context='half_time',eleven=list(range(1,12)),bench=list(range(12,21)),substitutions_left=5,
        substitutions_now=True,tactics=0,positions=[[i,6] for i in range(1,21)],injured=[],
        player_records=[[i,record(**changes).hex()] for i in range(1,21)])
    return model,SimpleNamespace(data=data,minute=45,score=[0,0])


def decoded(view,word,goaldat):
    """Spy on the existing decoder's input; no new game/display formula is tested."""
    raw=view.players[word]
    return dict(id=word,role='D',line='defence',full_name=goaldat.player_names[word],
        energy=raw[14],own=raw[15],status=raw[16],age=raw[1],caps=int.from_bytes(raw[8:10],'little'),
        performance=int.from_bytes(raw[18:20],'little'),position_code=raw[6],team=view.country_tactics,
        mark='' if raw[6]<2 else 'zone-from-record' if raw[16]&0x40 else 'default-from-record')


@requires.need(modules=("PySide6",))
class LiveOverlayPackets(unittest.TestCase):
    def answer(self,**changes):
        from goal2.ui.s19_bench import BenchAnswer
        model,decision=fixture(**changes)
        return model,decision,BenchAnswer(model,decision,opponents=range(21,32))

    def test_twenty_current_records_are_copied_immutable_and_leave_career_untouched(self):
        model,decision,answer=self.answer();before=copy.deepcopy(model.state.__dict__)
        self.assertEqual(len(answer.live_records),20)
        for word in answer.words():self.assertEqual(answer.record(word),record())
        decision.data['player_records'][0][1]='00'*20
        self.assertEqual(answer.record(1),record())
        with self.assertRaises(TypeError):answer.live_records[1]=b'x'*20
        self.assertEqual(model.state.__dict__,before)
        view=answer.state(1);self.assertIsNot(view,model.state);self.assertEqual(view.players[20],record())
        self.assertEqual(view.country_tactics,0)

    def test_bad_present_snapshots_refuse_and_legacy_missing_snapshot_remains_explicit(self):
        from goal2.ui.s19_bench import BenchAnswer
        model,decision=fixture();decision.data['player_records'][0][1]='bad'
        with self.assertRaises(ValueError):BenchAnswer(model,decision)
        model,decision=fixture();decision.data.pop('player_records');answer=BenchAnswer(model,decision)
        self.assertEqual(answer.live_records,{})
        self.assertEqual(answer.record(1),model.state.players[1])

    def test_fresh_position_club_and_own_precede_stale_events_then_pending_edits(self):
        model,decision,answer=self.answer(own=0x11)
        answer.live_own[1]=0;self.assertEqual(answer.record(1)[15],0x11)
        self.assertEqual(answer.position(1),3)
        answer.reposition(1);self.assertEqual(answer.position(1),4)
        answer.club_position(1);self.assertEqual(answer.position(1),9)
        answer.positions[1]=6  # equals stale packet position, but differs from current raw3
        self.assertEqual(answer.value()['positions'],{1:6})
        answer.own[1]=0x10;self.assertEqual(answer.record(1)[15],0x10)
        self.assertEqual(answer.own_tactics(),{1:{1:False}})
        answer.own[1]=0x11;self.assertEqual(answer.own_tactics(),{})
        self.assertEqual(model.state.players[1][15],0)

    def test_personal_cycle_uses_actual_packet_team_default_and_no_resubmission(self):
        model,decision,answer=self.answer()
        for expected in (0x10,0x11,0):
            answer.own_tactic(1,1);self.assertEqual(answer.record(1)[15],expected)
        self.assertEqual(answer.own_tactics(),{})
        self.assertEqual(model.state.country_tactics,1)

    def test_mark_targets_survive_but_stale_labels_cannot_hide_fresh_zone_or_keeper(self):
        with patch('goal2.game.player_card.card',side_effect=decoded):
            _,_,answer=self.answer();answer.live_marking[1]=25
            self.assertIn('P25',answer.card(1)['mark'])
            _,_,zone=self.answer(status=0x40);zone.live_marking[1]=25
            self.assertEqual(zone.card(1)['mark'],'zone-from-record');self.assertEqual(zone.mark_text(1),'zone-from-record')
            zone.marking[1]=26;self.assertIn('P26',zone.card(1)['mark'])  # explicit pending target, not stale cache
            _,_,keeper=self.answer(position=0);keeper.live_marking[1]=25
            self.assertEqual(keeper.card(1)['mark'],'');self.assertEqual(keeper.mark_text(1),'')

    def test_refresh_keeps_fresh_records_ahead_of_old_injury_and_tactic_events(self):
        from goal2.ui.match_day import MatchDay
        model,decision=fixture(own=0x11,energy=5)
        day=MatchDay.__new__(MatchDay);day.model=model;day.fixture=SimpleNamespace(kind=1)
        day.controller=SimpleNamespace(display=SimpleNamespace(managed=0),events=[
            {'kind':'injury','data':{'team':0,'player':1}},
            {'kind':'player_tactics','data':{'player':1,'own_set':0,'marking':25}}])
        pitch=SimpleNamespace(controller=SimpleNamespace(opponents=lambda:list(range(21,32))))
        answer=day.live_bench(pitch,decision);self.assertNotIn(1,answer.injured);self.assertEqual(answer.record(1)[15],0x11)
        self.assertEqual(answer.live_marking[1],25)
        previous=answer;previous.injured.add(1);previous.own[1]=0x10;previous.positions[1]=4;previous.marking[1]=26
        day.bench=previous;day._editing_screen=SimpleNamespace(preserve_player_edits=True,applied=lambda *args:None)
        day.edited(pitch,decision,{'made':[]});self.assertNotIn(1,day.bench.injured)
        self.assertEqual(day.bench.record(1)[15],0x10);self.assertEqual(day.bench.position(1),4)
        self.assertEqual(day.bench.marking[1],26)

    def test_controller_opt_in_and_legacy_default_do_not_change_packet_callers(self):
        from goal2.ui.s17_pitch import MatchController
        model,_=fixture();pending=SimpleNamespace(kind=1,fixture_id='f:21',side_a=7,side_b=19)
        for enabled in (True,False):
            bridge=SimpleNamespace(start=lambda *args,**kw:None);sent=[]
            bridge.start=lambda *args,**kw:sent.append(kw) or 'token'
            controller=MatchController(model,pending,bridge,**({'live_players':True} if enabled else {}));controller._send=lambda *args:None
            with patch('goal2.desktop.watched.pitch_identity',return_value={}):controller.start()
            self.assertEqual(sent[0].get('live_players',False),enabled)
            if not enabled:self.assertNotIn('live_players',sent[0])

    def test_match_day_explicit_opt_in_and_prompt_packet_route_preserve_captain_path(self):
        from goal2.ui.match_day import MatchDay
        model,decision=fixture();day=MatchDay.__new__(MatchDay);day.model=model;day.fixture=SimpleNamespace(kind=1);day.watch=True
        class Window:
            def __init__(self):self.stack=[object()]
            def pop(self):return self.stack.pop()
            def push(self,value):self.stack.append(value);return value
        day.window=Window();day.bridge=lambda competitive:object()
        controller=SimpleNamespace(start=lambda:None);day._match_name=lambda:'match'
        with patch('goal2.ui.s17_pitch.MatchController',return_value=controller) as constructor,patch('goal2.ui.s17_pitch.PitchScreen',return_value=object()):
            day.kick_off(None);self.assertIs(constructor.call_args.kwargs.get('live_players'),True)
        for method in ('_taker','_shootout_order'):
            with patch('goal2.ui.s16_choose.ChooseScreen',return_value=object()) as screen:
                getattr(day,method)(SimpleNamespace(),decision)
                self.assertIs(screen.call_args.kwargs.get('decision_data'),decision.data)
        with patch('goal2.ui.s16_choose.ChooseScreen',return_value=object()) as screen,patch('goal2.ui.s17_pitch.suggested_captain',return_value=1),patch('goal2.game.eligibility.available_words',return_value=list(range(1,12))):
            day.choose_captain();self.assertNotIn('decision_data',screen.call_args.kwargs)

    def test_same_choices_reference_explicitly_requests_live_metadata(self):
        from goal2.tests.match_day_policy import play_through_bridge
        sent=[]
        class Bridge:
            def __init__(self,model):self.busy=True;self.outcome='complete'
            def start(self,*args,**kw):sent.append(kw);return 't'
            def poll(self,token):self.busy=False
            def close(self):pass
        with patch('goal2.game.watched_jobs.WatchedJobs',Bridge):
            self.assertEqual(play_through_bridge(object(),[],fixture=object()),'complete')
        self.assertIs(sent[0].get('live_players'),True)

    def test_s16_running_cards_use_snapshot_while_pre_kickoff_keeps_career(self):
        from PySide6.QtWidgets import QApplication
        from goal2.ui.s16_choose import ChooseScreen
        application=QApplication.instance() or QApplication([])
        model,decision=fixture();window=SimpleNamespace(open_help=lambda:None)
        with patch('goal2.game.player_card.card',side_effect=decoded),patch('goal2.ui.squad_card.PlayerCard.set_card',lambda self,value:setattr(self,'packet_card',value)):
            before=ChooseScreen(window,model,'captain',list(range(1,12)),1,lambda value:None);before.timer.stop()
            running=ChooseScreen(window,model,'taker',list(range(1,12)),1,lambda value:None,decision_data=decision.data);running.timer.stop()
            order=ChooseScreen(window,model,'order',list(range(1,12)),1,lambda value:None,decision_data=decision.data)
            self.assertEqual(before.cards[0]['energy'],31)
            for screen in (running,order):
                self.assertEqual(screen.cards[0]['energy'],5);self.assertEqual(screen.cards[0]['performance'],155)
                self.assertEqual(screen.cards[0]['caps'],99);self.assertEqual(screen.cards[0]['team'],0)
                screen.deleteLater()
            before.deleteLater();application.processEvents()



@requires.need(modules=('PySide6', 'pygame', 'unicorn'), slow=True, **requires.HALFTIME)
class ActualLiveCards(unittest.TestCase):
    def test_personal_pending_team_reply_swap_reopen_and_play_use_current_records_once(self):
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import Qt
        from goal2.desktop import data_setup, fixed_page
        from goal2.ui.window import Window
        from goal2.ui.s17_pitch import engine_fixture
        from goal2.tests.test_ui_bench_t180 import Walk, app, career, key, enter_on, go_to, play_on, pump, PLAY_NEXT
        from goal2.tests.test_pypy_worker_t152 import pypy
        from goal2.tests.match_day_policy import play_through_bridge
        from goal2.tests.live_card_assertions_619 import verify_bench, verify_choose, report
        pypy()
        application = app()
        test = self
        receipts = []

        class CardsWalk(Walk):
            def react(self, screen):
                if type(screen).__name__ == 'ChooseScreen' and screen.mode != 'captain':
                    verify_choose(test, screen, self.model, self.out['controller'].stop.data, receipts)
                return super().react(screen)

            def on_menu(self, screen):
                if screen.phase == 'stop' and any(w in self.window.match_day.bench.injured
                        for w in self.window.match_day.bench.eleven):
                    key(self.window, Qt.Key.Key_Space)
                else:
                    play_on(self.window, screen)

            def on_board(self, screen):
                if screen.phase == 'half' and not self.out.get('personal_done'):
                    key(self.window, Qt.Key.Key_Escape)
                else:
                    super().on_board(screen)

            def on_bench(self, screen):
                controller = self.out['controller']
                verify_bench(test, screen, controller, receipts, 'natural-stop')
                answer = screen.answer
                if answer.context == 'half_time' and not self.out.get('personal_done'):
                    stay = next(w for w in answer.eleven if answer.position(w) >= 2 and w not in answer.injured)
                    off = next(w for w in answer.eleven if w != stay and answer.position(w) >= 2 and w not in answer.injured)
                    on = next(w for w in answer.bench if answer.position(w) >= 2 and w not in answer.injured)
                    go_to(self.window, screen, stay)
                    key(self.window, Qt.Key.Key_T)
                    personal = self.window.current()
                    test.assertEqual(type(personal).__name__, 'PlayerTacticsScreen')
                    key(self.window, Qt.Key.Key_Return)
                    wanted = personal.bench.record(stay)[15]
                    for _ in range(4):
                        key(self.window, Qt.Key.Key_Down)
                    key(self.window, Qt.Key.Key_Return)  # explicit nobody
                    key(self.window, Qt.Key.Key_Return)  # first opposing outfield player
                    wanted_mark = personal.bench.marking[stay]
                    key(self.window, Qt.Key.Key_Escape)
                    pending = dict(screen.answer.own)
                    key(self.window, Qt.Key.Key_Escape)  # team edit while personal draft is pending
                    menu = self.window.current()
                    key(self.window, Qt.Key.Key_T)
                    team = self.window.current()
                    key(self.window, Qt.Key.Key_Return)
                    pump(lambda: not team.pending or controller.error, 60, 'team edit did not finish')
                    test.assertIsNone(controller.error)
                    test.assertEqual(team.answer.own, pending)
                    test.assertEqual(team.answer.marking[stay], wanted_mark)
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertIs(self.window.current(), menu)
                    key(self.window, Qt.Key.Key_Space)
                    screen = self.window.current()
                    test.assertEqual(screen.answer.own, pending)
                    enter_on(self.window, screen, off)
                    enter_on(self.window, screen, on)
                    test.assertEqual(screen.answer.live_records[stay][15], wanted)
                    test.assertEqual(screen.answer.own, {})
                    test.assertEqual(screen.answer.marking, {})
                    test.assertEqual(screen.answer.live_marking[stay], wanted_mark)
                    test.assertEqual(screen.answer.value(), [])
                    verify_bench(test, screen, controller, receipts, 'confirmed-own-and-swap')
                    choices = len(controller.choices)
                    key(self.window, Qt.Key.Key_Escape)
                    key(self.window, Qt.Key.Key_Space)
                    screen = self.window.current()
                    test.assertEqual(screen.answer.value(), [])
                    test.assertEqual(screen.answer.live_records[stay][15], wanted)
                    test.assertEqual(len(controller.choices), choices)
                    go_to(self.window, screen, stay)
                    key(self.window, Qt.Key.Key_T)
                    personal = self.window.current()
                    test.assertEqual(personal.card(), screen.answer.card(stay))
                    key(self.window, Qt.Key.Key_Escape)
                    key(self.window, Qt.Key.Key_Escape)
                    play_on(self.window, self.window.current())
                    test.assertEqual(len(controller.choices), choices + 1)
                    test.assertEqual(controller.choices[-1][1], [])
                    self.out['personal_done'] = True
                    return
                injured = [w for w in answer.eleven if w in answer.injured]
                if answer.takes_substitutions and answer.left and injured:
                    off = injured[0]
                    used = set(self.out.get('taken_off', []))
                    on = next(w for w in answer.bench if w not in used and
                              (answer.position(w) == 0) == (answer.position(off) == 0))
                    enter_on(self.window, screen, off)
                    enter_on(self.window, screen, on)
                    self.out.setdefault('taken_off', []).append(off)
                    verify_bench(test, screen, controller, receipts, 'injury-swap')
                key(self.window, Qt.Key.Key_Escape)

        with tempfile.TemporaryDirectory() as folder:
            owner = career()
            before = owner.state.match_count
            fixture = owner.state.campaign.next_fixture
            window = Window(data_setup.paths(Path(folder)))
            window.resize(1440, 900)
            window.show()
            walk = CardsWalk('619-current-cards', window, owner)
            try:
                desk = window.open_career(owner)
                desk.highlight(PLAY_NEXT)
                key(window, Qt.Key.Key_Return)
                walk.run()
                controller = walk.out['controller']
                self.assertTrue(walk.out.get('personal_done'))
                self.assertIsNone(controller.error)
                self.assertEqual(owner.state.match_count, before + 1)
                own_commands = [value for _, value in controller.choices if isinstance(value, dict) and value.get('own_tactics')]
                self.assertEqual(len(own_commands), 1)
                other = career()
                other.state = copy.deepcopy(controller.given._snapshot)
                expected = play_through_bridge(other, controller.choices, fixture=engine_fixture(fixture), wait=1500)
                self.assertEqual(controller.outcome, expected, 'all result/events/RNG/seeds/year/fullmemory')
                self.assertEqual(owner.state, other.state, 'exact complete once-published career')
                self.assertEqual(fixed_page.problems(window), [])
                from goal2.tests.live_card_assertions_619 import verify_original_decisions
                verify_original_decisions(self, controller, engine_fixture(fixture), owner.template_bytes, receipts)
                report(self, receipts, 'personal-team-swap-reopen-play')
            finally:
                window.close()
                window.deleteLater()
                application.processEvents()


if __name__=='__main__':unittest.main(verbosity=2)
