"""[confirmed: T88/T89, archaeology9aa9f27c/922fd8d8] Actual role2/5 inputs and original keys."""
import hashlib
import os
from pathlib import Path
import tempfile
import time
import sys
import unittest
from unittest.mock import patch
from goal2.tests import requires

INPUTS=(
 ('t88-bda98a358d98a82f-corner-before-space.sav','bda98a358d98a82f9243ec7025bb8f7f02e0f80a69b37c5bc763faf2aa6e741d',2,1,6,386,14477),
 ('t89-cd047f4a697e5244-goal-kick-before-space.sav','cd047f4a697e5244ea11e1609138ca45d8d070754ce857ea89f6459f78eef482',5,0,4,383,31813),
 ('t88-72d72b0dc1b809fe-corner-pitch-read.sav','72d72b0dc1b809fe10c9c29814ebf33610ae8e900aa2eadd50661849eec0dafe',2,1,6,386,14477),
 ('t89-21e794f7867309dc-goal-kick-CF3A.sav','21e794f7867309dcacb2d6d034878a76fedef972619cf490e947b55dded96710',5,0,4,383,31813),
 ('t88-dc81d0bc8f325051-corner-after-pitch.sav','dc81d0bc8f325051be943d11b90e94a4b1415d0ca76e466c04d2d3a4f114f91f',2,1,6,386,14477),
 ('t89-58c1d8107a1269ec-goal-kick-after-pitch.sav','58c1d8107a1269ec90988104fa82473748b5eda4d25c5ba9a08b26bb498039bf',5,0,4,383,31813))
NEEDS=dict(modules=('unicorn',),files=tuple(r[0] for r in INPUTS)+('GOAL.DAT','e039-r0005-date-call.sav'))
SELECT,PITCH='set-piece-select','set-piece-pitch'

def raw(index):
 name,sha,*_=INPUTS[index];data=(requires.CACHE/name).read_bytes()
 assert hashlib.sha256(data).hexdigest()==sha
 return data

def loaded(index):
 from goal2.core import Core
 from goal2.core.driver import Driver
 c=Core.start(raw(index),goal_dat=requires.CACHE/'GOAL.DAT').core
 c.stop_at(SELECT,'match-live','substitution-notice','match-summary-save-prompt')
 return Driver(c)

@requires.need(**NEEDS)
class Entry(unittest.TestCase):
 def test_both_actual_timed_inputs_execute_at_their_saved_cpu_and_memory(self):
  from goal2.core import Core,runner
  from unicorn import UC_HOOK_CODE
  original=Core._run
  for i in (0,1):
   captures=[]
   def observe(c):
    first=[]
    def instruction(uc,address,size,user):
     if not first:first.append(c.m.snapshot())
    hook=c.m.uc.hook_add(UC_HOOK_CODE,instruction)
    try:return original(c)
    finally:
     c.m.uc.hook_del(hook);captures.extend(first)
   data=raw(i);image=runner._image(data);expected=bytearray(image.memory[:runner.MEM_SIZE])
   expected[runner.TEXT_PAGE:runner.TEXT_PAGE+4000]=runner.text_page(data)
   with patch.object(Core,'_run',observe):d=loaded(i)
   self.assertEqual(captures[0]['regs'],runner.cpu_state(data))
   self.assertTrue(captures[0]['memory']==bytes(expected),'Timed entry changed guest memory before execution')
   w=d.wait;_,_,role,side,slot,stored,seed=INPUTS[i]
   self.assertEqual(w.kind,SELECT);self.assertTrue(w.poll);self.assertEqual(w.site,'0791:CC54')
   self.assertEqual(w.view,dict(role=role,side=side,country=20,slot=slot,stored=stored))
   self.assertEqual(d.core.m.rd(0x7B62),seed);self.assertEqual(d.core.m.rd(0x7B64),0)
   from goal2.core import views
   choice=views.taker_choice(w.state,w.view);self.assertEqual(len(choice['players']),11)
   if i==1:self.assertEqual(choice['card']['position'],2)  # actual goal-kick taker is a defender

