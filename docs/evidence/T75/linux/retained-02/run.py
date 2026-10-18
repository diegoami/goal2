"""[designed: T75] Sequential retained desktop checks; never overlap source mutations."""
import hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
TEMPLATE='.cache/e010-r0008-halftime.sav';DATA='.cache/GOAL.DAT'
resource_args=['--template',TEMPLATE,'--data',DATA]
commands=[
 *[(name,[sys.executable,'-B','tools/desktop-ui/'+name+'.py']) for name in ('prove-pool','prove-halftime')],
 *[(name,[sys.executable,'-B','tools/desktop-ui/acceptance.py','--scenario',name,*resource_args]) for name in ('management','worker','campaign-pool','campaign-halftime')],
 ('shell',[sys.executable,'-B','tools/desktop-ui/redesign.py','--scenario','shell',*resource_args,'--evidence-dir',str(OUT/'shell')]),
]

digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=sorted((ROOT/'goal2').rglob('*.py'))
sources={str(p.relative_to(ROOT)):digest(p) for p in paths}
receipt={'tag':'[designed: T75]','platform':platform.platform(),'python':sys.version,
 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'driver_sha256':digest(Path(__file__)),'sources_before':sources,
 'resources':{name:digest(ROOT/name) for name in (TEMPLATE,DATA)},'checks':[]}
try:
 for name,command in commands:
  log=OUT/(name+'.log')
  assert not log.exists(),'never overwrite retained output'
  start=time.monotonic();print('START',name,flush=True)
  with log.open('w') as output:
   result=subprocess.run(command,cwd=ROOT,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1'},stdout=output,stderr=subprocess.STDOUT,timeout=600)
  record={'name':name,'command':command,'returncode':result.returncode,'seconds':time.monotonic()-start,'log_sha256':digest(log)}
  receipt['checks'].append(record)
  assert {str(p.relative_to(ROOT)):digest(p) for p in paths}==sources,'retained proof failed to restore exact source bytes'
  assert result.returncode==0,'retained check failed: '+name
  print('PASS',name,flush=True)
 receipt['result']='PASS'
except BaseException as exc:
 receipt['result']='FAIL';receipt['failure']=str(exc);raise
finally:
 receipt['sources_after']={str(p.relative_to(ROOT)):digest(p) for p in paths}
 (OUT/'interaction.json').write_text(json.dumps(receipt,indent=2)+'\n')
