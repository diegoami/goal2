"""[designed: T78] Serial final controls and two fresh-scale native processes."""
import json,subprocess,sys
from pathlib import Path
base=[sys.executable,'tools/desktop-ui/redesign.py','--scenario','results','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
receipt=[]
for name,extra in [('results-final-negative',['--evidence-dir','docs/evidence/T78/results-final-negative','--negative-controls']),('results-final-positive',['--evidence-dir','docs/evidence/T78/linux-final'])]:
 command=base+extra
 with Path('docs/evidence/T78/validation-01/'+name+'.log').open('x') as log:
  result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 receipt.append({'command':command,'returncode':result.returncode})
 Path('docs/evidence/T78/validation-01/final-linux-commands.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(name,result.returncode,flush=True)
 if result.returncode:sys.exit(result.returncode)
