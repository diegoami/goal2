"""[designed: T76/T78] Independently anchored native artifact/source identity audit."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path.cwd();config=json.loads((ROOT/'.cache/main-native-proof-config.json').read_text());task=config['task'];assert task in ('T76','T78')
evidence=ROOT/config['evidence'];original=ROOT/config['original_receipt'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
tracked=evidence/'host-receipt.json';assert tracked.read_bytes()==original.read_bytes(),'tracked receipt differs from independently retained main original';r=json.loads(original.read_text());assert r['result']=='PASS'and r['protected_before']==r['protected_after']and len(r['protected_before'])==4
for name,h in r['sources'].items():assert sha(ROOT/name)==h,('native/current product or scenario source mismatch',name)
assert len(r['runs'])==2 and [x['actual_ratio']for x in r['runs']]==[1.0,2.0]
reports=[]
for run in r['runs']:
 scale=run['scale'];path=evidence/run['report_path'];assert sha(path)==run['report_sha256'];assert sha(evidence/('native-'+scale+'.log'))==run['log_sha256'];assert sha(evidence/('native-'+scale+'.py'))==run['wrapper_sha256']
 log=(evidence/('native-'+scale+'.log')).read_text(errors='replace');assert 'Traceback (most recent call last)'not in log and 'Error calling Python override'not in log,('uncaught native exception',scale)
 if task=='T78':
  runtime=evidence/('native-runtime-'+scale+'.json');assert sha(runtime)==run['native_runtime_report_sha256'];native=json.loads(runtime.read_text());assert native['version']==run['native_runtime_version']==r['native_dependencies']['version']=='2.1.4';assert '.goal2-validation' in native['file'] and 'python-libs' in native['file']
 report=json.loads(path.read_text());assert report['result']=='PASS'and report['qpa']=='windows'and report['ratio']==int(scale)and report['requested_scale']==scale and'Windows'in report['platform'];assert report['qt']==run['qt']and report['python']==run['python']
 helper='tools/desktop-ui/'+('squad_scenario.py'if task=='T76'else'results_scenario.py');assert report['scenario_sha256']==r['sources'][helper]
 assert report['resources']=={'template':r['resources']['e010-r0008-halftime.sav'],'data':r['resources']['GOAL.DAT']}
 for name,h in report['sources'].items():assert r['sources'][name.replace('\\','/')]==h
 for capture in report['captures']:assert sha(path.parent/capture.get('path',capture.get('file')))==capture['sha256']
 assert len(report['captures'])==run['captures']and report['captures'];reports.append({'scale':scale,'captures':len(report['captures']),'platform':report['platform'],'qt':report['qt']})
for name,h in r['artifacts'].items():assert sha(evidence/name)==h,('artifact differs',name)
inventory=json.loads((evidence/'inventory.json').read_text())
for name,h in inventory.items():assert sha(evidence/name)==h,('inventory differs',name)
print(json.dumps({'result':'PASS','task':task,'native_checkpoint':r['checkpoint_head'],'current_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_files':len(r['sources']),'reports':reports,'protected_unchanged':len(r['protected_before']),'inventory_files':len(inventory),'independent_main_receipt_sha256':sha(original)}))
