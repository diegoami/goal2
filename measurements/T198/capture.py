"""Rebuilt original-backed display snapshots; normal queued-paint boundary, no live-match claim."""
from pathlib import Path
import os,sys,argparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import tempfile,json
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from goal2.desktop import data_setup
from goal2.desktop.model import DesktopModel
from goal2.game.state import from_savestate
from goal2.data.goaldat import load
from goal2.ui.window import Window
from goal2.ui.s07_team_info import TeamInfoScreen
from goal2.tests.test_core_team_panels_t144 import FIXTURES
app=QApplication.instance() or QApplication([])
root=ROOT/'.cache';parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True);receipts=[]
with tempfile.TemporaryDirectory() as temp:
 for fixture,country,active in (('selection',7,False),('friendly',16,True)):
  raw=(root/FIXTURES[fixture][0]).read_bytes();model=DesktopModel(load((root/'GOAL.DAT').read_bytes()),raw,Path(temp)/'never-written.g2save');model.state=from_savestate(raw);model.mark_saved()
  window=Window(data_setup.paths(Path(temp)/fixture));window.show();screen=TeamInfoScreen(window,model);window.push(screen);app.processEvents();QTest.qWait(50);window.grab()
  screen.card_view.match_context=active;screen.index=next(i for i,c in enumerate(screen.order) if c[0]==country);screen.preview();screen._show()
  for width,height in ((1440,900),(1800,1125),(2110,1213)):
   window.resize(width,height)
   for _ in range(3):app.processEvents()
   QTest.qWait(50)
   path=out/f'{fixture}-{country}-{width}x{height}.png';assert window.grab().save(str(path));receipts.append({'fixture':fixture,'country':country,'active_display_snapshot':active,'size':[width,height],'path':str(path)})
  window.leave();window.deleteLater();app.processEvents()
 (out/'index.json').write_text(json.dumps({'scope':'Rebuilt UI from hash-bound original snapshots; explicit test presentation context, not natural live match','captures':receipts},indent=2)+'\n')
