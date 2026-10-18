"""Main-only immutable Windows planning archive; runtime mocks, not product acceptance."""
from pathlib import Path
import hashlib,io,json,subprocess,tarfile,time
ROOT=Path('/home/diego/projects/goal2');KEEP=ROOT/'.cache/kept/review-receipts';WT=Path('/home/diego/projects/goal2-work/T79-football-ui');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(Path(p).relative_to('/mnt/c')).replace('/','\\')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip();assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
out=KEEP/('T79-windows-planning-'+str(time.time_ns()));out.mkdir();folder=WIN/'.goal2-validation'/('T79-planning-'+head[:12]+'-'+str(time.time_ns()));folder.mkdir(parents=True)
protected={str(p):sha(p)for p in(WIN/'.cache').rglob('*')if p.is_file()and p.suffix.lower()in('.sav','.g2save','.dat')};protected[str(WIN/'Start-goal2.cmd')]=sha(WIN/'Start-goal2.cmd')
r={'head':head,'directory':str(folder),'result':'INCOMPLETE','claim':'Planning runtime mocks only; not product implementation or style acceptance','protected_before':protected,'runs':[]}
try:
    raw=subprocess.check_output(['git','archive',head,'goal2','tools/desktop-ui'],cwd=WT)
    with tarfile.open(fileobj=io.BytesIO(raw))as tar:
        for item in tar.getmembers():
            assert not item.issym()and not item.islnk();dest=folder/item.name;assert dest.resolve().is_relative_to(folder.resolve())
            if item.isdir():dest.mkdir(parents=True,exist_ok=True)
            elif item.isfile():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(item).read())
    r['sources']={p.relative_to(folder).as_posix():sha(p)for p in folder.rglob('*')if p.is_file()}
    cache=folder/'.cache';cache.mkdir();(cache/'tmp').mkdir();r['resources']={}
    for name in('e010-r0008-halftime.sav','GOAL.DAT','e0afff6751747233-e006-1000-r0001.sav'):
        dest=cache/name;dest.write_bytes((WT/'.cache'/name).read_bytes());r['resources'][name]=sha(dest)
    paths=[windows(folder)];r['dependencies']={}
    for task in('T78','T79'):
        dep=json.loads((KEEP/(task+'-private-runtime-config.json')).read_text());dest=cache/('python-libs-'+task);dest.mkdir();paths.append(windows(dest));r['dependencies'][task]=dep
        for name,h in dep['files'].items():
            source=Path(dep['directory'])/name;assert sha(source)==h;target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());assert sha(target)==h
    r['probes']={}
    for name in('T79-handoff-planning-v3.py','T79-main-planning-probe.py'):
        (cache/name).write_bytes((WT/'.cache'/name).read_bytes());r['probes'][name]=sha(cache/name)
    for scale in('1','2'):
        jobs=[('handoff',mode)for mode in('baseline','mock','mutate-render')]+[('surface',mode)for mode in('baseline','mock','mutate-render')]
        for kind,mode in jobs:
            label=kind+'-'+mode+'-'+scale;target=folder/'observations'/label;wrapper=folder/('run-'+label+'.py')
            env={'PYTHONPATH':';'.join(paths),'QT_QPA_PLATFORM':'windows','QT_SCALE_FACTOR':scale,'QT_AUTO_SCREEN_SCALE_FACTOR':'0','SDL_VIDEODRIVER':'windows','SDL_AUDIODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':windows(cache/'tmp'),'TMP':windows(cache/'tmp'),'TEMP':windows(cache/'tmp')}
            probe=cache/('T79-handoff-planning-v3.py'if kind=='handoff'else'T79-main-planning-probe.py');args=[windows(probe),'--mode',mode,'--output',windows(target)]
            if kind=='handoff':args+=['--template',windows(cache/'e010-r0008-halftime.sav'),'--data',windows(cache/'GOAL.DAT')]
            else:args+=['--render-scale',scale]
            code='import os,sys,runpy,json,traceback\nfrom pathlib import Path\n'
            for key,value in env.items():code+='os.environ['+repr(key)+']='+repr(value)+'\n'
            code+='sys.path[:0]='+repr(paths)+'\nimport pygame,unicorn\nassert sys.platform=="win32" and pygame.version.ver=="2.5.8" and unicorn.__version__=="2.1.4"\n'
            code+='from PySide6.QtCore import QCoreApplication,QEvent\nfrom PySide6.QtWidgets import QApplication\ncallbacks=[]\ndef callback_error(kind,error,tb):\n callbacks.append("".join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)\nsys.excepthook=callback_error\nsys.argv='+repr(args)+'\n'
            code+='try:\n runpy.run_path('+repr(windows(probe))+',run_name="__main__")\nfinally:\n app=QApplication.instance()\n if app is not None:\n  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()\n  assert not app.topLevelWidgets(),"owned planning Qt widgets remain"\n assert not callbacks,callbacks\n'
            wrapper.write_text(code);log=out/(label+'.log');start=time.monotonic()
            with log.open('xb')as stream:run=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=720)
            report=json.loads((target/'report.json').read_text());row={'kind':kind,'mode':mode,'qt_scale':scale,'exit':run.returncode,'seconds':round(time.monotonic()-start,3),'log_sha256':sha(log),'wrapper_sha256':sha(wrapper),'report':(target/'report.json').relative_to(folder).as_posix(),'report_sha256':sha(target/'report.json')};r['runs'].append(row);(out/'progress.json').write_text(json.dumps({'head':head,'directory':str(folder),'runs':r['runs']},indent=2)+'\n')
            if mode=='mock':assert run.returncode==0 and report['result']=='PASS',log.read_text(errors='replace')[-5000:]
            elif kind=='handoff':
                expected='named match surface is absent on prestyle baseline'if mode=='baseline'else'renderer changed Display state'
                assert run.returncode==1 and report['exception']=='AssertionError'and expected in report['failure'],log.read_text(errors='replace')[-5000:]
            else:
                expected='shared_background'if mode=='baseline'else'render_is_read_only'
                assert run.returncode==1 and report['exception']=='AssertionError'and expected in report['failed_checks'],log.read_text(errors='replace')[-5000:]
            if kind=='handoff':assert report['qpa']=='windows'and report['qt_ratio']==int(scale)
            else:assert report['actual_sdl_driver']=='windows'and report['surface_size']==[900*int(scale),640*int(scale)]and report['windows_native']['dpi_for_window']>0
    for name,h in r['sources'].items():assert sha(folder/name)==sha(WT/name)==h
    for name,h in r['resources'].items():assert sha(cache/name)==h
    for task,dep in r['dependencies'].items():assert all(sha(cache/('python-libs-'+task)/name)==h for name,h in dep['files'].items())
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==head
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
    r['result']='PASS'
finally:
    r['protected_after']={name:sha(name)for name in protected};r['protected_unchanged']=r['protected_after']==protected;r['artifacts']={p.relative_to(folder).as_posix():sha(p)for p in(folder/'observations').rglob('*')if p.is_file()};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');assert r['protected_unchanged'],'protected original changed'
print(json.dumps({'result':r['result'],'receipt':str(out/'receipt.json'),'runs':r['runs']}))
