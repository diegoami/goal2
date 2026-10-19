"""[designed: #254] Reviewer-owned serial checks with separately owned Linux display and anchored native audit."""
import argparse,hashlib,json,os,re,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'.cache/independent-review';PY=[os.environ.get('GOAL2_VALIDATION_PYTHON','/home/diego/projects/goal2/.cache/validation-tools/venv/bin/python'),'-B']
def clean(head):
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
 assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
def execute(head,anchor):
 clean(head);OUT.mkdir(exist_ok=False);report={'head':head,'phase':'starting','rows':[],'native_receipt_sha256':anchor}
 def status():
  tmp=OUT/'status.new';tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(OUT/'status.json')
 env={**os.environ,'HARNESS_CLIENT':'codex','PATH':os.environ.get('GOAL2_NODE_BIN','/home/diego/.nvm/versions/node/v24.21.0/bin')+':'+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'}
 commands=[('ownership-controls',PY+['.cache/main-ownership-controls.py']),('native-proof',PY+['.cache/main-native-proof-check.py','--config','.cache/main-native-proof-config.json','--expected-receipt-sha256',anchor]),('native-proof-controls',PY+['.cache/main-native-proof-controls.py','--config','.cache/main-native-proof-config.json','--expected-receipt-sha256',anchor,'--checker','.cache/main-native-proof-check.py','--output','.cache/review-native-proof-controls']),('linux-integration',PY+['.cache/main-linux-validation.py'])]
 try:
  for name,command in commands:
   report.update(phase='running',current=name);status();log=OUT/(name+'.log');began=time.monotonic()
   with log.open('xb')as stream:run=subprocess.run(command,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=3000)
   report['rows'].append({'name':name,'command':command,'exit':run.returncode,'seconds':time.monotonic()-began,'log':log.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()});status()
   assert run.returncode==0,(name,log.read_text(errors='replace')[-4000:]);clean(head)
  linux=json.loads((ROOT/'.cache/fix254-linux-driver01/status.json').read_text());assert linux['result']=='PASS'and linux['phase']=='complete'and linux['owned_display_cleanup']and len(linux['rows'])==11
  report.update(phase='complete',passed=True,owned_display_cleanup=True,linux_groups=len(linux['rows']))
 except BaseException:
  report.update(phase='failed',passed=False,failure=traceback.format_exc());raise
 finally:status()
 print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--start',action='store_true');g.add_argument('--run',action='store_true');g.add_argument('--status',action='store_true');p.add_argument('--expected-receipt-sha256');a=p.parse_args();config=json.loads((ROOT/'.cache/main-review-config.json').read_text());assert config['task']=='fix254';head=config['head']
 if a.status:
  try:value=json.loads((OUT/'status.json').read_text())
  except FileNotFoundError:value={'phase':'starting'}
  marker=ROOT/'.cache/main-review-start.json'
  if marker.exists():
   unit=json.loads(marker.read_text())['unit'];value['service']=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','SubState','-p','ExecMainStatus'],capture_output=True,text=True).stdout.strip()
  print(json.dumps(value,indent=2))
 else:
  assert a.expected_receipt_sha256 and re.fullmatch('[0-9a-f]{64}',a.expected_receipt_sha256),'independent main receipt anchor required'
  if a.start:
   clean(head);assert not OUT.exists();unit='goal2r-fix254-review-'+head[:8]+'-'+str(time.time_ns());log=ROOT/'.cache/main-review-driver.log';assert not log.exists()
   subprocess.run(['systemd-run','--user','--unit='+unit,'--collect','-E','HARNESS_CLIENT=codex','-E','PATH='+os.environ['PATH'],'-E','GOAL2_VALIDATION_PYTHON='+PY[0],'-p','WorkingDirectory='+str(ROOT),'-p','StandardInput=null','-p','StandardOutput=file:'+str(log),'-p','StandardError=file:'+str(log),*PY,str(Path(__file__).resolve()),'--run','--expected-receipt-sha256',a.expected_receipt_sha256],check=True,stdin=subprocess.DEVNULL)
   (ROOT/'.cache/main-review-start.json').write_text(json.dumps({'unit':unit+'.service','head':head,'log':log.relative_to(ROOT).as_posix()})+'\n');print('started owned serial review validation',unit)
  else:execute(head,a.expected_receipt_sha256)
