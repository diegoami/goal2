"""[designed: T76] Independent checkpoint, caption and archived evidence audit."""
from pathlib import Path
import collections,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
evidence=ROOT/'docs/evidence/T76/windows';native=evidence/'native-03'
receipt=native/'host-receipt.json';expected='f8cf9a5c13def6300f0d82075eccdee55b0ba12f270d453b9d6ca44ad3c3b751'
original=Path('/home/diego/projects/goal2/.cache/kept/review-receipts/T76-windows-acceptance-1792347877077962399/receipt.json')
assert sha(receipt)==sha(original)==expected and receipt.read_bytes()==original.read_bytes()
r=json.loads(receipt.read_text());assert r['result']=='PASS' and r['checkpoint_head']=='b3e2c95d8c5e744782d43ece6c840a7bd0a595d9'
frozen=json.loads((evidence.parent/'source-freeze-03.json').read_text())['source_sha256'];assert r['sources']==frozen and len(frozen)==175
for name,h in frozen.items():
 assert sha(ROOT/name)==h
 assert hashlib.sha256(subprocess.check_output(['git','show',r['checkpoint_head']+':'+name],cwd=ROOT)).hexdigest()==h
assert r['protected_before']==r['protected_after'] and len(r['protected_before'])==4
runs=[]
for run in r['runs']:
 scale=run['scale'];p=native/run['report_path'];report=json.loads(p.read_text());assert sha(p)==run['report_sha256']
 log=native/('native-'+scale+'.log');assert sha(log)==run['log_sha256'];lines=log.read_text().splitlines();assert len(lines)==1 and lines[0].startswith('PASS squad:')
 assert report['result']=='PASS' and report['qpa']=='windows' and report['ratio']==int(scale) and report['requested_scale']==scale
 assert report['callback_exceptions']==[] and report['cleanup_retry_calls']>=2 and report['source_unchanged'] and report['clean_widgets']
 sizes=[(1440,900),(1050,780),(900,700)] if scale=='1' else [(900,640)]
 counts=collections.Counter((tuple(c['size']),c['button'],c['focused']) for c in report['footer_captions'])
 assert counts==collections.Counter({(size,button,focus):3 for size in sizes for button in ('confirm','discard') for focus in (False,True)})
 for c in report['footer_captions']:assert c['ratio']==int(scale) and c['font_advance']<=c['contents'][2] and c['font_height']<=c['contents'][3]
 for coverage in report['roster_coverage']:assert coverage['name_rows']==coverage['value_rows']==list(range(20))
 assert {tuple(c['size']) for c in report['roster_coverage']}==set(sizes)
 for coverage in report['reading_coverage']:
  intervals=coverage['intervals'];assert intervals[0][0]==0 and intervals[-1][1]==coverage['height']
  assert all(b[0]<=a[1]-40 for a,b in zip(intervals,intervals[1:]))
 for capture in report['captures']:assert sha(p.parent/capture['path'])==capture['sha256']
 assert len(report['captures'])==run['captures']
 runs.append({'scale':scale,'seconds':run['seconds'],'captures':run['captures'],'caption_records':len(report['footer_captions']),'qt':report['qt'],'platform':report['platform']})
for name,h in r['artifacts'].items():assert sha(native/name)==h
for name,h in json.loads((native/'inventory.json').read_text()).items():assert sha(native/name)==h
prior=[]
for attempt,anchor in [('native-01','cfb682bf444ee2a1ab920052e221df2206775f14c619da879a13e96403748182'),('native-02','7b90c2d6c56c9c65d99240f9bcc0027b3924107daf1cb74764918a0555de18b0')]:
 folder=evidence/attempt;assert sha(folder/'host-receipt.json')==anchor
 for name,h in json.loads((folder/'inventory.json').read_text()).items():assert sha(folder/name)==h
 assert not subprocess.check_output(['git','diff',r['checkpoint_head'],'--',str(folder.relative_to(ROOT))],cwd=ROOT)
 prior.append(attempt)
print(json.dumps({'result':'PASS','native_checkpoint':r['checkpoint_head'],'independent_original_sha256':expected,'source_files':len(frozen),'protected_unchanged':4,'runs':runs,'prior_inventory_unchanged':prior},indent=2))