@requires.need(**NEEDS,slow=True)
class Controls(unittest.TestCase):
 def test_space_and_each_actual_pitch_input_return_to_the_same_selector_and_replay(self):
  from goal2.core import Core
  from goal2.core.driver import Driver
  for i in range(6):
   d=loaded(i);before=dict(d.wait.view)
   if i not in (2,3):self.assertEqual(d.taker_key(32).kind,PITCH)
   self.assertFalse(d.wait.poll);self.assertEqual(d.wait.site,'0791:CF3A')
   saved=d.core.save();replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
   self.assertEqual(d.taker_key(13).kind,SELECT);replay.taker_key(13)
   self.assertEqual(d.wait.view,before);self.assertEqual(d.core.memory_sha256(),replay.core.memory_sha256())
   self.assertEqual(d.core.keys,replay.core.keys)

 def test_move_wrap_accept_c_escape_and_remaining_timeout_are_original(self):
  from goal2.core import views
  from goal2.core.screens import UP,DOWN,LEFT,RIGHT
  for i,remaining in ((0,977),(1,982)):
   for key in ('move','c','escape','timeout'):
    d=loaded(i);m=d.core.m;side=INPUTS[i][3];role=INPUTS[i][2]
    captain=m.rd(0x9978+10*side);left=m.rd(0x9B3A+side,1);stored=d.wait.view['stored']
    if key=='move':
     initial=dict(d.wait.view)
     for ignored in (LEFT,RIGHT):
      d.taker_key(ignored);self.assertEqual(d.wait.view,initial)
     slot=d.wait.view['slot'];d.taker_key(DOWN)
     expected=views.taker_choice(d.wait.state,d.wait.view)['selected_player']
     self.assertEqual(d.wait.view['slot'],slot+1)
     for _ in range(11):d.taker_key(UP)
     self.assertEqual(d.wait.view['slot'],slot+1)
     d.taker_key(13)
    elif key=='timeout':
     expected=stored;d.taker_key(None)
     self.assertEqual(dict(d.wait.polls)['0791:CC54'],remaining)
    else:
     expected=stored;d.taker_key('c' if key=='c' else 27)
    self.assertEqual(d.wait.kind,'match-live')
    self.assertEqual(m.rd(0x9976+2*role+10*side),expected)
    self.assertEqual(m.rd(0x9978+10*side),captain);self.assertEqual(m.rd(0x9B3A+side,1),left)

 def test_actual_unrelated_native_context_and_unobserved_roles_are_not_guessed(self):
  from goal2.core import Core,CoreError,screens
  with self.assertRaises(CoreError):Core.start((requires.CACHE/'e039-r0005-date-call.sav').read_bytes())
  class Frame:
   def byte(self,bp,off):return self.role if off==4 else 0
   def near_caller(self,bp):return 0x6D74
  f=Frame()
  for f.role in (0,1,3,4,6):self.assertIsNone(screens._taker(f,0))

 def test_the_script_requires_an_explicit_answer_and_pitch_is_not_a_timeout(self):
  from goal2.core.driver import DriverError
  d=loaded(0)
  # [designed] Resume the real decision in the loop without replaying an unrelated whole fixture.
  with patch.object(d,'round_start',return_value=d.wait),patch.object(d,'kick_off',return_value=d.wait):
   with self.assertRaisesRegex(DriverError,'on_taker'):d.play_round()
  self.assertEqual(d.wait.kind,SELECT);self.assertIsNone(d.core.stopped)
  class Boundary(Exception):pass
  real=d.taker_key;seen=[]
  def key(value):
   seen.append(value);real(value);raise Boundary
  with patch.object(d,'round_start',return_value=d.wait),patch.object(d,'kick_off',return_value=d.wait),patch.object(d,'taker_key',side_effect=key):
   with self.assertRaises(Boundary):d.play_round(on_taker=lambda driver,wait:'c')
  self.assertEqual(seen,['c']);self.assertEqual(d.wait.kind,'match-live')
  p=loaded(2);before=p.core.memory_sha256()
  with self.assertRaisesRegex(DriverError,'blocking'):p.taker_key(None)
  self.assertEqual(p.core.memory_sha256(),before);self.assertEqual(p.wait.kind,PITCH)


