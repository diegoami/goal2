"""T192 synthetic performance display fixtures over an isolated template career, never an owner save."""
import hashlib,json,sys,tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from goal2.desktop import data_setup,fixed_page
from goal2.tests.test_ui_squad_t165 import career
from goal2.ui import theme
from goal2.ui.window import Window
from goal2.ui.s08_squad import open_squad

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
app=QApplication.instance() or QApplication([]);theme.install(app)
model=career();rows=[]
with tempfile.TemporaryDirectory() as folder:
 window=Window(data_setup.paths(Path(folder)));window.open_career(model);window.show();screen=open_squad(window,model)
 try:
  word=screen.current()
  for name,value in [('blank',0x7FFF),('six-stars',205),('substitute-three-stars',10055)]:
   record=bytearray(model.state.players[word]);record[18:20]=value.to_bytes(2,'little');model.state.players[word]=bytes(record)
   for width,height in [(1440,900),(1800,1125),(2110,1213)]:
    window.resize(width,height);screen.refresh()
    for _ in range(3):app.processEvents()
    problems=fixed_page.problems(window)
    if problems:raise AssertionError(problems)
    path=out/f'{name}-{width}x{height}.png';window.grab().save(str(path))
    rows.append({'fixture':name,'raw_word':value,'size':[width,height],'facts':screen.card.facts.text(),
                 'layout_problems':problems,'screenshot':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 finally:window.leave();window.deleteLater();app.processEvents()
(out/'receipt.json').write_text(json.dumps({'fixture':'isolated original template career with explicitly controlled performance word; no live-match freshness claim','cases':rows},indent=2)+'\n')
print(f'{len(rows)} display captures; all geometry checks pass')
