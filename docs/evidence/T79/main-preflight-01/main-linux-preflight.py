"""Main-owned, planning-only actual-original preflight; production bytes stay frozen."""
from pathlib import Path
import hashlib,json,os,subprocess,time
w=Path('/home/diego/projects/goal2-work/T79-football-ui');py='/home/diego/projects/goal2/.cache/validation-venv/bin/python3';head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=w,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=w,text=True).strip()
out=w/'.cache'/('T79-main-handoff-planning-'+str(time.time_ns()));out.mkdir();(out/'tmp').mkdir()
files=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','goal2','tools/desktop-ui'],cwd=w,text=True).splitlines();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();sources={p:sha(w/p)for p in files}
fixtures=json.loads((w/'.cache/main-fixture-inventory.json').read_text())if(w/'.cache/main-fixture-inventory.json').exists()else{'e010-r0008-halftime.sav':sha(w/'.cache/e010-r0008-halftime.sav'),'GOAL.DAT':sha(w/'.cache/GOAL.DAT')}
env={**os.environ,'QT_QPA_PLATFORM':'xcb','SDL_VIDEODRIVER':'x11','SDL_AUDIODRIVER':'dummy','QT_SCALE_FACTOR':'1','PYTHONDONTWRITEBYTECODE':'1','PYGAME_HIDE_SUPPORT_PROMPT':'1','LD_LIBRARY_PATH':str(w/'.cache/xcb-libs/extracted/usr/lib/x86_64-linux-gnu'),'TMPDIR':str(out/'tmp')}
rows=[]
for mode in('baseline','mock','mutate-render'):
    command=['xvfb-run','-a','-s','-screen 0 2880x1800x24','dbus-run-session','--',py,'-B','.cache/main-native-display.py','--output',str(out/(mode+'-display')),'--',py,'-B','.cache/T79-handoff-planning-v1.py','--mode',mode,'--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT','--output',str(out/mode)]
    log=out/(mode+'.log');start=time.monotonic()
    with log.open('xb')as f:r=subprocess.run(command,cwd=w,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=720)
    row={'mode':mode,'exit':r.returncode,'seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(w)),'log_sha256':sha(log)};rows.append(row);(out/'progress.json').write_text(json.dumps({'head':head,'rows':rows},indent=2)+'\n')
    report=json.loads((out/mode/'report.json').read_text());text=log.read_text(errors='replace')
    if mode=='mock':assert r.returncode==0 and report['result']=='PASS'and len(report['rounds'])==2,text[-4000:]
    else:
        expected='named match surface is absent on prestyle baseline'if mode=='baseline'else'renderer changed Display state'
        assert r.returncode==1 and report['exception']=='AssertionError'and expected in report['failure'],text[-5000:]
    assert all(sha(w/p)==h for p,h in sources.items())
    assert all(sha(w/'.cache'/p)==h for p,h in fixtures.items())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=w,text=True).strip()==head
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=w,text=True).strip()
receipt={'head':head,'result':'PASS','claim':'Planning runtime-only mocks, no product implementation or Windows acceptance','rows':rows,'sources':sources,'fixtures':fixtures};(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'result':'PASS','receipt':str(out/'receipt.json'),'rows':rows}))
