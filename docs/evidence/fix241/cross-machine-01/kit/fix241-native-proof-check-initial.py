"""[designed: #241] Read-only audit of main's externally anchored native execution."""
import argparse,hashlib,json,re,struct,subprocess,sys
from pathlib import Path,PurePosixPath
FROZEN='7560fbc336fa0efd6ea188c3739eb66e6460df63'
RESOURCES={'e010-r0008-halftime.sav':'ae2935b9c490745450462b981eb133e611bc72de4abfb11aba3e850caf4e9949','GOAL.DAT':'bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def safe(root,name):
 p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name,name
 path=root.joinpath(*p.parts);assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),name
 return path


def validate_display(value,scale):
 assert value['qpa']=='windows' and value['requested_qt_scale']==scale and value['qt_ratio']==float(scale),'native display platform/scale differs'
 assert isinstance(value['qt_name'],str) and value['qt_name'] and type(value['os_dpi'])is int and value['os_dpi']>0
 logical=(1440,900)if scale=='1'else(900,640);ratio=float(scale)
 for name in ('qt_available','primary_pixels','virtual_pixels','workarea_pixels'):
  dimensions=value[name];assert len(dimensions)==2 and all(type(v)is int and v>0 for v in dimensions),(name,dimensions)
 assert all(value['qt_available'][i]>=logical[i]for i in (0,1)),'native Qt workarea too small'
 for name in ('primary_pixels','virtual_pixels','workarea_pixels'):
  assert all(value[name][i]>=logical[i]*ratio for i in (0,1)),('native physical workarea too small',name)
 for i in (0,1):
  assert abs(value['qt_available'][i]*ratio-value['workarea_pixels'][i])<=ratio,'Qt and OS workareas disagree'
  assert value['workarea_pixels'][i]<=value['primary_pixels'][i]<=value['virtual_pixels'][i],'inconsistent native OS bounds'
 return value

