"""[designed: T170b] Repeat bounded controls on immutable private original inputs.

Run with --inputs the private manifest described in README.md. Raw inputs never
enter this producer's output. This is an actual-dispatch/observation proof, not
an independent original comparison or a whole season/match proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from goal2.tests import pypy_engine


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    inputs=json.loads(args.inputs.read_text());rows=[]
    for item in inputs['cases']:
        raw=Path(item['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        row=pypy_engine.call('goal2.tests.test_season_session_t170b:actual_boundaries',raw,
                             waiting=item['waiting_key'],expected=item['expected'])
        assert row['status']==item['expected']
        rows.append({'case':item['case'],'lineage':item['lineage'],**row})
    paths=['goal2/game/season.py','goal2/tests/test_season_session_t170b.py',
           'tools/watched-kit-hashes.json','measurements/T170b/prove.py']
    paths+=['goal2/engine/original_match/'+p for p in ('route.py','match.py','screens.py','image.py','port/engine.py')]
    result={'schema':'t170b-boundaries/1','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'scope':'actual accepted sealed PyPy dispatcher vs session; original-built private inputs, no full match/season or independent original comparison',
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'inputs_manifest_sha256':hashlib.sha256(args.inputs.read_bytes()).hexdigest(),'cases':rows}
    with args.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print('T170B_BOUNDARIES '+json.dumps({'cases':len(rows),'statuses':[r['status'] for r in rows],'passed':True}),flush=True)

if __name__=='__main__':main()
