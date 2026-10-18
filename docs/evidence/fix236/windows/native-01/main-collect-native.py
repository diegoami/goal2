"""[designed: #236] Collect only main-owned new native observations, no private inputs."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
ROOT=Path.cwd();original=Path('/home/diego/projects/goal2/.cache/kept/review-receipts/fix236-windows-native-01-1792354669106214905/receipt.json')
ANCHOR='454bbb4a4bcd2bfc2a951a08b3ddda63c988d77eb8051263096eef25d028dd0a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(original)==ANCHOR
r=json.loads(original.read_text());folder=Path(r['directory']);assert r['head']=='dfed1519af51dcb105d2526621eec9b313dd4b83'and r['result']=='PASS'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==r['head']
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
assert r['protected_unchanged']and r['protected_before']==r['protected_after']and len(r['protected_before'])==4
for name,want in r['protected_before'].items():assert sha(name)==want,('protected file differs',name)
for name,want in r['sources'].items():assert sha(folder/name)==sha(ROOT/name)==want,('source differs',name)
assert len(r['sources'])==176
for name,want in r['resources'].items():assert sha(folder/'.cache'/name)==sha(ROOT/'.cache'/name)==want,('resource differs',name)
for task,dep in r['dependencies'].items():
 for name,want in dep['files'].items():assert sha(folder/'.cache'/('python-libs-'+task)/name)==sha(Path(dep['directory'])/name)==want,('private dependency differs',task,name)
 for name,want in dep['wheels'].items():assert sha(Path(dep['directory']).parent/'wheels'/name)==want
for name,want in r['observers'].items():assert sha(folder/name)==want
allowed=set(r['artifacts'])
assert allowed=={p.relative_to(folder).as_posix()for p in(folder/'observations').rglob('*')if p.is_file()}
for name in allowed:
 assert re.fullmatch(r'observations/scale-[12]/[^/]+\.(png|json|log)',name),name
 assert not(folder/name).is_symlink()and sha(folder/name)==r['artifacts'][name]
evidence=ROOT/'docs/evidence/fix236/windows/native-01';evidence.mkdir(parents=True,exist_ok=False)
def copy(source,name):
 target=evidence/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);assert sha(target)==sha(source)
copy(original,'host-receipt.json')
copy('/home/diego/projects/goal2/.cache/kept/review-receipts/fix236-windows-acceptance.py','main-native-validation.py')
copy(ROOT/'.cache/fix236-native-proof.py','main-native-proof-check.py')
for name in sorted(allowed):copy(folder/name,name)
for name in r['observers']:copy(folder/name,name)
for run in r['runs']:
 scale=run['scale'];copy(folder/f'native-{scale}.py',f'native-{scale}.py');copy(original.parent/f'native-{scale}.log',f'native-{scale}.log')
 assert sha(evidence/f'native-{scale}.py')==run['wrapper_sha256']and sha(evidence/f'native-{scale}.log')==run['log_sha256']
for p in evidence.rglob('*'):
 if p.is_file():assert p.suffix in('.json','.png','.log','.py'),p
receipt={'result':'PASS','claim':'Main-owned immutable observations only; private binaries/original assets/saves excluded','original_host_receipt_sha256':ANCHOR,'native_checkpoint':r['head'],'verified_source_files':176,'verified_dependency_files':sum(len(d['files'])for d in r['dependencies'].values()),'verified_resources':3,'verified_protected_files':4,'runner_sha256':sha(evidence/'main-native-validation.py'),'proof_sha256':sha(evidence/'main-native-proof-check.py')}
(evidence/'collection-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
shutil.copyfile(original,ROOT/'.cache/main-native-original-receipt.json');shutil.copyfile(ROOT/'.cache/fix236-native-proof.py',ROOT/'.cache/main-native-proof-check.py')
config={'task':'fix236','evidence':'docs/evidence/fix236/windows/native-01','original_receipt':'.cache/main-native-original-receipt.json'}
(ROOT/'.cache/main-native-proof-config.json').write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
