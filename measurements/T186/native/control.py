"""Run one packaged native UI probe with isolated data and no bytecode writes."""
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--factor',required=True)
p.add_argument('--work',type=Path,required=True);p.add_argument('--hashes',type=Path,required=True);a=p.parse_args()
a.work.mkdir(parents=True,exist_ok=True)
base=Path(__file__).resolve().parent
system=os.environ.get('SYSTEMROOT',r'C:\Windows')
kept={'SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','TEMP','TMP','USERPROFILE','HOMEDRIVE','HOMEPATH','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','OS','SYSTEMDRIVE','PROGRAMDATA','PUBLIC','USERNAME','COMPUTERNAME'}
env={k:v for k,v in os.environ.items() if k.upper() in kept}
env.update(PATH=str(Path(system)/'System32')+os.pathsep+str(Path(system)/'System32'/'Wbem'),PYTHONUTF8='1',
 PYTHONSAFEPATH='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM='windows',QT_SCALE_FACTOR=a.factor,
 GOAL2_ENGINE_PYTHON=str(a.root/'pypy'/'pypy.exe'),APPDATA=str(a.work/'appdata'),LOCALAPPDATA=str(a.work/'localappdata'))
for n in ('appdata','localappdata'): (a.work/n).mkdir(exist_ok=True)
command=[str(a.root/'python'/'python.exe'),'-B',str(base/'probe.py'),'--root',str(a.root),'--cache',str(base/'cache'),
 '--out',str(a.work/'evidence'),'--hashes',str(a.hashes)]
r=subprocess.run(command,cwd=a.work,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',
 timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
(a.work/'stdout.log').write_text(r.stdout,encoding='utf-8');(a.work/'stderr.log').write_text(r.stderr,encoding='utf-8')
print(json.dumps({'exit':r.returncode,'work':str(a.work),'stdout':r.stdout[-1500:],'stderr':r.stderr[-500:]}))
raise SystemExit(r.returncode)
