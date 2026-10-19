from pathlib import Path
import hashlib,json,subprocess,time
p=Path(__file__).parent;win=Path('/mnt/c/Users/diego/projects/goal2-exe');folder=win/'.goal2-validation'/('fix254-rename-diagnostic-'+str(time.time_ns()));folder.mkdir(exist_ok=False)
source=win/'.goal2-validation/fix254-25096176d11f-1792408124822336976'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def windows(path):return 'C:\\'+str(path.relative_to('/mnt/c')).replace('/','\\')
protected=json.loads(next(p.glob('fix254-windows-it13-full02-*/receipt.json')).read_text())['protected_after'];assert all(sha(Path(n))==h for n,h in protected.items())
script=folder/'diagnostic.py';script.write_bytes((p/'native-rename-diagnostic.py').read_bytes());log=p/'rename-diagnostic-native.log'
with log.open('xb')as stream:result=subprocess.run([str(win/'.venv/Scripts/python.exe'),'-B',windows(script),windows(source),windows(folder/'observations')],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
assert all(sha(Path(n))==h for n,h in protected.items())
(p/'rename-diagnostic-receipt.json').write_text(json.dumps({'exit':result.returncode,'directory':str(folder),'source':str(source),'script_sha256':sha(script),'log_sha256':sha(log),'protected_before':protected,'protected_after':{n:sha(Path(n))for n in protected}},indent=2)+'\n');print(result.returncode,folder)
