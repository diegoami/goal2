"""[designed: #636] Actual UI key routing for the portable smoke consumer; full packaged flow remains a Windows check."""
import importlib.util,unittest
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtCore import Qt
spec=importlib.util.spec_from_file_location('smoke_window',Path(__file__).resolve().parents[2]/'tools/portable/smoke_window.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Consumer(unittest.TestCase):
 def test_visible_opportunity_is_accepted_instead_of_ignored_on_pitch(self):
  pitch=SimpleNamespace(stop_box=SimpleNamespace(open=True,timed=True,answers={}))
  keys=[];window=SimpleNamespace(current=lambda:pitch)
  self.assertTrue(module.answer_live_stop(window,pitch,keys.append));self.assertEqual(keys,[Qt.Key.Key_Escape])
 def test_pending_bench_cannot_accumulate_another_key(self):
  bench=type('BenchScreen',(),{'pending':True})()
  keys=[];self.assertTrue(module.answer_live_stop(SimpleNamespace(current=lambda:bench),object(),keys.append));self.assertEqual(keys,[])
 def test_healthy_keeper_bench_returns_to_play_menu(self):
  record=bytearray(20);record[14]=32
  answer=SimpleNamespace(eleven=[1],position=lambda w:0,record=lambda w:record)
  bench=type('BenchScreen',(),{'pending':False,'answer':answer})()
  keys=[];self.assertTrue(module.answer_live_stop(SimpleNamespace(current=lambda:bench),object(),keys.append));self.assertEqual(keys,[Qt.Key.Key_Escape])
 def test_replay_question_retains_no_answer(self):
  pitch=SimpleNamespace(stop_box=SimpleNamespace(open=True,timed=False,answers={Qt.Key.Key_Y:'yes',Qt.Key.Key_N:'no'}))
  keys=[];module.answer_live_stop(SimpleNamespace(current=lambda:pitch),pitch,keys.append);self.assertEqual(keys,[Qt.Key.Key_N])
 def test_forced_keeper_uses_two_real_ui_marks_and_waits_for_ack(self):
  injured=bytearray(20);healthy=bytearray(20);healthy[14]=32
  answer=SimpleNamespace(eleven=[1],bench=[2],first=None,left=5,takes_substitutions=True,position=lambda w:0,record=lambda w:injured if w==1 else healthy,words=lambda:[1,2])
  bench=type('BenchScreen',(),{'pending':False,'answer':answer,'row':0,'current':lambda self:answer.words()[self.row]})()
  keys=[];pairs=[]
  def key(k):
   keys.append(k)
   if k==Qt.Key.Key_Down:bench.row+=1
   elif k==Qt.Key.Key_Return:
    if answer.first is None:answer.first=bench.current()
    else:pairs.append((answer.first,bench.current()));bench.pending=True
  window=SimpleNamespace(current=lambda:bench)
  module.answer_live_stop(window,object(),key);self.assertEqual(answer.first,1)
  module.answer_live_stop(window,object(),key);self.assertEqual(pairs,[(1,2)])
  before=list(keys);module.answer_live_stop(window,object(),key);self.assertEqual(keys,before)
 def test_zero_budget_keeper_repair_uses_position_key_without_a_pair(self):
  injured=bytearray(20);healthy=bytearray(20);healthy[14]=32;positions={1:0,3:13}
  answer=SimpleNamespace(eleven=[1,3],bench=[],first=None,left=0,takes_substitutions=True,position=lambda w:positions[w],record=lambda w:injured if w==1 else healthy,words=lambda:[1,3])
  bench=type('BenchScreen',(),{'pending':False,'answer':answer,'row':0,'current':lambda self:answer.words()[self.row]})()
  keys=[]
  def key(k):
   keys.append(k)
   if k==Qt.Key.Key_Down:bench.row+=1
   elif k==Qt.Key.Key_R:positions[bench.current()]=(positions[bench.current()]+1)%14
  module.answer_live_stop(SimpleNamespace(current=lambda:bench),object(),key)
  self.assertEqual(positions[3],0);self.assertNotIn(Qt.Key.Key_Return,keys);self.assertEqual(keys[-1],Qt.Key.Key_Escape)
if __name__=='__main__':unittest.main()
