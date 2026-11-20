"""Load the committed application versions without changing working files."""
import importlib.abc,importlib.util,subprocess,sys,unittest
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root))
BASE='7791016fc7aef78c7e29d7a88827fb1f51ec5c4f'
paths=['goal2/desktop/core_window.py', 'goal2/desktop/launch.py', 'goal2/ui/replays.py', 'goal2/ui/s03_new_game.py', 'goal2/ui/s06_desk.py', 'goal2/ui/s07_team_info.py', 'goal2/ui/s08_squad.py', 'goal2/ui/s10_team_tactics.py', 'goal2/ui/s15_match_menu.py']
old={p[:-3].replace('/','.'): (root/p,subprocess.check_output(['git','show',BASE+':'+p]))
     for p in paths if p.startswith('goal2/') and '/tests/' not in p and p.endswith('.py')}
class Loader(importlib.abc.Loader):
 def __init__(self,name):self.name=name
 def create_module(self,spec):return None
 def exec_module(self,module):
  path,data=old[self.name];module.__file__=str(path)
  exec(compile(data,str(path),'exec'),module.__dict__)
class Finder(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in old:return importlib.util.spec_from_loader(fullname,Loader(fullname),origin=str(old[fullname][0]))
sys.meta_path.insert(0,Finder())
suite=unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_ui_cues_799')
r=unittest.TextTestRunner(verbosity=2).run(suite)
assert len(r.failures)==10 and not r.errors,(len(r.failures),len(r.errors))
print('Verified baseline:8methods/10failing subcases, committed application loaded without filesystem mutation')
