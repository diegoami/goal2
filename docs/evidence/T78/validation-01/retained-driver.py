import os,subprocess,sys,json
from pathlib import Path
out=Path('docs/evidence/T78/validation-01');p=sys.executable
common=['--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
commands=[('competitive',[p,'tools/desktop-ui/competitive.py'])]+[(n,[p,'tools/desktop-ui/'+n+'.py']) for n in ('prove-management','prove-friendlies','prove-pool','prove-halftime')]+[(n,[p,'tools/desktop-ui/acceptance.py','--scenario',n]+common) for n in ('campaign-friendlies','worker','campaign-halftime','management','campaign-pool')]+[('country-selection',[p,'tools/desktop-ui/country-selection.py']+common),('standings',[p,'tools/desktop-ui/standings.py']+common),('overview',[p,'tools/desktop-ui/redesign.py','--scenario','overview']+common+['--evidence-dir','docs/evidence/T78/overview']),('overview-negative',[p,'tools/desktop-ui/redesign.py','--scenario','overview']+common+['--evidence-dir','docs/evidence/T78/overview-negative','--negative-controls']),('shell',[p,'tools/desktop-ui/redesign.py','--scenario','shell']+common+['--evidence-dir','docs/evidence/T78/shell'])]
receipt=[]
for name,cmd in commands:
 print('START',name,flush=True)
 with (out/(name+'.log')).open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 receipt.append({'name':name,'command':cmd,'returncode':r.returncode});(out/'retained.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('END',name,r.returncode,flush=True)
 if r.returncode:sys.exit(r.returncode)
