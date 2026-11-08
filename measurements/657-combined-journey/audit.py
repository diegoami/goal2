"""#657 actual UI-created career -> watched match -> recordings -> save/reload.
Private snapshots/journals stay in TARGET, never in public evidence.
"""
import copy,hashlib,json,os,pickle,shutil,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(sys.argv[1]);TARGET=Path(sys.argv[2]);MODE=sys.argv[3]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop import data_setup,fixed_page
from goal2.ui.window import Window
from goal2.ui import saves,replays
from goal2.tests.test_ui_bench_t180 import Walk,key as send,play_on,pump,PLAY_NEXT
from goal2.tests.substitution_selectors_636 import compatible_pair,swap_immediately,request_from_bench,accept_opportunity_with_escape
from goal2.tests.match_day_policy import play_through_bridge
from goal2.desktop.model import DesktopModel
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()
def canonical(v):return json.loads(json.dumps(v))
if MODE=='create':assert not TARGET.exists(),'use a new target for each attempt'
TARGET.mkdir(parents=True,exist_ok=True);captures=TARGET/'captures';captures.mkdir(exist_ok=True)
paths=data_setup.Paths(TARGET/'data-root');app=QApplication.instance() or QApplication([])
w=Window(paths);w.resize(1440,900);w.show();app.processEvents();actions=[]
def note(message):actions.append(message);print(message,flush=True)
def key(value):send(w,value)
def text(value):QTest.keyClicks(w,value);app.processEvents()
def current(name):assert type(w.current()).__name__==name,(name,type(w.current()).__name__);return w.current()
def snap(name):
 app.processEvents();QTest.qWait(50);app.processEvents();assert not fixed_page.problems(w),(name,fixed_page.problems(w))
 file=captures/(MODE+'-'+name+'.png');assert not file.exists();assert w.grab().save(str(file))
def name_box(value):
 box=w.current()
 for _ in range(len(box.field.text)):key(Qt.Key.Key_Backspace)
 text(value);key(Qt.Key.Key_Return)
def move(s,index):
 for _ in range(100):
  if s.cursor[s.side]==index:return
  key(Qt.Key.Key_Down if s.cursor[s.side]<index else Qt.Key.Key_Up)
 raise AssertionError('squad cursor did not reach requested row')

