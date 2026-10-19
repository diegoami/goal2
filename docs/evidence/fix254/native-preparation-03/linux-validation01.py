"""[designed: fix254] Main-owned serial integration on private X11 and D-Bus."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback

root = Path.cwd()
out = root / '.cache/fix254-linux-driver01'
if '--inner' not in sys.argv:
    out.mkdir(exist_ok=False)
    dirs = {name: out / name for name in ('tmp','config','cache','runtime')}
    for directory in dirs.values():
        directory.mkdir()
    dirs['runtime'].chmod(0o700)
    env = {**os.environ,'HARNESS_CLIENT':'codex','QT_QPA_PLATFORM':'xcb',
           'QT_AUTO_SCREEN_SCALE_FACTOR':'0','SDL_VIDEODRIVER':'x11','SDL_AUDIODRIVER':'dummy',
           'PYTHONDONTWRITEBYTECODE':'1','PYGAME_HIDE_SUPPORT_PROMPT':'1',
           'TMPDIR':str(dirs['tmp']),'XDG_CONFIG_HOME':str(dirs['config']),
           'XDG_CACHE_HOME':str(dirs['cache']),'XDG_RUNTIME_DIR':str(dirs['runtime']),
           'LD_LIBRARY_PATH':str(root/'.cache/xcb-libs/extracted/usr/lib/x86_64-linux-gnu')}
    for name in ('QT_SCALE_FACTOR','QT_SCREEN_SCALE_FACTORS','WAYLAND_DISPLAY','SESSION_MANAGER'):
        env.pop(name,None)
    result = subprocess.run(['/usr/bin/dbus-run-session','--',sys.executable,'-B',__file__,'--inner'],env=env,stdin=subprocess.DEVNULL)
    sys.exit(result.returncode)

assert os.environ.get('DBUS_SESSION_BUS_ADDRESS')
head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head == json.loads((root/'.cache/main-validation-config.json').read_text())['head']
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
paths = sorted((root/'goal2').rglob('*.py')) + sorted((root/'tools/desktop-ui').glob('*.py'))
def hashes():
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
initial = hashes()
report = {'claim':'Main integrated Linux execution, not native Windows or independent review',
          'head':head,'phase':'starting','rows':[],'initial_sources':initial,'private_dbus':True}
owned = []
streams = []
def status():
    (out/'status.json').write_text(json.dumps(report,indent=2)+'\n')
try:
    display = str(2000+os.getpid()%20000)
    address = chr(0)+'/tmp/.X11-unix/X'+display
    probe = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    probe.bind(address)
    probe.close()
    stream = (out/'xvfb.log').open('xb')
    streams.append(stream)
    xvfb = subprocess.Popen(['/usr/bin/Xvfb',':'+display,'-screen','0','2880x1800x24','-nolisten','tcp','-nolisten','unix'],stdin=subprocess.DEVNULL,stdout=stream,stderr=stream)
    owned.append(xvfb)
    for attempt in range(100):
        assert xvfb.poll() is None,'owned Xvfb exited'
        probe = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            probe.connect(address)
            break
        except OSError:
            time.sleep(.1)
        finally:
            probe.close()
    else:
        raise RuntimeError('owned Xvfb socket not ready')
    env = {**os.environ,'DISPLAY':':'+display}
    stream = (out/'xfwm.log').open('xb')
    streams.append(stream)
    wm = subprocess.Popen(['/usr/bin/xfwm4','--compositor=off','--sm-client-disable'],env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
    owned.append(wm)
    for attempt in range(200):
        assert wm.poll() is None,'owned window manager exited'
        check = subprocess.run(['xprop','-root','_NET_SUPPORTING_WM_CHECK'],env=env,capture_output=True,text=True)
        if check.returncode==0 and 'window id #' in check.stdout:
            break
        time.sleep(.05)
    else:
        raise RuntimeError('owned window manager not ready')
    report.update(display=env['DISPLAY'],screen='2880x1800x24',owned_pids=[p.pid for p in owned])
    base=[sys.executable,'-B'];resources=['--template',str(root/'.cache/e010-r0008-halftime.sav'),'--data',str(root/'.cache/GOAL.DAT')]
    commands=[('sharing',base+['-m','unittest','goal2.tests.test_desktop_watched_sharing','-v']),('lifecycle',base+['-m','unittest','goal2.tests.test_pygame_match_view','goal2.tests.test_desktop_quick_jobs','goal2.tests.test_pygame_pitch_view','goal2.tests.test_watched_pitch_jobs','-v']),('animated-pitch',base+['tools/desktop-ui/animated-pitch.py']),('competitive',base+['tools/desktop-ui/competitive_play.py']),('friendlies-controls',base+['tools/desktop-ui/prove-friendlies.py']),('worker',base+['tools/desktop-ui/acceptance.py','--scenario','worker',*resources,'--screenshot',str(out/'worker.png')]),('provenance',base+['tools/check_provenance.py']),('links',base+['tools/check_links.py']),('whitespace',['git','diff','--check']),('authored-whitespace',['git','diff','origin/main...HEAD','--check']),('premerge',base+['tools/check_premerge.py','--expected-head',head])]
    for name,command in commands:
        report.update(phase='running',current=name);status()
        prior={x for top in(root/'docs/evidence/T80',root/'docs/evidence/T83')for x in top.iterdir()}
        started=time.monotonic();log=out/(name+'.log')
        with log.open('xb')as stream:run=subprocess.run(command,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=2400)
        same=hashes()==initial;report['rows'].append({'name':name,'command':command,'exit':run.returncode,'seconds':time.monotonic()-started,'sources_unchanged':same,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()});status()
        for top in(root/'docs/evidence/T80',root/'docs/evidence/T83'):
            for source in top.iterdir():
                if source not in prior:
                    import shutil
                    target=out/'retained-artifacts'/top.name/source.name;target.parent.mkdir(parents=True,exist_ok=True)
                    if source.is_dir():shutil.copytree(source,target)
                    else:shutil.copyfile(source,target)
        assert run.returncode==0 and same,(name,run.returncode,log.read_text(errors='replace')[-4000:])
    report.update(phase='complete',result='PASS',final_sources=hashes())
except BaseException:
    report.update(phase='failed',result='FAIL',failure=traceback.format_exc())
    raise
finally:
    for process in reversed(owned):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    for stream in streams:
        stream.close()
    report['owned_display_cleanup'] = all(p.poll() is not None for p in owned)
    status()
print(json.dumps({'result':report.get('result'),'head':head,'rows':report['rows'],'owned_display_cleanup':report['owned_display_cleanup']}))
