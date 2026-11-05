"""[designed: T148] Native jobs and receipts must prove focus and actual Qt scaling."""
import copy
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_t148', ROOT / 'measurements/T148/run_native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Workflows(unittest.TestCase):
    def job(self, filename):
        text = (ROOT / '.github/workflows' / filename).read_text()
        match = re.search(r'^  native-scaling:\n.*?(?=^  [\w-]+:\n|\Z)', text, re.M | re.S)
        self.assertIsNotNone(match, f'{filename}: no native scaling job')
        return match.group()

    def test_both_native_jobs_run_separate_factors_and_upload_filtered_receipts(self):
        for filename, backend in [('ci.yml', 'xcb'), ('windows.yml', 'windows')]:
            with self.subTest(workflow=filename):
                job = self.job(filename)
                self.assertIn('needs: changes', job)
                self.assertIn('head.repo.full_name == github.repository', job)
                self.assertIn('factor: [1, 2]', job)
                self.assertIn('fail-fast: false', job)
                self.assertIn(f'QT_QPA_PLATFORM: {backend}', job)
                self.assertNotIn('offscreen', job)
                self.assertIn('--factor "${{ matrix.factor }}"', job)
                self.assertIn('measurements/T148/run_native.py', job)
                self.assertIn('secrets.GOAL2_RCLONE_TOKEN', job)
                # GitHub's runner context exists in steps, not in job-level env.
                self.assertNotIn('${{ runner.', job.split('    steps:', 1)[0])
                self.assertIn('sha256sum -c', job)
                self.assertIn('check_goaldat.py', job)
                self.assertIn('T144-E015-snap-0003.sav', job)
                self.assertIn('T144-E015-snap-0120.sav', job)
                self.assertIn('e006-r0001-main.sav', job)
                self.assertIn('actions/upload-artifact@v4', job)
                self.assertIn('path: upload', job)
                self.assertIn("-name '*.png'", job)
                self.assertIn("-name '*.json'", job)
                self.assertIn(r'\.(exe|dat|hlp|hil|pif|bat|sav|gl|g2save)$', job)
                self.assertIn('if: always()', job)
                self.assertNotRegex(job, r'cp .*\.cache')

    def test_linux_has_a_window_manager_and_isolated_bus_and_runtime(self):
        job = self.job('ci.yml')
        for required in ('xvfb', 'xfwm4', 'dbus-run-session', 'XDG_RUNTIME_DIR',
                         '3840x2160x24', 'xvfb-run'):
            self.assertIn(required, job)

    def test_windows_display_fits_factor_two(self):
        job = self.job('windows.yml')
        self.assertIn('runs-on: windows-latest', job)
        self.assertIn('Set-DisplayResolution -Width 3840 -Height 2160 -Force', job)


class Receipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'source.py').write_text('unchanged source')
        (self.root / 'view.png').write_bytes(b'test raster')
        self.report = dict(passed=True, head='exact-head', qt_backend='xcb',
                           source_unchanged=True, core_save_unchanged=True,
                           source_sha256={'source.py': native.digest(self.root / 'source.py')},
                           cases=[dict(case=name, native_active=True, device_pixel_ratio=2,
                                       screenshot='view.png', screenshot_sha256=native.digest(self.root / 'view.png'))
                                  for name in ('team-info', 'selection', 'friendly')])

    def verify(self, report=None):
        native.verify(self.report if report is None else report, self.root, 2, 'exact-head', self.root)

    def test_valid_receipt_passes_for_each_native_backend(self):
        for backend in ('xcb', 'windows'):
            self.report['qt_backend'] = backend
            self.verify()

    def test_offscreen_focus_and_wrong_scale_are_rejected(self):
        for field, value in [('qt_backend', 'offscreen'), ('head', 'stale-head'),
                             ('core_save_unchanged', False), ('source_unchanged', False)]:
            report = copy.deepcopy(self.report)
            report[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.verify(report)
        for field, value in [('native_active', False), ('device_pixel_ratio', 1)]:
            report = copy.deepcopy(self.report)
            report['cases'][0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.verify(report)

    def test_missing_cases_and_changed_source_or_capture_are_rejected(self):
        report = copy.deepcopy(self.report)
        report['cases'].pop()
        with self.assertRaises(AssertionError):
            self.verify(report)
        for name in ('source.py', 'view.png'):
            path = self.root / name
            before = path.read_bytes()
            path.write_bytes(b'changed')
            with self.subTest(path=name), self.assertRaises(AssertionError):
                self.verify()
            path.write_bytes(before)


if __name__ == '__main__':
    unittest.main()
