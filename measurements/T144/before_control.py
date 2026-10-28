"""Re-run the new behavioural tests against genuine pre-integration source.

Only child-process module objects are replaced; tracked files stay untouched.
The separate initial before-v1.log proves vendor absence on actual main.
"""
from pathlib import Path
import subprocess,sys,types,unittest,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
base='af2f7419'
for name,path in [('goal2.core.views','goal2/core/views.py'),('goal2.desktop.country_card','goal2/desktop/country_card.py')]:
 parent,child=name.rsplit('.',1);package=__import__(parent,fromlist=['*'])
 source=subprocess.check_output(['git','show',base+':'+path],cwd=ROOT,text=True)
 module=types.ModuleType(name);module.__file__=str(ROOT/path);module.__package__=parent
 sys.modules[name]=module;setattr(package,child,module);exec(compile(source,'<'+base+':'+path+'>','exec'),module.__dict__)
from goal2.tests import test_core_team_panels_t144 as tests
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (tests.LiveProjection,tests.AuthoredBoundaries,tests.PaintedPanels))
class Result(unittest.TextTestResult):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.successes=[]
 def addSuccess(self,test):self.successes.append(test.id());super().addSuccess(test)
r=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
assert r.testsRun==17 and not r.skipped and not r.successes,(r.testsRun,r.skipped,r.successes)
print(json.dumps(dict(base=base,tests=r.testsRun,expected_before_failures=True,unchanged_tracked_source=True)))
