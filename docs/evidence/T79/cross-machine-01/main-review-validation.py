"""[designed: T79] Main-prepared independent serial gates; no sibling source reads."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path.cwd();OUT=ROOT/'.cache/independent-review';STATUS=OUT/'status.json'
p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True)
for name in ('start','status','run','display'):group.add_argument('--'+name,action='store_true')
p.add_argument('--command',nargs=argparse.REMAINDER);args=p.parse_args()
def write(value):
 temporary=OUT/'status.new';temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(STATUS)
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def sources():
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for top in ('goal2','tools/desktop-ui')for p in (ROOT/top).rglob('*')if p.is_file()and '__pycache__'not in p.parts}
def clean(head):
 assert git('rev-parse','HEAD')==head,'review HEAD changed'
 assert not git('status','--porcelain','--untracked-files=no'),'tracked tree changed'
if args.status:
 print(STATUS.read_text()if STATUS.exists()else'not started');sys.exit(0)
config=json.loads((ROOT/'.cache/main-review-config.json').read_text());head=config['head'];assert config['task']=='T79';clean(head)
if args.start:
 assert not OUT.exists(),'output exists; inspect --status, never overwrite'
 OUT.mkdir();(OUT/'tmp').mkdir();(OUT/'runtime').mkdir(mode=0o700)
 unit='goal2-t79-review-'+str(time.time_ns())
 write({'head':head,'task':'T79','phase':'starting','unit':unit})
 command=['systemd-run','--user','--unit='+unit,'--collect','-p','WorkingDirectory='+str(ROOT),'-p','StandardInput=null','-p','StandardOutput=file:'+str(OUT/'driver.log'),'-p','StandardError=file:'+str(OUT/'driver.log')]
 env={'HARNESS_CLIENT':'codex','PATH':os.environ['PATH'],'TMPDIR':str(OUT/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','QT_QPA_PLATFORM':'xcb','LD_LIBRARY_PATH':str(ROOT/'.cache/xcb-libs/extracted/usr/lib/x86_64-linux-gnu'),'XDG_RUNTIME_DIR':str(OUT/'runtime')}
 for k,v in env.items():command+=['-E',k+'='+v]
 command += [sys.executable,'-B',str(Path(__file__).resolve()),'--run']
 subprocess.run(command,cwd=ROOT,check=True);print(json.dumps({'head':head,'unit':unit,'status':str(STATUS)}));sys.exit(0)
if args.display:
 assert os.environ.get('DISPLAY','').startswith(':') and os.environ.get('QT_QPA_PLATFORM')=='xcb'
 display=OUT/'display';display.mkdir(exist_ok=False)
 env={**os.environ,'XDG_CONFIG_HOME':str(display/'config'),'XDG_CACHE_HOME':str(display/'cache')}
 with (display/'xfwm.log').open('xb')as stream:
  wm=subprocess.Popen(['xfwm4','--compositor=off','--sm-client-disable'],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
  receipt={'display':os.environ['DISPLAY'],'owned_window_manager_pid':wm.pid}
  try:
   deadline=time.monotonic()+10
   while True:
    assert wm.poll()is None,'owned WM exited before readiness'
    result=subprocess.run(['xprop','-root','_NET_SUPPORTING_WM_CHECK'],env=env,capture_output=True,text=True)
    if result.returncode==0 and 'window id #'in result.stdout:break
    assert time.monotonic()<deadline,'owned WM readiness timeout';time.sleep(.05)
   command=args.command[1:]if args.command[:1]==['--']else args.command;assert command
   receipt['command']=command;result=subprocess.run(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL);receipt['exit']=result.returncode
   sys.exit(result.returncode)
  finally:
   wm.terminate()
   try:wm.wait(timeout=5)
   except subprocess.TimeoutExpired:wm.kill();wm.wait(timeout=5)
   receipt['owned_window_manager_exit']=wm.returncode;(display/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert args.run and OUT.is_dir();initial=sources();state=json.loads(STATUS.read_text());state.update(phase='running',pid=os.getpid(),rows=[]);write(state)
# [designed] One owned display encloses both drivers sequentially; mutations never overlap another gate.
inside=OUT/'serial.py';inside.write_text('import subprocess,sys\nfrom pathlib import Path\nroot=Path.cwd()\nfor name,script in [("full","validation_driver.py"),("retained","retained_validation_driver.py")]:\n subprocess.run([sys.executable,"-B",str(root/"docs/evidence/T79"/script),"--output",str(root/".cache/independent-review"/name)],cwd=root,check=True)\n')
proof_config=json.loads((ROOT/'.cache/main-native-proof-config.json').read_text());anchor=proof_config['expected_receipt_sha256'];py=[sys.executable,'-B']
commands=[('native-evidence',py+['.cache/main-native-proof-check.py','--config','.cache/main-native-proof-config.json','--expected-receipt-sha256',anchor]),('serial-full-and-retained',['env','-u','WAYLAND_DISPLAY','-u','QT_SCALE_FACTOR','dbus-run-session','--','xvfb-run','-a','-s','-screen 0 2880x1800x24',*py,str(Path(__file__).resolve()),'--display','--command','--',*py,str(inside)])]
started=time.monotonic()
try:
 for name,command in commands:
  clean(head);assert sources()==initial,'source bytes changed before gate';state['current']=name;write(state);log=OUT/(name+'.log');t=time.monotonic()
  with log.open('xb')as stream:run=subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=5400)
  same=sources()==initial;row={'name':name,'command':command,'exit':run.returncode,'seconds':round(time.monotonic()-t,3),'source_bytes_unchanged':same,'log':str(log.relative_to(ROOT)),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()};state['rows'].append(row);write(state)
  assert run.returncode==0 and same,row;clean(head)
 state.update(phase='complete',passed=True,seconds=round(time.monotonic()-started,3));write(state);print(json.dumps(state))
except BaseException as exc:
 state.update(phase='failed',passed=False,error=str(exc),seconds=round(time.monotonic()-started,3));write(state);raise
