#!/usr/bin/env python3
"""[designed: T51a] Assertion-based competitive controls on disposable package copies."""
from pathlib import Path
import hashlib
import json
import time
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ("missing winner", ', "winner": fx[3]', ''),
    ("extra-time detection suppressed", '"extra_time": st.get("score_90") is not None', '"extra_time": False'),
    ("wrong shootout score", 'final[t] - st["score_120"][t] for t in (0, 1)',
     'final[t] - st["score_120"][t] + 1 for t in (0, 1)'),
]
CHILD = r'''
import pathlib,sys,unittest
sys.path.insert(0,sys.argv[1]);sys.path.insert(1,sys.argv[2])
import original_match as candidate
assert pathlib.Path(candidate.__file__).is_relative_to(pathlib.Path(sys.argv[1]))
import goal2.engine
goal2.engine.original_match=candidate
for name,module in list(sys.modules.items()):
 if name=="original_match" or name.startswith("original_match."):
  sys.modules["goal2.engine."+name]=module
suite=unittest.defaultTestLoader.loadTestsFromName(
 "goal2.tests.test_watched_competitive_runtime.ConsumerAcceptanceTests.test_result_shape_matches_independent_guest_execution")
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
'''


def main():
    folder_log=ROOT/".cache"/("watched-competitive-proofs-"+str(time.time_ns()))
    folder_log.mkdir();rows=[]
    for number,mutation in enumerate([None] + MUTATIONS):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / "original_match"
            shutil.copytree(ROOT / "goal2/engine/original_match", package,
                            ignore=shutil.ignore_patterns("__pycache__"))
            if mutation:
                name, old, new = mutation
                path = package / "match.py"
                saved = path.read_text()
                if saved.count(old) != 1:raise AssertionError(f"mutation site changed: {name}")
                path.write_text(saved.replace(old,new))
            run = subprocess.run([sys.executable,"-B","-c",CHILD,folder,str(ROOT)],
                                 cwd=ROOT,capture_output=True,text=True,timeout=180)
            output = run.stdout + run.stderr
            log=folder_log/(str(number)+".log");log.write_text(output)
            rows.append({"name":mutation[0] if mutation else "unmodified baseline",
                         "exit_code":run.returncode,"log":str(log.relative_to(ROOT)),
                         "log_sha256":hashlib.sha256(log.read_bytes()).hexdigest(),
                         "assertion_failure":"FAIL:" in output,"error":"ERROR:" in output})
            if mutation is None:
                if run.returncode:raise AssertionError("baseline failed\n"+output)
                print("PASS unmodified competitive control",flush=True)
            else:
                if run.returncode == 0 or "FAIL:" not in output or "ERROR:" in output:
                    raise AssertionError(f"expected assertion failure for {name}\n{output}")
                print("PASS assertion kills "+name,flush=True)
    (folder_log/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
    print("PASS3 competitive mutants; vendored bytes untouched; "+str(folder_log))


if __name__ == "__main__":
    main()
