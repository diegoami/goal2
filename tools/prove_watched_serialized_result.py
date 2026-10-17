#!/usr/bin/env python3
"""[designed: T51a] Full serialized-result comparison detects changed new values.
Changes only a test's returned result after original execution, never vendor bytes.
Run sequentially after other suites; saved source bytes are restored in finally.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[('winner','result["winner"]=(result["winner"]+1)%3'),
           ('shootout','result["shootout"]={"score":[1,0],"kicks":[]}'),
           ('player energy','result["players"][0]["energy"][1]^=1')]


def main():
    path=ROOT/'goal2/tests/test_watched_runtime.py';folder=ROOT/'.cache'/('watched-serialized-result-proofs-'+str(time.time_ns()));folder.mkdir();rows=[]
    for number,(name,damage) in enumerate(MUTATIONS):
        saved=path.read_bytes()
        try:
            text=saved.decode();old='            result = match.result()'
            if text.count(old)!=1:raise AssertionError('result mutation site changed')
            path.write_text(text.replace(old,old+'\n            if resume:'+damage))
            run=subprocess.run([sys.executable,'-B','-m','unittest',
                'goal2.tests.test_watched_runtime.RuntimeTests.test_disallowed_goal_save_preserves_complete_match_and_closes_coverage','-v'],
                cwd=ROOT,capture_output=True,text=True,timeout=120)
            output=run.stdout+run.stderr;log=folder/(str(number)+'.log');log.write_text(output)
            if run.returncode==0 or 'FAIL:' not in output or 'ERROR:' in output or 'self.assertEqual(straight,resumed)' not in output:
                raise AssertionError('full result value damage not caught by assertion: '+name+'\n'+output)
            rows.append({'name':name,'assertion_killed':True,'log':str(log.relative_to(ROOT)),
                         'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
            print('PASS full serialized result detects '+name,flush=True)
        finally:path.write_bytes(saved)
    (folder/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('PASS3 full-result value controls; saved bytes restored; '+str(folder),flush=True)


if __name__=='__main__':main()