class AuditWalk(Walk):
 def __init__(self):
  super().__init__('657wholejourney',w,w.career);self.expect={};self.replayed=[];self._last_replay=None
 def each(self):
  if time.monotonic()-getattr(self,'_last_note',0)>3:
   self._last_note=time.monotonic();print('JOURNEY '+self.label(w.current()),flush=True)
  if type(w.current()).__name__=='RecordingNameScreen':
   box=w.current();kind=box.record_kind;name_box('Audit goal' if kind=='goal' else 'Audit summary');note('saved '+kind+' through S21 keys');return
  if type(w.current()).__name__=='MenuScreen' and w.current().phase=='pause' and self.out.get('pause_done'):
   # This audit synchronously visits T/bench/ack inside on_menu, then returns
   # to the same label. The base walker intentionally reacts to label changes.
   play_on(w,w.current());return
  return super().each()
 def playing(self,pitch):
  super().playing(pitch)
  if pitch.replay is not None:
   frame=pitch.replay.frame
   if frame is not None and frame['sequence']!=self._last_replay:
    self.replayed.append(copy.deepcopy(frame));self._last_replay=frame['sequence']
   return
  c=pitch.controller;frame=c.display.frame
  if frame is None or c.stop is not None or c.held or pitch.stop_box.open:return
  if not self.out.get('commentary') and frame['minute']>=2:
   key(Qt.Key.Key_Space);assert c.commentary_paused
   before=(c.drawn,c.acked,len(c.events),len(c.choices));QTest.qWait(100)
   assert (c.drawn,c.acked,len(c.events),len(c.choices))==before
   snap('commentary-paused');key(Qt.Key.Key_Space);assert not c.commentary_paused
   self.out['commentary']=True;note('commentary Space holds and resumes');return
  if not self.out.get('pause_sent') and frame['minute']>=5:
   self.out['pause_sent']=True;key(Qt.Key.Key_Escape)
 def on_menu(self,screen):
  if screen.phase=='pause' and not self.out.get('pause_done'):
   self.out['pause_after']=w.match_day.controller.bridge._frame_sequence-1
   key(Qt.Key.Key_T);editor=current('TeamTacticsScreen');assert editor.team_header.team['manager'].text()=='Audit A'
   old=editor.answer.team_tactics;key(Qt.Key.Key_Return)
   pump(lambda:not editor.pending,120,'657 team tactic acknowledgement')
   assert editor.answer.team_tactics==old^16;snap('live-team-ack');key(Qt.Key.Key_Escape)
   key(Qt.Key.Key_Space);bench=current('BenchScreen')
   request_from_bench(w,bench,True);self.out['pause_done']=True
   snap('request-confirmed');key(Qt.Key.Key_Escape);return
  play_on(w,screen)
 def on_box(self,pitch,box):
  if box.timed:accept_opportunity_with_escape(w,pitch);return
  if box.kind=='replay' and 'goal' not in self.expect:
   self.expect['goal']=canonical(copy.deepcopy(pitch.goal_record));self.replayed=[];self._last_replay=None
   snap('replay-question');key(Qt.Key.Key_Y);return
  if box.kind=='save-goal' and not self.out.get('saved_goal') and 'goal' in self.expect:
   assert self.replayed==self.expect['goal']['frames'],'replay samples differ from the captured goal'
   self.out['saved_goal']=True;key(Qt.Key.Key_Y);return
  return super().on_box(pitch,box)
 def on_board(self,screen):
  if screen.phase=='half':
   self.out['half']=True;snap('half-time');key(Qt.Key.Key_Escape);return
  if screen.save_summary:
   self.expect['summary']=canonical(replays.summary_data(screen));snap('full-time');key(Qt.Key.Key_Y);return
  super().on_board(screen)
 def on_bench(self,screen):
  answer=screen.answer
  if screen.mode=='refused':raise AssertionError('positive audit input refused: '+screen.message)
  if answer.takes_substitutions and answer.left and (answer.context=='half_time' or not self.out.get('first_swap')):
   pair=compatible_pair(answer,taken_off=self.out.get('taken_off',()),injured_first=True)
   before=list(answer.eleven);swap_immediately(w,screen,pair)
   assert screen.answer.eleven!=before and not screen.pending
   self.out.setdefault('taken_off',[]).append(pair[0]);self.out['first_swap']=True
   note('immediate legal swap '+answer.context);snap('swap-'+str(len(self.out['taken_off'])))
  key(Qt.Key.Key_Escape)

