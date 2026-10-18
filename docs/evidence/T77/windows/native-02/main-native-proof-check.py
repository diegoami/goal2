"""[designed: T76/T77/T78] Independently anchored native artifact/source identity audit."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path.cwd();config=json.loads((ROOT/'.cache/main-native-proof-config.json').read_text());task=config['task'];assert task in ('T76','T77','T78')
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
 if task=='T76':
  assert report['callback_exceptions']==[] and report['cleanup_retry_calls']>=2 and report['clean_widgets'] and report['source_unchanged'],'native cancellation proof incomplete'
  captions=report['footer_captions'];assert len(captions)>=12
  for c in captions:
   assert c['ratio']==int(scale) and c['font_advance']<=c['contents'][2] and c['font_height']<=c['contents'][3],('native caption clipped',c)
   assert c['text']=={'confirm':'Confirm management','discard':'Discard draft'}[c['button']]
  required=[(1440,900),(1050,780),(900,700)]if scale=='1'else[(900,640)]
  for size in required:assert {(c['button'],c['focused'])for c in captions if tuple(c['size'])==size}>={(b,f)for b in('confirm','discard')for f in(False,True)},('missing native caption state',size)
 if task=='T77':
  assert report['callback_exceptions']==[] and report['clean_widgets'] and report['owned_processes_closed'] and report['sources_unchanged'] and report['sources']==report['sources_after']
  assert len(report['table_reading_coverage'])==80 and len(set(report['table_reading_coverage']))==80
  per_size=report['table_reading_by_size'];required_sizes=[(1440,900),(1050,780),(900,700)]if scale=='1'else[(900,640)]
  assert {tuple(x['size'])for x in per_size}==set(required_sizes) and len(per_size)==len(required_sizes)
  def contains(parent,child):
   x,y,w,h=parent;cx,cy,cw,ch=child
   return w>0 and h>0 and cw>0 and ch>0 and x<=cx and y<=cy and cx+cw<=x+w and cy+ch<=y+h
  for measurement in per_size:
   assert measurement['ratio']==int(scale) and measurement['pure_state_draft_save_rng'] is True
   assert measurement['ids']==report['table_reading_coverage'] and len(set(measurement['ids']))==80
   cells=measurement['cells'];assert len(cells)==560 and {(c['id'],c['column'])for c in cells}=={(word,column)for word in measurement['ids']for column in range(7)}
   for c in cells:
    assert c['text'] and c['font_height']>0 and c['font_advance']>0
    assert c['glyph'][2:]==[c['font_advance'],c['font_height']]
    assert all(contains(c[parent],c['glyph'])for parent in('cell','text_contents','table_viewport','visible_bounds'))
    assert contains(c['outer_viewport'],c['outer_glyph']) and c['outer_glyph'][2:]==c['glyph'][2:]
  expected={'filtered','hidden-selection-other-visible','empty-filter','synthetic-long-name','unavailable','closed-window','pending-busy','preview','standalone'}
  expected|={'selected-'+size for size in(['1440x900','1050x780','900x700']if scale=='1'else['900x640'])}
  assert expected<={Path(c['file']).stem for c in report['captures']}
  for c in report['captures']:
   assert c['outgoing_text_width']<=c['outgoing_reading_width']
   assert {x['name']for x in c['reading']}=={'poolDetail','exchangeSummary','poolPolicy'}
   for reading in c['reading']:assert reading['text_bounds'][1]<=reading['available'][1]
  for size in(['1440x900','1050x780','900x700']if scale=='1'else['900x640']):
   assert next(c for c in report['captures']if Path(c['file']).stem=='selected-'+size)['focused_action']
 helper='tools/desktop-ui/'+{'T76':'squad_scenario.py','T77':'pool_scenario.py','T78':'results_scenario.py'}[task];assert report['scenario_sha256']==r['sources'][helper]
 assert report['resources']=={'template':r['resources']['e010-r0008-halftime.sav'],'data':r['resources']['GOAL.DAT']}
 for name,h in report['sources'].items():assert r['sources'][name.replace('\\','/')]==h
 for capture in report['captures']:assert sha(path.parent/capture.get('path',capture.get('file')))==capture['sha256']
 assert len(report['captures'])==run['captures']and report['captures'];reports.append({'scale':scale,'captures':len(report['captures']),'platform':report['platform'],'qt':report['qt']})
for name,h in r['artifacts'].items():assert sha(evidence/name)==h,('artifact differs',name)
inventory=json.loads((evidence/'inventory.json').read_text())
for name,h in inventory.items():assert sha(evidence/name)==h,('inventory differs',name)
print(json.dumps({'result':'PASS','task':task,'native_checkpoint':r['checkpoint_head'],'current_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_files':len(r['sources']),'reports':reports,'protected_unchanged':len(r['protected_before']),'inventory_files':len(inventory),'independent_main_receipt_sha256':sha(original)}))
