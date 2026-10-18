#!/usr/bin/env python3
"""[designed: T80] Bounded omission control for the retained standings Qt teardown."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'tools/desktop-ui/standings.py';saved=source.read_bytes()
    assert saved.decode().count('window.deleteLater()')==1
    folder=ROOT/'docs/evidence/T80'/f'standings-control-{time.time_ns()}';folder.mkdir()
    # [designed] Exit immediately after the intended assertion so unrelated interpreter
    # teardown cannot obscure the observed lifecycle failure in this negative control.
    code="""import os,runpy,sys,traceback
sys.argv=['tools/desktop-ui/standings.py','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
try:runpy.run_path(sys.argv[0],run_name='__main__')
except AssertionError:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
"""
    try:
        source.write_text(saved.decode().replace('window.deleteLater()','None'))
        changed=source.read_bytes()
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,capture_output=True,text=True,
            timeout=30,env=dict(os.environ,QT_QPA_PLATFORM='offscreen',PYTHONDONTWRITEBYTECODE='1'))
    finally:source.write_bytes(saved)
    output=result.stdout+result.stderr;(folder/'omitted-delete.log').write_text(output)
    expected='AssertionError: standings management window was not destroyed'
    accepted=result.returncode==1 and expected in output and 'ModuleNotFoundError' not in output
    receipt=dict(accepted=accepted,returncode=result.returncode,expected_assertion=expected,
        source='tools/desktop-ui/standings.py',original_sha256=hashlib.sha256(saved).hexdigest(),
        mutated_sha256=hashlib.sha256(changed).hexdigest(),restored=source.read_bytes()==saved)
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Standings teardown omission control: '+('PASS' if accepted else 'FAIL'));print(folder.relative_to(ROOT))
    if not accepted:print(output)
    return 0 if accepted else 1
if __name__=='__main__':sys.exit(main())
