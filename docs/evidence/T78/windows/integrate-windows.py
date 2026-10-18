"""[designed: T78] Preserve verified native failure/provenance metadata; never copy private assets."""
import hashlib,json,shutil,subprocess
from pathlib import Path
base=Path('/home/diego/projects/goal2/.cache/kept/review-receipts');target=Path('docs/evidence/T78/windows')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
summary=[]
for source_name,dest_name in [('T78-windows-acceptance-1792343689034471409','failed-bootstrap-01'),('T78-windows-acceptance-1792343787318625328','failed-runtime-02')]:
 source=base/source_name;r=json.loads((source/'receipt.json').read_text());dest=target/dest_name;dest.mkdir();archive=Path(r['directory'])
 assert r['result']=='INCOMPLETE' and r['protected_before']==r['protected_after'] and len(r['protected_before'])==4
 for name in ('receipt.json','native-1.log'):shutil.copyfile(source/name,dest/name)
 assert sha(dest/'native-1.log')==r['runs'][0]['log_sha256']
 wrapper=archive/'native-1.py';assert sha(wrapper)==r['runs'][0]['wrapper_sha256'];shutil.copyfile(wrapper,dest/'native-1.py')
 for name,h in r['artifacts'].items():
  p=Path(name);assert p.parts[0]=='observations' and p.suffix in ('.json','.png')
  assert sha(archive/p)==h;output=dest/p;output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(archive/p,output)
 summary.append({'attempt':dest_name,'result':r['result'],'exit':r['runs'][0]['exit'],'seconds':r['runs'][0]['seconds'],'protected_unchanged':4,'artifacts':len(r['artifacts']),'original_receipt_sha256':sha(source/'receipt.json')})
 if r['artifacts']:
  report=json.loads((dest/'observations/scale-1/report.json').read_text());assert report['result']=='FAIL' and report['failure']=='unsupported Play guard differs'
  assert 'AssertionError: unsupported Play guard differs' in (dest/'native-1.log').read_text()
 else:assert "ModuleNotFoundError: No module named 'results_scenario'" in (dest/'native-1.log').read_text()
setup=target/'private-runtime-provenance';setup.mkdir()
for name in ('receipt.json','pip-setup.log'):shutil.copyfile(base/'T78-private-runtime-1792344046090029933'/name,setup/name)
r=json.loads((setup/'receipt.json').read_text());assert sha(setup/'pip-setup.log')==r['setup_log_sha256']
assert r['wheels']=={'unicorn-2.1.4-cp37-abi3-win_amd64.whl':'d7107500c64ce5c168fbff6bef9485b5db1350050036f4cea568650cf8bdbdf5'}
for name in ('T78-private-runtime-setup.py','T78-private-runtime-config.json','GUI-next-windows-acceptance-v1-preserved.py','GUI-next-windows-acceptance-v2-preserved.py','GUI-next-windows-acceptance.py'):
 shutil.copyfile(base/name,setup/name)
# [designed] Receipts contain hashes only for dependency contents; no package/wheel/DLL bytes copied.
summary.append({'setup':'private Unicorn2.1.4','wheel_sha256':next(iter(r['wheels'].values())),'scope':r['scope']})
for folder in (target/'failed-bootstrap-01',target/'failed-runtime-02',setup):
 inventory={p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
 (folder/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
(target/'integration-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
