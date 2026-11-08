import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from goal2.tests.test_ui_bench_t180 import career
from goal2.ui.s17_pitch import suggested_captain,engine_fixture
from goal2.tests.live_tactics_probe import trace
from goal2.tests import pypy_engine
model=career();s=model.state
model.confirm(s.starting_eleven or s.managed_squad[:11],suggested_captain(s),s.country_tactics)
fixture=engine_fixture(s.campaign.next_fixture)
for engine in ('original','port'):
 result=trace(copy.deepcopy(model.state),fixture,engine) if engine=='original' else pypy_engine.call('goal2.tests.live_tactics_probe:trace',copy.deepcopy(model.state),fixture,engine)
 p=Path('measurements/610-live-team-tactics/diagnostic-v1')/(engine+'.json')
 with p.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('keys','decisions')}),flush=True)
