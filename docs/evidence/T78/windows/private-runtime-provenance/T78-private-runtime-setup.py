"""[designed: T78] Stage the existing project-pinned optional Windows runtime privately."""
from pathlib import Path
import hashlib,json,subprocess,time
ROOT=Path('/home/diego/projects/goal2');WIN=Path('/mnt/c/Users/diego/projects/goal2-exe');out=ROOT/'.cache/kept/review-receipts'/('T78-private-runtime-'+str(time.time_ns()));out.mkdir();target=WIN/'.goal2-validation'/('T78-runtime-unicorn214-'+str(time.time_ns()));target.mkdir();wheel=target/'wheels';wheel.mkdir();libs=target/'python-libs'
def windows(p):return 'C:\\'+str(p.relative_to('/mnt/c')).replace('/','\\')
py=str(WIN/'.venv/Scripts/python.exe');log=out/'pip-setup.log'
with log.open('xb')as f:
 args=['-m','pip','download','--disable-pip-version-check','--no-cache-dir','--only-binary=:all:','--no-deps','--index-url','https://pypi.org/simple','--dest',windows(wheel),'unicorn==2.1.4']
 r=subprocess.run([py,*args],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=180);assert r.returncode==0,'private wheel download failed; see '+str(log)
 wheels=list(wheel.glob('*.whl'));assert len(wheels)==1
 args=['-m','pip','install','--disable-pip-version-check','--no-cache-dir','--no-index','--no-deps','--target',windows(libs),windows(wheels[0])]
 r=subprocess.run([py,*args],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=180);assert r.returncode==0,'private wheel install failed; see '+str(log)
code='import sys,json;sys.path.insert(0,'+repr(windows(libs))+');import unicorn;print(json.dumps({"version":unicorn.__version__,"file":unicorn.__file__}))';info=json.loads(subprocess.check_output([py,'-c',code],text=True));assert info['version']=='2.1.4'and info['file'].startswith(windows(libs))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r={'version':'2.1.4','directory':str(libs),'native_import':info,'wheels':{p.name:sha(p)for p in wheel.glob('*.whl')},'files':{p.relative_to(libs).as_posix():sha(p)for p in libs.rglob('*')if p.is_file()and'__pycache__'not in p.parts},'setup_log_sha256':sha(log),'scope':'Already declared pyproject watched dependency; private validation folder only, existing Windows venv unchanged'};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');(ROOT/'.cache/kept/review-receipts/T78-private-runtime-config.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'result':'PASS','receipt':str(out/'receipt.json'),'version':r['version'],'directory':r['directory'],'wheel_sha256':r['wheels']}))
