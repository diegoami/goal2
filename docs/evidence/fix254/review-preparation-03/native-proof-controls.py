"""[designed: #254] Native evidence audit controls; synthetic alterations never claim native execution."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--expected-receipt-sha256',required=True);p.add_argument('--checker',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path.cwd();config=json.loads(Path(a.config).read_text());out=root/a.output;assert out.resolve().is_relative_to((root/'.cache').resolve());out.mkdir(exist_ok=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
base=root/config['evidence'];original=root/config['original_receipt'];assert sha(original)==a.expected_receipt_sha256
rows=[]
def check(name,cfg,anchor,expected):
 log=out/(name+'.log');cfgfile=out/(name+'-config.json');cfgfile.write_text(json.dumps(cfg,indent=2)+'\n')
 with log.open('xb')as stream:run=subprocess.run([sys.executable,'-B',a.checker,'--config',str(cfgfile),'--expected-receipt-sha256',anchor],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
 text=log.read_text();assert run.returncode!=0 and expected in text,(name,run.returncode,text[-2000:]);rows.append({'name':name,'exit':run.returncode,'expected_rejection':expected,'log_sha256':sha(log),'synthetic_semantic_anchor':anchor!=a.expected_receipt_sha256})
check('wrong-external-anchor',config,'0'*64,'external original receipt anchor differs')
for name in('resigned-receipt','callback','heartbeat','frame-ack','sdl-bounds','capture','protected'):
 case=out/name;case.mkdir();evidence=case/'evidence';shutil.copytree(base,evidence);r=json.loads(original.read_text());collection=json.loads((evidence/'collection.json').read_text())
 def write_json(filename,value):
  path=evidence/filename;raw=(json.dumps(value,indent=2)+'\n').encode();path.write_bytes(raw)
  envelope=Path(str(path)+'.raw-envelope.json')
  if envelope.exists():envelope.write_text(json.dumps({'encoding':'utf-8','sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()},indent=2)+'\n')
  if filename in collection['normalization']:collection['normalization'][filename].update(raw_sha256=sha(path),reading_sha256=sha(path))
  return hashlib.sha256(raw).hexdigest()
 run=r['runs'][0];report=run['report'];v=json.loads((evidence/report).read_text())
 if name in('callback','heartbeat','frame-ack','sdl-bounds'):
  if name=='callback':v['callbacks']=['synthetic callback failure']
  elif name=='heartbeat':v['frames'][0]['maximum_heartbeat_gap']=1.0
  elif name=='frame-ack':v['frames'][0]['final_ack']-=1
  else:
   v['sdl'][0]['window_rect'][0]=-1;metadata=str(Path(report).parent/Path(v['sdl'][0]['capture']).with_suffix('.json'));r['artifacts'][metadata]=write_json(metadata,v['sdl'][0])
  run['frames']=v['frames'];run['report_sha256']=r['artifacts'][report]=write_json(report,v)
 elif name=='capture':
  filename=str(Path(report).parent/v['qt_captures'][0]['file']);path=evidence/filename;data=path.read_bytes();path.write_bytes(b'!'+data[1:]);r['artifacts'][filename]=sha(path)
 else:r['protected_after'][next(iter(r['protected_after']))]='0'*64
 raw=(json.dumps(r,indent=2)+'\n').encode();retained=case/'original.json';retained.write_bytes(raw);write_json('host-receipt.json',r)
 anchor=a.expected_receipt_sha256 if name=='resigned-receipt'else sha(retained)
 collection['original_receipt_sha256']=sha(retained);(evidence/'collection.json').write_text(json.dumps(collection,indent=2)+'\n')
 (evidence/'inventory.json').write_text(json.dumps({f.relative_to(evidence).as_posix():sha(f)for f in sorted(evidence.rglob('*'))if f.is_file()and f.name!='inventory.json'},indent=2)+'\n')
 expected={'resigned-receipt':'external original receipt anchor differs','callback':'native controller/callback/cleanup invalid','heartbeat':'native responsiveness invalid','frame-ack':'final frame ACK invalid','sdl-bounds':'native window outside physical workarea','capture':"assert data[:8]",'protected':'protected baseline differs'}[name]
 check(name,{'evidence':evidence.relative_to(root).as_posix(),'original_receipt':retained.relative_to(root).as_posix()},anchor,expected)
# [designed: #254] No other source reader or native job may run during this saved-byte mutation.
source=root/'goal2/desktop/watched.py';saved=source.read_bytes()
try:
 text=saved.decode();old='read_access = 0x80000000';assert text.count(old)==1;source.write_text(text.replace(old,'read_access = 0x80000001'))
 check('current-source',config,a.expected_receipt_sha256,'current source differs')
finally:source.write_bytes(saved)
assert source.read_bytes()==saved
(out/'report.json').write_text(json.dumps({'claim':'[designed: #254] Synthetic tampering controls; only baseline original anchor is actual main native evidence','result':'PASS','rows':rows,'source_restored':True,'original_receipt_sha256':a.expected_receipt_sha256},indent=2)+'\n');print('PASS all nine intended native-proof rejections; original evidence and source bytes preserved')
