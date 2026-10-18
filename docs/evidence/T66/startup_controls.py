#!/usr/bin/env python3
"""[designed: T66] Scoped startup cleanup/save assertion controls; source restored in finally."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]


def main():
    target=Path(sys.argv[1]);target.mkdir(parents=True,exist_ok=False)
    path=ROOT/'goal2/desktop/watched.py';saved=path.read_bytes();source=saved.decode()
    cases=[('automatic-cleanup','            self.close_viewer()\n            if isinstance(exc,','            pass\n            if isinstance(exc,'),
           ('stream-release','                    cleanup.callback(handle.close)','                    pass'),
           ('saved-bytes','        except Exception as exc:\n            self.close_viewer()',
            "        except Exception as exc:\n            self.model.save_path.write_bytes(b'control-corrupted-save')\n            self.close_viewer()")]
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',QT_QPA_PLATFORM='offscreen',TMPDIR=str(ROOT/'.cache/tmp'))
    receipts=[]
    for name,before,after in cases:
        if source.count(before)!=1:raise ValueError(f'{name}: source anchor differs')
        try:
            path.write_text(source.replace(before,after))
            result=subprocess.run([sys.executable,'-B','-m','unittest',
                'goal2.tests.test_pygame_match_view.PresentationTests.test_partial_startup_allocation_cleanup_and_retry_preserve_save','-v'],
                cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
            output=result.stdout.decode(errors='replace');(target/f'{name}.log').write_text(output)
            intended=result.returncode!=0 and 'FAIL:' in output and '\nERROR:' not in output and 'ModuleNotFoundError' not in output
            receipts.append({'name':name,'returncode':result.returncode,'intended_assertion_failure':intended,
                             'source_sha256':hashlib.sha256(saved).hexdigest()})
            if not intended:raise AssertionError(f'{name} did not produce an intended assertion failure')
        finally:
            path.write_bytes(saved)
            assert path.read_bytes()==saved
    (target/'controls.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print(json.dumps(receipts,indent=2));print('PASS all3 scoped startup assertion controls; source bytes restored')


if __name__=='__main__':main()
