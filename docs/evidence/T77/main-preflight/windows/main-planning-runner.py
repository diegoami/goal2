"""[designed: T77/T79] Main-only planning mock feasibility, never final acceptance."""
from pathlib import Path
import hashlib, io, json, subprocess, tarfile, time

ROOT=Path('/home/diego/projects/goal2'); WORK=Path('/home/diego/projects/goal2-work')
WIN=Path('/mnt/c/Users/diego/projects/goal2-exe'); KEEP=ROOT/'.cache/kept/review-receipts'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(p.relative_to('/mnt/c')).replace('/','\\')
out=KEEP/('GUI-next-planning-windows-'+str(time.time_ns()));out.mkdir()
protected={str(p):sha(p)for p in (WIN/'.cache').rglob('*')if p.is_file()and p.suffix.lower()in('.sav','.g2save','.dat')}
protected[str(WIN/'Start-goal2.cmd')]=sha(WIN/'Start-goal2.cmd')
receipt={'tag':'[designed] planning only; synthetic T79 packets; not task acceptance','protected_before':protected,'runs':[],'result':'INCOMPLETE'}
try:
 for task in ('T77','T79'):
  wt=WORK/(task+'-football-ui');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=wt,text=True).strip()
  assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=wt,text=True).strip()
  folder=WIN/'.goal2-validation'/(task+'-planning-'+str(time.time_ns()));folder.mkdir()
  archive=subprocess.check_output(['git','archive',head,'goal2','tools/desktop-ui'],cwd=wt)
  with tarfile.open(fileobj=io.BytesIO(archive))as tar:
   for m in tar.getmembers():
    assert not m.issym()and not m.islnk();p=folder/m.name;assert p.resolve().is_relative_to(folder.resolve())
    if m.isdir():p.mkdir(parents=True,exist_ok=True)
    elif m.isfile():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
  sources={p.relative_to(folder).as_posix():sha(p)for p in folder.rglob('*')if p.is_file()}
  cache=folder/'.cache';cache.mkdir();(cache/'tmp').mkdir();probe=cache/(task+'-main-planning-probe.py');probe.write_bytes((wt/'.cache'/probe.name).read_bytes())
  for name in ('GOAL.DAT','e010-r0008-halftime.sav'):(cache/name).write_bytes((wt/'.cache'/name).read_bytes())
  runtime=None
  if task=='T79':
   dep=json.loads((KEEP/'T79-private-runtime-config.json').read_text());runtime=cache/'python-libs';runtime.mkdir()
   for name,h in dep['files'].items():
    src=Path(dep['directory'])/name;assert sha(src)==h;dst=runtime/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
  for scale,mode in [('1','baseline'),('1','mock'),('2','mock'),('1','filter-mutates'if task=='T77'else'mutate-render')]:
   dest=folder/'observations'/(mode+'-'+scale);wrapper=folder/(mode+'-'+scale+'.py')
   argv=[windows(probe),'--mode',mode,'--output',windows(dest)]
   if task=='T79':argv+=['--render-scale',scale]
   code='import os,sys,runpy,json\nfrom pathlib import Path\n'
   for key,value in {'QT_QPA_PLATFORM':'windows','QT_SCALE_FACTOR':scale,'QT_AUTO_SCREEN_SCALE_FACTOR':'0','PYGAME_HIDE_SUPPORT_PROMPT':'1','SDL_VIDEODRIVER':'windows','SDL_AUDIODRIVER':'dummy','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':windows(cache/'tmp'),'TEMP':windows(cache/'tmp'),'TMP':windows(cache/'tmp')}.items():code+='os.environ['+repr(key)+']='+repr(value)+'\n'
   code+='sys.path.insert(0,'+repr(windows(folder))+')\nsys.path.insert(0,'+repr(windows(folder/'tools/desktop-ui'))+')\n'
   if runtime is not None:
    code+='sys.path.insert(0,'+repr(windows(runtime))+')\n'
    # A separate actual Qt window proves Qt ratio; no engine or SDL scaling inference.
    qt_out=folder/('qt-'+scale+'-'+mode);code+='qout=Path('+repr(windows(qt_out))+');qout.mkdir()\n'
    code+='from PySide6.QtWidgets import QApplication\nfrom PySide6.QtTest import QTest\nfrom PySide6.QtCore import qVersion\nfrom goal2.desktop.model import DesktopModel\nfrom goal2.desktop.window import ManagementWindow\n'
    code+='app=QApplication([])\nm=DesktopModel.open('+repr(windows(cache/'e010-r0008-halftime.sav'))+','+repr(windows(cache/'GOAL.DAT'))+',qout/"owned.g2save",country=18)\nw=ManagementWindow(m);w.resize(900,'+('640'if scale=='2'else'700')+');w.show();w.activateWindow();QTest.qWait(100)\n'
    code+='assert QTest.qWaitForWindowActive(w,2000);assert w.devicePixelRatioF()=='+scale+'\nassert w.grab().save(str(qout/"qt-window.png"))\n(qout/"qt.json").write_text(json.dumps({"ratio":w.devicePixelRatioF(),"qpa":app.platformName(),"qt":qVersion(),"size":[w.width(),w.height()]}))\nw.close();app.processEvents()\n'
   code+='sys.argv='+repr(argv)+'\nrunpy.run_path(sys.argv[0],run_name="__main__")\n';wrapper.write_text(code)
   log=out/(task+'-'+mode+'-'+scale+'.log');started=time.monotonic()
   with log.open('xb')as stream:r=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
   report_path=dest/'report.json';report=json.loads(report_path.read_text());expected=mode=='mock'
   row={'task':task,'head':head,'scale':scale,'mode':mode,'exit':r.returncode,'expected_success':expected,'seconds':round(time.monotonic()-started,3),'directory':str(folder),'log_sha256':sha(log),'wrapper_sha256':sha(wrapper),'probe_sha256':sha(probe),'report':str(report_path),'report_sha256':sha(report_path)}
   receipt['runs'].append(row)
   assert (r.returncode==0)==expected,(row,log.read_text(errors='replace'))
   if expected:
    assert 'Traceback (most recent call last)'not in log.read_text(errors='replace')
    if task=='T77':assert report['passed']and not report['callback_exceptions']and report['sources_unchanged']
    else:assert report['result']=='PASS'and report['actual_sdl_driver']=='windows'and report['surface_size']==[900*int(scale),640*int(scale)]
   elif mode=='baseline':assert ('focused incoming detail/exchange summary absent'if task=='T77'else'shared_background')in log.read_text(errors='replace')
   else:assert ('search/filter changed complete state or RNG'if task=='T77'else'render_is_read_only')in log.read_text(errors='replace')
  assert all(sha(folder/name)==h for name,h in sources.items())
 receipt['result']='PASS'
finally:
 receipt['protected_after']={p:sha(Path(p))for p in protected};assert receipt['protected_after']==protected
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'result':receipt['result'],'receipt':str(out/'receipt.json'),'runs':len(receipt['runs']),'protected':len(protected)}))
