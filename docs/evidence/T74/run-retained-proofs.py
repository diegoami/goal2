#!/usr/bin/env python3
"""[designed: T74] Reproduce retained proofs with approved environment/site adapters.
Run exclusively: these unchanged proof oracles temporarily mutate production source.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]

def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'goal2').rglob('*.py')}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence-dir',required=True);args=parser.parse_args()
    out=Path(args.evidence_dir);out.mkdir(parents=True,exist_ok=False);receipts=[]
    for name in ('prove-management.py','prove-friendlies.py','prove-pool.py','prove-halftime.py'):
        path=ROOT/'tools/desktop-ui'/name;original=path.read_bytes();text=original.decode()
        if name=='prove-friendlies.py':
            old="if self.busy:raise ValueError('A friendly is already running')"
            current="if self.busy or getattr(self.model,'match_pending',False):raise ValueError('A match is already running')"
            assert old in text and current in (ROOT/'goal2/desktop/jobs.py').read_text(),'approved guard adapter site changed'
            text=text.replace(old,current).replace("if False:raise ValueError('A friendly is already running')","if False:raise ValueError('A match is already running')")
        text=text.replace("'/tmp/T69-desktop-venv/bin/python'",'sys.executable')
        before=hashes()
        # [designed] __file__ keeps the original root calculation; source scripts stay untouched.
        code='import sys\nsys.path.insert(0,'+repr(str(path.parent))+')\n'
        code+='exec(compile('+repr(text)+','+repr(str(path))+',"exec"),{"__name__":"__main__","__file__":'+repr(str(path))+'})\n'
        with tempfile.TemporaryDirectory(prefix='T74-proof-') as folder:
            launcher=Path(folder)/'proof.py';launcher.write_text(code)
            with (out/(name+'.log')).open('w') as log:
                result=subprocess.run([sys.executable,'-B',str(launcher)],cwd=ROOT,
                    env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT)
        restored=before==hashes()
        receipts.append({'proof':name,'original_sha256':hashlib.sha256(original).hexdigest(),
                         'adapted_source_sha256':hashlib.sha256(text.encode()).hexdigest(),
                         'interpreter':sys.executable,'returncode':result.returncode,'source_restored':restored,
                         'adapter':'interpreter path; friendlies bypass same accepted expanded busy/match_pending guard; all assertion oracles unchanged'})
        (out/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
        assert restored,'retained proof failed exact source restoration'
        assert result.returncode==0,f'{name} failed; inspect retained log'
        print('PASS retained proof:',name,flush=True)
if __name__=='__main__':main()
