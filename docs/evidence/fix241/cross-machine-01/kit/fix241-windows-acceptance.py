"""Main-only native frozen-source validation for existing #241."""
import argparse,hashlib,io,json,subprocess,tarfile,time,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--head',required=True);a=p.parse_args()
ROOT=Path('/home/diego/projects/goal2');WT=Path('/home/diego/projects/goal2-work/fix241-player-table-browsing');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe');KEEP=ROOT/'.cache/kept/review-receipts/resume-20261019'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def wp(p):return 'C:'+chr(92)+str(Path(p).relative_to('/mnt/c')).replace('/',chr(92))
def git(*args):return subprocess.check_output(['git',*args],cwd=WT,text=True).strip()
assert len(a.head)==40 and git('rev-parse','HEAD')==git('rev-parse','origin/fix/241-player-table-browsing')==a.head
assert not git('status','--porcelain','--untracked-files=no')
stamp=str(time.time_ns());out=KEEP/('fix241-native-'+stamp);out.mkdir()
folder=WIN/'.goal2-validation'/('fix241-production-'+a.head[:12]+'-'+stamp);folder.mkdir(parents=True)
protected={str(p):sha(p) for p in WIN.rglob('*') if p.is_file() and (p.suffix.lower() in ('.sav','.g2save','.dat') or p.name in ('Start-goal2.cmd','Start-goal2-modern.cmd'))}
r={'head':a.head,'claim':'Actual committed source and native Windows Qt; no product/widget mocks','directory':str(folder),'result':'INCOMPLETE','protected_before':protected,'runs':[]}
try:
 raw=subprocess.check_output(['git','archive',a.head,'goal2','tools/desktop-ui'],cwd=WT)
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
  for m in tar.getmembers():
   assert not m.issym() and not m.islnk();dest=folder/m.name;assert dest.resolve().is_relative_to(folder.resolve())
   if m.isdir():dest.mkdir(parents=True,exist_ok=True)
   elif m.isfile():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
 r['sources']={p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
 cache=folder/'.cache';cache.mkdir();(cache/'tmp').mkdir();r['resources']={}
 for name in ('e010-r0008-halftime.sav','GOAL.DAT'):
  dest=cache/name;dest.write_bytes((WT/'.cache'/name).read_bytes());r['resources'][name]=sha(dest)
 paths=[wp(folder)];r['dependencies']={}
 for task in ('T78','T79'):
  dep=json.loads((ROOT/'.cache/kept/review-receipts'/(task+'-private-runtime-config.json')).read_text());dest=cache/('python-libs-'+task);dest.mkdir();paths.append(wp(dest));r['dependencies'][task]=dep
  for name,h in dep['files'].items():
   source=Path(dep['directory'])/name;assert sha(source)==h;target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());assert sha(target)==h
 for scale in ('1','2'):
  obs=folder/'observations'/('scale-'+scale);wrapper=folder/('native-'+scale+'.py')
  env={'PYTHONPATH':';'.join(paths),'QT_QPA_PLATFORM':'windows','QT_SCALE_FACTOR':scale,'QT_AUTO_SCREEN_SCALE_FACTOR':'0','SDL_VIDEODRIVER':'windows','SDL_AUDIODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':wp(cache/'tmp'),'TMP':wp(cache/'tmp'),'TEMP':wp(cache/'tmp')}
  args=[wp(folder/'tools/desktop-ui/player-browsing.py'),'--source-head',a.head,'--template',wp(cache/'e010-r0008-halftime.sav'),'--data',wp(cache/'GOAL.DAT'),'--evidence-dir',wp(obs)]
  code='import os,sys,runpy\n'
  for k,v in env.items():code+='os.environ['+repr(k)+']='+repr(v)+'\n'
  code+='sys.path[:0]='+repr([wp(folder/'tools/desktop-ui'),*paths])+'\nassert sys.platform=="win32"\nfrom PySide6.QtCore import QCoreApplication,QEvent\nfrom PySide6.QtWidgets import QApplication\nsys.argv='+repr(args)+'\n'
  code+='try:\n runpy.run_path('+repr(wp(folder/'tools/desktop-ui/player-browsing.py'))+',run_name="__main__")\nfinally:\n app=QApplication.instance()\n if app is not None:\n  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()\n  assert not app.topLevelWidgets(),"owned Qt widgets remain"\n'
  wrapper.write_text(code);log=out/('native-'+scale+'.raw.txt');start=time.monotonic()
  with log.open('xb') as stream:run=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',wp(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
  row={'scale':scale,'exit':run.returncode,'seconds':time.monotonic()-start,'log_sha256':sha(log),'wrapper_sha256':sha(wrapper)};r['runs'].append(row);(out/'progress.json').write_text(json.dumps(r,indent=2)+'\n');assert run.returncode==0,log.read_text(errors='replace')[-6000:]
  report=obs/'report.json';value=json.loads(report.read_text());assert value['result']=='PASS' and value['qpa']=='windows' and value['ratio']==int(scale) and value['source_head']==a.head and not value['callbacks'] and value['sources_unchanged'];assert len(value['tables'])==(12 if scale=='1' else 4)
  assert all(len(v['selected_ids'])==v['rows'] and v['wheel_coverage']==list(range(v['rows'])) for v in value['tables'])
  row.update(report=report.relative_to(folder).as_posix(),report_sha256=sha(report))
 for name,h in r['sources'].items():assert sha(folder/name)==sha(WT/name)==h
 for name,h in r['resources'].items():assert sha(cache/name)==h
 for task,dep in r['dependencies'].items():assert all(sha(cache/('python-libs-'+task)/name)==h for name,h in dep['files'].items())
 assert git('rev-parse','HEAD')==a.head and not git('status','--porcelain','--untracked-files=no');r['result']='PASS'
except BaseException:r['failure']=traceback.format_exc();raise
finally:
 r['protected_after']={p:sha(Path(p)) for p in protected};r['protected_unchanged']=r['protected_after']==protected;r['artifacts']={p.relative_to(folder).as_posix():sha(p) for p in (folder/'observations').rglob('*') if p.is_file()};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');assert r['protected_unchanged']
print(json.dumps({'result':r['result'],'receipt':str(out/'receipt.json'),'runs':r['runs']}))
