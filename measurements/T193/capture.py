"""T193 isolated display fixtures. Initial normal paint, no stylesheet reset, no owner game/profile."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from goal2.desktop import data_setup,fixed_page
from goal2.ui import theme
from goal2.ui.window import Window
from goal2.ui.s08_squad import open_squad
from goal2.ui.s16_choose import ChooseScreen
from goal2.tests.test_ui_squad_t165 import career
from goal2.tests.test_immediate_bench_t188 import ImmediateBench

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
app=QApplication.instance() or QApplication([]);theme.install(app);rows=[]
def settle(window):
 for _ in range(3):app.processEvents()
 window.grab()  # ordinary initial paint barrier, not a style/size/data workaround

def capture(window,screen,name,refresh):
 settle(window)
 for width,height in [(1440,900),(1800,1125),(2110,1213)]:
  window.resize(width,height);refresh()
  settle(window)
  problems=fixed_page.problems(window)
  if problems:raise AssertionError((name,width,height,problems))
  path=out/f'{name}-{width}x{height}.png';pix=window.grab();pix.save(str(path))
  card=screen.card
  image=pix.toImage();point=card.mapTo(window,QPoint(0,0))
  border=image.pixelColor(point.x(),point.y()).name()
  if border!=theme.FRAME_DARK:raise AssertionError(('card inherited frame not painted',name,border))
  rows.append({'view':name,'size':[width,height],'facts':card.facts.text(),'positions':card.positions.text(),
   'card_border':border,'layout_problems':problems,'screenshot':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})

with tempfile.TemporaryDirectory() as folder:
 model=career();window=Window(data_setup.paths(Path(folder)));window.open_career(model);window.show()
 screen=open_squad(window,model);settle(window)
 try:
  capture(window,screen,'squad-keeper',screen.refresh)
  screen.cursor['squad']=3;screen.refresh()
  capture(window,screen,'squad-outfield',screen.refresh)
  words=model.state.managed_squad[:11]
  choice=window.push(ChooseScreen(window,model,'captain',words,words[0],lambda value:None));choice.timer.stop()
  capture(window,choice,'captain',choice._show)
 finally:window.leave();window.deleteLater();app.processEvents()

fixture=unittest.TestCase();ImmediateBench.setUp(fixture);settle(fixture.window)
try:
 card=copy.deepcopy(fixture.bench.card.card)
 card.update(position='defensive midfielder',club_position='defensive midfielder',foot='two footed',
             cards=['carried booking','booked','sent off'])
 def update_bench():
  fixture.bench.feedback_report={'made':[],'requested':[],
   'refused':[[fixture.off,fixture.on,'This player already left the field and cannot return to this match.']]}
  fixture.bench.refresh();fixture.bench.card.set_card(card)
 capture(fixture.window,fixture.bench,'bench-long-fields-refusal',update_bench)
finally:fixture.doCleanups();app.processEvents()

source=Path(sys.modules['goal2.ui.squad_card'].__file__)
(out/'receipt.json').write_text(json.dumps({'fixture':'isolated template career; bench long fields/refusal are explicit UI-only packets, no natural-play or live-record freshness claim',
 'paint':'normal initial page paint before mutations; no forced stylesheet refresh',
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':rows},indent=2)+'\n')
print(f'{len(rows)} captures: no geometry problems; inherited card frame painted in each')
