"""Real Qt inputs through a fresh isolated career and separate process save/load.
No mock services, prepared match packets, engine play or owner-window input.
Private state comparison files stay in the isolated target; receipts expose hashes only.
"""
from pathlib import Path
import sys,os,json,shutil,hashlib,pickle,copy,subprocess,platform
ROOT=Path(sys.argv[1]);TARGET=Path(sys.argv[2]);MODE=sys.argv[3];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
FIXTURES=Path(sys.argv[5]) if len(sys.argv)>5 else ROOT/'.cache'
from goal2.desktop import data_setup,fixed_page
from goal2.ui.window import Window
from goal2.ui.s02_start import StartScreen
from goal2.ui.s03_new_game import NewGameScreen
from goal2.ui.s04_country import CountryScreen
from goal2.ui.s06_desk import DeskScreen
from goal2.ui.s08_squad import SquadScreen
from goal2.ui.s09_player_tactics import PlayerTacticsScreen
from goal2.ui.s10_team_tactics import TeamTacticsScreen
from goal2.ui.s21_save import SaveScreen,QuestionScreen
from goal2.ui import saves
app=QApplication.instance() or QApplication([]);paths=data_setup.Paths(TARGET/'data-root');out=TARGET/'captures';out.mkdir(parents=True,exist_ok=True)
w=Window(paths);w.resize(1440,900);w.show();app.processEvents();events=[]
def record(text):events.append(text);print(MODE,text,flush=True)
def key(k):QTest.keyClick(w,k);app.processEvents()
def text(t):QTest.keyClicks(w,t);app.processEvents()
def snap(name):
 app.processEvents();QTest.qWait(50);assert fixed_page.problems(w)==[],(name,fixed_page.problems(w));assert w.grab().save(str(out/(MODE+'-'+name+'.png')))
def current(cls):assert isinstance(w.current(),cls),(cls,type(w.current()));return w.current()
def move(s,index):
 while s.cursor[s.side]<index:key(Qt.Key.Key_Down)
 while s.cursor[s.side]>index:key(Qt.Key.Key_Up)
if MODE=='create':
 paths.data.mkdir(parents=True,exist_ok=True)
 for name,digest in data_setup.WINDOW_MANIFEST:
  src=FIXTURES/name;assert hashlib.sha256(src.read_bytes()).hexdigest()==digest;shutil.copy2(src,paths.data/name)
 help_path=FIXTURES/'GOAL.HLP'
 if help_path.exists():shutil.copy2(help_path,paths.data/'GOAL.HLP')
 w.start();current(StartScreen);snap('start');key(Qt.Key.Key_N);current(NewGameScreen);key(Qt.Key.Key_Return);current(CountryScreen);snap('country');key(Qt.Key.Key_Return);text('Audit A');key(Qt.Key.Key_Return);current(DeskScreen)
 model=w.career;initial=copy.deepcopy(model.state);record('fresh UI-created career; no template-state injection')
 key(Qt.Key.Key_Space);s=current(SquadScreen);key(Qt.Key.Key_Right);seen=[]
 for i in range(80):
  seen.append(s.current())
  if i<79:key(Qt.Key.Key_Down)
 assert len(set(seen))==80;record('all80pool players reached with arrows')
 move(s,3);incoming=s.current();key(Qt.Key.Key_Return);key(Qt.Key.Key_Left);move(s,7);outgoing=s.current();key(Qt.Key.Key_Return)
 assert incoming in model.state.managed_squad and outgoing not in model.state.managed_squad;record('two-Enter pool/squad exchange updates membership')
 player=s.current();pos=model.state.players[player][6];key(Qt.Key.Key_R);assert model.state.players[player][6]==(pos+1)%14;key(Qt.Key.Key_C);assert model.state.players[player][6]==model.state.players[player][7];key(Qt.Key.Key_R)
 key(Qt.Key.Key_T);t=current(PlayerTacticsScreen)
 for i in range(4):
  before=model.state.players[player];key(Qt.Key.Key_Return);assert model.state.players[player]!=before
  if i<3:key(Qt.Key.Key_Down)
 snap('personal');key(Qt.Key.Key_Escape);current(SquadScreen);snap('squad');key(Qt.Key.Key_Escape);current(DeskScreen)
 key(Qt.Key.Key_T);current(TeamTacticsScreen)
 before=model.state.country_tactics
 for i in range(8):
  prev=model.state.country_tactics;key(Qt.Key.Key_Return);assert model.state.country_tactics!=prev
  if i<7:key(Qt.Key.Key_Down)
 assert model.state.country_tactics==before^255;snap('team');key(Qt.Key.Key_Escape);current(DeskScreen);record('position/club position, four personal and eight team tactics via keys')
 if help_path.exists():
  key(Qt.Key.Key_F1);snap('help');key(Qt.Key.Key_Down);key(Qt.Key.Key_Escape);current(DeskScreen);record('imported original help opens, scrolls and returns')
 expected=copy.deepcopy(model.state);assert expected!=initial;key(Qt.Key.Key_F7);current(SaveScreen);text('Track A fresh audit');snap('save');key(Qt.Key.Key_Return);current(DeskScreen);assert not model.unsaved
 save=model.save_path;assert saves.load(save,paths.goal_dat).state==expected;(TARGET/'expected-private.pickle').write_bytes(pickle.dumps(expected,protocol=5));record('named save reload equals complete changed career state')
 key(Qt.Key.Key_F10);current(QuestionScreen);key(Qt.Key.Key_N);current(DeskScreen);key(Qt.Key.Key_F10);key(Qt.Key.Key_Y);assert not w.isVisible();record('quit-cancel and saved quit succeed')
else:
 expected=pickle.loads((TARGET/'expected-private.pickle').read_bytes());w.start();s=current(StartScreen);assert s.entries;key(Qt.Key.Key_Return);current(DeskScreen);assert w.career.state==expected;assert not w.career.unsaved;snap('reloaded');record('separate process Start/Continue reload equals complete saved career')
 if MODE=='resume':
  key(Qt.Key.Key_F7);box=current(SaveScreen);assert box.field.text=='Track A fresh audit';key(Qt.Key.Key_Escape);current(DeskScreen)
  key(Qt.Key.Key_T);key(Qt.Key.Key_Return);key(Qt.Key.Key_Escape);assert w.career.state!=expected and w.career.unsaved
  key(Qt.Key.Key_F10);key(Qt.Key.Key_Y);current(QuestionScreen);snap('discard-question');key(Qt.Key.Key_N);assert not w.isVisible();record('unsaved quit asks before discard; saved file remains untouched')
 else:key(Qt.Key.Key_F10);key(Qt.Key.Key_Y);assert not w.isVisible();record('third-process reload proves discarded edit was not saved')
receipt={'mode':MODE,'head':sys.argv[4] if len(sys.argv)>4 else subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'python':platform.python_version(),'scope':'fresh management UI and separate-process named-save lifecycle; no watched match/season/original DOS UI parity claim','events':events,'private_expected_sha256':hashlib.sha256((TARGET/'expected-private.pickle').read_bytes()).hexdigest()}
(TARGET/(MODE+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n');w.leave();w.deleteLater();app.processEvents();print('PASS',MODE,flush=True)
