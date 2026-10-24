"""[designed: owner#73; confirmed: F027@53d7ef5, A5FB/A605/E544] Declared budgets, original keys."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from goal2.tests import requires

PATCH='owner-substitutions-v1'
INPUTS=(('g13-aec219b9376383e7-g1a-original-manager.sav','aec219b9376383e79acdfb2a5bcf4e6ca365502b4026c4dae4c8899faffd92b0'),
        ('g13-b2497a51f41fa52a-g4c-loaded-manager.sav','b2497a51f41fa52a733fe880e3b144b43db05d5de11f4da6e45c51dc76a715a0'))
HALF='g13-66a92624ff602447-g1a-original-halftime.sav'
NEEDS=dict(modules=('unicorn',),files=tuple(p[0] for p in INPUTS)+(HALF,'GOAL.DAT'))

def manager(index=0):
    from goal2.core import Core
    name,sha=INPUTS[index];data=(requires.CACHE/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==sha
    c=Core.start(data,goal_dat=requires.CACHE/'GOAL.DAT').core
    assert c.wait.kind=='manager-menu'
    return c

def table(c):return tuple(c.m.rd(a,1) for a in (0x66b,0x66c))

def header(data,**changes):
    # Clearly synthetic serializer corruption/backward-format controls; no guest execution or original claim.
    n=int.from_bytes(data[4:8],'little');state=json.loads(data[8:8+n]);state.update(changes)
    blob=json.dumps(state).encode();return data[:4]+len(blob).to_bytes(4,'little')+blob+data[8+n:]

@requires.need(**NEEDS)
class Registry(unittest.TestCase):
    def test_both_genuine_inputs_activate_exactly_two_bytes_and_replay_declaration(self):
        from goal2.core import Core
        for index in (0,1):
            with self.subTest(index=index):
                c=manager(index);before=c.m.snapshot();keys=list(c.keys)
                self.assertEqual(table(c),(5,2))
                c.apply_patch(PATCH)
                after=c.m.snapshot();self.assertEqual(table(c),(255,5))
                changes=[i for i,(a,b) in enumerate(zip(before['memory'],after['memory'])) if a!=b]
                self.assertEqual(changes,[c.m.DS*16+0x66b,c.m.DS*16+0x66c])
                self.assertEqual(after['regs'],before['regs']);self.assertEqual(c.keys,keys)
                self.assertEqual(c.patches,(PATCH,))
                saved=c.save();c.apply_patch(PATCH);self.assertEqual(c.save(),saved)
                loaded=Core.load(saved);self.assertEqual(loaded.m.snapshot(),after);self.assertEqual(loaded.patches,(PATCH,))

    def test_unknown_and_wrong_preconditions_leave_state_unchanged(self):
        c=manager();snap=c.m.snapshot()
        with self.assertRaisesRegex(ValueError,'patch'):c.apply_patch('arbitrary-bytes')
        self.assertEqual(c.m.snapshot(),snap)
        c.m.wr(0x66c,3,1)  # non-executed synthetic wrong-precondition control
        snap=c.m.snapshot()
        with self.assertRaisesRegex(ValueError,'table'):c.apply_patch(PATCH)
        self.assertEqual(c.m.snapshot(),snap);self.assertEqual(c.patches,())

    def test_legacy_half_cannot_be_activated_or_refilled(self):
        from goal2.core import Core
        c=Core.start((requires.CACHE/HALF).read_bytes()).core;snap=c.m.snapshot()
        from goal2.core.views import match_sides
        side=match_sides(c.wait.state)['managed_side']
        self.assertEqual(c.m.rd(0x9b3a+side,1),5)
        with self.assertRaisesRegex(ValueError,'manager'):c.apply_patch(PATCH)
        self.assertEqual(c.m.snapshot(),snap)
        for version in (1,2,3,4):
            loaded=Core.load(header(c.save(),version=version))
            self.assertEqual(loaded.m.snapshot(),snap);self.assertEqual(loaded.patches,());self.assertEqual(table(loaded),(5,2))

    def test_bad_declarations_fail_and_quit_origins_keep_the_policy(self):
        from goal2.core import Core
        from goal2.core.screens import F10
        c=manager();original=c.save();c.apply_patch(PATCH);saved=c.save()
        for bad in ([PATCH,PATCH],['unknown'],PATCH,[]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):Core.load(header(saved,patches=bad))
        with self.assertRaises(ValueError):Core.load(header(original,patches=[PATCH]))
        with self.assertRaises(ValueError):Core.load(header(saved,version=4))
        c.press(F10);c.press('y');c.press('y')
        loaded=Core.load(c.save());self.assertEqual(loaded.patches,(PATCH,));self.assertEqual(Core.load(loaded.quit_origin).patches,(PATCH,))
        c.quit_origin=original
        with self.assertRaisesRegex(ValueError,'origin.*policy'):Core.load(c.save())

    @requires.need(files=('e039-r0005-date-call.sav',))
    def test_failed_new_career_activation_discards_consumed_preview_and_retries(self):
        from unittest.mock import patch
        from goal2.core import Core
        from goal2.desktop.core_model import CoreNewGame
        with tempfile.TemporaryDirectory() as tmp:
            creator=CoreNewGame(requires.CACHE/'e039-r0005-date-call.sav',requires.CACHE/'GOAL.DAT',Path(tmp)/'new.g2core')
            # Host activation failure control; no guest data is edited and no synthetic original claim made.
            with patch.object(Core,'apply_patch',side_effect=ValueError('table mismatch')):
                with self.assertRaisesRegex(ValueError,'table mismatch'):creator.start(2028,20,'A Test')
            self.assertNotIn(2028,creator._drivers)
            model,_=creator.start(2028,20,'A Test')
            self.assertEqual(model.core.patches,(PATCH,));self.assertEqual(table(model.core),(255,5))

def interval(index,patched):
    from goal2.core.driver import Driver
    from goal2.tests.test_core_continuation_t111 import fix_eleven
    d=Driver(manager(index))
    if patched:d.core.apply_patch(PATCH)
    d.round_start(False)
    for _ in range(8):
        result=d.kick_off()
        if not isinstance(result,dict):break
        fix_eleven(d,result['refused'])
    else:raise AssertionError('original eleven could not be repaired')
    for _ in range(1000):
        if d.wait.kind=='match-menu-halftime':return d
        if d.wait.kind=='substitution-notice':d.notice(False)
        elif d.wait.kind=='set-piece-select':d.taker_key('c')
        elif d.wait.kind=='match-menu' and d.stoppage():d.play_on()
        else:raise AssertionError((d.wait.kind,d.wait.site))
    raise AssertionError('first half did not reach its original interval')

def pair(d):
    from goal2.core import views
    state=d.wait.state;mem=views.Memory(state);rows=views.team(state)['squad']
    ready={r['player']:views.player_card(state,r['player'])['readiness'] for r in rows}
    for on in rows:
        if on['eleven'] or ready[on['player']]!=mem.code_str(0x1771,0x42af):continue
        off=next((r for r in rows if r['eleven'] and r['line']==on['line']
                  and ready[r['player']]==mem.code_str(0x1771,0x42a6)),None)
        if off:return off['player'],on['player']
    raise AssertionError('no actual ready same-line pair in retained fixture')

@requires.need(**NEEDS,slow=True)
class OriginalKeys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.halves={(i,p):interval(i,p).core.save() for i in (0,1) for p in (False,True)}

    def driver(self,index,patched):
        from goal2.core import Core
        from goal2.core.driver import Driver
        return Driver(Core.load(self.halves[index,patched]))

    def test_original_caps_and_declared_sixth_friendly_fifth_competitive(self):
        from goal2.core import views
        for index,patched,start,count in ((0,False,5,5),(0,True,255,6),(1,False,2,2),(1,True,5,5)):
            with self.subTest(index=index,patched=patched):
                d=self.driver(index,patched);self.assertEqual(views.bench(d.wait.state)['left'],start)
                for n in range(count):
                    result=d.substitute(*pair(d))
                    self.assertTrue(result['made'],result);self.assertEqual(result['left'],start-n-1)
                if start==count:
                    before=views.bench(d.wait.state)['eleven'];result=d.substitute(*pair(d))
                    self.assertFalse(result['made']);self.assertTrue(result['refused']);self.assertEqual(result['left'],0)
                    self.assertEqual(views.bench(d.wait.state)['eleven'],before)

    def test_spent_budget_replay_idempotence_and_original_no_reentry(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        from goal2.core import views
        d=self.driver(0,True);first=pair(d);self.assertTrue(d.substitute(*first)['made'])
        for _ in range(5):self.assertTrue(d.substitute(*pair(d))['made'])
        self.assertEqual(views.bench(d.wait.state)['left'],249)
        saved=d.core.save();d.core.apply_patch(PATCH);self.assertEqual(d.core.save(),saved)
        replay=Driver(Core.load(saved));self.assertEqual(views.bench(replay.wait.state)['left'],249)
        off,_=pair(d);result=d.substitute(off,first[0]);again=replay.substitute(off,first[0])
        self.assertFalse(result['made']);self.assertTrue(result['refused']);self.assertEqual(result,again)
        self.assertEqual(result['left'],249);self.assertEqual(d.core.m.snapshot(),replay.core.m.snapshot())
        self.assertEqual(d.core.keys,replay.core.keys)

@requires.need(**NEEDS,slow=True)
@requires.need(modules=('PySide6',),files=('e039-r0005-date-call.sav',))
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([]);load_fonts()
        cls.halves={i:interval(i,True).core.save() for i in (0,1)}

    def fits(self,w,page):
        from goal2.desktop.fixed_page import problems
        for size in ((1440,900),(1050,780),(900,640),(2560,1600)):
            w.resize(*size);self.app.processEvents();self.assertEqual(problems(w),[])
            need=page.minimumSizeHint();self.assertLessEqual(need.width(),.9*page.width());self.assertLessEqual(need.height(),.9*page.height())

    def test_real_new_career_explicitly_declares_rule_before_start_and_activates_it(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.launch import LaunchWindow
        with tempfile.TemporaryDirectory() as tmp:
            w=LaunchWindow(requires.CACHE/'GOAL.DAT',None,Path(tmp)/'new.g2core',lambda model:None,
                           core_boot=requires.CACHE/'e039-r0005-date-call.sav')
            w.show();w.show_page(1);self.app.processEvents()
            ids=[w.country_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(w.country_list.count())]
            w.country_list.setCurrentRow(ids.index(20));w.preview();w.review();self.app.processEvents()
            self.assertIn('Unlimited',w.substitution_rule.text());self.assertIn('five',w.substitution_rule.text())
            self.assertTrue(w.substitution_rule.isVisible());self.fits(w,w.pages.currentWidget())
            w.manager_name.setText('A Test');QTest.mouseClick(w.start,Qt.MouseButton.LeftButton);self.app.processEvents()
            self.assertEqual(w.started.core.patches,(PATCH,));self.assertEqual(table(w.started.core),(255,5))
            self.assertFalse(w.save_path.exists());self.assertEqual(manager().patches,())
            w.close();self.app.processEvents()

    def test_real_bench_labels_exact_save_busy_and_round_guards(self):
        from concurrent.futures import Future
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        cases=[(Core.load(self.halves[0]),'Unlimited'),(Core.load(self.halves[1]),'5'),
               (Core.start((requires.CACHE/HALF).read_bytes()).core,'5')]
        for c,label in cases:
            with self.subTest(label=label,patches=c.patches),tempfile.TemporaryDirectory() as tmp:
                target=Path(tmp)/'round.g2core';model=CoreModel(c,None,target);w=CoreWindow(model)
                w.show();self.app.processEvents();self.assertIn(label,w.core_round.bench.counter.text())
                if label!='Unlimited':self.assertNotIn('Unlimited',w.core_round.bench.counter.text())
                self.fits(w,w.pages[3]);snap=c.m.snapshot()
                self.assertFalse(w.begin_save_name());self.assertFalse(w.core_team_buttons['reposition'].isEnabled())
                w.core_jobs.future=Future();self.assertFalse(w.save_core());w.core_jobs.future=None
                self.assertEqual(c.m.snapshot(),snap);self.assertTrue(w.save_core())
                loaded=Core.load(target.read_bytes());self.assertEqual(loaded.m.snapshot(),snap);self.assertEqual(loaded.patches,c.patches)
                w.close();self.app.processEvents()
