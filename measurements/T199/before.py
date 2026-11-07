"""Run current boundary controls against the original client/server source, without checkout edits."""
import pathlib,subprocess,sys,types,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import goal2.game
BASE='bccf17fa16699cfe925be3d1748c2d32efaa049c'
for name in ('engine_server','engine_process'):
 path='goal2/game/'+name+'.py'
 source=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
 module=types.ModuleType('goal2.game.'+name);module.__file__=str(ROOT/path);module.__package__='goal2.game'
 sys.modules[module.__name__]=module;setattr(goal2.game,name,module)
 exec(compile(source,module.__file__,'exec'),module.__dict__)
suite=unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_completion_boundary_t199')
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==10 and len(result.failures)==10 and not result.errors and not result.skipped
print('All10new controls fail on original source; no match or port executes.')
