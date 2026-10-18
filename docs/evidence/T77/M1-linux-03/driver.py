from pathlib import Path
import subprocess,sys,json,os,hashlib,time
root=Path.cwd();out=root/'docs/evidence/T77/M1-linux-03';py=sys.executable
assets=['--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
commands=[('positive',[py,'-B','tools/desktop-ui/redesign.py','--scenario','pool',*assets,'--evidence-dir',str(out/'positive')]),('controls',[py,'-B','tools/desktop-ui/redesign.py','--scenario','pool',*assets,'--negative-controls','--evidence-dir',str(out/'controls')]),('retained-pool',[py,'-B','tools/desktop-ui/acceptance.py','--scenario','campaign-pool',*assets]),('prove-pool',[py,'-B','tools/desktop-ui/prove-pool.py'])]
paths=sorted((root/'goal2').rglob('*.py'))+sorted((root/'tools/desktop-ui').glob('*.py'))
def hashes():return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
r={'cases':[]}
for name,cmd in commands:
 before=hashes();start=time.monotonic();print('START',name,flush=True)
 with (out/(name+'.log')).open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=240,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 after=hashes();r['cases'].append({'name':name,'command':cmd,'returncode':result.returncode,'seconds':time.monotonic()-start,'before':before,'after':after,'restored':before==after});(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('END',name,result.returncode,'restored',before==after,flush=True)
 assert result.returncode==0 and before==after,'validation or exact source restoration failed'
