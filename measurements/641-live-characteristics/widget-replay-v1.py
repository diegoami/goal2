"""Prepared widget replay of actual695 records; NOT a new natural UI/worker match."""
import argparse,copy,hashlib,json,os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha256',required=True)
p.add_argument('--template',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--captures',type=Path,required=True);p.add_argument('--native',action='store_true');a=p.parse_args()
assert not a.out.exists() and not a.captures.exists();a.captures.mkdir(parents=True)
if a.native:assert sys.platform=='win32'
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtGui import QColor
from goal2.desktop import data_setup,fixed_page
from goal2.desktop.model import DesktopModel
from goal2.data.goaldat import load
from goal2.game.state import from_savestate
from goal2.game.team_card import TeamMemory
from goal2.game.player_card import _wrap_raw
from goal2.desktop.country_card import characteristic_view
from goal2.ui.window import Window
from goal2.ui.s19_bench import BenchAnswer
from goal2.ui.s10_team_tactics import TeamTacticsScreen
from goal2.ui import theme
from goal2.tests.test_live_tactics_characteristics_641 import expected_panel
raw=a.input.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.input_sha256
source=json.loads(raw);decisions=[e for e in source['events'] if e['kind']=='decision'];assert len(decisions)==37
original=a.template.read_bytes();assert hashlib.sha256(original).hexdigest()=='e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d'
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory(prefix='goal2-641-view-') as directory:
 model=DesktopModel(load((ROOT/'.cache/GOAL.DAT').read_bytes()),original,Path(directory)/'unused.g2game')
 model.state=from_savestate(original);model.mark_saved()
 before=copy.deepcopy(model.state);identities=tuple(id(v) for v in (model.state,model.state.players,model.state.countries,model.state.mem))
 initial_words=list(model.state.managed_squad);initial_players=list(model.state.players)
 initial_data=dict(eleven=initial_words[:11],bench=initial_words[11:],tactics=model.state.country_tactics,
  player_records=[[w,initial_players[w].hex()] for w in initial_words])
 initial_panel=expected_panel(model,initial_data)
 window=Window(data_setup.paths(Path(directory)/'data'));window.resize(1440,900);window.show();window.open_career(model)
 screen=None;widgets=None;observations=[];changed_input=False;changed_first=False;first_expected=None;kept_views=[];shots=[]
 try:
  for index,event in enumerate(decisions):
   packet=copy.deepcopy(event['data']);packet_hash=digest(packet);words=packet['eleven']+packet['bench']
   assert len(words)==20 and len(packet['player_records'])==20 and [w for w,_ in packet['player_records']]==words
   answer=BenchAnswer(model,SimpleNamespace(data=packet,minute=event['minute'],score=event['score']))
   if screen is None:
    screen=TeamTacticsScreen(window,model,answer=answer,apply=lambda *args:None);window.push(screen);app.processEvents()
    widgets={id(w) for w in screen.findChildren(QWidget)}
   screen.answer=answer
   seen=[];country_record=TeamMemory.country_record
   def inspect(reader,country):
    if country==model.state.managed_country:
     assert reader.state is not model.state and reader.state.players is not model.state.players
     assert reader.state.managed_squad==words and reader.state.country_tactics==packet['tactics']
     assert all(reader.state.players[w]==bytes.fromhex(raw) for w,raw in packet['player_records'])
     kept_views.append(reader.state);seen.append(country)
    return country_record(reader,country)
   with mock.patch.object(TeamMemory,'country_record',inspect),mock.patch('goal2.game.player_card._wrap_raw',wraps=_wrap_raw) as parses,\
        mock.patch('goal2.game.player_card.card',side_effect=AssertionError('full card decode')),\
        mock.patch.object(model,'view',side_effect=AssertionError('career view decode')):
    screen.refresh();assert parses.call_count==1
   assert seen==[model.state.managed_country]
   expected=expected_panel(model,packet)
   assert screen.characteristics.panel==expected and screen.characteristics.cells.grid==characteristic_view(expected['descriptors'])
   assert {id(w) for w in screen.findChildren(QWidget)}==widgets
   assert digest(packet)==packet_hash and packet==event['data']
   assert model.state==before and tuple(id(v) for v in (model.state,model.state.players,model.state.countries,model.state.mem))==identities
   changed_input|=expected!=initial_panel
   if first_expected is None:first_expected=expected
   else:changed_first|=expected!=first_expected
   energy_changes=sum(bytes.fromhex(raw)[14]!=initial_players[w][14] for w,raw in packet['player_records'])
   observations.append(dict(index=index,context=packet['context'],minute=event['minute'],records=20,
    members_sha256=digest(words),raw_records_sha256=digest(packet['player_records']),panel_sha256=digest(expected),
    cells_sha256=digest(screen.characteristics.cells.grid),energy_changes_vs_declared_initial_input=energy_changes,
    state_identity_unchanged=True,ordered_current_inputs_verified=True,independent_core_equal=True,raw_parses=1))
  assert len({id(v) for v in kept_views})==37
  assert changed_input and changed_first and any(x['energy_changes_vs_declared_initial_input'] for x in observations)
  for width,height in ((1440,900),(1800,1125),(2110,1213)):
   window.resize(width,height);app.processEvents();window.grab()
   assert fixed_page.problems(window)==[]
   cells=screen.characteristics.cells
   assert cells.width()+1>=cells.content_size().width() and cells.height()+1>=cells.content_size().height()
   assert cells.font().pixelSize()>=round(24*window.frame.scale)
   assert len(screen.strip.shown_texts())==20
   assert all(label.palette().color(label.foregroundRole())==QColor(theme.CARD_LABEL) for label in cells.labels.values())
   image=cells.grab().toImage();colors={image.pixelColor(x,y).name() for y in range(image.height()) for x in range(image.width())}
   assert theme.BAR_FILLED in colors and theme.BAR_EMPTY in colors
   capture=a.captures/f'live-traits-{width}x{height}.png';assert window.grab().save(str(capture))
   shots.append(dict(size=[width,height],capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),layout_clean=True,
    labelled_cells_readable=True,pixels_grey_magenta=True,records_visible=20))
  assert not model.save_path.exists() and model.state==before
 finally:
  window.leaving=True;window.leave();app.processEvents()
value={'method':'prepared real-data widget replay; no new natural UI/worker execution or save publication',
 'platform':sys.platform,'native_requested':a.native,'qt_platform':app.platformName(),'input_run_sha256':a.input_sha256,
 'input_template_sha256':hashlib.sha256(original).hexdigest(),'observations':observations,'record_checks':740,
 'traits_changed_vs_declared_initial_input':changed_input,'traits_changed_after_first_captured_stop':changed_first,
 'original_backed_core_projection_equal':True,'state_and_packet_identity_unchanged':True,'captures':shots,
 'capture_privacy':'raw names/records and captures remain private; hashes/counts only public',
 'sources_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['goal2/ui/s10_team_tactics.py','goal2/ui/live_cards.py','goal2/game/team_card.py',
  'goal2/engine/team_card/team_characteristics.py','goal2/ui/team_card.py','goal2/tests/test_live_tactics_characteristics_641.py',str(Path(__file__).relative_to(ROOT))]}}
with a.out.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps({'prepared_replay':True,'native':a.native,'snapshots':37,'records':740,'all_core_equal':True,'state_unchanged':True,'sizes':3}),flush=True)
