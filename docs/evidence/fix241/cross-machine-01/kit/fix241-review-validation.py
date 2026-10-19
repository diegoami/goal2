"""[designed: #241] Reviewer-owned serial replay, private native X11 and anchored Windows audit."""
import argparse,hashlib,json,os,select,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'.cache/independent-review';PY=[os.environ.get('GOAL2_VALIDATION_PYTHON','/home/diego/projects/goal2/.cache/validation-venv/bin/python3'),'-B']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(head):
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==head
 assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip()
def run_all(head,anchor):
 clean(head);OUT.mkdir(exist_ok=False);rows=[];owned=[];streams=[];report={'head':head,'phase':'starting','rows':rows}
 def status(): (OUT/'status.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(name,cmd,env,timeout=1200):
  report.update(phase='running',current=name);status();start=time.monotonic();log=OUT/(name+'.log')
  with log.open('xb')as stream:r=subprocess.run(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
  rows.append({'name':name,'command':cmd,'exit':r.returncode,'seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(ROOT)),'sha256':sha(log)});status()
  assert r.returncode==0,(name,log.read_text(errors='replace')[-4000:]);clean(head)
 try:
  dirs={name:OUT/name for name in ('tmp','config','cache','runtime')}
  for path in dirs.values():path.mkdir()
  dirs['runtime'].chmod(0o700)
  env={**os.environ,'HARNESS_CLIENT':'codex','PATH':os.environ.get('GOAL2_NODE_BIN','/home/diego/.nvm/versions/node/v24.21.0/bin')+':'+os.environ['PATH'],'QT_QPA_PLATFORM':'xcb','SDL_VIDEODRIVER':'dummy','SDL_AUDIODRIVER':'dummy','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(dirs['tmp']),'XDG_CONFIG_HOME':str(dirs['config']),'XDG_CACHE_HOME':str(dirs['cache']),'XDG_RUNTIME_DIR':str(dirs['runtime']),'LD_LIBRARY_PATH':str(ROOT/'.cache/xcb-libs/extracted/usr/lib/x86_64-linux-gnu')}
  err=(OUT/'xvfb.log').open('xb');streams.append(err)
  xvfb=subprocess.Popen(['/usr/bin/Xvfb','-displayfd','1','-screen','0','2880x1800x24','-nolisten','tcp'],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=err);owned.append(xvfb)
  assert select.select([xvfb.stdout],[],[],15)[0],'owned Xvfb did not report display'
  display=xvfb.stdout.readline().decode().strip();assert display.isdigit()and xvfb.poll()is None;env['DISPLAY']=':'+display
  log=(OUT/'xfwm.log').open('xb');streams.append(log)
  wm=subprocess.Popen(['/usr/bin/xfwm4','--replace','--compositor=off'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT);owned.append(wm);time.sleep(.5);assert wm.poll()is None
  report.update(display=env['DISPLAY'],qpa='xcb',screen='2880x1800x24',native_receipt_sha256=anchor);status()
  run('native-proof',PY+['.cache/main-native-proof-check.py','--expected-receipt-sha256',anchor],env)
  run('serial-21-groups',PY+['docs/evidence/fix241/serial-02/review-driver.py.txt'],env,timeout=2400)
  receipt=json.loads((ROOT/'.cache/fix241-independent-suite/receipt.json').read_text());assert receipt['result']=='PASS'and receipt['source_restored']and len(receipt['cases'])==21
  assert all(row['returncode']==0 for row in receipt['cases'])
  negative=json.loads((ROOT/'.cache/fix241-independent-suite/browsing-negative/negative-controls.json').read_text());assert negative['restored']and len(negative['controls'])==3 and all(x['returncode']!=0 for x in negative['controls'])
  units=(ROOT/'.cache/fix241-independent-suite/focused-unit.log').read_text();assert 'Ran 18 tests' in units and '\nOK\n'in units and 'skipped'not in units.lower()
  for name,cmd in [('provenance',PY+['tools/check_provenance.py']),('links',PY+['tools/check_links.py']),('whitespace',['git','diff','--check']),('pr-whitespace',['git','diff','--check','origin/main...HEAD']),('premerge',PY+['tools/check_premerge.py','--expected-head',head])]:run(name,cmd,env)
  report.update(phase='complete',passed=True,seconds=round(sum(x['seconds']for x in rows),3));status()
 except BaseException:
  report.update(phase='failed',passed=False,failure=traceback.format_exc());status();raise
 finally:
  for process in reversed(owned):
   if process.poll()is None:
    process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
  for stream in streams:stream.close()
  report['owned_display_cleanup']=all(p.poll()is not None for p in owned);status()
 print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--start',action='store_true');g.add_argument('--status',action='store_true');g.add_argument('--run',action='store_true');p.add_argument('--expected-receipt-sha256');a=p.parse_args()
 config=json.loads((ROOT/'.cache/main-review-config.json').read_text());head=config['head'];assert config['task']=='fix241'
 if a.status:
  value=json.loads((OUT/'status.json').read_text())if(OUT/'status.json').exists()else{'phase':'starting'}
  marker=ROOT/'.cache/main-review-start.json'
  if marker.exists():
   unit=json.loads(marker.read_text())['unit'];check=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','SubState','-p','ExecMainStatus'],capture_output=True,text=True)
   value['owned_unit']=unit;value['service_state']=check.stdout.strip();value['service_query_exit']=check.returncode
  print(json.dumps(value,indent=2))
 else:
  import re
  assert a.expected_receipt_sha256 and re.fullmatch('[0-9a-f]{64}',a.expected_receipt_sha256),'main externally anchored native receipt hash required'
  if a.start:
   clean(head);assert not OUT.exists();unit='goal2r-fix241-review-'+head[:8]+'-'+str(time.time_ns());log=ROOT/'.cache/main-review-driver.log';assert not log.exists()
   command=['systemd-run','--user','--unit='+unit,'--collect','-E','HARNESS_CLIENT=codex','-E','PATH='+os.environ['PATH'],'-E','GOAL2_VALIDATION_PYTHON='+PY[0],'-E','GOAL2_NODE_BIN='+os.environ.get('GOAL2_NODE_BIN','/home/diego/.nvm/versions/node/v24.21.0/bin'),'-p','WorkingDirectory='+str(ROOT),'-p','StandardInput=null','-p','StandardOutput=file:'+str(log),'-p','StandardError=file:'+str(log),*PY,str(Path(__file__).resolve()),'--run','--expected-receipt-sha256',a.expected_receipt_sha256]
   subprocess.run(command,check=True,stdin=subprocess.DEVNULL);marker={'unit':unit+'.service','head':head,'log':str(log.relative_to(ROOT))};(ROOT/'.cache/main-review-start.json').write_text(json.dumps(marker,indent=2)+'\n');print(json.dumps(marker))
  else:run_all(head,a.expected_receipt_sha256)
