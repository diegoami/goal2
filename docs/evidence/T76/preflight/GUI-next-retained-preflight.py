"""[designed: T76/T78] Main retained acceptance before implementation, serial mutations."""
from pathlib import Path
import subprocess,os,json,time,hashlib
w=Path('/home/diego/projects/goal2-work/T76-football-ui');out=w/'.cache/main-preflight/retained-01';out.mkdir(exist_ok=False);(out/'tmp').mkdir();py=['/home/diego/projects/goal2/.cache/validation-venv/bin/python3','-B'];rows=[]
commands=[('units',py+['-m','unittest','goal2.tests.test_desktop_model','goal2.tests.test_desktop_pool','goal2.tests.test_desktop_quick_jobs','-v'])]
for n in ('management','friendlies','pool','halftime'):commands.append(('prove-'+n,py+['tools/desktop-ui/prove-'+n+'.py']))
for n in ('management','campaign-halftime'):commands.append((n,py+['tools/desktop-ui/acceptance.py','--scenario',n,'--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']))
for name,cmd in commands:
 subprocess.run(['git','diff','--quiet','HEAD'],cwd=w,check=True);log=out/(name+'.log');t=time.monotonic()
 with log.open('x')as f:r=subprocess.run(cmd,cwd=w,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(out/'tmp')},stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
 row={'name':name,'command':cmd,'exit':r.returncode,'seconds':round(time.monotonic()-t,3),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()};rows.append(row);(out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');assert r.returncode==0,log.read_text()[-2400:];subprocess.run(['git','diff','--quiet','HEAD'],cwd=w,check=True)
print(json.dumps(rows))
