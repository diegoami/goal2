#!/usr/bin/env python3
"""[designed: T83] Real Qt/SDL animation acceptance; captures contain rebuild pixels only."""
from navigation import reveal
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# [designed] Instrument the actual production renderer and post-flip surface, without
# extending product protocols or writing original Memory, poses, assets or executables.
VIEWER = r'''
import collections, json, pathlib, sys, time
import pygame
from goal2.desktop import pygame_viewer as v
out=pathlib.Path(sys.argv.pop(1));out.mkdir(parents=True,exist_ok=True)
slow=float(sys.argv.pop(1));close_after=int(sys.argv.pop(1))
original_render=v.render_pitch;original_flip=pygame.display.flip
state={'rendered':0,'changed':0,'selectors':[],'rebindings':0,'last_sequence':-1,'last_minute':None,'complete':False,
       'first_flip_monotonic':None,'last_flip_monotonic':None,'playback_seconds':0,'observed_samples_per_second':0,
       'minimum_sample_interval':None,'maximum_sample_interval':None,'maximum_samples_per_second':None,
       'selector_samples':{},'capture_counts':{}}
current=None;previous=None;display=None;last_pixels=None;caption_set=False
def render(screen,font,d,scroll=0):
 global current,display
 result=original_render(screen,font,d,scroll)
 current=d.frame;display=d
 return result
def flip():
 global previous,last_pixels,caption_set
 if not caption_set:
  pygame.display.set_caption('goal2 — T83 automated pitch acceptance');caption_set=True
  state['actual_sdl_driver']=pygame.display.get_driver()
  state['pygame_version']=pygame.version.ver;state['sdl_version']=list(pygame.get_sdl_version())
 original_flip()
 if (out/'close-request').exists():pygame.event.post(pygame.event.Event(pygame.QUIT))
 if current is not None and current['sequence']!=state['last_sequence']:
  assert current['sequence']==state['last_sequence']+1,'a discrete sample was skipped'
  if display.result is None:
   visible=display.visible()
   assert len(visible.events)==current['watermark'],'commentary escaped its causal watermark'
   assert visible.lines()[2]==('%s min   %s — %s'%(current['minute'],*current['score'])),'score/minute differs from rendered sample'
  pixels=pygame.image.tobytes(pygame.display.get_surface(),'RGB')
  now=time.monotonic()
  if state['first_flip_monotonic'] is None:state['first_flip_monotonic']=now
  if state['last_flip_monotonic'] is not None:
   interval=now-state['last_flip_monotonic']
   state['minimum_sample_interval']=min(state['minimum_sample_interval'] or interval,interval)
   state['maximum_sample_interval']=max(state['maximum_sample_interval'] or interval,interval)
   state['maximum_samples_per_second']=1/state['minimum_sample_interval']
  state['last_flip_monotonic']=now
  state['playback_seconds']=now-state['first_flip_monotonic']
  if state['playback_seconds']:state['observed_samples_per_second']=state['rendered']/state['playback_seconds']
  state['changed']+=int(last_pixels is not None and pixels!=last_pixels)
  state['rendered']+=1;state['last_sequence']=current['sequence'];state['last_minute']=current['minute']
  if previous is not None:state['rebindings']+=sum(a[3]!=b[3] for a,b in zip(previous['players'],current['players']))
  selector=current['selector']
  if selector not in state['selectors']:
   state['selectors'].append(selector)
  previous=current;last_pixels=pixels
  key=str(selector);state['selector_samples'][key]=state['selector_samples'].get(key,0)+1
  ordinal=state['selector_samples'][key]
  if ordinal in (1,300):
   counts=collections.Counter(v.project(p[4],p[5]) for p in current['players'] if not p[7])
   name=('half-' if ordinal==1 else 'sample-300-selector-')+key
   state['capture_counts'][name]={'sample_ordinal_within_selector':ordinal,'sequence':current['sequence'],
    'minute':current['minute'],'hidden_players':sum(p[7] for p in current['players']),
    'visible_players':sum(counts.values()),'unique_projected_player_positions':len(counts),
    'overlap_multiplicities':sorted(n for n in counts.values() if n>1),'ball_hidden':current['ball'][2]}
   pygame.image.save(pygame.display.get_surface(),str(out/(name+'.png')))
  if close_after and state['rendered']>=close_after:pygame.event.post(pygame.event.Event(pygame.QUIT))
  if slow:time.sleep(slow)
 if display is not None and display.result is not None and not state['complete']:
  state['complete']=True
  pygame.image.save(pygame.display.get_surface(),str(out/'full-time.png'))
 # [designed] Atomic diagnostics avoid reading partial JSON during Qt polling.
 tmp=out/'metrics.new';tmp.write_text(json.dumps(state));tmp.replace(out/'metrics.json')
v.render_pitch=render;pygame.display.flip=flip
sys.exit(v.main())
'''


