"""[designed: T79] Own a window manager on an already-isolated Xvfb display."""
from pathlib import Path
import argparse,os,subprocess,time,sys,json
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();cmd=a.command[1:]if a.command[:1]==['--']else a.command;assert cmd
out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
assert os.environ.get('DISPLAY','').startswith(':'),'launch this helper inside a private xvfb-run server'
env={**os.environ,'XDG_CONFIG_HOME':str(out/'config'),'XDG_CACHE_HOME':str(out/'cache')}
with (out/'xfwm.log').open('xb')as stream:
 wm=subprocess.Popen(['xfwm4','--compositor=off','--sm-client-disable'],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
 receipt={'display':os.environ['DISPLAY'],'owned_window_manager_pid':wm.pid,'command':cmd,'exit':None}
 try:
  deadline=time.monotonic()+10
  while True:
   assert wm.poll()is None,'owned window manager exited before readiness'
   r=subprocess.run(['xprop','-root','_NET_SUPPORTING_WM_CHECK'],env=env,capture_output=True,text=True)
   if r.returncode==0 and 'window id #'in r.stdout:break
   assert time.monotonic()<deadline,'owned window manager did not become ready'
   time.sleep(.05)
  print('Owned private display/window manager ready:',os.environ['DISPLAY'],wm.pid,flush=True)
  r=subprocess.run(cmd,env=env,stdin=subprocess.DEVNULL);receipt['exit']=r.returncode
  sys.exit(r.returncode)
 finally:
  wm.terminate()
  try:wm.wait(timeout=5)
  except subprocess.TimeoutExpired:wm.kill();wm.wait(timeout=5)
  receipt['owned_window_manager_exit']=wm.returncode;(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
