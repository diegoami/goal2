import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
out=ROOT/'docs/evidence/T77/linux-retained-04';out.mkdir(exist_ok=False)
py=sys.executable
base=[py,'-B','tools/desktop-ui/redesign.py'];assets=['--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
cases=[
 ('pool-final',base+['--scenario','pool',*assets,'--evidence-dir',str(out/'pool-final')]),
 ('pool-controls-final',base+['--scenario','pool',*assets,'--negative-controls','--evidence-dir',str(out/'pool-controls-final')]),
 ('overview-controls-paired',base+['--scenario','overview',*assets,'--negative-controls','--evidence-dir',str(out/'overview-controls-paired')]),
 ('competitive-labels',[py,'-B','tools/desktop-ui/competitive.py']),
 ('competitive-play',[py,'-B','tools/desktop-ui/competitive_play.py'])]
# [designed: T77] All mutations are serial; hash the complete Python source inventory before/after each child.
paths=sorted((ROOT/'goal2').rglob('*.py'))+sorted((ROOT/'tools/desktop-ui').glob('*.py'))
def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
receipt={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'cases':[]}
def write(): (out/'progress.json').write_text(json.dumps(receipt,indent=2)+'\n')
for name,command in cases:
 generated_before=set((ROOT/'docs/evidence/T80').glob('competitive-play-*.json'))
 before=hashes();started=time.time();print('START',name,flush=True)
 with (out/(name+'.log')).open('w') as log:
  try:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=600);code=result.returncode
  except BaseException as e:log.write(repr(e));code=-1
 for generated in set((ROOT/'docs/evidence/T80').glob('competitive-play-*.json'))-generated_before:generated.rename(out/generated.name)
 after=hashes();row={'name':name,'command':command,'returncode':code,'seconds':round(time.time()-started,2),'sources_before':before,'sources_after':after,'restored':before==after};receipt['cases'].append(row);write();print('END',name,code,'restored',before==after,flush=True)
 if code or before!=after:sys.exit(1)
receipt['result']='PASS';write();print('PASS retained batch',flush=True)
