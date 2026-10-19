"""[designed: T79] Main-only immutable native launch; no production/render/widget mocks."""
from pathlib import Path
import argparse,hashlib,io,json,subprocess,tarfile,time,traceback
p=argparse.ArgumentParser();p.add_argument('--head',required=True);p.add_argument('--attempt',required=True);a=p.parse_args()
ROOT=Path('/home/diego/projects/goal2');KEEP=ROOT/'.cache/kept/review-receipts';WT=Path('/home/diego/projects/goal2-work/T79-football-ui');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(Path(p).relative_to('/mnt/c')).replace('/','\\')
assert len(a.head)==40 and subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head
assert subprocess.check_output(['git','rev-parse','origin/task/T79-football-ui'],cwd=WT,text=True).strip()==a.head
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
out=KEEP/'T79-it13-20261019'/('T79-windows-'+a.attempt+'-'+str(time.time_ns()));out.mkdir(exist_ok=False)
folder=WIN/'.goal2-validation'/('T79-production-'+a.head[:12]+'-'+str(time.time_ns()));folder.mkdir(parents=True,exist_ok=False)
protected_paths=[WIN/'Start-goal2.cmd',WIN/'Start-goal2-modern.cmd']
for protected_folder in (WIN/'.cache',WIN/'.goal2-modern-saves',WIN/'.goal2-releases/accepted-5c266169/.cache'):
 if protected_folder.is_dir():protected_paths.extend(p for p in protected_folder.rglob('*') if p.is_file() and p.suffix.lower() in ('.sav','.g2save','.dat'))
protected={str(p):sha(p) for p in protected_paths}
r={'claim':'Diagnostic-only native Qt1x heartbeat/geometry timings around unchanged product; not final native acceptance','head':a.head,'attempt':a.attempt,'directory':str(folder),'result':'INCOMPLETE','protected_before':protected,'runs':[]}
try:
 from windows_display_probe import display
 r['display_probe_sha256']=sha(Path(__file__).with_name('windows_display_probe.py'))
 r['native_display_before']={scale:display(WIN,scale) for scale in ('1','2')}
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
 for scale in('1',):
  observations=folder/'observations'/('scale-'+scale);wrapper=folder/('native-'+scale+'.py')
  env={'PYTHONPATH':';'.join(paths),'QT_QPA_PLATFORM':'windows','QT_SCALE_FACTOR':scale,'QT_AUTO_SCREEN_SCALE_FACTOR':'0','SDL_VIDEODRIVER':'windows','SDL_AUDIODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':windows(cache/'tmp'),'TMP':windows(cache/'tmp'),'TEMP':windows(cache/'tmp')}
  args=[windows(folder/'tools/desktop-ui/redesign.py'),'--scenario','match-handoff','--single-scale','--template',windows(cache/'e010-r0008-halftime.sav'),'--data',windows(cache/'GOAL.DAT'),'--evidence-dir',windows(observations)]
  code='import os,sys,runpy,json,traceback,platform\nfrom pathlib import Path\n'
  for key,value in env.items():code+='os.environ['+repr(key)+']='+repr(value)+'\n'
  code+='sys.path[:0]='+repr([windows(folder/'tools/desktop-ui'),*paths])+'\nimport pygame,unicorn\nassert sys.platform=="win32" and pygame.version.ver=="2.5.8" and unicorn.__version__=="2.1.4"\n'
  code+='from PySide6.QtCore import QCoreApplication,QEvent,qVersion\nfrom PySide6.QtWidgets import QApplication\ncallbacks=[]\ndef callback_error(kind,error,tb):\n callbacks.append("".join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)\nsys.excepthook=callback_error\nsys.argv='+repr(args)+'\n'
  code+='import time,match_handoff_scenario as diagnostic_module\nphase_timings=[]\nreal_geometry=diagnostic_module.geometry\ndef diagnostic_geometry(*args,**kwargs):\n start=time.monotonic()\n try: return real_geometry(*args,**kwargs)\n finally: phase_timings.append({"stage":args[4],"start":start,"end":time.monotonic()})\ndiagnostic_module.geometry=diagnostic_geometry\n'
  code+='try:\n runpy.run_path('+repr(windows(folder/'tools/desktop-ui/redesign.py'))+',run_name="__main__")\nexcept BaseException as diagnostic_error:\n tb=diagnostic_error.__traceback__\n detail={"phase_timings":phase_timings}\n while tb is not None:\n  if tb.tb_frame.f_code.co_name=="scenario":\n   local=tb.tb_frame.f_locals;beats=local.get("beats",[]);detail.update(round=local.get("round_index"),heartbeat_count=len(beats),long_gaps=[{"start":a,"end":b,"seconds":b-a} for a,b in zip(beats,beats[1:]) if b-a>=.3])\n  tb=tb.tb_next\n Path('+repr(windows(folder/('heartbeat-diagnostic-'+scale+'.json')))+').write_text(json.dumps(detail,indent=2)+"\\n")\n raise\nfinally:\n app=QApplication.instance()\n if app is not None:\n  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()\n  assert not app.topLevelWidgets(),"owned T79 Qt widgets remain"\n assert not callbacks,callbacks\n'
  wrapper.write_text(code);log=out/('native-'+scale+'.log');start=time.monotonic()
  with log.open('xb')as stream:run=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
  row={'physical_display':{'before':r['native_display_before'][scale],'after':display(WIN,scale)},'scale':scale,'exit':run.returncode,'seconds':round(time.monotonic()-start,3),'log_sha256':sha(log),'wrapper_sha256':sha(wrapper)};r['runs'].append(row);(out/'progress.json').write_text(json.dumps({'head':a.head,'directory':str(folder),'runs':r['runs']},indent=2)+'\n');assert run.returncode==0,log.read_text(errors='replace')[-6000:]
  report=observations/'report.json';value=json.loads(report.read_text());assert value['result']=='PASS' and value['qpa']=='windows' and value['qt_ratio']==int(scale) and value['requested_qt_scale']==scale;assert len(value['rounds'])==2 and value['geometry'] and value['focus'] and value['captures'] and value['sdl'];assert all(item['full_exact_parity'] for item in value['rounds']);assert not value['uncaught_qt_callbacks'] and value['cleanup']['window_closed'] and value['cleanup']['owned_processes_reaped'] and not value['cleanup']['pending'];row.update(report=report.relative_to(folder).as_posix(),report_sha256=sha(report))
 for name,h in r['sources'].items():assert sha(folder/name)==sha(WT/name)==h
 for name,h in r['resources'].items():assert sha(cache/name)==h
 for task,dep in r['dependencies'].items():assert all(sha(cache/('python-libs-'+task)/name)==h for name,h in dep['files'].items())
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head
 assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
 r['result']='PASS'
except BaseException:
 r['failure']=traceback.format_exc();raise
finally:
 r['protected_after']={p:sha(Path(p))for p in protected};r['protected_unchanged']=r['protected_after']==protected;r['artifacts']={p.relative_to(folder).as_posix():sha(p)for p in(folder/'observations').rglob('*')if p.is_file()};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');assert r['protected_unchanged'],'protected launcher/save changed'
print(json.dumps({'result':r['result'],'receipt':str(out/'receipt.json'),'runs':r['runs'],'source_files':len(r['sources']),'protected':len(protected)}))
