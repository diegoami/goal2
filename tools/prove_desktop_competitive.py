#!/usr/bin/env python3
"""[designed: T80] Saved-byte controls for protocol and publication boundaries.
Run only after other readers finish. Original bytes remain in ignored local caches.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PREFIX='goal2.tests.test_desktop_competitive_jobs.CompetitiveJobsTests.'
CONTROLS=(
    ('duplicate-completion','goal2/game/watched_jobs.py',
     ' or self._complete is not None:', ':',
     'test_duplicate_completion_packet_is_rejected'),
    ('stale-owner','goal2/game/watched_jobs.py',
     'if (self.owner.state is not self._original or self.owner.state != self._snapshot\n                    or self.owner.template_bytes != self._template):',
     'if False:', 'test_changed_owner_is_rejected_before_any_publication'),
    ('original-tail','goal2/game/watched_publication.py',
     "not kinds or kinds[-1]!='end' or kinds.count('end')!=1 or kinds.count('full_time')!=1",
     "not kinds or kinds.count('full_time')!=1", 'test_missing_original_end_tail_is_rejected'),
)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    report=ROOT/'docs/evidence/T80'/f'controls-{time.time_ns()}'
    report.mkdir(parents=True)
    receipts=[]
    for name,file,old,new,test in CONTROLS:
        path=ROOT/file;saved=path.read_bytes();original=saved.decode()
        if original.count(old)!=1:raise RuntimeError(f'{name}: mutation anchor changed')
        started=time.monotonic()
        try:
            if not args.baseline:path.write_text(original.replace(old,new))
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
            # [designed] Changed source size invalidates prior bytecode; -B keeps the
            # mutation from writing a bytecode artifact for later readers.
            result=subprocess.run([sys.executable,'-B','-m','unittest',PREFIX+test,'-v'],cwd=ROOT,
                                  env=env,capture_output=True,text=True,timeout=180)
        finally:path.write_bytes(saved)
        output=result.stdout+result.stderr
        (report/f'{name}.log').write_text(output)
        intended='AssertionError: ValueError not raised' in output
        if args.baseline:
            valid=result.returncode==0 and '\nOK\n' in output
        else:
            valid=result.returncode==1 and intended and 'ERROR:' not in output
        receipts.append(dict(control=name,file=file,test=PREFIX+test,baseline=args.baseline,
                             returncode=result.returncode,intended_assertion=intended,accepted=valid,
                             seconds=round(time.monotonic()-started,3),
                             original_sha256=hashlib.sha256(saved).hexdigest(),
                             restored=path.read_bytes()==saved))
        print(f'{name}: '+('PASS' if valid else 'FAIL'),flush=True)
        if not valid:
            print(output)
            break
    (report/'receipt.json').write_text(json.dumps(dict(platform=platform.platform(),python=sys.version,
        mode='unmodified baseline' if args.baseline else 'saved-byte negative controls',controls=receipts),indent=2)+'\n')
    print(report.relative_to(ROOT))
    return 0 if len(receipts)==len(CONTROLS) and all(r['accepted'] for r in receipts) else 1


if __name__=='__main__':sys.exit(main())
