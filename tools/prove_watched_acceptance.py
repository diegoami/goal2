#!/usr/bin/env python3
"""[designed: T62] Acceptance-tool negatives; no vendored file is edited."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ("vendor byte guard","tools/watched_evidence.py",'(ROOT / rel).read_bytes() != raw','False',
     'test_changed_vendor_bytes_and_added_files_are_rejected'),
    ("vendor file set","tools/watched_evidence.py",'if actual != set(manifest["files"]):','if False:',
     'test_changed_vendor_bytes_and_added_files_are_rejected'),
    ("entry evidence failure","tools/check_watched_upstream.py",'if (len(faithful) != 1','if False and (len(faithful) != 1',
     'test_entry_probe_false_or_incomplete_evidence_is_rejected'),
]
for name,file,old,new,test in MUTATIONS:
    path=ROOT/file;saved=path.read_bytes()
    try:
        text=saved.decode()
        if text.count(old)!=1:raise AssertionError(f"mutation site changed: {name}")
        path.write_text(text.replace(old,new))
        result=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_watched_runtime.RuntimeTests.'+test],
                              cwd=ROOT,capture_output=True,text=True)
        output=result.stdout+result.stderr
        if result.returncode==0 or 'FAIL:' not in output or 'ERROR:' in output:
            raise AssertionError(f"mutation did not fail targeted assertion: {name}\n{output}")
        print('PASS mutation: '+name,flush=True)
    finally:path.write_bytes(saved)
print('PASS3 acceptance-tool mutations; saved bytes restored')
