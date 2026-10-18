"""[designed: #236] Deterministic Windows sharing, deadlines and ownership regressions."""
from contextlib import ExitStack
import errno
import io
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from goal2.desktop import pygame_viewer as viewer, watched
from goal2.desktop.match_view import Display


def denied(winerror=5, number=errno.EACCES):
    error = PermissionError(number, 'injected sharing denial')
    if winerror is not None:
        error.winerror = winerror
    return error


class Clock:
    def __init__(self):
        self.now = 0.
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, duration):
        assert duration > 0
        self.sleeps.append(duration)
        self.now += duration


class SharingTests(unittest.TestCase):
    def environment(self, module, clock, platform='win32'):
        stack = ExitStack()
        stack.enter_context(patch.object(module, 'sys', SimpleNamespace(**{**vars(module.sys), 'platform':platform})))
        stack.enter_context(patch.object(module.time, 'monotonic', clock.monotonic))
        stack.enter_context(patch.object(module.time, 'sleep', clock.sleep))
        return stack

    def controller(self, directory):
        model = SimpleNamespace(match_pending=True)
        with patch.object(watched, 'WatchedJobs') as jobs:
            controller = watched.WatchedController(model)
        controller.engine = jobs.return_value
        controller.engine.busy = False
        controller.process = Mock()
        controller.process.poll.return_value = None
        controller.directory = Path(directory)
        controller.token = 'owned'
        controller.display = Display('owned')
        controller.digests = {0: controller.display.digest()}
        controller.frames_enabled = False
        controller.frame_ack = -1
        controller.frame_receipts = {}
        controller.started = 0.
        controller._pending_owned = True
        return controller

    def value(self, controller, **changes):
        return {'token': controller.token, 'kind': 'ready', 'sequence': 0,
                'digest': controller.digests[0], **changes}

    def test_writer_retries_same_atomic_payload_without_schema_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'status'
            target.write_text('old')
            value = {'token':'owned', 'kind':'ready', 'sequence':7, 'digest':'exact',
                     'frame_sequence':3, 'frame_digest':'rendered'}
            original = viewer.os.replace
            attempts = []
            def replace(source, destination):
                attempts.append(Path(source).read_bytes())
                self.assertEqual(destination, target)
                if len(attempts) < 3:
                    self.assertEqual(target.read_text(), 'old')
                    raise denied()
                original(source, destination)
            clock = Clock()
            with self.environment(viewer, clock), patch.object(viewer.os, 'replace', replace):
                viewer.status(target, value)
            self.assertEqual(len(attempts), 3)
            self.assertEqual(len(set(attempts)), 1)
            self.assertEqual(json.loads(target.read_bytes()), value)
            self.assertFalse(target.with_suffix('.new').exists())
            self.assertEqual(clock.sleeps, [.01, .01])

    def test_writer_permanent_denial_stops_at_deadline_and_keeps_old_status(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'status'; target.write_text('old')
            clock = Clock(); error = denied()
            with self.environment(viewer, clock), patch.object(viewer.os, 'replace', side_effect=error) as replace:
                with self.assertRaises(PermissionError) as caught:
                    viewer.status(target, {'kind':'ready'})
            self.assertIs(caught.exception, error)
            self.assertAlmostEqual(clock.now, .25)
            self.assertLessEqual(replace.call_count, 26)
            self.assertEqual(target.read_text(), 'old')

    def test_writer_does_not_retry_unrelated_or_non_windows_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = Clock()
            with self.environment(viewer, clock), patch.object(viewer.os, 'replace', side_effect=[denied(), None]):
                viewer.status(Path(folder)/'status', {})
            self.assertEqual(clock.sleeps, [.01])
        for platform, error in [('linux', denied()), ('win32', denied(32)),
                                ('win32', OSError(errno.ENOSPC, 'full'))]:
            with self.subTest(platform=platform, error=error), tempfile.TemporaryDirectory() as folder:
                clock = Clock()
                with self.environment(viewer, clock, platform), patch.object(viewer.os, 'replace', side_effect=error) as replace:
                    with self.assertRaises(type(error)) as caught:
                        viewer.status(Path(folder)/'status', {})
                self.assertIs(caught.exception, error)
                self.assertEqual(replace.call_count, 1)
                self.assertEqual(clock.sleeps, [])
        clock = Clock()
        with self.environment(viewer, clock), patch.object(Path, 'write_text', side_effect=denied()), patch.object(viewer.os, 'replace') as replace:
            with self.assertRaises(PermissionError):viewer.status(Path('status'), {})
        replace.assert_not_called()
        self.assertEqual(clock.sleeps, [])

    def test_parent_read_defers_native_errno13_and_win5_without_blocking(self):
        for error in (denied(None), denied()):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as folder:
                c = self.controller(folder); path = c.directory/'status'
                path.write_text(json.dumps(self.value(c)))
                clock = Clock()
                with self.environment(watched, clock), patch.object(Path, 'open', side_effect=error):
                    self.assertFalse(c.poll())
                self.assertEqual(clock.sleeps, [])
                self.assertTrue(c.model.match_pending)
                self.assertIsNone(c.last_status)
                c.engine.poll.assert_not_called()
                with self.environment(watched, clock):self.assertFalse(c.poll())
                self.assertEqual(c.last_status, self.value(c))
                self.assertIsNotNone(c.process)

    def test_parent_read_deadline_is_inclusive_and_success_resets_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            c = self.controller(folder); (c.directory/'status').write_text(json.dumps(self.value(c)))
            clock = Clock(); error = denied(None)
            with self.environment(watched, clock):
                with patch.object(Path, 'open', side_effect=error):
                    self.assertFalse(c.poll()); clock.now = .249; self.assertFalse(c.poll())
                self.assertFalse(c.poll())
                clock.now = .3
                with patch.object(Path, 'open', side_effect=error):
                    self.assertFalse(c.poll()); clock.now = .549; self.assertFalse(c.poll())
                    clock.now = .55
                    with self.assertRaises(PermissionError) as caught:c.poll()
            self.assertIs(caught.exception, error)
            self.assertEqual(clock.sleeps, [])
            self.assertIsNone(c.process)
            self.assertFalse(c.model.match_pending)

    def test_parent_read_unrelated_and_non_windows_errors_propagate(self):
        with tempfile.TemporaryDirectory() as folder:
            c = self.controller(folder); (c.directory/'status').write_text(json.dumps(self.value(c)))
            clock = Clock()
            with self.environment(watched, clock):
                with patch.object(Path, 'open', side_effect=denied(None)):self.assertFalse(c.poll())
                self.assertFalse(c.poll())
            self.assertEqual(c.last_status, self.value(c))
        for platform, error in [('linux', denied(None)), ('linux', denied()),
                                ('win32', denied(32)), ('win32', denied(None, errno.EPERM)),
                                ('win32', OSError(errno.EIO, 'broken read'))]:
            with self.subTest(platform=platform, error=error), tempfile.TemporaryDirectory() as folder:
                c = self.controller(folder); (c.directory/'status').touch(); clock = Clock()
                with self.environment(watched, clock, platform), patch.object(Path, 'open', side_effect=error):
                    with self.assertRaises(type(error)) as caught:c.poll()
                self.assertIs(caught.exception, error)
                self.assertEqual(clock.sleeps, [])
                self.assertIsNone(c.process)

    def test_deferred_read_preserves_malformed_stale_digest_and_frame_ack_oracles(self):
        for changes in ({'token':'stale'}, {'kind':'invented'}, {'sequence':True},
                        {'digest':'bad'}, {'extra':1}, {'frame_sequence':0,'frame_digest':'bad'}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as folder:
                c = self.controller(folder); c.frames_enabled = 'frame_sequence' in changes
                path = c.directory/'status'; path.write_text(json.dumps(self.value(c, **changes)))
                clock = Clock()
                with self.environment(watched, clock):
                    with patch.object(Path, 'open', side_effect=denied(None)):self.assertFalse(c.poll())
                    with self.assertRaises(ValueError):c.poll()
                c.engine.ack_frames.assert_not_called()
                self.assertFalse(c.model.match_pending)

    def resources(self, c, *, cleanup=None):
        c.folder = Mock()
        c.folder.cleanup.side_effect = cleanup
        c.stream = io.BytesIO(b'display'); c.errors = io.BytesIO(b'errors')
        return (c.process, c.folder, c.stream, c.errors, c.directory)

    def test_cleanup_retries_win32_after_closing_owned_handles(self):
        c = self.controller('owned'); clock = Clock()
        refs = self.resources(c, cleanup=[denied(32), denied(32), None])
        def cleanup():
            self.assertTrue(c.stream.closed and c.errors.closed)
            if c.folder.cleanup.call_count < 3:raise denied(32)
        c.folder.cleanup.side_effect = cleanup
        with self.environment(watched, clock):c.cancel()
        self.assertEqual(refs[1].cleanup.call_count, 3)
        self.assertEqual(clock.sleeps, [.02, .02])
        self.assertEqual((c.process,c.folder,c.stream,c.errors,c.directory),(None,)*5)
        self.assertFalse(c.model.match_pending)
        refs[0].wait.assert_called_once_with(timeout=.5)

    def test_cleanup_permanent_win32_retains_references_and_pending_for_retry(self):
        c = self.controller('owned'); clock = Clock(); error = denied(32)
        refs = self.resources(c, cleanup=error)
        c.engine.busy = True
        c.engine_token = 'active-engine'
        def engine_cancel(token):
            self.assertEqual(token, c.engine_token)
            c.engine.busy = False
            c.model.match_pending = False
        c.engine.cancel.side_effect = engine_cancel
        with self.environment(watched, clock):
            with self.assertRaises(PermissionError) as caught:c.cancel()
        self.assertIs(caught.exception,error)
        self.assertAlmostEqual(clock.now,.5)
        self.assertEqual((c.process,c.folder,c.stream,c.errors,c.directory),refs)
        self.assertTrue(c.model.match_pending and c._pending_owned)
        self.assertTrue(c.stream.closed and c.errors.closed)
        c.process.poll.return_value = 0; c.folder.cleanup.side_effect = None
        with self.environment(watched, clock):c.cancel(); c.cancel()
        self.assertFalse(c.model.match_pending or c._pending_owned)
        self.assertEqual((c.process,c.folder,c.stream,c.errors,c.directory),(None,)*5)

    def test_cleanup_unrelated_or_non_windows_error_retains_owned_folder(self):
        for platform,error in [('linux',denied(32)),('win32',denied()),('win32',OSError(errno.EIO,'broken'))]:
            with self.subTest(platform=platform,error=error):
                c=self.controller('owned'); clock=Clock(); refs=self.resources(c,cleanup=error)
                with self.environment(watched,clock,platform):
                    with self.assertRaises(type(error)) as caught:c.close_viewer()
                self.assertIs(caught.exception,error)
                self.assertIs(c.folder,refs[1]); self.assertIs(c.directory,refs[4])
                self.assertEqual(clock.sleeps,[])

    def test_completed_old_viewer_failed_cleanup_cannot_unlock_newer_quick_job(self):
        c=self.controller('owned'); c._pending_owned=False; clock=Clock()
        self.resources(c,cleanup=denied(32))
        with self.environment(watched,clock):
            with self.assertRaises(PermissionError):c.cancel()
            self.assertTrue(c.model.match_pending)
            c.folder.cleanup.side_effect=None; c.cancel()
        self.assertTrue(c.model.match_pending)
        c.engine.cancel.assert_not_called()

    def test_partial_startup_failure_retains_folder_and_retry_cleans_before_new_allocation(self):
        for failed in ('display','errors','launch','engine'):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory() as folder:
                c=self.controller(folder); c.process=None; c.directory=None; c._pending_owned=False
                c.model.match_pending=False
                c.fixture=Mock(return_value=SimpleNamespace(side_a=0,side_b=1,fixture_id='fixture:1'))
                c.model.goaldat=SimpleNamespace(country_names=['A','B'])
                clock=Clock(); acquired=[]; opened=[]; original_open=Path.open; owned=Mock(name=folder)
                owned.name=folder; owned.cleanup.side_effect=denied(32)
                injected = OSError(f'{failed} startup failure')
                def opening(path,*args,**kwargs):
                    opened.append(path.name)
                    if path.name==failed:raise injected
                    handle=original_open(path,*args,**kwargs); acquired.append(handle); return handle
                c.engine.start.side_effect=injected if failed=='engine' else None
                with self.environment(watched,clock), patch.object(watched.importlib.util,'find_spec',return_value=object()), patch.object(watched.tempfile,'TemporaryDirectory',return_value=owned) as allocate_owned, patch.object(Path,'open',opening), patch.object(watched.subprocess,'Popen',side_effect=injected if failed=='launch' else None) as launch:
                    with self.assertRaises(PermissionError) as caught:c.start(frames=False)
                    # [designed: #236] Cleanup denial must follow the intended startup failure.
                    self.assertIs(caught.exception.__context__, injected)
                    allocate_owned.assert_called_once_with(prefix='goal2-viewer-')
                    self.assertEqual(opened, ['display'] if failed=='display' else ['display','errors'])
                    self.assertEqual(len(acquired), {'display':0,'errors':1,'launch':2,'engine':2}[failed])
                    if failed in ('launch','engine'):
                        launch.assert_called_once()
                        self.assertEqual(launch.call_args.args[0][:3],
                                         [watched.sys.executable,'-m','goal2.desktop.pygame_viewer'])
                    else:
                        launch.assert_not_called()
                    if failed=='engine':
                        c.engine.start.assert_called_once()
                        self.assertIs(c.process, launch.return_value)
                    else:
                        c.engine.start.assert_not_called()
                    self.assertIs(c.folder,owned); self.assertEqual(c.directory,Path(folder))
                    self.assertTrue(all(h.closed for h in acquired))
                    owned.cleanup.side_effect=None
                    with patch.object(watched.tempfile,'TemporaryDirectory',side_effect=OSError('new allocation')) as allocate:
                        with self.assertRaisesRegex(ValueError,'new allocation'):c.start(frames=False)
                    self.assertIsNone(c.folder); allocate.assert_called_once()

    def test_cleanup_kill_and_wait_remain_bounded_and_references_survive_timeout(self):
        c=self.controller('owned'); refs=self.resources(c); clock=Clock()
        c.process.wait.side_effect=subprocess.TimeoutExpired('owned',.5)
        with self.environment(watched,clock):
            with self.assertRaises(subprocess.TimeoutExpired):c.cancel()
        self.assertEqual(c.process.wait.call_args_list,[unittest.mock.call(timeout=.5)]*2)
        c.process.kill.assert_called_once()
        self.assertEqual((c.process,c.folder,c.stream,c.errors,c.directory),refs)
        self.assertTrue(c.model.match_pending and c._pending_owned)


if __name__ == '__main__':unittest.main()
