"""[designed: T75] Verify main-owned native artifacts against frozen local source."""
import hashlib,json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[4];base=root/'docs/evidence/T75/windows/native-01'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
local=lambda name:root/name.replace('\\','/')
inventory=json.loads((base/'inventory.json').read_text());receipt=json.loads((base/'receipt.json').read_text())
assert inventory['result']==receipt['result']=='PASS'
for name,expected in inventory['files'].items():assert digest(base/name)==expected,name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()}==set(inventory['files'])|{'inventory.json'}
for name,expected in receipt['source_files'].items():assert digest(local(name))==expected,name
assert receipt['protected_before']==receipt['protected_after'] and len(receipt['protected_before'])==4
scenario=digest(root/'tools/desktop-ui/redesign.py');assert scenario==inventory['scenario_sha256']
records=[]
for number,count in ((1,19),(2,7)):
 folder=base/'observations'/f'scale-{number}';report=json.loads((folder/'interaction.json').read_text())
 assert report['result']=='PASS' and report['ratio']==number and report['qpa']=='windows'
 assert report['scenario_sha256']==scenario and report['qt']=='6.12.0' and report['platform']=='Windows-11-10.0.26200-SP0'
 assert len(report['captures'])==count and len(report['steps'])==3
 assert report['invalid_draft_return'] and report['explicit_campaign_friendly_resume'] and report['completed_result_restored']
 for name,expected in report['sources'].items():assert digest(local(name))==expected,name
 for name,file in (('template','.cache/e010-r0008-halftime.sav'),('data','.cache/GOAL.DAT')):assert report['resources'][name]==digest(root/file)
 for capture in report['captures']:
  path=folder/capture['path'];assert digest(path)==capture['sha256']
  if 'size' in capture:assert tuple(struct.unpack('>II',path.read_bytes()[16:24]))==tuple(v*number for v in capture['size'])
 assert all(item['target']==item['actual'] and item['visible'] and item['enabled'] and item['window_active'] for item in report['focus_trace'])
 records.append({'scale':number,'captures':count,'all_inventory_and_source_hashes_match':True,'actual_native_qpa':'windows','result':'PASS'})
out={'tag':'[confirmed: main-owned native-01 inventory/receipt/reports; designed: author verification]','native_source_head':receipt['head'],'current_scenario_sha256':scenario,'inventory_files':len(inventory['files']),'protected_hashes_unchanged':True,'runs':records,'result':'PASS'}
path=root/'docs/evidence/T75/windows/author-verification-01.json';assert not path.exists();path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
