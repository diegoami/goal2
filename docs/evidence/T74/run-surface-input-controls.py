#!/usr/bin/env python3
"""[designed: T74] Verify diagnostic/input oracles with real Qt events."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('--evidence-dir',required=True)
parser.add_argument('--template',default='.cache/e010-r0008-halftime.sav')
parser.add_argument('--data',default='.cache/GOAL.DAT')
args=parser.parse_args()
out=Path(args.evidence_dir).resolve();out.mkdir(parents=True,exist_ok=False)
base=[sys.executable,str(ROOT/'tools/desktop-ui/redesign.py'),'--scenario','shell',
      '--template',args.template,'--data',args.data,'--single-scale']
expected={'wrong-focus':'synthetic input target did not acquire focus',
          'country-change':'surface inspection changed state/draft/preview/save/job ownership at controlled-country-change'}
receipt=[]
for name,oracle in expected.items():
    result=subprocess.run(base+['--evidence-dir',str(out/name),'--surface-input-control',name],
                          cwd=ROOT,capture_output=True,text=True,timeout=180)
    (out/(name+'.log')).write_text(result.stdout+result.stderr)
    assert result.returncode!=0 and 'AssertionError: '+oracle in result.stderr,result.stderr
    report=json.loads((out/name/'interaction.json').read_text())
    if name=='country-change':
        fields={change['field'] for change in report['surface_trace'][-1]['delta']}
        assert fields=={'draft','active_draft','preview_identity','encoded_preview'},fields
    receipt.append({'control':name,'expected':oracle,'returncode':result.returncode})
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS two controlled input failures; country change leaves save/job fields unchanged')