def baseline(owner):
    """[designed: T66/T83] Independent direct original continuation; no frame channel."""
    from goal2.tests.test_watched_adapter import direct
    from goal2.game.watched_publication import WatchedPublication
    from goal2.game.watched_match import WatchedOutcome, engine_year
    from goal2.engine.original_match import Fixture, Image
    from goal2.engine.original_match.match import Event
    f = owner.state.campaign.next_fixture
    publication = WatchedPublication(owner)
    fixture = Fixture(f.side_a, f.side_b, int(f.fixture_id.split(':')[1]))
    job = publication.begin(fixture)
    result, memory, events = direct(job.state, fixture, seed=None, delay=0)
    image = Image.from_memory_component(memory)
    outcome = WatchedOutcome(result, memory, tuple(Event(**e) for e in events),
                             (image.rd(0x7b62), image.rd(0x8336)), engine_year(job.state.campaign))
    publication.complete(job.token, outcome)
    return outcome, json.loads(json.dumps(events))


def main():
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from goal2.desktop.window import ManagementWindow
    from goal2.desktop.match_view import completion
    from goal2.desktop.jobs import QuickJobs
    from goal2.tests.test_pygame_match_view import model, pump

    mode = os.environ.get('QT_QPA_PLATFORM', 'native') + '-' + os.environ.get('SDL_VIDEODRIVER', 'native')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    evidence = ROOT / 'docs/evidence/T83' / (stamp + '-' + mode)
    evidence.mkdir(parents=True)
    receipts = {'mode': mode, 'platform': sys.platform, 'rounds': [], 'boundaries': []}
    app = QApplication.instance() or QApplication([])
    receipts['actual_qt_platform'] = app.platformName()
    with tempfile.TemporaryDirectory(prefix='goal2-t83-') as folder:
        save = Path(folder) / 'pitch.g2save'
        m = model(save)
        w = ManagementWindow(m)
        w.setWindowTitle('goal2 — T83 automated pitch acceptance controls')
        w.show()
        app.processEvents()
        beats = []
        timer = QTimer();timer.setInterval(5)
        timer.timeout.connect(lambda: beats.append(time.monotonic()));timer.start()
        original_start = w.watched.start

        def configure(name, *, rate=None, slow=0, close_after=0):
            target = evidence / name
            w.watched.viewer_command = [sys.executable, '-c', VIEWER, str(target), str(slow), str(close_after)]
            # [designed] First run exercises the production default. Later runs only
            # accelerate its fixed discrete rate, preserving each sampled pose.
            w.watched.start = original_start if rate is None else lambda **kw: original_start(playback_rate=rate, **kw)
            return target

        def click_watch():
            reveal(w.watch);QTest.mouseClick(w.watch, Qt.MouseButton.LeftButton);app.processEvents()
            assert w.watched.busy, w.status.text()
            assert w.watched.frames_enabled, 'Watch did not enable the production pitch by default'

        def locked():
            assert m.match_pending and not w.save.isEnabled()
            for control in (w.new, w.resume, w.country, w.confirm, w.play, w.watch, w.captain):
                assert not control.isEnabled(), 'mutating management control enabled during playback'
            try:m.save(save)
            except ValueError:pass
            else:raise AssertionError('pending playback allowed saving')

        try:
            reveal(w.confirm);QTest.mouseClick(w.confirm, Qt.MouseButton.LeftButton);app.processEvents()
            m.save(save)
            control = type(m)(m.goaldat, m.template_bytes, Path(folder) / 'baseline')
            control.state = copy.deepcopy(m.state)
            for round_number in range(2):
                outcome, events = baseline(control)
                target = configure('round-%s' % (round_number + 1), rate=None if round_number == 0 else 240)
                before = copy.deepcopy(m.state);saved = save.read_bytes();beats.clear()
                click_watch();viewer = w.watched.process;engine = w.watched.engine.process
                locked()
                max_backlog = 0;pending_tail = False
                deadline = time.monotonic() + 600
                while w.watched.busy and time.monotonic() < deadline:
                    app.processEvents()
                    if w.watched.busy:
                        locked()
                        assert m.state == before and save.read_bytes() == saved
                        max_backlog = max(max_backlog, len(w.watched.display.frames))
                        assert max_backlog <= 64
                        if w.watched.engine.engine_complete:
                            pending_tail = True
                            assert w.watched.engine.outcome is None
                    time.sleep(.01)
                assert not w.watched.busy, w.status.text()
                assert pending_tail, 'did not visit completed engine waiting for visible playback'
                assert m.state == control.state, 'canonical state/full Memory/both seeds/history differs'
                assert w.watched.engine.outcome == outcome, 'full original result/Memory/events/both seeds differs'
                assert w.watched.display.events == events, 'canonical ordered events differ'
                assert w.watched.display.result == completion(outcome, m.goaldat.player_names)
                assert w.watched.frame_ack == outcome.result['ticks'] - 1, 'final tick was not rendered'
                pump(lambda: (target/'metrics.json').exists() and json.loads((target/'metrics.json').read_text())['complete'], app=app)
                metrics = json.loads((target/'metrics.json').read_text())
                assert metrics['rendered'] == outcome.result['ticks']
                assert metrics['changed'] > 10 and set(metrics['selectors']) == {0, 1}
                assert metrics['last_sequence'] == w.watched.frame_ack
                assert len(beats) > 5, 'Qt heartbeat blocked'
                reveal(w.save);QTest.mouseClick(w.save, Qt.MouseButton.LeftButton);app.processEvents()
                reveal(w.resume);QTest.mouseClick(w.resume, Qt.MouseButton.LeftButton);app.processEvents()
                assert m.state == control.state
                for _ in range(3):w.poll_watched();app.processEvents()
                assert m.state == control.state, 'redraw republished result'
                receipts['rounds'].append({'round': round_number+1, 'default_rate':round_number==0,
                    'events':len(events), 'score':outcome.result['score'], 'ticks':outcome.result['ticks'],
                    'seeds':list(outcome.seeds), 'memory_sha256':hashlib.sha256(outcome.memory).hexdigest(),
                    'canonical_state_memory_seeds_equal':True, 'pending_tail_locked':pending_tail,
                    'max_backlog':max_backlog, 'heartbeats':len(beats), 'render':metrics})
                # [designed] An old viewer's teardown must preserve a newer job owner.
                if round_number == 0:
                    quick = QuickJobs(m, command=[sys.executable, '-c', 'import time;time.sleep(60)'])
                    quick.start();other = quick.process
                    try:
                        w.watched.cancel();w.poll_watched()
                        assert m.match_pending and other.poll() is None
                        assert not w.save.isEnabled()
                    finally:quick.cancel();w.set_busy(False)
                else:
                    w.watched.close_viewer();w.poll_watched()
                assert viewer.poll() is not None and engine.poll() is not None
                receipts['boundaries'].append('owned-only teardown round 1' if round_number==0 else 'completed-viewer close round 2')

            # [designed] New campaign restores a friendly boundary for cancellation probes.
            reveal(w.new);QTest.mouseClick(w.new, Qt.MouseButton.LeftButton);app.processEvents()
            reveal(w.confirm);QTest.mouseClick(w.confirm, Qt.MouseButton.LeftButton);app.processEvents()
            m.save(save)
            for failure in ('slow-close', 'malformed', 'stale'):
                before = copy.deepcopy(m.state);saved = save.read_bytes()
                target = configure(failure, rate=240, slow=.05 if failure=='slow-close' else 0)
                click_watch();viewer=w.watched.process;engine=w.watched.engine.process
                if failure=='slow-close':
                    locked()
                    pump(lambda:w.watched.engine.engine_complete, app=app, timeout=300)
                    locked()
                    assert w.watched.engine.outcome is None and m.state==before
                    (target/'close-request').write_text('owned SDL QUIT request\n')
                    pump(lambda:w.watched.process is None, app=app, timeout=60)
                else:
                    # [designed] Pause only this owned child to prevent a valid status
                    # racing our malformed/stale protocol probe. The controller reaps
                    # a still-stopped child with its bounded SIGKILL fallback.
                    import signal
                    os.kill(viewer.pid, signal.SIGSTOP)
                    path = w.watched.directory/'status'
                    path.write_text('[]' if failure=='malformed' else json.dumps({'token':'stale','kind':'ready'}))
                    try:w.watched.poll()
                    except ValueError:pass
                    else:raise AssertionError('malformed/stale acknowledgement accepted')
                    w.set_busy(False)
                assert viewer.poll() is not None and engine.poll() is not None
                assert m.state==before and save.read_bytes()==saved and not m.match_pending
                receipts['boundaries'].append(failure+' preserves state and prior save')
            receipts['pass'] = True
            (evidence/'acceptance.json').write_text(json.dumps(receipts, indent=2)+'\n')
            print(json.dumps(receipts, indent=2), flush=True)
            print('PASS T83 real Qt/SDL animated pitch: '+str(evidence), flush=True)
        finally:
            timer.stop();w.close();w.deleteLater();app.processEvents()
            if not receipts.get('pass'):
                (evidence/'failure.json').write_text(json.dumps(receipts, indent=2)+'\n')
    return receipts


if __name__ == '__main__':
    main()
