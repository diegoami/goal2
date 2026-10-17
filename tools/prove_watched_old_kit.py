#!/usr/bin/env python3
"""[designed: T51a] Reproduce all eight accepted competitive regressions on the old exact kit.
Refuse skips, missing dependencies and unrelated failures; never replace consumer vendor bytes.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from watched_evidence import ROOT,SOURCE,archaeology,stage

OLD='3656a2d26e0f57a410d648edeaa6cd9eb7d1f607'
CHILD=r'''
import importlib.util,pathlib,sys,unittest
sys.path.insert(0,sys.argv[1])
import original_match
assert pathlib.Path(original_match.__file__).is_relative_to(pathlib.Path(sys.argv[1]))
spec=importlib.util.spec_from_file_location('accepted_tests',sys.argv[2]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
suite=unittest.defaultTestLoader.loadTestsFromTestCase(m.CompetitiveTests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
expected=("ValueError: only friendlies (kind 1) are supported",
          "TypeError: Match.__init__() got an unexpected keyword argument 'substitutions'")
assert result.testsRun==8 and len(result.errors)==8 and not result.failures and not result.skipped
assert all(trace.strip().endswith(expected) for test,trace in result.errors),result.errors
print('PASS8 old-kit capability failures: no skips, missing resources or unrelated failures')
'''


def main():
    accepted=stage();folder=ROOT/'.cache'/('watched-old-kit-proof-'+str(time.time_ns()));package=folder/'original_match';package.mkdir(parents=True)
    hashes={}
    for file in sorted((ROOT/'goal2/engine/original_match').iterdir()):
        if not file.is_file():continue
        raw=subprocess.check_output(['git','show',OLD+':runtime/original_match/'+file.name],cwd=archaeology())
        (package/file.name).write_bytes(raw);hashes[file.name]=hashlib.sha256(raw).hexdigest()
    log=folder/'result.log';start=time.monotonic()
    with log.open('x') as out:
        run=subprocess.run([sys.executable,'-B','-c',CHILD,str(folder),str(accepted/'tests/test_original_match.py')],stdout=out,stderr=subprocess.STDOUT)
    row={'source':OLD,'test_source':SOURCE,'old_vendor':hashes,'tests':8,'expected_capability_errors':8,
         'exit_code':run.returncode,'wall_s':round(time.monotonic()-start,3),'log':str(log.relative_to(ROOT)),
         'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
    (folder/'summary.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row,indent=2))
    raise SystemExit(run.returncode)


if __name__=='__main__':main()
