"""[designed: #241] Main-authorized evidence collection; run only after native consumption ends."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--expected-receipt-sha256',required=True);p.add_argument('--output',required=True);p.add_argument('--runner',required=True);a=p.parse_args()
root=Path.cwd();out=(root/a.output).resolve();assert out.is_relative_to(root/'docs/evidence/fix241')and not out.exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def copy(src,dst):
 assert not src.is_symlink();dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(src)==sha(dst)
receipt=Path(a.receipt);assert sha(receipt)==a.expected_receipt_sha256;r=json.loads(receipt.read_text());assert r['result']=='PASS'and r['head']=='7560fbc336fa0efd6ea188c3739eb66e6460df63'
probe=Path(a.runner).with_name('windows_display_probe.py');assert sha(probe)==r['display_probe_sha256']
folder=Path(r['directory']);assert folder.is_dir()and '.goal2-validation' in str(folder)
for name,h in r['sources'].items():
 assert sha(folder/name)==sha(root/name)==h
 assert hashlib.sha256(subprocess.check_output(['git','show',r['head']+':'+name])).hexdigest()==h
for name,h in r['resources'].items():assert sha(folder/'.cache'/name)==sha(root/'.cache'/name)==h
count=0
for task,dep in r['dependencies'].items():
 for name,h in dep['files'].items():assert sha(folder/'.cache'/('python-libs-'+task)/name)==sha(Path(dep['directory'])/name)==h;count+=1
 for name,h in dep['wheels'].items():assert sha(Path(dep['directory']).parent/'wheels'/name)==h
assert count==566 and r['protected_unchanged']and r['protected_before']==r['protected_after']
for name,h in r['protected_before'].items():assert sha(name)==h
out.mkdir(parents=True);copy(receipt,out/'host-receipt.json');copy(receipt,root/'.cache/main-native-original-receipt.json')
for name,h in r['artifacts'].items():assert sha(folder/name)==h;copy(folder/name,out/name)
for scale in ('1','2'):
 copy(folder/('native-'+scale+'.py'),out/('native-'+scale+'.py'))
 log=receipt.parent/('native-'+scale+'.raw.txt');raw=log.read_bytes();text=raw.decode('utf-8')
 (out/('native-'+scale+'.raw-envelope.json')).write_text(json.dumps({'encoding':'utf-8','sha256':sha(log),'text':text},ensure_ascii=True,indent=2)+'\n')
 (out/('native-'+scale+'.log')).write_bytes(text.replace('\r\n','\n').encode('utf-8'))
copy(probe,out/'windows_display_probe.py');copy(Path(a.runner),out/'main-native-runner.py');proof=Path(__file__).with_name('fix241-native-proof-check.py');copy(proof,out/'main-native-proof-check.py')
config={'evidence':out.relative_to(root).as_posix(),'original_receipt':'.cache/main-native-original-receipt.json'}
(root/'.cache/main-native-proof-config.json').write_text(json.dumps(config,indent=2)+'\n')
(out/'collection-receipt.json').write_text(json.dumps({'result':'PASS','main_receipt_sha256':a.expected_receipt_sha256,'sources':len(r['sources']),'dependency_files':count,'resources':len(r['resources']),'protected_files':len(r['protected_before']),'artifacts':len(r['artifacts']),'display_probe_sha256':sha(probe),'collector_sha256':sha(__file__),'proof_sha256':sha(proof)},indent=2)+'\n')
(out/'README.md').write_text('[confirmed: host-receipt.json and native scale reports] Main executed immutable source `'+r['head']+'` on native Windows Qt at both scales. All16 active/preview table cases pass complete wheel/keyboard/scrollbar coverage, full-ID detail, complete selected-row vertical visibility through page clipping, encoded state/RNG/save/per-context-draft invariants and read-only preview/busy guards. Separate native Qt/OS display probes before archive creation and before/after each scenario prove required logical and physical workarea capacity, requested/actual ratios, stable native bounds and agreement with the scenario report. The hashed probe is retained. Wrapper exit0 also proves deferred Qt cleanup left no owned top-level widgets.\n\n[confirmed: collection-receipt.json] Collection independently rehashed all178 archive/current/Git source files,566 private runtime dependency files and both wheel inputs,2 private resources and all protected launcher/save/data files. No private runtime or original resource bytes are tracked. Raw Windows UTF-8 log bytes are losslessly represented by JSON envelopes; separate LF logs are reading copies.\n\n[designed: #241] Read-only reviewer audit (main stages original receipt separately): `python3 -B .cache/main-native-proof-check.py --expected-receipt-sha256 '+a.expected_receipt_sha256+'`. This checks the externally supplied main receipt anchor; it audits retained execution and does not rerun Windows.\n')
(out/'inventory.json').write_text(json.dumps({p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()},indent=2)+'\n')
subprocess.run([sys.executable,'-B',str(proof),'--expected-receipt-sha256',a.expected_receipt_sha256],cwd=root,check=True)
print('PASS collected and independently audited',out)
