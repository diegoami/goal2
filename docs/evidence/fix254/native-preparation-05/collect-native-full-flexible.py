"""[designed: #254] Lossless main native execution collection; acceptance is audited separately."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--output',required=True);p.add_argument('--launcher',default='native-full-launcher.py');a=p.parse_args();assert Path(a.launcher).name==a.launcher and a.launcher.endswith('.py')
root=Path('/home/diego/projects/goal2-work/fix254-native-status-sharing');receipt=Path(a.receipt);r=json.loads(receipt.read_text());folder=Path(r['directory']);out=root/a.output
assert out.resolve().is_relative_to((root/'docs/evidence/fix254').resolve())and not out.exists()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert r['protected_unchanged']and r['protected_before']==r['protected_after']
for n,h in r['sources'].items():
 assert sha(folder/n)==sha(root/n)==h
 assert hashlib.sha256(subprocess.check_output(['git','show',r['head']+':'+n],cwd=root)).hexdigest()==h
for n,h in r['resources'].items():assert sha(folder/'.cache'/n)==sha(root/'.cache'/n)==h
count=0
for task,d in r['dependencies'].items():
 for n,h in d['files'].items():assert sha(folder/'.cache'/('python-libs-'+task)/n)==sha(Path(d['directory'])/n)==h;count+=1
 for n,h in d['wheels'].items():assert sha(Path(d['directory']).parent/'wheels'/n)==h
for n,h in r['protected_after'].items():assert sha(n)==h
out.mkdir(parents=True);maps={}
def copy(src,name):
 raw=src.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
 if src.suffix in('.json','.log','.new'):
  text=raw.decode('utf-8');reading=text.replace('\r\n','\n');reading=reading.rstrip('\n')+'\n'if reading else ''
  Path(str(target)+'.raw-envelope.json').write_text(json.dumps({'encoding':'utf-8','sha256':hashlib.sha256(raw).hexdigest(),'text':text},indent=2)+'\n');target.write_text(reading)
  maps[str(name)]={'raw_sha256':hashlib.sha256(raw).hexdigest(),'reading_sha256':sha(target),'normalization':'CRLF to LF; terminal newlines to one (empty stays empty)'}
 else:target.write_bytes(raw)
copy(receipt,'host-receipt.json')
for n,h in r['artifacts'].items():
 assert PurePosixPath(n).parts[0]=='observations'and '..'not in PurePosixPath(n).parts
 source=folder/n;assert source.suffix in('.json','.log','.png','.new')and sha(source)==h;copy(source,n)
for n,h in r['observers'].items():assert sha(folder/n)==h;copy(folder/n,n)
for run in r['runs']:
 scale=run['scale'];source=folder/('native-'+scale+'.py');assert sha(source)==run['wrapper_sha256'];copy(source,source.name)
 source=receipt.parent/('native-'+scale+'.log');assert sha(source)==run['log_sha256'];copy(source,source.name)
for n in(a.launcher,'windows_display_probe.py'):copy(Path(__file__).with_name(n),n)
(out/'collection.json').write_text(json.dumps({'claim':'[confirmed: independent post-run rehashes] Native execution collected; no acceptance claim beyond original result','original_result':r['result'],'original_receipt_sha256':sha(receipt),'source_files':len(r['sources']),'dependency_files':count,'resources':len(r['resources']),'protected_files':len(r['protected_before']),'normalization':maps},indent=2)+'\n')
(out/'inventory.json').write_text(json.dumps({q.relative_to(out).as_posix():sha(q)for q in sorted(out.rglob('*'))if q.is_file()},indent=2)+'\n');print(out)
