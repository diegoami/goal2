"""[designed: T76/T78] Main-only immutable native Windows implementation validation."""
from pathlib import Path
import argparse,hashlib,io,json,os,subprocess,tarfile,time
p=argparse.ArgumentParser();p.add_argument('--task',choices=['T76','T78'],required=True);p.add_argument('--head',required=True);a=p.parse_args()
ROOT=Path('/home/diego/projects/goal2');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe');WT=Path('/home/diego/projects/goal2-work')/(a.task+'-football-ui');scenario={'T76':'squad','T78':'results'}[a.task]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def windows(p):return 'C:\\'+str(p.relative_to('/mnt/c')).replace('/','\\')
assert len(a.head)==40 and subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=WT,text=True).strip()
assert subprocess.check_output(['git','rev-parse','origin/task/'+a.task+'-football-ui'],cwd=WT,text=True).strip()==a.head
out=ROOT/'.cache/kept/review-receipts'/(a.task+'-windows-acceptance-'+str(time.time_ns()));out.mkdir(exist_ok=False)
folder=WIN/'.goal2-validation'/(a.task+'-implementation-'+a.head[:12]+'-'+str(time.time_ns()));folder.mkdir(parents=True,exist_ok=False)
protected={str(p):sha(p)for p in (WIN/'.cache').rglob('*')if p.is_file()and p.suffix.lower()in('.sav','.g2save','.dat')};protected[str(WIN/'Start-goal2.cmd')]=sha(WIN/'Start-goal2.cmd')
r={'tag':'[designed: '+a.task+'] actual immutable implementation validation','checkpoint_head':a.head,'directory':str(folder),'protected_before':protected,'runs':[],'result':'INCOMPLETE'}
raw=subprocess.check_output(['git','archive',a.head,'goal2','tools/desktop-ui'],cwd=WT)
with tarfile.open(fileobj=io.BytesIO(raw))as archive:
 for m in archive.getmembers():
  assert not m.issym()and not m.islnk();path=folder/m.name;assert path.resolve().is_relative_to(folder.resolve())
  if m.isdir():path.mkdir(parents=True,exist_ok=True)
  elif m.isfile():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.extractfile(m).read())
sources={p.relative_to(folder).as_posix():sha(p)for p in folder.rglob('*')if p.is_file()};r['sources']=sources
cache=folder/'.cache';cache.mkdir();(cache/'tmp').mkdir();resources={}
for name in ('e010-r0008-halftime.sav','GOAL.DAT'):
 (cache/name).write_bytes((WT/'.cache'/name).read_bytes());resources[name]=sha(cache/name)
if a.task=='T78':
 dest=cache/'T78-presentation-inputs-03';dest.mkdir();src=WT/'.cache/T78-presentation-inputs-03'
 for name in ('inventory.json','competitive-regulation.g2save','original-friendly-kit1.g2save','competitive-shootout.g2save'):(dest/name).write_bytes((src/name).read_bytes())
 r['private_inputs']={p.relative_to(cache).as_posix():sha(p)for p in dest.iterdir()if p.is_file()}
r['resources']=resources
try:
 for scale in ('1','2'):
  wrapper=folder/('native-'+scale+'.py');observations=folder/'observations'/('scale-'+scale)
  script=folder/'tools/desktop-ui/redesign.py';argv=[windows(script),'--scenario',scenario,'--template',windows(cache/'e010-r0008-halftime.sav'),'--data',windows(cache/'GOAL.DAT'),'--evidence-dir',windows(observations),'--single-scale']
  wrapper.write_text('import os,sys,runpy\n'+"os.environ['QT_QPA_PLATFORM']='windows'\n"+"os.environ['QT_SCALE_FACTOR']="+repr(scale)+'\n'+"os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'\n"+"os.environ['PYTHONDONTWRITEBYTECODE']='1'\n"+''.join('os.environ['+repr(key)+']='+repr(windows(cache/'tmp'))+'\n'for key in ('TMPDIR','TEMP','TMP'))+"assert sys.platform=='win32'\n"+'sys.argv='+repr(argv)+'\n'+"runpy.run_path(sys.argv[0],run_name='__main__')\n")
  log=out/('native-'+scale+'.log');t=time.monotonic()
  with log.open('xb')as f:proc=subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],cwd=folder,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  row={'scale':scale,'command':argv,'exit':proc.returncode,'seconds':round(time.monotonic()-t,3),'log_sha256':sha(log),'wrapper_sha256':sha(wrapper)};r['runs'].append(row);assert proc.returncode==0,log.read_text(errors='replace')[-5000:]
  candidates=[p for p in (observations/'report.json',observations/'interaction.json')if p.is_file()];assert len(candidates)==1,candidates;report=json.loads(candidates[0].read_text());assert report['result']=='PASS'and report['qpa']=='windows'and report['ratio']==int(scale)and'Windows'in report['platform'];assert report['requested_scale']==scale
  helper='tools/desktop-ui/'+{'T76':'squad_scenario.py','T78':'results_scenario.py'}[a.task];assert report['scenario_sha256']==sources[helper]
  assert report['resources']=={'template':resources['e010-r0008-halftime.sav'],'data':resources['GOAL.DAT']}
  for name,h in report['sources'].items():assert sources[name.replace('\\','/')]==h
  for capture in report['captures']:assert sha(observations/capture.get('path',capture.get('file')))==capture['sha256']
  assert report['captures'],'no native captures';row.update({'qt':report['qt'],'python':report['python'],'platform':report['platform'],'actual_ratio':report['ratio'],'captures':len(report['captures']),'report_path':candidates[0].relative_to(folder).as_posix(),'report_sha256':sha(candidates[0])})
 assert all(sha(folder/n)==h for n,h in sources.items());assert all(sha(cache/n)==h for n,h in resources.items());assert all(sha(cache/n)==h for n,h in r.get('private_inputs',{}).items());assert all(sha(Path(n))==h for n,h in protected.items())
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()==a.head;subprocess.run(['git','diff','--quiet','HEAD','--','goal2','tools'],cwd=WT,check=True);r['result']='PASS'
finally:
 r['protected_after']={n:sha(Path(n))for n in protected};r['artifacts']={p.relative_to(folder).as_posix():sha(p)for p in (folder/'observations').rglob('*')if p.is_file()};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'result':r['result'],'receipt':str(out/'receipt.json'),'directory':str(folder),'runs':r['runs'],'protected':len(protected)}))
