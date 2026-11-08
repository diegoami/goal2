"""Run the accepted audit on Windows, with physical Temp fixtures and no owner focus."""
import hashlib,json,os,runpy,shutil,sys,tempfile,time,traceback
from pathlib import Path
ROOT=Path(sys.argv[1]);MODE=sys.argv[2];LABEL=sys.argv[3]
assert os.name=='nt'
assert MODE in ('create','reload')
HEAD=sys.argv[4];assert len(HEAD)==40
os.environ['GOAL2_AUDIT_HEAD']=HEAD
os.environ.update(QT_QPA_PLATFORM='offscreen',SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT))
pypy=Path(r'C:\Users\diego\goal2-playtest\main-f5703ddb\goal2-0.1.0-win64\pypy\pypy.exe');assert pypy.is_file()
os.environ['GOAL2_ENGINE_PYTHON']=str(pypy)
manifest=json.loads((ROOT/'.cache'/('native660-source-'+LABEL+'.json')).read_text())
assert manifest['head']==HEAD
for name,sha in manifest['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
state=ROOT/'.cache'/('native660-state-'+LABEL+'.json')
if MODE=='create':
 assert not state.exists(),'new attempt label required'
 private=Path(tempfile.mkdtemp(prefix='goal2-native660-'));fixtures=private/'fixtures';fixtures.mkdir()
 original=Path(r'\\wsl.localhost\Ubuntu\home\diego\projects\goal2\.cache')
 for name in ('GOAL.DAT','e010-r0008-halftime.sav'):shutil.copyfile(original/name,fixtures/name)
 helpfile=Path(r'\\wsl.localhost\Ubuntu\home\diego\projects\goal2-archaeology-engine\.cache\goal2\GOAL.HLP')
 shutil.copyfile(helpfile,fixtures/'GOAL.HLP')
 data={'private':str(private),'fixtures':str(fixtures),'target':str(private/'case'),'source_head':HEAD}
 state.write_text(json.dumps(data,indent=2)+'\n')
else:
 data=json.loads(state.read_text());assert data['source_head']==HEAD
 fixtures=Path(data['fixtures'])
sys.path.insert(0,str(ROOT))
from goal2.tests import requires
requires.CACHE=fixtures
from goal2.game.engine_python import engine_python,_is_pypy311
assert _is_pypy311(engine_python())
started=time.monotonic();passed=False;error=None;result={}
try:
 sys.argv=[str(ROOT/'measurements/660-native-journey/audit-v2.py'),str(ROOT),data['target'],MODE,str(fixtures),str(fixtures/'GOAL.HLP')]
 values=runpy.run_path(sys.argv[0],run_name='__main__')
 result=json.loads((Path(data['target'])/(MODE+'-receipt.json')).read_text())
 assert result['source']==HEAD
 if MODE=='create':assert result['full_same_choice_equal'] and result['saved_goal'] and result['saved_summary']
 else:assert result['complete_saved_career_equal'] and result['separate_process']
 for name,sha in manifest['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
 assert values['app'].platformName()=='offscreen'
 passed=True
except BaseException as exception:
 error=type(exception).__name__+': '+str(exception);traceback.print_exc()
receipt={'source_head':HEAD,'mode':MODE,'label':LABEL,'os_name':os.name,'python':sys.version,'qt_platform':'offscreen','engine_python_sha256':hashlib.sha256(pypy.read_bytes()).hexdigest(),'sources':manifest['files'],'fixture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures.iterdir() if p.is_file()},'seconds':time.monotonic()-started,'passed':passed,'error':error,'private_output':data['target'],'audit_receipt':result}
out=ROOT/'.cache'/('native660-'+MODE+'-'+LABEL+'.json');assert not out.exists();out.write_text(json.dumps(receipt,indent=2)+'\n')
print('NATIVE660_RESULT '+json.dumps({k:v for k,v in receipt.items() if k!='sources'},sort_keys=True),flush=True)
sys.exit(0 if passed else 1)
