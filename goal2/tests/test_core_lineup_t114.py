"""[designed: T114] Recover original lineup refusals and reposition through original keys only."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

ARTIFACTS=json.loads((requires.ROOT/'docs/evidence/T114/artifacts.json').read_text())['artifacts']
NEEDS=dict(modules=('unicorn',),files=tuple(a['name'] for a in ARTIFACTS)+('GOAL.DAT',))


def loaded(index):
    from goal2.core import Core
    from goal2.core.driver import Driver
    a=ARTIFACTS[index];raw=(requires.CACHE/a['name']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==a['sha256']
    return Driver(Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT'))


def repair_target(d,case):
    from goal2.core import views
    cards=[views.player_card(d.wait.state,r['player']) for r in views.team(d.wait.state)['squad'] if r['eleven']]
    return next(c['player'] for c in cards if c['club_position']==0) if case==0 else next(
        c['player'] for c in cards if c['position']==1 and c['club_position']!=1)


@requires.need(**NEEDS)
class Recovery(unittest.TestCase):
    def test_the_two_original_warnings_can_be_closed_repaired_and_saved(self):
        from goal2.core import Core,views
        from goal2.core.driver import Driver
        for case,quote in ((0,'no goalkeeper'),(1,'too many sweepers')):
            with self.subTest(case=case):
                d=loaded(case);d.round_start(watch=True)
                answer=d.kick_off(watch=True)
                self.assertIn(quote,answer['refused']);self.assertIsNone(d.core.stopped)
                self.assertEqual(d.wait.kind,'match-menu')
                target=repair_target(d,case);before=views.bench(d.wait.state)['left'];saved=d.core.save()
                changed=d.round_position(target,'c')
                self.assertEqual(changed['position'],changed['club_position'])
                self.assertEqual(views.bench(d.wait.state)['left'],before)
                self.assertEqual(d.wait.view['context'],'before')
                replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'));replay.round_position(target,'c')
                self.assertEqual(replay.core.memory_sha256(),d.core.memory_sha256())
                self.assertEqual(d.kick_off(watch=True).kind,'match-live')


@requires.need(**NEEDS,slow=True)
class RoundPositions(unittest.TestCase):
    def test_half_time_and_stoppage_positions_use_r_c_without_spending_a_substitution(self):
        from goal2.core import Core,views
        from goal2.core.driver import Driver
        for case in (2,3):
            d=loaded(case);home=d.wait.kind;before=views.bench(d.wait.state)['left']
            if case==2:
                answer=d.play_on();self.assertIn('no goalkeeper',answer['refused'])
                word=next(r['player'] for r in views.team(d.wait.state)['squad'] if r['eleven']
                          and views.player_card(d.wait.state,r['player'])['club_position']!=0)
                saved=d.core.save()
                for _ in range(14):
                    if views.player_card(d.wait.state,word)['position']==0:break
                    d.round_position(word,'r')
                else:self.fail('Original R did not reach goalkeeper')
                self.assertEqual(views.bench(d.wait.state)['left'],before)

                replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
                while views.player_card(replay.wait.state,word)['position']!=0:replay.round_position(word,'r')
                self.assertEqual(replay.core.memory_sha256(),d.core.memory_sha256())
                # Accepting Play proves the original, rather than a client validator, accepts the repair.
                d.core.stop_at('match-live','substitution-notice','match-summary-save-prompt')
                self.assertEqual(d.play_on().kind,'match-live')
            else:
                word=next(r['player'] for r in views.team(d.wait.state)['squad'] if r['eleven']
                          and views.player_card(d.wait.state,r['player'])['position']!=0)
                changed=d.round_position(word,'r');self.assertEqual(changed['player'],word)
                restored=d.round_position(word,'c');self.assertEqual(restored['position'],restored['club_position'])
                self.assertEqual(d.wait.kind,home);self.assertEqual(d.wait.view['context'],'stoppage')
                self.assertEqual(views.bench(d.wait.state)['left'],before)

    def test_position_keys_respect_no_substitutes_and_the_pause_request_context(self):
        from goal2.core import views
        from goal2.core.driver import DriverError
        from goal2.core.screens import RETURN
        d=loaded(2)
        for _ in range(4):
            b=views.bench(d.wait.state);m=views.Memory(d.wait.state)
            on=next(w for w in b['bench'] if views.player_card(d.wait.state,w)['readiness']==m.code_str(0x1771,0x42AF))
            off=next(w for w in b['eleven'] if views.player_card(d.wait.state,w)['position']!=0)
            self.assertTrue(d.substitute(off,on)['made'])
        self.assertEqual(views.bench(d.wait.state)['left'],0)
        player=views.bench(d.wait.state)['eleven'][0];old=views.player_card(d.wait.state,player)['position']
        answer=d.round_position(player,'r')
        self.assertIn('no more substitutes',answer['refused'].lower())
        self.assertEqual(d.wait.kind,'match-menu-halftime')
        self.assertEqual(views.player_card(d.wait.state,player)['position'],old)
        self.assertEqual(views.bench(d.wait.state)['left'],0)
        d=loaded(0);d.round_start(watch=True);d.kick_off(watch=True)
        d.round_position(repair_target(d,0),'c');d.kick_off(watch=True);d.live_step(RETURN)
        self.assertEqual(d.wait.view['context'],'pause');sha=d.core.memory_sha256()
        with self.assertRaises(DriverError):d.round_position(views.bench(d.wait.state)['eleven'][0],'r')
        self.assertEqual(d.core.memory_sha256(),sha)


@requires.need(**(NEEDS|{'modules':('unicorn','PySide6')}),slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([]);load_fonts()

    def test_position_controls_keep_selection_round_lock_and_the_four_size_bounds(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.core import views
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        for case in (0,1,2,3):
            d=loaded(case)
            if case in (0,1):d.round_start()
            with tempfile.TemporaryDirectory() as folder:
                model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core');w=CoreWindow(model)
                w.show();w.activateWindow();self.app.processEvents();w.finish_core()
                try:
                    r=w.core_round
                    quote='too many sweepers' if case==1 else 'no goalkeeper'
                    if case in (0,1,2):
                        w.run_core('kick_off' if case in (0,1) else 'play_on');w.finish_core();self.app.processEvents()
                        self.assertIn(quote,w.model.refused)
                    if case in (0,1):r.show_pre_match()
                    b=r.bench;self.assertTrue(b.position_next.isVisible());self.assertTrue(b.position_club.isVisible())
                    if case in (0,1,2):self.assertIn(quote,b.message_label.text())
                    def bounds():
                        for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
                            w.resize(round(.9*width),round(.9*height));self.app.processEvents();self.app.processEvents()
                            self.assertEqual(problems(w),[],(case,width,height,problems(w)))
                    bounds()
                    word=repair_target(d,case) if case in (0,1) else next(x for x in b.words()[0]
                         if views.player_card(d.wait.state,x)['position']!=0)
                    words=sum((list(x) for x in b.words()),[]);b.roster.set_current(words.index(word));self.app.processEvents()
                    before=views.bench(d.wait.state)['left']
                    # Mouse C and keyboard R both go through the worker and keep the selected full ID.
                    b.position_club.click();w.finish_core();self.app.processEvents()
                    self.assertEqual(sum((list(x) for x in b.words()),[])[b.roster.current],word)
                    self.assertEqual(views.player_card(d.wait.state,word)['position'],
                                     views.player_card(d.wait.state,word)['club_position'])
                    old=views.player_card(d.wait.state,word)['position']
                    b.roster.setFocus();QTest.keyClick(b.roster,Qt.Key.Key_R);w.finish_core();self.app.processEvents()
                    self.assertEqual(sum((list(x) for x in b.words()),[])[b.roster.current],word)
                    self.assertNotEqual(views.player_card(d.wait.state,word)['position'],old)
                    if case==0:
                        from unittest.mock import patch
                        b.position_next.click();future=w.core_jobs.future
                        self.assertTrue(w.core_jobs.busy);self.assertFalse(b.roster.isEnabled())
                        with patch.object(model,'card',side_effect=AssertionError('UI read a running core')):b.show_card()
                        self.assertTrue(b.escape());self.assertEqual(r.views.currentIndex(),1)
                        b.reposition('c');self.assertIs(w.core_jobs.future,future)
                        w.finish_core();self.app.processEvents()
                        self.assertEqual(sum((list(x) for x in b.words()),[])[b.roster.current],word)
                    self.assertEqual(views.bench(d.wait.state)['left'],before)
                    self.assertTrue(model.in_round)
                    self.assertFalse(any(button.isEnabled() for button in w.core_team_buttons.values()))
                    if case in (0,1):
                        b.position_club.click();w.finish_core();self.app.processEvents()
                        card=views.player_card(d.wait.state,word)
                        self.assertEqual(card['position'],card['club_position'])
                    elif case==2:
                        for _ in range(14):
                            if views.player_card(d.wait.state,word)['position']==0:break
                            b.roster.setFocus();QTest.keyClick(b.roster,Qt.Key.Key_R);w.finish_core();self.app.processEvents()
                            self.assertEqual(sum((list(x) for x in b.words()),[])[b.roster.current],word)
                        else:self.fail('Keyboard R never reached goalkeeper')
                        self.assertEqual(views.bench(d.wait.state)['left'],before)
                    bounds()
                finally:w.close();self.app.processEvents()


if __name__=='__main__':unittest.main()
