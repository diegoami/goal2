"""[designed: T119] Both genuine original extra-time menus, original controls and saved replay."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from goal2.tests import requires

ARTIFACTS=(('g13-2c927e5f3a564090-extra-time-start.g2core','2c927e5f3a564090b5c565b55747da8d0f6b41836dd2978df5bd49d58a2545c6'),('g13-fcf77812110b99b4-extra-time-half.g2core','fcf77812110b99b4fd76550fab04f6463dfaa57b81db89a5a34a1fe10cb20cd0'))
NEEDS=dict(modules=('unicorn',),files=tuple(p for p,_ in ARTIFACTS)+('GOAL.DAT',))
KINDS=('match-menu-extra-time','match-menu-extra-halftime')

def loaded(index):
 from goal2.core import Core
 from goal2.core.driver import Driver
 name,sha=ARTIFACTS[index];raw=(requires.CACHE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
 return Driver(Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT'))

@requires.need(**NEEDS)
class First(unittest.TestCase):
 def test_the_first_extra_menu_has_its_actual_caller_clock_and_original_budget(self):
  from goal2.core import views
  d=loaded(0);f=d.core._frame();m=views.Memory(d.wait.state)
  self.assertEqual((d.wait.site,d.wait.kind),('214B:157C',KINDS[0]))
  self.assertEqual(f.far_caller(f.bp),'0791:EE9F');self.assertEqual(f.near_caller(f.up(f.bp)),0x9B42)
  self.assertEqual((m.ds_word(0x831F),m.ds_byte(0x8319)),(89,15))
  self.assertIn('EXTRA TIME',d.wait.text)
  self.assertEqual(views.bench(d.wait.state)['left'],2)

@requires.need(**NEEDS,slow=True)
class Intervals(unittest.TestCase):
 def test_second_menu_and_original_play_progress_to_the_existing_shootout(self):
  from goal2.core import views
  d=loaded(0);before=views.bench(d.wait.state)['left'];d.play_on()
  self.assertEqual(d.wait.kind,KINDS[1]);f=d.core._frame()
  self.assertEqual(f.near_caller(f.up(f.bp)),0x9B70)
  self.assertEqual((views.Memory(d.wait.state).ds_word(0x831F),views.Memory(d.wait.state).ds_byte(0x8319)),(105,15))
  self.assertEqual(views.bench(d.wait.state)['left'],before)
  self.assertEqual(d.play_on().kind,'shootout-announcement')
  self.assertIsNone(d.core.stopped)

 def test_saved_interval_position_repair_and_substitution_follow_original_keys(self):
  from goal2.core import Core,views
  from goal2.core.driver import Driver
  for index in (0,1):
   with self.subTest(interval=index):
    d=loaded(index);before=views.bench(d.wait.state)['left'];saved=d.core.save()
    player=next(p['player'] for p in views.team(d.wait.state)['squad'] if p['eleven'] and views.player_card(d.wait.state,p['player'])['position']!=0)
    d.round_position(player,'c')
    self.assertEqual(d.wait.kind,KINDS[index]);self.assertEqual(views.bench(d.wait.state)['left'],before)
    replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'));replay.round_position(player,'c')
    self.assertEqual(d.core.memory_sha256(),replay.core.memory_sha256());self.assertEqual(d.core.keys,replay.core.keys)
    b=views.bench(d.wait.state)
    pair=next((a,z) for a in b['eleven'] for z in b['bench'] if views.player_card(d.wait.state,a)['position']==views.player_card(d.wait.state,z)['position'] and views.player_card(d.wait.state,z)['readiness']==views.Memory(d.wait.state).code_str(0x1771,0x42AF))
    saved=d.core.save();start=len(d.log);answer=d.substitute(*pair)
    self.assertTrue(answer['made']);self.assertEqual(answer['left'],before-1)
    direct=Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT')
    for _,key in d.log[start:]:direct.press(key)
    self.assertEqual(d.core.memory_sha256(),direct.memory_sha256());self.assertEqual(d.core.keys,direct.keys)

@requires.need(**(NEEDS|{'modules':('unicorn','PySide6')}),slow=True)
class Desktop(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
  from PySide6.QtWidgets import QApplication
  from goal2.desktop.style import load_fonts
  cls.app=QApplication.instance() or QApplication([]);load_fonts()

 def test_both_resumed_intervals_have_correct_labels_bounds_and_guards(self):
  from goal2.desktop.core_model import CoreModel
  from goal2.desktop.core_window import CoreWindow
  from goal2.desktop.fixed_page import problems
  for index in (0,1):
   with self.subTest(interval=index),tempfile.TemporaryDirectory() as folder:
    d=loaded(index);model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
    w=CoreWindow(model);w.show();self.app.processEvents();w.finish_core()
    try:
     r=w.core_round;self.assertEqual(r.views.currentIndex(),1)
     self.assertIn('EXTRA',r.bench.title.text())
     self.assertEqual('HALF TIME' in r.bench.title.text(),index==1)
     self.assertTrue(model.in_round);self.assertFalse(w.core_routes['play next game'].isEnabled())
     self.assertEqual(r.state['bench']['left'],2)
     if os.environ.get('QT_SCALE_FACTOR'):self.assertEqual(w.devicePixelRatioF(),float(os.environ['QT_SCALE_FACTOR']))
     for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
      w.resize(width,height);self.app.processEvents();self.app.processEvents()
      self.assertEqual(problems(w),[])
      page=w.pages[3];need=page.minimumSizeHint();self.assertLessEqual(need.width(),.9*page.width());self.assertLessEqual(need.height(),.9*page.height())
     before=model.memory_sha256()
     with self.assertRaises(ValueError):model.act('swap',0,1)
     self.assertEqual(model.memory_sha256(),before);self.assertTrue(w.save_core())
     resumed=CoreModel.from_save(model.save_path,requires.CACHE/'GOAL.DAT');self.assertEqual(resumed.memory_sha256(),before)
     r.bench.play.click();self.assertTrue(w.core_jobs.busy);self.assertFalse(w.save_core());self.assertFalse(w.run_core('play_on'))
     self.assertEqual(w.finish_core()[0],'done')
     self.assertEqual(model.core.wait.kind,KINDS[1] if index==0 else 'shootout-announcement')
    finally:w.close();self.app.processEvents()

if __name__=='__main__':unittest.main()
