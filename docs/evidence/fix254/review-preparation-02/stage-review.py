"""[designed: #254] Main-owned setup inside this invocation's actual review checkout."""
import argparse,hashlib,json,re,shutil,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--log',required=True);p.add_argument('--head',required=True);p.add_argument('--task',choices=['fix254'],required=True);p.add_argument('--notes',required=True);p.add_argument('--native-original',required=True);p.add_argument('--native-evidence',required=True);p.add_argument('--driver',required=True);p.add_argument('--proof',required=True);p.add_argument('--proof-config',required=True);a=p.parse_args()
base=Path('/home/diego/projects/goal2');work=Path('/home/diego/projects/goal2-work').resolve();assert re.fullmatch('[0-9a-f]{40}',a.head);wt=None;deadline=time.monotonic()+180
while time.monotonic()<deadline:
 log=Path(a.log).read_text(errors='replace')if Path(a.log).exists()else''
 for name,head in re.findall(r'^worktree: (.+?) at ([0-9a-f]{40})',log,re.M):
  if head==a.head:
   candidate=Path(name);assert candidate.parent.resolve()==work and not candidate.is_symlink();assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=candidate,text=True).strip()==a.head;wt=candidate;break
 if wt:break
 time.sleep(.1)
assert wt is not None,'actual owned review checkout not reported within180s';cache=wt/'.cache';cache.mkdir(exist_ok=True);assert cache.resolve().is_relative_to(wt.resolve());subprocess.run(['git','check-ignore','-q','.cache'],cwd=wt,check=True);rows={}
def copy(src,dst):
 assert src.is_file()and not src.is_symlink(),src;raw=src.read_bytes();h=hashlib.sha256(raw).hexdigest()
 if dst.exists():assert not dst.is_symlink()and hashlib.sha256(dst.read_bytes()).hexdigest()==h,('different existing input',dst)
 else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 rows[dst.relative_to(cache).as_posix()]=h
for folder in (base/'.cache/validation-assets/original-match-fixtures',):
 if not folder.is_dir():continue
 for src in folder.iterdir():
  if src.is_file()and(src.suffix.lower()=='.sav'or src.name.upper()=='GOAL.DAT'):copy(src,cache/src.name)
  elif src.is_dir()and src.name.startswith('watched-legacy-v3-'):
   for child in src.rglob('*'):
    if child.is_file():copy(child,cache/src.name/child.relative_to(src))
assert rows['e010-r0008-halftime.sav']=='ae2935b9c490745450462b981eb133e611bc72de4abfb11aba3e850caf4e9949';assert rows['GOAL.DAT']=='bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca'
aux=base/'.cache/validation-tools/xcb-libs';expected={'libxcb-cursor0_0.1.6-1_amd64.deb':'3e5a4ae404eb05b8592cd42502e1379de8d51c810aa1e2450ec0d0b32fb6f038','libxkbcommon-x11-0_1.13.1-1_amd64.deb':'231f44bf451c6263bbd69c23620018aad94297581391f9094b924912ca77a8a8'}
for name,h in expected.items():
 found=list(aux.rglob(name));assert len(found)==1 and hashlib.sha256(found[0].read_bytes()).hexdigest()==h;dst=cache/'xcb-libs/packages'/name;copy(found[0],dst);target=cache/'xcb-libs/extracted';target.mkdir(parents=True,exist_ok=True);subprocess.run(['dpkg-deb','--extract',str(dst),str(target)],check=True,timeout=30)
for item in (cache/'xcb-libs/extracted').rglob('*'):
 if item.is_symlink():assert item.resolve().is_relative_to((cache/'xcb-libs/extracted').resolve())
(cache/'tmp').mkdir(exist_ok=True)
with (cache/'main-guard-setup.log').open('x')as log:subprocess.run(['npm','ci','--prefix','tools/harness/opencode-guard','--ignore-scripts','--no-audit','--no-fund'],cwd=wt,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
with (cache/'main-guard-validation.log').open('x')as log:subprocess.run(['node','tools/harness/check-opencode-guard.mjs'],cwd=wt,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
owned=base/'.cache/kept/review-receipts';copy(Path(a.driver),cache/'main-review-validation.py');copy(Path(a.proof),cache/'main-native-proof-check.py');copy(Path(a.proof).with_name('native-proof-controls.py'),cache/'main-native-proof-controls.py');copy(Path(a.native_original),cache/'main-native-original-receipt.json');copy(Path(a.notes),cache/'author-run-notes.txt')
author=work/'fix254-native-status-sharing'
for src in (author/'.cache').glob('*premerge*.log'):copy(src,cache/'author-logs'/src.name)
copy(Path(a.driver).with_name('linux-validation01.py'),cache/'main-linux-validation.py');copy(Path(a.driver).with_name('linux-ownership-controls.py'),cache/'main-ownership-controls.py');(cache/'main-validation-config.json').write_text(json.dumps({'head':a.head})+'\n')
copy(Path(a.proof_config),cache/'main-native-proof-config.json');(cache/'main-review-config.json').write_text(json.dumps({'task':a.task,'head':a.head},indent=2)+'\n')
# Physically stage complete bounded-readable PR artifacts inside the allowed checkout.
for name,args in [('main-pr-inventory.txt',['git','diff','--name-only','origin/main...HEAD']),('main-pr-product.patch',['git','diff','origin/main...HEAD','--','goal2','tools','docs/desktop-management.md']),('main-pr-scope.json',None)]:
 if args: (cache/name).write_bytes(subprocess.check_output(args,cwd=wt))
 else: (cache/name).write_text(json.dumps({'head':a.head,'main':subprocess.check_output(['git','rev-parse','origin/main'],cwd=wt,text=True).strip(),'merge_base':subprocess.check_output(['git','merge-base','origin/main','HEAD'],cwd=wt,text=True).strip(),'inventory':'.cache/main-pr-inventory.txt','diff':'.cache/main-pr-product.patch'},indent=2)+'\n')
for name in ('main-validation-config.json','main-review-config.json','main-pr-inventory.txt','main-pr-product.patch','main-pr-scope.json','main-guard-setup.log','main-guard-validation.log'):
 rows[name]=hashlib.sha256((cache/name).read_bytes()).hexdigest()
for item in sorted((cache/'xcb-libs/extracted').rglob('*')):
 if item.is_file():
  assert item.resolve().is_relative_to((cache/'xcb-libs/extracted').resolve());rows[item.relative_to(cache).as_posix()]=hashlib.sha256(item.read_bytes()).hexdigest()
r={'head':a.head,'task':a.task,'worktree':str(wt),'files':rows,'staged_files':len(rows),'source':'Main-verified private fixtures, native receipt original, own helpers/notes and task-local xcb/guard setup; no sibling reads or global changes required'};(cache/'main-fixtures-ready.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'worktree':str(wt),'task':a.task,'staged_files':len(rows),'marker':str(cache/'main-fixtures-ready.json')}))