def audit(config,anchor):
 root=Path.cwd();evidence=safe(root,config['evidence']);original=safe(root,config['original_receipt'])
 assert re.fullmatch('[0-9a-f]{64}',anchor) and sha(original)==anchor,'external main receipt anchor differs'
 assert (evidence/'host-receipt.json').read_bytes()==original.read_bytes(),'tracked main receipt differs'
 r=json.loads(original.read_text());assert r['head']==FROZEN and r['result']=='PASS'
 assert r['claim']=='Actual committed source and native Windows Qt; no product/widget mocks'
 assert r['protected_unchanged'] is True and r['protected_before']==r['protected_after']
 protected=r['protected_before'];assert len(protected)>=2 and {'Start-goal2.cmd','Start-goal2-modern.cmd'}<={Path(p).name for p in protected}
 assert all(re.fullmatch('[0-9a-f]{64}',v) for v in protected.values())
 assert sha(evidence/'windows_display_probe.py')==r['display_probe_sha256'],'retained display probe differs'
 assert set(r['native_display_before'])=={'1','2'}
 for scale,value in r['native_display_before'].items():validate_display(value,scale)
 for name in ('primary_pixels','virtual_pixels','workarea_pixels','os_dpi','qt_name'):
  assert r['native_display_before']['1'][name]==r['native_display_before']['2'][name],('display changed between scale preflights',name)
 assert r['resources']==RESOURCES
 for name,h in RESOURCES.items():assert sha(root/'.cache'/name)==h
 archived=set(git('ls-tree','-r','--name-only',FROZEN,'goal2','tools/desktop-ui').splitlines())
 assert set(r['sources'])==archived and len(archived)==178,'native archive incomplete'
 for name,h in r['sources'].items():
  assert sha(safe(root,name))==h,('current source differs',name)
  assert hashlib.sha256(subprocess.check_output(['git','show',FROZEN+':'+name])).hexdigest()==h,('frozen source differs',name)
 changes=set(git('diff','--name-only',FROZEN,'HEAD').splitlines())|set(git('diff','--name-only','HEAD').splitlines())
 assert all(p.startswith('docs/evidence/fix241/')for p in changes),('non-evidence carry',changes)
 versions={'T78':('2.1.4','unicorn',43),'T79':('2.5.8','pygame',523)};assert set(r['dependencies'])==set(versions)
 for task,(version,package,count) in versions.items():
  d=r['dependencies'][task];assert d['version']==d['native_import']['version']==version and len(d['files'])==count and len(d['wheels'])==1
  assert '.goal2-validation' in d['directory'] and d['directory'].endswith('/python-libs')
  assert re.split(r'[\\/]+',d['native_import']['file'])[-3:]==['python-libs',package,'__init__.py']
  assert all(re.fullmatch('[0-9a-f]{64}',h)for h in [*d['files'].values(),*d['wheels'].values(),d['setup_log_sha256']])
 # [designed] Independent Qt-free model reconstruction verifies complete source-order IDs.
 sys.path.insert(0,str(root));from goal2.desktop.model import DesktopModel
 expected={}
 for context,country in [('active',13),('preview',14)]:
  m=DesktopModel.open(root/'.cache/e010-r0008-halftime.sav',root/'.cache/GOAL.DAT',root/'.cache/unused-native-audit-save.g2save',country=country)
  expected[context,'squad']=[x['id']for x in m.view()['players']];expected[context,'reserves']=[x['id']for x in m.pool_view()['reserves']]
 assert [run['scale']for run in r['runs']]==['1','2'];total=0;measurements=[]
 for run in r['runs']:
  scale=run['scale'];assert run['exit']==0 and run['seconds']>0
  physical=run['physical_display'];assert set(physical)=={'before','after'}
  assert physical['before']==r['native_display_before'][scale]
  for value in physical.values():validate_display(value,scale)
  assert physical['before']==physical['after'],'physical display changed during native scenario'
  assert run['report']==f'observations/scale-{scale}/report.json'
  report_path=safe(evidence,run['report']);assert sha(report_path)==run['report_sha256']
  wrapper=evidence/f'native-{scale}.py';assert sha(wrapper)==run['wrapper_sha256'];code=wrapper.read_text()
  assert 'runpy.run_path' in code and 'assert sys.platform=="win32"' in code and 'assert not app.topLevelWidgets()' in code and 'finally:' in code
  envelope=json.loads((evidence/f'native-{scale}.raw-envelope.json').read_text());raw=envelope['text'].encode('utf-8')
  assert envelope['encoding']=='utf-8' and hashlib.sha256(raw).hexdigest()==envelope['sha256']==run['log_sha256']
  log=raw.decode('utf-8').replace('\r\n','\n');assert (evidence/f'native-{scale}.log').read_bytes()==log.encode('utf-8')
  assert 'PASS player browsing:' in log and not any(x in log for x in ('Traceback (most recent call last)','Error calling Python override','FAILED','skipped'))
  report=json.loads(report_path.read_text());assert report['result']=='PASS' and report['qpa']=='windows' and 'Windows' in report['platform']
  assert report['screen']==physical['before']['qt_available'] and report['ratio']==physical['before']['qt_ratio'],'scenario differs from measured native display'
  assert report['scale']==scale and report['ratio']==float(scale) and report['source_head']==FROZEN and report['callbacks']==[] and report['sources_unchanged'] is True
  assert report['qt']=='6.12.0' and report['resources']=={'template':RESOURCES['e010-r0008-halftime.sav'],'data':RESOURCES['GOAL.DAT']}
  assert report['sources']=={p:h for p,h in r['sources'].items()if p.startswith('goal2/desktop/') and p.endswith('.py')}
  assert report['scenario_sha256']==r['sources']['tools/desktop-ui/player-browsing.py']
  assert report['state_invariants']=='encoded active/preview, both RNG pairs, save bytes, per-context draft and jobs unchanged; active draft restored'
  sizes=[(900,640)]if scale=='2'else[(1440,900),(1050,780),(900,700)]
  assert len(report['screen'])==2 and all(report['screen'][i]>=max(size[i]for size in sizes)for i in (0,1)),'native screen clips requested logical targets'
  cases={(context,size,table)for context in ('active','preview')for size in sizes for table in ('squad','reserves')}
  assert len(report['tables'])==len(cases)
  seen=set()
  for row in report['tables']:
   key=(row['context'],tuple(row['size']),row['table']);assert key in cases and key not in seen;seen.add(key)
   count=20 if row['table']=='squad' else 80;assert row['rows']==count and row['scroll_maximum']>0
   assert row['wheel_coverage']==list(range(count)) and row['selected_ids']==expected[row['context'],row['table']]
   assert len(set(row['selected_ids']))==count and all(type(v)is int for v in row['selected_ids'])
   assert f"ID {row['selected_ids'][-1]}"in row['last_detail']
   assert row['visibility_oracle']=='complete row vertical band within viewport visibleRegion (ancestor clipping included)'
   image=safe(report_path.parent,row['capture']);assert sha(image)==row['capture_sha256'];raw=image.read_bytes()
   assert raw[:8]==b'\x89PNG\r\n\x1a\n' and raw[12:16]==b'IHDR'
   assert list(struct.unpack('!II',raw[16:24]))==[int(v*float(scale))for v in row['size']]
  assert seen==cases;total+=len(cases)
  measurements.append({'scale':scale,'captured_window_dpr':report['ratio'],'workarea_logical_size':report['screen'],'workarea_physical_size':[int(v*report['ratio'])for v in report['screen']],'requested_logical_sizes':[list(size)for size in sizes],'verified_capture_physical_sizes':[[int(v*report['ratio'])for v in size]for size in sizes],'native_os_before':physical['before'],'native_os_after':physical['after'],'window_global_position':'not retained by source helper; size/workarea checks are explicit'})
 assert len(r['artifacts'])==18
 for name,h in r['artifacts'].items():assert sha(safe(evidence,name))==h,('native artifact differs',name)
 assert set(r['artifacts'])=={p.relative_to(evidence).as_posix()for p in (evidence/'observations').rglob('*')if p.is_file()}
 collection=json.loads((evidence/'collection-receipt.json').read_text());assert collection['result']=='PASS' and collection['main_receipt_sha256']==anchor and collection['sources']==178 and collection['dependency_files']==566 and collection['resources']==2 and collection['protected_files']==len(protected) and collection['display_probe_sha256']==r['display_probe_sha256']
 inventory=json.loads((evidence/'inventory.json').read_text())
 for name,h in inventory.items():assert sha(safe(evidence,name))==h,('inventory differs',name)
 assert set(inventory)=={p.relative_to(evidence).as_posix()for p in evidence.rglob('*')if p.is_file()and p.name!='inventory.json'}
 return {'result':'PASS','claim':'Audit of retained main Windows execution; no Windows re-execution','native_checkpoint':FROZEN,'current_head':git('rev-parse','HEAD'),'source_files':178,'dependency_files':566,'resources':2,'protected_files':len(protected),'native_table_cases':total,'measurements':measurements,'main_receipt_sha256':anchor,'inventory_files':len(inventory)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',default='.cache/main-native-proof-config.json');p.add_argument('--expected-receipt-sha256',required=True);a=p.parse_args();print(json.dumps(audit(json.loads(Path(a.config).read_text()),a.expected_receipt_sha256),indent=2))
