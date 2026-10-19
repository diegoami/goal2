"""[designed: #254] Evidence-only correction and exact-head completion after passing runtime groups."""
import argparse,hashlib,json,subprocess,sys,time,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--head',required=True);a=p.parse_args();root=Path.cwd();out=root/'.cache/fix254-final-linux02';out.mkdir(exist_ok=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==a.head and not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
prior=json.loads((root/'.cache/fix254-linux-driver01/status.json').read_text());assert prior['result']=='FAIL'and prior['owned_display_cleanup']and len(prior['rows'])==10 and all(x['exit']==0 for x in prior['rows'][:9])and prior['rows'][-1]['name']=='authored-whitespace'
assert all(sha(root/n)==h for n,h in prior['initial_sources'].items())
r={'claim':'[confirmed: unchanged Python sources] Complete final repository checks after evidence-only whitespace correction; earlier FAIL preserved','head':a.head,'runtime_head':prior['head'],'runtime_groups_passed':9,'python_sources_unchanged':len(prior['initial_sources']),'rows':[],'result':'INCOMPLETE'}
try:
 for name,command in [('authored-whitespace',['git','diff','--check','origin/main...HEAD']),('premerge',[sys.executable,'-B','tools/check_premerge.py','--expected-head',a.head])]:
  began=time.monotonic();log=out/(name+'.log')
  with log.open('xb')as stream:run=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
  r['rows'].append({'name':name,'command':command,'exit':run.returncode,'seconds':time.monotonic()-began,'log_sha256':sha(log)});assert run.returncode==0,(name,log.read_text(errors='replace')[-3000:])
 assert all(sha(root/n)==h for n,h in prior['initial_sources'].items());r['result']='PASS'
except BaseException:r['failure']=traceback.format_exc();raise
finally:(out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
