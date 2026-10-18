#!/usr/bin/env python3
"""[designed: T80] Saved-byte control for the actual Qt competitive Play dispatch.
Run exclusively, with no other source readers; restore exact source even on failure.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'goal2/desktop/window.py';saved=source.read_bytes()
    old='self.competitive.start(record_draws=True)'
    assert saved.decode().count(old)==1
    folder=ROOT/'docs/evidence/T80'/f'qt-route-control-{time.time_ns()}'
    folder.mkdir()
    started=time.monotonic()
    try:
        source.write_text(saved.decode().replace(old,'None'))
        mutated=source.read_bytes()
        result=subprocess.run([sys.executable,'-B','tools/desktop-ui/competitive_play.py'],cwd=ROOT,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM='offscreen'),
            capture_output=True,text=True,timeout=30)
    finally:
        source.write_bytes(saved)
    output=result.stdout+result.stderr
    (folder/'dispatch-deleted.log').write_text(output)
    expected='AssertionError: Play did not start the original competitive child'
    accepted=result.returncode==1 and expected in output and all(value not in output for value in
        ('AttributeError','ModuleNotFoundError','ExtraTimeNotModelled'))
    receipt=dict(mode='saved-byte actual Qt route deletion',accepted=accepted,
        expected_assertion=expected,returncode=result.returncode,seconds=round(time.monotonic()-started,3),
        source='goal2/desktop/window.py',original_sha256=hashlib.sha256(saved).hexdigest(),
        mutated_sha256=hashlib.sha256(mutated).hexdigest(),restored=source.read_bytes()==saved)
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Qt competitive dispatch control: '+('PASS' if accepted else 'FAIL'))
    print(folder.relative_to(ROOT))
    if not accepted:print(output)
    return 0 if accepted else 1

if __name__=='__main__':sys.exit(main())
