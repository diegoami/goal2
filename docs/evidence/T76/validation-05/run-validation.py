from pathlib import Path
import subprocess,os,json,time,hashlib,sys
root=Path.cwd();out=root/'docs/evidence/T76/validation-05';out.mkdir(exist_ok=False);(root/'.cache/tmp').mkdir(exist_ok=True)
py=[sys.executable,'-B'];resources=['--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT'];rows=[]
commands=[('results',py+['tools/desktop-ui/redesign.py','--scenario','results']+resources+['--evidence-dir',str(out/'results')]),('results-negative',py+['tools/desktop-ui/redesign.py','--scenario','results']+resources+['--evidence-dir',str(out/'results-negative'),'--negative-controls']),('competitive',py+['tools/desktop-ui/competitive.py']),('units',py+['-m','unittest','goal2.tests.test_desktop_quick_jobs','goal2.tests.test_campaign_substitutions','goal2.tests.test_desktop_model','goal2.tests.test_desktop_pool','-v'])]
for name in ('management','friendlies','pool','halftime'):commands.append(('prove-'+name,py+['tools/desktop-ui/prove-'+name+'.py']))
for name in ('management','campaign-pool','campaign-halftime'):commands.append((name,py+['tools/desktop-ui/acceptance.py','--scenario',name]+resources))
commands.append(('country-selection',py+['tools/desktop-ui/country-selection.py']+resources))
commands.append(('tactics-labels',py+['tools/desktop-ui/tactics-labels.py']+resources))
for scenario in ('overview','shell'):
 commands.append((scenario,py+['tools/desktop-ui/redesign.py','--scenario',scenario]+resources+['--evidence-dir',str(out/scenario)]))
 commands.append((scenario+'-negative',py+['tools/desktop-ui/redesign.py','--scenario',scenario]+resources+['--evidence-dir',str(out/(scenario+'-negative')),'--negative-controls']))
commands.append(('squad-negative',py+['tools/desktop-ui/redesign.py','--scenario','squad']+resources+['--evidence-dir',str(out/'squad-negative'),'--negative-controls']))
commands.append(('squad-offscreen',py+['tools/desktop-ui/redesign.py','--scenario','squad']+resources+['--evidence-dir',str(out/'squad-offscreen')]))
commands.append(('squad-native',['xvfb-run','-a','-s','-screen 0 3840x2160x24','env','QT_QPA_PLATFORM=xcb','LD_LIBRARY_PATH='+str(root/'.cache/xcb-libs/extracted/usr/lib/x86_64-linux-gnu')]+py+['tools/desktop-ui/redesign.py','--scenario','squad']+resources+['--evidence-dir',str(out/'squad-native')]))
print('Owned validation PID',os.getpid(),flush=True)
for name,cmd in commands:
 log=out/(name+'.log');t=time.monotonic()
 with log.open('x') as f:r=subprocess.run(cmd,cwd=root,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(root/'.cache/tmp')},stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
 row={'name':name,'command':cmd,'exit':r.returncode,'seconds':round(time.monotonic()-t,3),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()};rows.append(row);(out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
 if r.returncode:raise SystemExit(name+' failed; see '+str(log))
