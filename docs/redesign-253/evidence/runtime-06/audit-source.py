#!/usr/bin/env python3
"""[designed: #253] Observe accepted UI in disposable state; no product edits or saved game writes."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def terminal(out, env):
    master, slave = pty.openpty()
    import fcntl
    import struct
    import termios
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 25, 80, 0, 0))
    proc = subprocess.Popen([sys.executable, '-m', 'goal2.loop', '--save', str(ROOT / '.cache/253-observation/terminal.g2save'), str(ROOT / '.cache/e010-r0008-halftime.sav'), str(ROOT / '.cache/GOAL.DAT')], cwd=ROOT, stdin=slave, stdout=slave, stderr=slave, env={**env, 'TERM': 'xterm'})
    os.close(slave)
    chunks = []
    def drain():
        until = time.monotonic() + .7
        while time.monotonic() < until:
            ready, _, _ = select.select([master], [], [], .1)
            if ready:
                try: chunks.append(os.read(master, 65536))
                except OSError: break
    try:
        drain()
        os.write(master, b'\x1b[B'); drain()
        os.write(master, b'\r'); drain()
        os.write(master, b'\x1b'); drain()
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None: proc.terminate(); proc.wait(timeout=5)
        os.close(master)
    raw = b''.join(chunks).decode('utf-8', errors='replace').replace('\r', '')
    frames = [re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', x) for x in raw.split('\x1b[2J\x1b[H') if x.strip()]
    (out / 'terminal.txt').write_text('\n\n--- actual PTY frame ---\n\n'.join(frames))
    return {'command': 'python -m goal2.loop <verified template> <verified data> --save <owned unused path>', 'input': ['Down', 'Enter', 'Escape'], 'frames': len(frames), 'exit': proc.returncode, 'save_written': (ROOT / '.cache/253-observation/terminal.g2save').exists()}


def desktop(out):
    from PySide6.QtCore import QCoreApplication, QEvent, Qt, qVersion
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.game.session_save import encode
    app = QApplication([])
    model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT', ROOT / '.cache/253-observation/desktop.g2save', country=4)
    window = ManagementWindow(model); window.show(); window.activateWindow(); QTest.qWait(300)
    before = encode(model.state, model.template_bytes)
    report = {'python': sys.version, 'qt': qVersion(), 'qpa': app.platformName(), 'ratio': window.devicePixelRatioF(), 'screens': [], 'observed': []}
    try:
        for width, height in [(1440, 900), (900, 640)]:
            window.resize(width, height); QTest.qWait(150)
            for i, name in enumerate(['overview', 'squad', 'pool', 'fixtures', 'save']):
                QTest.mouseClick(window.navigation[i], Qt.MouseButton.LeftButton); app.processEvents(); QTest.qWait(50)
                filename = f'desktop-{name}-{width}.png'
                assert window.grab().save(str(out / filename))
                page = window.pages[i]
                labels = [{'name': w.objectName(), 'text': w.text(), 'enabled': w.isEnabled(), 'visible': w.isVisible()} for w in page.findChildren(QLabel)]
                report['screens'].append({'file': filename, 'requested': [width, height], 'actual': [window.width(), window.height()], 'page': name, 'vertical_range': page.verticalScrollBar().maximum(), 'labels': labels, 'actions': [{'text': b.text(), 'enabled': b.isEnabled()} for b in page.findChildren(QPushButton)]})
        assert encode(model.state, model.template_bytes) == before
        report['navigation_state_unchanged'] = True
        window.resize(1440, 900); window.navigate(1); window.table.setCurrentCell(19, 1); window.table.scrollToItem(window.table.item(19, 1)); QTest.qWait(80)
        assert window.grab().save(str(out / 'desktop-final-roster-row.png'))
        report['observed'].append({'squad_rows': window.table.rowCount(), 'squad_columns': window.table.columnCount(), 'headers': [window.table.horizontalHeaderItem(i).text() for i in range(window.table.columnCount())], 'selected_last_row': window.table.currentRow(), 'player_detail': window.player_detail.text()})
        window.navigate(3); window.pages[3].verticalScrollBar().setValue(0); app.processEvents()
        report['observed'].append({'play_label': window.play.text(), 'watch_label': window.watch.text(), 'watch_enabled': window.watch.isEnabled(), 'watch_rate_control_present': any('speed' in w.objectName().lower() or 'rate' in w.objectName().lower() for w in window.findChildren(QLabel)), 'fixture_guidance': window.fixture_routes.text()})
        # [designed: #253] Start only a disposable session, observe a painted frame, then cancel.
        report['draft_before_watch'] = {'displayed': window.draft(), 'active': [model.state.starting_eleven,model.state.captain,model.state.country_tactics]}
        window.navigate(1); QTest.mouseClick(window.cancel, Qt.MouseButton.LeftButton); app.processEvents()
        report['draft_after_discard'] = {'displayed': window.draft(), 'active': [model.state.starting_eleven,model.state.captain,model.state.country_tactics]}
        QTest.mouseClick(window.confirm, Qt.MouseButton.LeftButton); app.processEvents()
        report['ephemeral_setup_confirmation'] = window.status.text()
        watched_before = encode(model.state, model.template_bytes)
        window.navigate(3); window.start_watched()
        deadline = time.monotonic() + 25
        while window.watched.process is not None and time.monotonic() < deadline:
            QTest.qWait(25)
            if window.watched.last_status and window.watched.last_status.get('frame_sequence', -1) >= 3:
                break
        report['watched'] = {'started': window.watched.process is not None, 'status': window.status.text(), 'painted_frame_sequence': (window.watched.last_status or {}).get('frame_sequence'), 'management_enabled': window.confirm.isEnabled(), 'save_enabled': window.save.isEnabled()}
        if report['watched']['painted_frame_sequence'] is not None:
            result = subprocess.run(['xdotool', 'search', '--pid', str(window.watched.process.pid), '--name', '^goal2 — Original friendly$'], capture_output=True, text=True, check=False)
            ids = result.stdout.split()
            if ids:
                assert app.primaryScreen().grabWindow(int(ids[-1])).save(str(out / 'watched-actual.png'))
                report['watched']['capture'] = 'watched-actual.png'
        assert report['watched']['painted_frame_sequence'] is not None and report['watched']['painted_frame_sequence'] >= 3, report['watched']
        window.cancel_match(); QTest.qWait(100)
        report['watched']['cancel_restored_state'] = encode(model.state, model.template_bytes) == watched_before
        report['save_written'] = model.save_path.exists()
        assert report['navigation_state_unchanged'] and report['watched']['cancel_restored_state'] and not report['save_written']
    finally:
        window.close(); window.deleteLater(); QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete); app.processEvents(); app.shutdown()
    return report


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True); ap.add_argument('--inner', action='store_true'); args = ap.parse_args()
    out = args.out.resolve()
    private = ROOT / '.cache/253-observation'; private.mkdir(parents=True, exist_ok=True)
    for part in ['tmp', 'config', 'cache', 'runtime']:
        (private / part).mkdir(exist_ok=True, mode=0o700)
    metadata = json.loads((ROOT / '.cache/main-environment-ready.json').read_text())
    env = dict(os.environ, QT_QPA_PLATFORM='xcb', LD_LIBRARY_PATH=metadata['xcb_libraries'], XDG_CONFIG_HOME=str(private/'config'), XDG_CACHE_HOME=str(private/'cache'), XDG_RUNTIME_DIR=str(private/'runtime'), TMPDIR=str(private/'tmp'), SDL_AUDIODRIVER='dummy')
    for name in ('QT_SCALE_FACTOR','QT_SCREEN_SCALE_FACTORS','WAYLAND_DISPLAY','SESSION_MANAGER'):
        env.pop(name, None)
    if not args.inner:
        result = subprocess.run(['/usr/bin/dbus-run-session','--',sys.executable,'-B',__file__,'--out',str(out),'--inner'], env=env, stdin=subprocess.DEVNULL)
        raise SystemExit(result.returncode)
    out.mkdir(parents=True, exist_ok=False)
    display = str(2000 + os.getpid() % 20000)
    address = chr(0) + '/tmp/.X11-unix/X' + display
    probe = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); probe.bind(address); probe.close()
    xvfb = subprocess.Popen(['/usr/bin/Xvfb',':'+display,'-screen','0','2880x1800x24','-nolisten','tcp','-nolisten','unix'], stdin=subprocess.DEVNULL, stdout=(private/'xvfb-abstract.log').open('w'),stderr=subprocess.STDOUT)
    for _ in range(80):
        assert xvfb.poll() is None, 'owned Xvfb exited'
        probe = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            probe.connect(address); break
        except OSError: time.sleep(.1)
        finally: probe.close()
    else: raise RuntimeError('owned Xvfb not ready')
    env['DISPLAY'] = ':' + display
    wm = subprocess.Popen(['/usr/bin/xfwm4','--compositor=off','--sm-client-disable'],env=env,stdin=subprocess.DEVNULL,stdout=(private/'wm-abstract.log').open('w'),stderr=subprocess.STDOUT)
    for _ in range(100):
        assert wm.poll() is None, 'owned window manager exited'
        check = subprocess.run(['xprop','-root','_NET_SUPPORTING_WM_CHECK'],env=env,capture_output=True,text=True)
        if check.returncode==0 and 'window id #' in check.stdout: break
        time.sleep(.05)
    else: raise RuntimeError('owned window manager not ready')
    os.environ.update(env)
    try:
        report = {'evidence': '[confirmed: #253 direct runtime observation]', 'audited_commit': '3335da830d289cc869f989b73816926c54360ff1', 'runtime_checkout_head': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), 'display_pixels': [2880,1800], 'resources': {n: sha(ROOT/'.cache'/n) for n in ['e010-r0008-halftime.sav','GOAL.DAT','e0afff6751747233-e006-1000-r0001.sav']}, 'sources': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))}, 'audit_sha256': sha(__file__)}
        report['terminal'] = terminal(out, env)
        report['desktop'] = desktop(out)
        report['resources_after'] = {n: sha(ROOT/'.cache'/n) for n in report['resources']}
        report['sources_after'] = {n: sha(ROOT/n) for n in report['sources']}
        assert report['resources']==report['resources_after'] and report['sources']==report['sources_after']
        report['artifacts'] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'out': str(out.relative_to(ROOT)), 'terminal_frames': report['terminal']['frames'], 'desktop_captures': len(report['desktop']['screens']), 'watched': report['desktop']['watched'], 'state_unchanged': report['desktop']['navigation_state_unchanged']}))
    finally:
        wm.terminate(); wm.wait(timeout=5)
        xvfb.terminate(); xvfb.wait(timeout=5)

if __name__ == '__main__': main()
