"""[designed: #254] Retain native regression receipts after owned writers exit."""
from pathlib import Path
import argparse,hashlib,json,shutil
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path('/home/diego/projects/goal2-work/fix254-native-status-sharing');receipt=Path(a.receipt);r=json.loads(receipt.read_text());folder=Path(r['directory']);out=root/a.output
assert out.resolve().is_relative_to((root/'docs/evidence/fix254').resolve())and not out.exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert r['result']=='EXECUTED'and r['protected_unchanged']and r['protected_before']==r['protected_after']
for n,h in r['sources'].items():assert sha(folder/n)==sha(root/n)==h
assert sha(folder/'tools/desktop-ui/native-status-sharing.py')==r['probe_sha256'];assert sha(folder/'observations/report.json')==r['report_sha256'];assert sha(folder/'run-probe.py')==r['wrapper_sha256'];assert sha(receipt.parent/'native.log')==r['log_sha256']
for n,h in r['protected_after'].items():assert sha(n)==h
out.mkdir(parents=True)
def copy(source,name):
 raw=source.read_bytes();target=out/name
 if source.suffix in('.json','.log'):
  (out/(name+'.raw-envelope.json')).write_text(json.dumps({'encoding':'utf-8','sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()},indent=2)+'\n');target.write_text(raw.decode().replace('\r\n','\n').rstrip('\n')+'\n'if raw else '')
 else:target.write_bytes(raw)
copy(receipt,'host-receipt.json');copy(folder/'observations/report.json','report.json');copy(receipt.parent/'native.log','native.log');copy(folder/'run-probe.py','run-probe.py');copy(folder/'tools/desktop-ui/native-status-sharing.py','native-status-sharing.py')
copy(Path(__file__).with_name('native-probe-launcher.py'),'main-native-launcher.py')
(out/'collection.json').write_text(json.dumps({'claim':'[confirmed: independent post-run hashes] Native regression receipt collection, not full match/UI acceptance','original_receipt_sha256':sha(receipt),'source_files':len(r['sources']),'probe_sha256':r['probe_sha256'],'protected_files':len(r['protected_after']),'native_exit':r['exit'],'probe_result':r['probe_result']},indent=2)+'\n')
(out/'inventory.json').write_text(json.dumps({q.name:sha(q)for q in sorted(out.iterdir())if q.is_file()},indent=2)+'\n');print(out)
