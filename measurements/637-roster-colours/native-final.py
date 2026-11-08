import pathlib,sys,tempfile,json,hashlib,types,unittest,importlib
from PySide6.QtWidgets import QApplication
from goal2.ui import theme
repo=pathlib.Path(r'\\wsl.localhost\Ubuntu\home\diego\projects\m3-trackb\goal2')
out=pathlib.Path(r'\\wsl.localhost\Ubuntu\tmp\goal2-roster-colours')
sources={}
for name in ('squad_card','s15_match_menu'):
 p=repo/'goal2'/'ui'/(name+'.py');raw=p.read_bytes();sources[str(p.relative_to(repo))]=hashlib.sha256(raw).hexdigest()
 module=importlib.import_module('goal2.ui.'+name)
 exec(compile(raw,str(p),'exec'),module.__dict__)
p=repo/'goal2/tests/test_roster_colours_637.py';raw=p.read_bytes();sources[str(p.relative_to(repo))]=hashlib.sha256(raw).hexdigest()
test=types.ModuleType('native_colour_test');test.__file__=str(p);exec(compile(raw,str(p),'exec'),test.__dict__)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test))
assert result.wasSuccessful()
from goal2.desktop.model import DesktopModel
from goal2.desktop import fixed_page
from goal2.ui.window import Window
from goal2.ui.s08_squad import SquadScreen
app=QApplication.instance();root=pathlib.Path(r'C:\Users\diego\AppData\Local\goal2-preview-d56e793\data')
results=[]
with tempfile.TemporaryDirectory(prefix='goal2-colour-exact-source-') as tmp:
 m=DesktopModel.open(root/'e010-r0008-halftime.sav',root/'GOAL.DAT',pathlib.Path(tmp)/'probe.g2save',country=7)
 w=Window();s=SquadScreen(w,m);w.push(s);w.show()
 for width,height in ((1440,900),(1200,750)):
  w.resize(width,height);app.processEvents();w.frame.fit();app.processEvents()
  image=out/f'squad-final-{width}.png';assert w.grab().save(str(image))
  problems=fixed_page.problems(w);rows=len(s.strip.shown_texts());assert rows==20;assert not problems,problems
  results.append({'size':[width,height],'visible_rows':rows,'layout_problems':problems,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
 w.leaving=True;w.close()
record={'source':'24b87f7797047b663187c58d3ca131f2cce89705','native_python':sys.version,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source_sha256':sources,'screens':results,'installed_runtime':'d56e793','production_files_changed':False,'owner_game_and_saves_changed':False}
(out/'native-final.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record))
