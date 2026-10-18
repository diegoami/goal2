"""[designed: T76/T78] Main-only native Windows planning feasibility, no implementation acceptance."""
from pathlib import Path
import argparse,hashlib,io,json,os,subprocess,tarfile,time
p=argparse.ArgumentParser();p.add_argument('--task',choices=['T76','T78'],required=True);a=p.parse_args()
ROOT=Path('/home/diego/projects/goal2');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe');WT=Path('/home/diego/projects/goal2-work')/(a.task+'-football-ui')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(p.relative_to('/mnt/c')).replace('/','\\')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip();subprocess.run(['git','diff','--quiet','HEAD'],cwd=WT,check=True)
out=ROOT/'.cache/kept/review-receipts'/(a.task+'-windows-preflight-'+str(time.time_ns()));out.mkdir(exist_ok=False)
folder=WIN/'.goal2-validation'/(a.task+'-planning-'+head[:12]+'-'+str(time.time_ns()));folder.mkdir(parents=True,exist_ok=False)
protected={str(p):sha(p)for p in (WIN/'.cache').rglob('*')if p.is_file()and p.suffix.lower()in('.sav','.g2save','.dat')};protected[str(WIN/'Start-goal2.cmd')]=sha(WIN/'Start-goal2.cmd')
r={'tag':'[designed: '+a.task+'] planning-only mock','head':head,'directory':str(folder),'protected_before':protected,'runs':[],'result':'INCOMPLETE'}
raw=subprocess.check_output(['git','archive',head,'goal2','tools/desktop-ui'],cwd=WT)
with tarfile.open(fileobj=io.BytesIO(raw))as archive:
 for m in archive.getmembers():
  assert not m.issym()and not m.islnk();path=folder/m.name;assert path.resolve().is_relative_to(folder.resolve())
  if m.isdir():path.mkdir(parents=True,exist_ok=True)
  elif m.isfile():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.extractfile(m).read())
helper=ROOT/'.cache/kept/review-receipts'/(a.task+'-main-preflight.py');target=folder/'tools/desktop-ui/main-preflight.py';target.write_bytes(helper.read_bytes());sources={p.relative_to(folder).as_posix():sha(p)for p in folder.rglob('*')if p.is_file()};r['sources']=sources
cache=folder/'.cache';cache.mkdir();(cache/'tmp').mkdir();resources={}
for name in ('e010-r0008-halftime.sav','GOAL.DAT'):
 (cache/name).write_bytes((WT/'.cache'/name).read_bytes());resources[name]=sha(cache/name)
if a.task=='T78':
 dest=cache/'T78-presentation-inputs-03';dest.mkdir();src=WT/'.cache/T78-presentation-inputs-03'
 for name in ('inventory.json','competitive-regulation.g2save','original-friendly-kit1.g2save','competitive-shootout.g2save'):(dest/name).write_bytes((src/name).read_bytes())
r['resources']=resources
try:
 for scale in ('1','2'):
  wrapper=folder/('native-'+scale+'.py');observations=folder/'observations'/('scale-'+scale)
  wrapper.write_text('import os,sys,runpy\n'+"os.environ['QT_QPA_PLATFORM']='windows'\n"+"os.environ['QT_SCALE_FACTOR']="+repr(scale)+'\n'+"os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'\n"+"os.environ['PYTHONDONTWRITEBYTECODE']='1'\n"+''.join('os.environ['+repr(key)+']='+repr(windows(cache/'tmp'))+'\n'for key in ('TMPDIR','TEMP','TMP'))+"assert sys.platform=='win32'\n"+'sys.argv='+repr([windows(target),'--mode','mock','--output',windows(observations)])+'\n'+"runpy.run_path(sys.argv[0],run_name='__main__')\n")
  log=out/('native-'+scale+'.log');t=time.monotonic()
  with log.open('xb')as f:proc=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  row={'scale':scale,'exit':proc.returncode,'seconds':round(time.monotonic()-t,3),'log_sha256':sha(log)};r['runs'].append(row);assert proc.returncode==0,log.read_text(errors='replace')[-4000:]
  report=json.loads((observations/'receipt.json').read_text());assert report['result']=='PASS'and report['qpa']=='windows'and report['ratio']==int(scale)and'Windows'in report['platform'];assert report['probe_sha256']==sha(helper);assert report['resources']==resources
  for name,h in report['sources'].items():assert sources[name.replace('\\','/')]==h
  for capture in report['captures']:assert sha(observations/capture['path'])==capture['sha256']
  row.update({'qt':report['qt'],'platform':report['platform'],'actual_ratio':report['ratio'],'captures':len(report['captures']),'report_sha256':sha(observations/'receipt.json')})
 assert all(sha(folder/n)==h for n,h in sources.items());assert all(sha(Path(n))==h for n,h in protected.items());r['result']='PASS'
finally:
 r['protected_after']={n:sha(Path(n))for n in protected};r['artifacts']={p.relative_to(folder).as_posix():sha(p)for p in (folder/'observations').rglob('*')if p.is_file()};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'result':r['result'],'receipt':str(out/'receipt.json'),'directory':str(folder),'runs':r['runs'],'protected':len(protected)}))
