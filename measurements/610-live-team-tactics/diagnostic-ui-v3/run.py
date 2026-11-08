import sys,unittest,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from goal2.game.engine_process import EngineProcess
from goal2.game.engine_python import worker_command
from goal2.ui.match_day import MatchDay
from goal2.tests.test_live_team_tactics_610 import ActualLiveTeamTactics
command=worker_command('goal2.game.engine_server');i=command.index('-m');command=command[:i]+[str(Path(__file__).with_name('engine.py'))]
start=EngineProcess._start
edit=MatchDay.edit_tactics
edited=MatchDay.edited
def launch(self):
 print('ACTUAL_ENGINE_START',self.command,'=>',command,flush=True)
 self.command=command
 return start(self)
def submit(self,screen,element,value):
 print('TACTIC_SEND',json.dumps(dict(element=element,value=value,pending=self.controller.edit_pending,stop=None if self.controller.stop is None else self.controller.stop.data,choices=self.controller.choices)),flush=True)
 result=edit(self,screen,element,value)
 print('TACTIC_SENT',json.dumps(dict(pending=self.controller.edit_pending,choices=self.controller.choices)),flush=True)
 return result
def reply(self,pitch,decision,report):
 print('EDITED_REPLY',json.dumps(dict(data=decision.data,tactics_events=[e['data'] for e in self.controller.events if e['kind']=='tactics'][-3:])),flush=True)
 return edited(self,pitch,decision,report)
with patch.object(EngineProcess,'_start',launch),patch.object(MatchDay,'edit_tactics',submit),patch.object(MatchDay,'edited',reply):
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([ActualLiveTeamTactics('test_requested_pause_all_flags_confirm_and_esc_returns_to_the_pitch')]))
raise SystemExit(0 if r.wasSuccessful() else 1)