@requires.need(**(NEEDS|{'modules':('unicorn','PySide6','pygame')}),slow=True)
class Desktop(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('SDL_VIDEODRIVER','dummy')
  os.environ.setdefault('SDL_AUDIODRIVER','dummy')
  from PySide6.QtWidgets import QApplication
  from goal2.desktop.style import load_fonts
  cls.app=QApplication.instance() or QApplication([]);load_fonts()

 def bounds(self,w):
  from goal2.desktop.fixed_page import problems
  for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
   w.resize(width,height);self.app.processEvents();self.app.processEvents()
   self.assertEqual(problems(w),[],(width,height,problems(w)))
   page=w.pages[3];need=page.minimumSizeHint()
   self.assertLessEqual(need.width(),.9*page.width(),(width,height,'width',need.toTuple()))
   self.assertLessEqual(need.height(),.9*page.height(),(width,height,'height',need.toTuple()))
  self.assertAlmostEqual(w.devicePixelRatio(),float(os.environ.get('QT_SCALE_FACTOR','1')),places=2)
  w.resize(1440,900);self.app.processEvents()

 def test_both_choices_have_full_cards_original_keys_locks_saves_and_bounds(self):
  from PySide6.QtCore import Qt
  from PySide6.QtCore import QPoint
  from PySide6.QtTest import QTest
  from goal2.desktop.core_model import CoreModel
  from goal2.desktop.core_window import CoreWindow
  for i in (0,1):
   with tempfile.TemporaryDirectory() as folder:
    model=CoreModel(loaded(i).core,requires.CACHE/'GOAL.DAT',Path(folder)/'taker.g2core')
    w=CoreWindow(model);w.show();self.app.processEvents();w.finish_core()
    try:
     r=w.core_round;t=r.takers;self.assertEqual(r.state['stop'],'taker')
     self.assertEqual(t.roster.current,INPUTS[i][4]-1)
     self.assertEqual(t.card.card['full_name'],r.state['taker']['card']['name'])
     self.assertEqual(len(t.card.card['skills']),12);self.bounds(w)
     self.assertTrue(model.in_round);before=model.memory_sha256()
     with self.assertRaises(ValueError):model.act('swap',0,1)
     self.assertEqual(model.memory_sha256(),before)
     t.roster.setFocus();QTest.keyClick(t.roster,Qt.Key.Key_Up)
     self.assertTrue(w.core_jobs.busy);self.assertFalse(w.save_core());self.assertFalse(t.roster.isEnabled())
     self.assertFalse(w.run_core('taker_key',13));w.finish_core();self.app.processEvents()
     self.assertEqual(model.core.wait.view['slot'],INPUTS[i][4]-1)
     self.assertEqual(t.roster.current,model.core.wait.view['slot']-1)
     target=INPUTS[i][4]-1;s=t.roster.scale()
     QTest.mouseClick(t.roster,Qt.MouseButton.LeftButton,pos=QPoint(round(60*s),round((t.roster.baseline(target)-8)*s)))
     w.finish_core();self.app.processEvents();self.assertEqual(model.core.wait.view['slot'],target+1)
     self.assertTrue(w.save_core());copy=CoreModel.from_save(model.save_path,requires.CACHE/'GOAL.DAT')
     self.assertEqual(copy.memory_sha256(),model.memory_sha256())
     t.space.click();w.finish_core();self.app.processEvents();self.assertEqual(model.core.wait.kind,PITCH)
     end=time.monotonic()+20
     while r.viewer is not None and not r.viewer.drained and time.monotonic()<end:
      self.app.processEvents();time.sleep(.005)
     self.assertIsNotNone(r.viewer);self.assertTrue(r.viewer.drained);self.bounds(w)
     self.assertTrue(t.back.isEnabled());self.assertTrue(w.save_core())
     copy=CoreModel.from_save(model.save_path,requires.CACHE/'GOAL.DAT')
     self.assertEqual(copy.core.wait.kind,PITCH);self.assertEqual(copy.memory_sha256(),model.memory_sha256())
     t.back.click();w.finish_core();self.app.processEvents();self.assertEqual(model.core.wait.kind,SELECT)
     r.stop_viewer('test keeps the next live wait stable');r.watch_suspended=True
     t.select.click();w.finish_core();self.assertEqual(model.core.wait.kind,'match-live');self.bounds(w)
    finally:w.close();self.app.processEvents()

 def test_actual_pitch_reads_resume_and_real_sdl_enter_returns_without_advancing_the_match(self):
  from goal2.desktop.core_model import CoreModel
  from goal2.desktop.core_window import CoreWindow
  from goal2.desktop.core_viewer import CoreViewer
  from goal2.core import Core
  from goal2.core.driver import Driver
  script=("import pygame,sys;from goal2.desktop import pygame_viewer as v;original=v.status;sent=[False];"
          "exec(\"def write(p,x):\\n original(p,x)\\n if x.get('frame_sequence',-1)>=0 and not sent[0]:"
          "\\n  sent[0]=True;pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))\");"
          "v.status=write;sys.exit(v.main())")
  for i in (2,3):
   with tempfile.TemporaryDirectory() as folder:
    c=loaded(i).core;saved=c.save();model=CoreModel(c,requires.CACHE/'GOAL.DAT',Path(folder)/'pitch.g2core')
    with patch('goal2.desktop.core_viewer.CoreViewer',side_effect=lambda identity:CoreViewer(identity,command=[sys.executable,'-c',script])):
     w=CoreWindow(model);w.show();self.app.processEvents()
    try:
     end=time.monotonic()+20
     while time.monotonic()<end:
      self.app.processEvents()
      if c.wait is not None and c.wait.kind==SELECT and not w.core_jobs.busy:break
      time.sleep(.005)
     self.assertEqual(c.wait.kind,SELECT,w.status.text());self.assertEqual(c.wait.view['slot'],INPUTS[i][4])
     replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
     with replay.core.live_frames():replay.taker_key(13)
     self.assertEqual(c.memory_sha256(),replay.core.memory_sha256());self.assertEqual(c.keys,replay.core.keys)
     self.assertIsNotNone(w.core_round.viewer);self.assertTrue(model.in_round);self.bounds(w)
    finally:w.close();self.app.processEvents()

 def test_closing_and_reopening_the_pitch_preserves_the_real_blocking_wait(self):
  from goal2.desktop.core_model import CoreModel
  from goal2.desktop.core_window import CoreWindow
  from goal2.desktop.core_viewer import CoreViewer
  script=("import pygame,sys;from goal2.desktop import pygame_viewer as v;original=v.status;sent=[False];"
          "exec(\"def write(p,x):\\n original(p,x)\\n if x.get('frame_sequence',-1)>=0 and not sent[0]:"
          "\\n  sent[0]=True;pygame.event.post(pygame.event.Event(pygame.QUIT))\");"
          "v.status=write;sys.exit(v.main())")
  with tempfile.TemporaryDirectory() as folder:
   c=loaded(2).core;before=c.memory_sha256();keys=list(c.keys)
   model=CoreModel(c,requires.CACHE/'GOAL.DAT',Path(folder)/'closed.g2core')
   with patch('goal2.desktop.core_viewer.CoreViewer',side_effect=lambda identity:CoreViewer(identity,command=[sys.executable,'-c',script])):
    w=CoreWindow(model);w.show();self.app.processEvents()
   try:
    r=w.core_round;t=r.takers;end=time.monotonic()+20
    while time.monotonic()<end:
     self.app.processEvents()
     if r.viewer is None and 'closed' in t.preview_note.text():break
     time.sleep(.005)
    self.assertIsNone(r.viewer,t.preview_note.text());self.assertEqual(c.wait.kind,PITCH)
    self.assertEqual(c.memory_sha256(),before);self.assertEqual(c.keys,keys)
    self.assertTrue(w.save_core());self.assertTrue(t.back.isEnabled());self.assertTrue(t.reopen.isEnabled())
    t.reopen.click();end=time.monotonic()+20
    while r.viewer is not None and not r.viewer.drained and time.monotonic()<end:
     self.app.processEvents();time.sleep(.005)
    self.assertIsNotNone(r.viewer);self.assertTrue(r.viewer.drained);self.assertEqual(c.memory_sha256(),before)
    t.back.click();w.finish_core();self.assertEqual(c.wait.kind,SELECT)
   finally:w.close();self.app.processEvents()

if __name__=='__main__':unittest.main()