try:
 if MODE=='create':
  paths.data.mkdir(parents=True)
  for filename,expected in data_setup.WINDOW_MANIFEST:
   source=Path('/home/diego/projects/goal2/.cache')/filename
   assert hashlib.sha256(source.read_bytes()).hexdigest()==expected;shutil.copyfile(source,paths.data/filename)
  helpfile=Path('/home/diego/projects/goal2-archaeology-engine/.cache/goal2/GOAL.HLP')
  assert hashlib.sha256(helpfile.read_bytes()).hexdigest()=='2f3be8648a52045b6f7af1f41cba020d6a662229e5db499e203c5d0957308f60'
  shutil.copyfile(helpfile,paths.data/'GOAL.HLP')
  w.start();current('StartScreen');key(Qt.Key.Key_N);current('NewGameScreen');key(Qt.Key.Key_Tab);text('2028');key(Qt.Key.Key_Return)
  country=current('CountryScreen')
  for _ in range(128):
   if country.chosen()[0]==2:break
   key(Qt.Key.Key_Down)
  assert country.chosen()[0]==2;key(Qt.Key.Key_Return);text('Audit A');key(Qt.Key.Key_Return);current('DeskScreen')
  model=w.career;note('fresh Austria career through S02/S03/S04 UI');snap('desk-new')
  key(Qt.Key.Key_Space);s=current('SquadScreen');key(Qt.Key.Key_Right);pool=[]
  for i in range(80):
   pool.append(s.current())
   if i<79:key(Qt.Key.Key_Down)
  assert len(set(pool))==80
  outgoing=model.state.managed_squad[1];role=model.state.players[outgoing][6]
  index=next(i for i,word in enumerate(pool) if model.state.players[word][6]==role)
  move(s,index);incoming=s.current();key(Qt.Key.Key_Return);key(Qt.Key.Key_Left);move(s,1);key(Qt.Key.Key_Return)
  assert incoming in model.state.managed_squad and outgoing not in model.state.managed_squad
  original=model.state.players[incoming][6];key(Qt.Key.Key_R);key(Qt.Key.Key_C)
  while model.state.players[incoming][6]!=original:key(Qt.Key.Key_R)
  key(Qt.Key.Key_T);current('PlayerTacticsScreen')
  for i in range(4):
   for _ in range(3):key(Qt.Key.Key_Return)
   if i<3:key(Qt.Key.Key_Down)
  snap('personal');key(Qt.Key.Key_Escape);key(Qt.Key.Key_Escape);current('DeskScreen')
  key(Qt.Key.Key_T);editor=current('TeamTacticsScreen');old=model.state.country_tactics
  for _ in range(2):
   for i in range(8):
    key(Qt.Key.Key_Return)
    if i<7:key(Qt.Key.Key_Down)
   for _ in range(7):key(Qt.Key.Key_Up)
  assert model.state.country_tactics==old;snap('pre-match-team');key(Qt.Key.Key_Escape)
  key(Qt.Key.Key_F1);current('HelpScreen');key(Qt.Key.Key_Down);snap('help');key(Qt.Key.Key_Escape)
  before=copy.deepcopy(model.state);walk=AuditWalk();w.current().highlight(PLAY_NEXT);key(Qt.Key.Key_Return);walk.run()
  controller=walk.out['controller'];assert controller.error is None
  assert model.state.match_count==before.match_count+1
  assert walk.out.get('commentary') and walk.out.get('pause_done') and walk.out.get('half') and walk.out.get('first_swap')
  reference=DesktopModel(model._goaldat,model.template_bytes,TARGET/'reference-never-saved.g2save');reference.state=copy.deepcopy(before)
  outcome=play_through_bridge(reference,controller.choices,pause_after=walk.out['pause_after'])
  assert outcome.result==controller.outcome.result and outcome.events==controller.outcome.events
  assert outcome.memory==controller.outcome.memory and outcome.seeds==controller.outcome.seeds
  assert reference.state==model.state;note('whole same-choice result/events/memory/seeds/career equal')
  for kind,data in walk.expect.items():
   entries=replays.entries(paths.root/'recordings',kind);assert entries
   assert replays.read(entries[0]['path'])['data']==data
  key(Qt.Key.Key_F4);listing=current('RecordingsScreen');assert listing.entries;key(Qt.Key.Key_Return);current('BoardScreen');snap('summary-reopened');key(Qt.Key.Key_Escape);key(Qt.Key.Key_Escape);current('DeskScreen')
  if walk.out.get('saved_goal'):
   key(Qt.Key.Key_F3);key(Qt.Key.Key_Return);current('SavedGoalMenu');snap('goal-menu');key(Qt.Key.Key_Escape);key(Qt.Key.Key_Escape)
  expected=copy.deepcopy(model.state);key(Qt.Key.Key_F7);current('SaveScreen');name_box('Whole audit');current('DeskScreen')
  assert saves.load(model.save_path,paths.goal_dat).state==expected
  (TARGET/'expected-private.pickle').write_bytes(pickle.dumps(expected,protocol=5))
  key(Qt.Key.Key_F10);key(Qt.Key.Key_Y);assert not w.isVisible()
  receipt=dict(source=HEAD,actions=actions,screen_order=walk.order,choices=controller.choices,pause_after=walk.out['pause_after'],full_same_choice_equal=True,match_count=model.state.match_count,saved_goal=bool(walk.out.get('saved_goal')),saved_summary='summary' in walk.expect,unvisited=['extra_time','shootout','season_continuation','all22screens'],scope='Fresh GUI-created career + one watched friendly, recording/save lifecycle; no forced outcomes/state insertion')
 else:
  expected=pickle.loads((TARGET/'expected-private.pickle').read_bytes());w.start();current('StartScreen');key(Qt.Key.Key_Return);current('DeskScreen')
  assert w.career.state==expected;assert not w.career.unsaved;snap('separate-process-reload')
  for keycode,kind in ((Qt.Key.Key_F4,'summary'),(Qt.Key.Key_F3,'goal')):
   if replays.entries(paths.root/'recordings',kind):key(keycode);assert current('RecordingsScreen').entries;key(Qt.Key.Key_Escape)
  key(Qt.Key.Key_F10);key(Qt.Key.Key_Y);assert not w.isVisible()
  receipt=dict(source=HEAD,complete_saved_career_equal=True,separate_process=True)
 (TARGET/(MODE+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n');print('PASS '+MODE,flush=True)
finally:
 if w.match_day is not None:w.match_day.close()
 w.leave();w.close();app.processEvents()
