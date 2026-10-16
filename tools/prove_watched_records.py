#!/usr/bin/env python3
"""[designed: T62] Black-box strict-checker negatives on TEMPORARY kit copies, never vendor edits."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ("missing original player-update tail",'self._call(PLAYER_UPDATE, PLAYER_UPDATE_RETURN)','self._finish()',
     'original post-match state differs'),
    ("false returned seed",'"seed_after": m.rd(SEED)','"seed_after": m.rd(SEED) ^ 1',
     'original post-match state differs'),
    ("false draw count",'"draws": len(draws)','"draws": len(draws) + 1',
     'kit differs from strict original'),
]
CHILD=r'''
import runpy,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);sys.path.insert(1,sys.argv[2])
import original_match as candidate
import goal2.engine
assert Path(candidate.__file__).is_relative_to(Path(sys.argv[1]))
sys.modules["goal2.engine.original_match"]=candidate
goal2.engine.original_match=candidate
for key,value in list(sys.modules.items()):
 if key.startswith("original_match."):sys.modules["goal2.engine."+key]=value
root=Path(sys.argv[2]);sys.path.insert(0,str(root/"tools"))
file=root/"tools/check_watched_records.py"
sys.argv=[str(file),"--seeds","1"]
runpy.run_path(str(file),run_name="__main__")
'''
for case in [None]+MUTATIONS:
    with tempfile.TemporaryDirectory() as folder:
        package=Path(folder)/"original_match"
        shutil.copytree(ROOT/"goal2/engine/original_match",package,ignore=shutil.ignore_patterns("__pycache__"))
        if case:
            name,old,new,want=case
            path=package/"match.py";text=path.read_text()
            if text.count(old)!=1:raise AssertionError(f"mutation site changed: {name}")
            path.write_text(text.replace(old,new))
        result=subprocess.run([sys.executable,"-B","-c",CHILD,folder,str(ROOT)],cwd=ROOT,
                              capture_output=True,text=True,timeout=180)
        output=result.stdout+result.stderr
        if case is None:
            if result.returncode!=0:raise AssertionError("unmodified checker baseline failed\n"+output)
            print("PASS unmodified strict-checker baseline",flush=True)
        else:
            if result.returncode==0 or "ValueError:" not in output or want not in output:
                raise AssertionError(f"checker failed to reject {name} for the expected reason\n{output}")
            print("PASS checker negative: "+name,flush=True)
print("PASS3 strict-checker negatives; vendored files untouched")
