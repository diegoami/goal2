"""[designed: #254] Serial saved-byte ownership deletion controls; restores before any other reader."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path.cwd();out=root/'.cache/fix254-ownership-controls01';out.mkdir(exist_ok=False)
paths=sorted((root/'goal2').rglob('*.py'))+sorted((root/'tools/desktop-ui').glob('*.py'))
def hashes():return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
initial=hashes();rows=[]
mutants=[('raw-handle','goal2/desktop/watched.py','        close(handle)\n        raise','        pass\n        raise','test_native_handle_bridge_failure_closes_only_the_current_owner'),('descriptor','goal2/desktop/watched.py','        os.close(descriptor)\n        raise','        pass\n        raise','test_native_handle_bridge_failure_closes_only_the_current_owner'),('rename-handle','goal2/desktop/pygame_viewer.py','    finally:\n        close(handle)','    finally:\n        pass','test_native_rename_encodes_target_and_closes_only_an_acquired_handle')]
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
try:
 for name,file,old,new,test in mutants:
  path=root/file;saved=path.read_bytes();text=saved.decode();assert text.count(old)==1
  try:
   path.write_text(text.replace(old,new));log=out/(name+'.log')
   with log.open('xb')as stream:run=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_desktop_watched_sharing.SharingTests.'+test,'-v'],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
   output=log.read_text();assert run.returncode!=0 and 'FAIL:'in output and 'AssertionError:'in output and 'ERROR:'not in output,output
   rows.append({'name':name,'file':file,'before_sha256':hashlib.sha256(saved).hexdigest(),'mutant_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'exit':run.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'intended_cleanup_assertion_failed':True})
  finally:path.write_bytes(saved)
  assert hashes()==initial
finally:
 (out/'report.json').write_text(json.dumps({'claim':'[designed: #254] Saved-byte ownership controls; unit mocks only, not native I/O acceptance','rows':rows,'all_sources_restored':hashes()==initial,'sources':initial},indent=2)+'\n')
assert len(rows)==3 and hashes()==initial
print('PASS all three ownership deletion controls; all source bytes restored')
