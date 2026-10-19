"""[designed: #254] Main-only native resource-free regression launch and guards."""
from pathlib import Path
import argparse,hashlib,io,json,os,subprocess,tarfile,time,traceback
p=argparse.ArgumentParser();p.add_argument('--head',required=True);p.add_argument('--probe',required=True);p.add_argument('--attempt',required=True);p.add_argument('--mutation',choices=['omit-delete-share','legacy-writer','bypass-reader','replacefile-writer'],required=True);a=p.parse_args()
ROOT=Path('/home/diego/projects/goal2');WT=Path('/home/diego/projects/goal2-work/fix254-native-status-sharing');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe');KEEP=ROOT/'.cache/kept/review-receipts/fix254-it13-20261019'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(Path(p).relative_to('/mnt/c')).replace('/','\\')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
out=KEEP/('native-'+a.attempt+'-'+str(time.time_ns()));out.mkdir(exist_ok=False)
folder=WIN/'.goal2-validation'/('fix254-'+a.attempt+'-'+str(time.time_ns()));folder.mkdir(exist_ok=False)
protected=[WIN/'Start-goal2.cmd',WIN/'Start-goal2-modern.cmd']
for base in(WIN/'.cache',WIN/'.goal2-modern-saves',WIN/'.goal2-releases/accepted-5c266169/.cache'):
 if base.is_dir():protected.extend(q for q in base.rglob('*')if q.is_file()and q.suffix.lower()in('.sav','.g2save','.dat'))
before={str(q):sha(q)for q in protected};r={'claim':'[designed: #254] Actual native controlled mutation of immutable private copy; not match/UI acceptance','head':a.head,'attempt':a.attempt,'directory':str(folder),'protected_before':before,'result':'INCOMPLETE'}
try:
 raw=subprocess.check_output(['git','archive',a.head,'goal2','tools/desktop-ui'],cwd=WT)
 with tarfile.open(fileobj=io.BytesIO(raw))as tar:
  for m in tar.getmembers():
   assert not m.issym()and not m.islnk();target=folder/m.name;assert target.resolve().is_relative_to(folder.resolve())
   if m.isdir():target.mkdir(parents=True,exist_ok=True)
   elif m.isfile():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
 r['original_sources']={q.relative_to(folder).as_posix():sha(q)for q in folder.rglob('*')if q.is_file()}
 mutations={'omit-delete-share':('goal2/desktop/watched.py','share_mode = 0x1 | 0x2 | 0x4','share_mode = 0x1 | 0x2'), 'legacy-writer':('goal2/desktop/pygame_viewer.py','            _replace_status(temporary, path)','            os.replace(temporary, path)'), 'bypass-reader':('goal2/desktop/watched.py',"with _open_status(path) as stream:","with path.open('rb') as stream:")}
 if a.mutation=='replacefile-writer':
  name='goal2/desktop/pygame_viewer.py';file=folder/name;old=file.read_text();new=subprocess.check_output(['git','show','25096176d11f18fb0b96a32bcbb558de96246cbe:'+name],cwd=WT,text=True);file.write_text(new)
 else:
  name,old,new=mutations[a.mutation];file=folder/name;text=file.read_text();assert text.count(old)==1;file.write_text(text.replace(old,new))
 r['mutation']={'name':a.mutation,'file':name,'old':old,'new':new,'before_sha256':r['original_sources'][name],'after_sha256':sha(file)}
 r['runner_sha256']=sha(__file__)
 r['sources']={q.relative_to(folder).as_posix():sha(q)for q in folder.rglob('*')if q.is_file()}
 probe=folder/'tools/desktop-ui/native-status-sharing.py';raw=Path(a.probe).read_bytes()
 if probe.exists():assert probe.read_bytes()==raw
 else:probe.write_bytes(raw)
 r['probe_sha256']=sha(probe);tmp=folder/'.cache/tmp';tmp.mkdir(parents=True);paths=[windows(folder)]
 for task in('T78','T79'):
  dep=json.loads((ROOT/'.cache/kept/review-receipts'/(task+'-private-runtime-config.json')).read_text());paths.append(windows(dep['directory']))
 wrapper=folder/'run-probe.py';env={'PYTHONPATH':';'.join(paths),'TMPDIR':windows(tmp),'TMP':windows(tmp),'TEMP':windows(tmp),'PYTHONDONTWRITEBYTECODE':'1'}
 code='import os,sys,runpy\n'
 for k,v in env.items():code+='os.environ['+repr(k)+']='+repr(v)+'\n'
 code+='sys.path[:0]='+repr(paths)+'\nassert sys.platform=="win32"\nsys.argv='+repr([windows(probe),'--evidence-dir',windows(folder/'observations')])+'\nrunpy.run_path('+repr(windows(probe))+',run_name="__main__")\n'
 compile(code,'native-probe-wrapper','exec');wrapper.write_text(code);log=out/'native.log';start=time.monotonic()
 with log.open('xb')as stream:run=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
 r.update(exit=run.returncode,seconds=time.monotonic()-start,wrapper_sha256=sha(wrapper),log_sha256=sha(log))
 r['report_sha256']=sha(folder/'observations/report.json');r['probe_result']=json.loads((folder/'observations/report.json').read_text())['result']
 for n,h in r['sources'].items():assert sha(folder/n)==h
 for n,h in r['original_sources'].items():assert sha(WT/n)==h
 assert sha(probe)==sha(a.probe)==r['probe_sha256'];r['result']='EXECUTED'
except BaseException:r['failure']=traceback.format_exc();raise
finally:
 r['protected_after']={n:sha(n)for n in before};r['protected_unchanged']=r['protected_after']==before;(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');assert r['protected_unchanged']
print(json.dumps({'receipt':str(out/'receipt.json'),'result':r['result'],'probe_result':r.get('probe_result'),'exit':r.get('exit'),'protected':len(before)}))
