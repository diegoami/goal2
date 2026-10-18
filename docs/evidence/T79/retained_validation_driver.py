#!/usr/bin/env python3
"""[designed: T79] Retained UI gates; source-mutating suites have no other readers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]

def hashes():
    paths=list((ROOT/'goal2').rglob('*.py'))+list((ROOT/'tools/desktop-ui').glob('*.py'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();initial=hashes()
    py=sys.executable;ui=ROOT/'tools/desktop-ui';template=ROOT/'.cache/e010-r0008-halftime.sav';data=ROOT/'.cache/GOAL.DAT'
    commands=[]
    for name in ('management','friendlies','pool','halftime'):
        commands.append(('prove-'+name,[py,str(ui/('prove-'+name+'.py'))]))
    for name in ('management','campaign-friendlies','worker','campaign-pool','campaign-halftime'):
        commands.append(('acceptance-'+name,[py,str(ui/'acceptance.py'),'--scenario',name,'--template',str(template),'--data',str(data),'--screenshot',str(out/(name+'.png'))]))
    base=[py,str(ui/'redesign.py'),'--template',str(template),'--data',str(data)]
    commands.append(('results-inputs',base+['--scenario','results','--evidence-dir',str(out/'results-inputs'),'--prepare-results-inputs']))
    for name in ('results','shell','overview','squad','pool'):
        for negative in (False,True):
            label=name+('-controls' if negative else '')
            command=base+['--scenario',name,'--evidence-dir',str(out/label)]
            if negative:command+=['--negative-controls']
            commands.append((label,command))
    commands += [('provenance',[py,'tools/check_provenance.py']),('links',[py,'tools/check_links.py']),('working-whitespace',['git','diff','--check']),('authored-whitespace',['git','diff','5c26616917d19a77a0e548a0baa2a3997112c477..HEAD','--check'])]
    report={'tag':'[designed: T79] Serial author acceptance','head':head,'initial_sources':initial,'commands':[],'result':'RUNNING'}
    for name,command in commands:
        prior={p for top in (ROOT/'docs/evidence/T80',ROOT/'docs/evidence/T83') for p in top.iterdir()}
        started=time.monotonic();print('START',name,flush=True)
        with (out/(name+'.log')).open('x') as log:
            run=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
        same=hashes()==initial
        row={'name':name,'command':command,'returncode':run.returncode,'seconds':time.monotonic()-started,'source_bytes_unchanged':same,'log_sha256':hashlib.sha256((out/(name+'.log')).read_bytes()).hexdigest()}
        report['commands'].append(row)
        for top in (ROOT/'docs/evidence/T80',ROOT/'docs/evidence/T83'):
            for path in top.iterdir():
                if path not in prior:
                    dest=out/'retained-artifacts'/top.name/path.name;dest.parent.mkdir(parents=True,exist_ok=True)
                    if path.is_dir():shutil.copytree(path,dest)
                    else:shutil.copy2(path,dest)
        if run.returncode or not same:
            report['result']='FAIL';(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            raise AssertionError(f'{name}: returncode={run.returncode}, source bytes unchanged={same}')
        print('PASS',name,round(row['seconds'],3),flush=True)
        (out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    report['result']='PASS';report['final_sources']=hashes()
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS all serial author gates',flush=True)

if __name__=='__main__':main()
