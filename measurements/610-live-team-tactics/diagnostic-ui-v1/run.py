import sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from goal2.game.engine_process import EngineProcess
from goal2.game.engine_python import worker_command
from goal2.tests.test_live_team_tactics_610 import ActualLiveTeamTactics
command=worker_command('goal2.game.engine_server');i=command.index('-m');command=command[:i]+[str(Path(__file__).with_name('engine.py'))]
original=EngineProcess.__init__
def init(self,on_reply,**kwargs):
 if kwargs.get('command') is None:kwargs['command']=command
 original(self,on_reply,**kwargs)
print('Read-only tracing under actual worker:',command,flush=True)
with patch.object(EngineProcess,'__init__',init):
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([ActualLiveTeamTactics('test_requested_pause_all_flags_confirm_and_esc_returns_to_the_pitch')]))
raise SystemExit(0 if r.wasSuccessful() else 1)
