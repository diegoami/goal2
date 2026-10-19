"""[designed: #254] Read-only audit of main's externally anchored real Windows match execution."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path,PurePosixPath
RESOURCES={'e010-r0008-halftime.sav':'ae2935b9c490745450462b981eb133e611bc72de4abfb11aba3e850caf4e9949','GOAL.DAT':'bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca','e0afff6751747233-e006-1000-r0001.sav':'e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d'}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(path.read_bytes())
def safe(root,name):
 p=PurePosixPath(name);assert not p.is_absolute()and '..'not in p.parts and '\\'not in name,'unsafe receipt path'
 target=root.joinpath(*p.parts);assert not target.is_symlink()and target.resolve().is_relative_to(root.resolve()),'receipt path escapes root'
 return target
def raw(path):
 envelope=Path(str(path)+'.raw-envelope.json')
 if not envelope.exists():return path.read_bytes()
 value=json.loads(envelope.read_text());assert value['encoding']=='utf-8';data=value['text'].encode('utf-8');assert digest(data)==value['sha256'],'raw envelope hash differs'
 reading=data.decode('utf-8').replace('\r\n','\n');reading=reading.rstrip('\n')+'\n'if reading else ''
 assert path.read_bytes()==reading.encode('utf-8'),'reading derivative differs'
 return data
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def display(value,scale):
 assert value['qpa']=='windows'and value['requested_qt_scale']==scale and value['qt_ratio']==float(scale)
 assert value['qt_name']and type(value['os_dpi'])is int and value['os_dpi']>0
 for name in('qt_available','primary_pixels','virtual_pixels','workarea_pixels'):
  assert len(value[name])==2 and all(type(v)is int and v>0 for v in value[name])
 assert all(value['qt_available'][i]>=([1050,780]if scale=='1'else[900,640])[i]for i in(0,1))
 for i in(0,1):
  assert abs(value['qt_available'][i]*int(scale)-value['workarea_pixels'][i])<=int(scale)
  assert value['workarea_pixels'][i]<=value['primary_pixels'][i]<=value['virtual_pixels'][i]
def png(path,size):
 data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'and data[12:16]==b'IHDR'
 assert list(struct.unpack('!II',data[16:24]))==size,'native capture size differs'
def rect(item,work):
 x,y,right,bottom=item;assert 0<=x<right<=work[0]and 0<=y<bottom<=work[1],'native window outside physical workarea'
def audit(config,anchor):
 root=Path.cwd();evidence=safe(root,config['evidence']);original=safe(root,config['original_receipt'])
 assert re.fullmatch('[0-9a-f]{64}',anchor)and sha(original)==anchor,'external original receipt anchor differs'
 assert raw(evidence/'host-receipt.json')==original.read_bytes(),'collected receipt differs from main original'
 r=json.loads(original.read_text());assert r['result']=='PASS'and re.fullmatch('[0-9a-f]{40}',r['head'])
 assert r['claim']=='Actual committed #254 Qt/SDL match acceptance; frames=True helper option and capture/ACK observers; deterministic fault-injection units separate, NO sharing mocks in actual matches'
 assert r['protected_unchanged']is True and r['protected_before']==r['protected_after']and len(r['protected_before'])==6,'protected baseline differs'
 assert {'Start-goal2.cmd','Start-goal2-modern.cmd'}<={Path(p).name for p in r['protected_before']}
 assert all(re.fullmatch('[0-9a-f]{64}',h)for h in r['protected_before'].values())
 assert set(r['native_display_before'])=={'1','2'}
 for scale,value in r['native_display_before'].items():display(value,scale)
 for name in('primary_pixels','virtual_pixels','workarea_pixels','os_dpi','qt_name'):
  assert r['native_display_before']['1'][name]==r['native_display_before']['2'][name]
 assert sha(evidence/'windows_display_probe.py')==r['display_probe_sha256']
 assert r['resources']==RESOURCES
 for name,h in RESOURCES.items():assert sha(root/'.cache'/name)==h,'private resource differs'
 archived=set(git('ls-tree','-r','--name-only',r['head'],'goal2','tools/desktop-ui').splitlines())
 assert set(r['sources'])==archived and len(archived)==179,'incomplete source archive'
 for name,h in r['sources'].items():
  assert sha(safe(root,name))==h,('current source differs',name)
  assert digest(subprocess.check_output(['git','show',r['head']+':'+name]))==h,('frozen Git source differs',name)
 changes=set(git('diff','--name-only',r['head'],'HEAD').splitlines())|set(git('diff','--name-only','HEAD').splitlines())
 assert all(n.startswith('docs/evidence/fix254/')for n in changes),'non-evidence carry since native execution'
 assert set(r['dependencies'])=={'T78','T79'}
 for task,version,package,count in(('T78','2.1.4','unicorn',43),('T79','2.5.8','pygame',523)):
  d=r['dependencies'][task];assert d['version']==d['native_import']['version']==version and len(d['files'])==count and len(d['wheels'])==1
  assert re.split(r'[\\/]+',d['native_import']['file'])[-3:]==['python-libs',package,'__init__.py']
  assert all(re.fullmatch('[0-9a-f]{64}',h)for h in[*d['files'].values(),*d['wheels'].values(),d['setup_log_sha256']])
 assert set(r['observers'])=={'parent-observer.py','viewer-observer.py'}
 for name,h in r['observers'].items():assert sha(safe(evidence,name))==h,'native observer differs'
 for name,h in r['artifacts'].items():
  assert name.startswith('observations/')and digest(raw(safe(evidence,name)))==h,('native artifact differs',name)
 assert set(r['artifacts'])=={p.relative_to(evidence).as_posix()for p in(evidence/'observations').rglob('*')if p.is_file()and not p.name.endswith('.raw-envelope.json')},'native artifact set differs'
 assert [x['scale']for x in r['runs']]==['1','2'];measurements=[]
 for run in r['runs']:
  scale=run['scale'];assert run['exit']==0 and run['seconds']>0
  assert set(run['physical_display'])=={'before','after'}
  physical=run['physical_display'];assert physical['before']==physical['after']==r['native_display_before'][scale]
  work=physical['before']['workarea_pixels'];log=raw(evidence/('native-'+scale+'.log'))
  assert digest(log)==run['log_sha256']and b'Ran 16 tests'in log and b'Ran 1 test'in log and b'PASS actual publication after final rendered-frame ACK'in log
  assert not any(n in log for n in(b'Traceback (most recent call last)',b'Error calling Python override',b'FAILED',b'skipped')),'native execution has a failure/skip'
  assert sha(evidence/('native-'+scale+'.py'))==run['wrapper_sha256']
  assert run['report']=='observations/scale-'+scale+'/report.json'
  report_path=safe(evidence,run['report']);assert digest(raw(report_path))==run['report_sha256']
  v=json.loads(report_path.read_text());assert v['result']=='PASS'and v['qpa']=='windows'and 'Windows'in v['platform']and '3.13.15'in v['python']and v['qt']=='6.12.0'
  assert v['requested_qt_scale']==scale and v['actual_qt_ratio']==float(scale)
  assert v['controller_errors']==v['callbacks']==[]and v['owned_resources_closed']is True and v['clean_widgets']is True and v['import_context_restored']is True,'native controller/callback/cleanup invalid'
  assert v['deterministic_tests']==run['deterministic_tests']==16 and v['original_acceptance_tests']==1
  assert len(v['frames'])==len(v['complete_acks'])==len(v['qt_captures'])==2 and v['frames']==run['frames']
  for frame in v['frames']:
   assert type(frame['frames'])is int and frame['frames']>=1000 and frame['final_ack']==frame['frames']-1,'final frame ACK invalid'
   assert re.fullmatch('[0-9a-f]{64}',frame['frame_digest'])and frame['heartbeats']>5 and 0<frame['maximum_heartbeat_gap']<1,'native responsiveness invalid'
  for ack in v['complete_acks']:assert type(ack['sequence'])is int and ack['sequence']>0 and re.fullmatch('[0-9a-f]{64}',ack['digest'])
  for capture in v['qt_captures']:
   size=[900,640]if scale=='2'else[1050,780]
   assert capture['ratio']==float(scale)and capture['logical_size']==size and capture['qt_available']==physical['before']['qt_available']and capture['active']is True
   rect(capture['native_rect'],work);png(safe(report_path.parent,capture['file']),[n*int(scale)for n in size])
  assert len(v['sdl'])==4 and sorted(x['stage']for x in v['sdl'])==['complete','complete','live','live']
  assert len({x['pid']for x in v['sdl']})==2
  for item in v['sdl']:
   assert item['driver']=='windows'and item['surface']==item['window']==[1000,720]and type(item['dpi'])is int and item['dpi']>0
   assert item['qt_scale_requested']==scale and type(item['frame_sequence'])is int and item['frame_sequence']>=0
   assert json.loads(safe(report_path.parent,str(PurePosixPath(item['capture']).with_suffix('.json'))).read_text())==item,'SDL report/metadata differs'
   rect(item['window_rect'],work);png(safe(report_path.parent,item['capture']),item['surface'])
  assert not list(report_path.parent.glob('*observer-errors.log'))
  measurements.append({'qt_ratio':v['actual_qt_ratio'],'qt_available':physical['before']['qt_available'],'workarea_physical':work,'frames':v['frames'],'complete_acks':v['complete_acks'],'sdl':v['sdl']})
 collection=json.loads((evidence/'collection.json').read_text());assert collection['original_result']=='PASS'and collection['original_receipt_sha256']==anchor
 assert collection['source_files']==179 and collection['dependency_files']==566 and collection['resources']==3 and collection['protected_files']==6
 for name,entry in collection['normalization'].items():
  path=safe(evidence,name);assert digest(raw(path))==entry['raw_sha256']and sha(path)==entry['reading_sha256']
  assert entry['normalization']=='CRLF to LF; terminal newlines to one (empty stays empty)'
 inventory=json.loads((evidence/'inventory.json').read_text())
 for name,h in inventory.items():assert sha(safe(evidence,name))==h,('inventory differs',name)
 assert set(inventory)=={p.relative_to(evidence).as_posix()for p in evidence.rglob('*')if p.is_file()and p.name!='inventory.json'}
 return {'result':'PASS','claim':'Read-only audit of retained main native execution, not native re-execution or independent review','current_head':git('rev-parse','HEAD'),'native_head':r['head'],'original_receipt_sha256':anchor,'source_files':179,'runtime_files':566,'resources':3,'protected_files':6,'measurements':measurements}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--expected-receipt-sha256',required=True);a=p.parse_args();print(json.dumps(audit(json.loads(Path(a.config).read_text()),a.expected_receipt_sha256),indent=2))
