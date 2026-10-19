"""[designed: #254] Serial main-native negative controls in private immutable copies."""
from pathlib import Path
import json,subprocess,sys
here=Path(__file__).parent;head='61ceef67df574c1d74318f06148fb51c4de92280'
for mutation in('omit-delete-share','legacy-writer','bypass-reader'):
 command=[sys.executable,'-B',str(here/'native-probe-mutants.py'),'--head',head,'--probe','/home/diego/projects/goal2-work/fix254-native-status-sharing/tools/desktop-ui/native-status-sharing.py','--attempt','mutant-'+mutation+'01','--mutation',mutation]
 print('START',mutation,flush=True);run=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);print(run.stdout.decode(),flush=True);assert run.returncode==0
 receipt=max(here.glob('native-mutant-'+mutation+'01-*/receipt.json'),key=lambda p:p.stat().st_mtime);r=json.loads(receipt.read_text());assert r['probe_result']=='FAIL'and r['exit']!=0 and r['protected_unchanged']
 report=json.loads((Path(r['directory'])/'observations/report.json').read_text())
 expected='production read factory was not visited'if mutation=='bypass-reader'else'native production writer could not replace status'
 assert expected in report['failure'],report
 print('PASS intended rejection',mutation,flush=True)
print('PASS all three native controls; task source unchanged',flush=True)
