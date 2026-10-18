"""[designed: #236] Main-only actual fixed-source immutable Windows acceptance."""
from pathlib import Path
import argparse,hashlib,io,json,subprocess,tarfile,time
p=argparse.ArgumentParser();p.add_argument('--head',required=True);p.add_argument('--attempt',required=True);a=p.parse_args()
ROOT=Path('/home/diego/projects/goal2');KEEP=ROOT/'.cache/kept/review-receipts';WT=Path('/home/diego/projects/goal2-work/fix236-windows-viewer-sharing');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(p.relative_to('/mnt/c')).replace('/','\\')
assert len(a.head)==40 and subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head
assert subprocess.check_output(['git','rev-parse','origin/fix/236-windows-viewer-sharing'],cwd=WT,text=True).strip()==a.head
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
out=KEEP/('fix236-windows-'+a.attempt+'-'+str(time.time_ns()));out.mkdir(exist_ok=False)
folder=WIN/'.goal2-validation'/('fix236-'+a.head[:12]+'-'+str(time.time_ns()));folder.mkdir(parents=True,exist_ok=False)
protected={str(p):sha(p)for p in (WIN/'.cache').rglob('*')if p.is_file()and p.suffix.lower()in('.sav','.g2save','.dat')};protected[str(WIN/'Start-goal2.cmd')]=sha(WIN/'Start-goal2.cmd')
r={'claim':'Actual fixed product source; original acceptance switched to frames=True only; observational capture wrappers, NO sharing mocks','head':a.head,'attempt':a.attempt,'directory':str(folder),'result':'INCOMPLETE','protected_before':protected,'runs':[]}
try:
 raw=subprocess.check_output(['git','archive',a.head,'goal2','tools/desktop-ui'],cwd=WT)
 with tarfile.open(fileobj=io.BytesIO(raw))as tar:
  for m in tar.getmembers():
   assert not m.issym()and not m.islnk();dest=folder/m.name;assert dest.resolve().is_relative_to(folder.resolve())
   if m.isdir():dest.mkdir(parents=True,exist_ok=True)
   elif m.isfile():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
 r['sources']={p.relative_to(folder).as_posix():sha(p)for p in folder.rglob('*')if p.is_file()}
 cache=folder/'.cache';cache.mkdir();(cache/'tmp').mkdir();r['resources']={}
 for name in('e010-r0008-halftime.sav','GOAL.DAT','e0afff6751747233-e006-1000-r0001.sav'):
  dest=cache/name;dest.write_bytes((WT/'.cache'/name).read_bytes());r['resources'][name]=sha(dest)
 paths=[windows(folder)];r['dependencies']={}
 for task in('T78','T79'):
  dep=json.loads((KEEP/(task+'-private-runtime-config.json')).read_text());dest=cache/('python-libs-'+task);dest.mkdir();paths.append(windows(dest));r['dependencies'][task]=dep
  for name,h in dep['files'].items():
   source=Path(dep['directory'])/name;assert sha(source)==h;target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());assert sha(target)==h
 for source,name in(('fix236-native-parent-observer.py','parent-observer.py'),('fix236-native-viewer-observer.py','viewer-observer.py')):(folder/name).write_bytes((KEEP/source).read_bytes())
 r['observers']={name:sha(folder/name)for name in('parent-observer.py','viewer-observer.py')}
 for scale in('1','2'):
  observations=folder/'observations'/('scale-'+scale);wrapper=folder/('native-'+scale+'.py');code='import os,sys,runpy\n'
  env={'PYTHONPATH':';'.join(paths),'QT_QPA_PLATFORM':'windows','QT_SCALE_FACTOR':scale,'QT_AUTO_SCREEN_SCALE_FACTOR':'0','SDL_VIDEODRIVER':'windows','SDL_AUDIODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','PYTHONDONTWRITEBYTECODE':'1','GOAL2_NATIVE_OBSERVATIONS':windows(observations),'TMPDIR':windows(cache/'tmp'),'TMP':windows(cache/'tmp'),'TEMP':windows(cache/'tmp')}
  for key,value in env.items():code+='os.environ['+repr(key)+']='+repr(value)+'\n'
  code+='sys.path[:0]='+repr(paths)+'\nimport pygame,unicorn\nassert sys.platform=="win32" and pygame.version.ver=="2.5.8" and unicorn.__version__=="2.1.4"\n'
  code+='runpy.run_path('+repr(windows(folder/'parent-observer.py'))+',run_name="__main__")\n';wrapper.write_text(code)
  log=out/('native-'+scale+'.log');start=time.monotonic()
  with log.open('xb')as stream:run=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
  row={'scale':scale,'exit':run.returncode,'seconds':round(time.monotonic()-start,3),'log_sha256':sha(log),'wrapper_sha256':sha(wrapper)};r['runs'].append(row);text=log.read_text(errors='replace');assert run.returncode==0 and 'Traceback (most recent call last)'not in text and 'Error calling Python override'not in text,text[-6000:]
  report=observations/'report.json';value=json.loads(report.read_text());assert value['result']=='PASS'and value['qpa']=='windows'and value['actual_qt_ratio']==int(scale)and value['requested_qt_scale']==scale and value['callbacks']==[]and value['clean_widgets']and value['owned_resources_closed'];assert len(value['frames'])==2 and all(x['frames']>=1000 and x['final_ack']==x['frames']-1 for x in value['frames']);assert len(value['qt_captures'])==2
  assert all(x['driver']=='windows'and all(v>0 for v in x['surface'])and x['dpi']>0 for x in value['sdl']);row.update(report=report.relative_to(folder).as_posix(),report_sha256=sha(report),frames=value['frames'],deterministic_tests=value['deterministic_tests'])
 for name,h in r['sources'].items():assert sha(folder/name)==h
 for name,h in r['resources'].items():assert sha(cache/name)==h
 for task,dep in r['dependencies'].items():assert all(sha(cache/('python-libs-'+task)/name)==h for name,h in dep['files'].items())
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head;subprocess.run(['git','diff','--quiet','HEAD','--','goal2','tools'],cwd=WT,check=True)
 r['result']='PASS'
finally:
 r['protected_after']={p:sha(Path(p))for p in protected};r['protected_unchanged']=r['protected_after']==protected;r['artifacts']={p.relative_to(folder).as_posix():sha(p)for p in(folder/'observations').rglob('*')if p.is_file()};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');assert r['protected_unchanged'],'protected launcher/save changed'
print(json.dumps({'result':r['result'],'receipt':str(out/'receipt.json'),'runs':r['runs'],'source_files':len(r['sources']),'protected':len(protected)}))
