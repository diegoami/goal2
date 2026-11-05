"""[designed: T148] Run T144's native probe in a fresh Qt process and verify its receipt.

The two scale factors run separately: Qt reads its scale environment at startup.
Only the probe's rebuilt widgets are captured; original fixtures remain in .cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(report, output, factor, head, root=ROOT):
    """Reject an offscreen, unfocused, wrong-scale or stale native receipt."""
    assert report['passed'] is True
    assert report['head'] == head, 'receipt is from another commit'
    assert report['qt_backend'] in ('xcb', 'windows'), 'not a native backend'
    assert report['source_unchanged'] is True
    assert report['core_save_unchanged'] is True
    assert report['source_sha256'], 'missing source hashes'
    for name, expected in report['source_sha256'].items():
        assert digest(root / name) == expected, f'source changed: {name}'
    assert {case['case'] for case in report['cases']} == {'team-info', 'selection', 'friendly'}
    assert len(report['cases']) == 3
    for case in report['cases']:
        assert case['native_active'] is True, f"no focus: {case['case']}"
        assert abs(case['device_pixel_ratio'] - factor) < .01, 'wrong measured Qt scale'
        name = case['screenshot']
        assert Path(name).name == name and name.endswith('.png'), 'unexpected screenshot path'
        assert digest(output / name) == case['screenshot_sha256'], 'screenshot changed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factor', required=True, type=int, choices=(1, 2))
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    backend = 'windows' if sys.platform == 'win32' else 'xcb'
    assert os.environ.get('QT_QPA_PLATFORM') == backend, f'expected native {backend} backend'
    environment = dict(os.environ, QT_SCALE_FACTOR=str(args.factor))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    subprocess.run([sys.executable, str(ROOT / 'measurements/T144/native_probe.py'),
                    '--out', str(args.out)], cwd=ROOT, env=environment, check=True)
    path = args.out / 'receipt.json'
    report = json.loads(path.read_text())
    report.update(requested_qt_scale_factor=args.factor, native_ci_verified=False)
    path.write_text(json.dumps(report, indent=2) + '\n')
    verify(report, args.out, args.factor, head)
    report['source_sha256']['measurements/T148/run_native.py'] = digest(Path(__file__))
    report['native_ci_verified'] = True
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS native {backend}, factor {args.factor}, head {head}', flush=True)


if __name__ == '__main__':
    main()
