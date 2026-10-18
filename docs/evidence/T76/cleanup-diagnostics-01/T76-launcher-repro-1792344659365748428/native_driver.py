
from pathlib import Path
import sys,subprocess,tempfile,time,json,os,base64,hashlib
folder=Path(tempfile.mkdtemp(prefix='T76-launcher-diagnostic-',dir=r'C:\Users\diego\projects\goal2-exe\.goal2-validation'))
child=folder/'owned_sleep.py'
child.write_text("import os,sys,time,json\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'executable':sys.executable,'base_executable':sys._base_executable}))\nsys.stderr.write('owned diagnostic child ready\\n');sys.stderr.flush()\ntime.sleep(60)\n")
r={'folder':str(folder),'driver_pid':os.getpid(),'driver_executable':sys.executable,'base_executable':sys._base_executable,'cases':[]}
def ps(script):
 enc=base64.b64encode(script.encode('utf-16-le')).decode()
 p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',enc],capture_output=True,text=True,timeout=15)
 if p.returncode:raise RuntimeError(p.stderr)
 return json.loads(p.stdout)
def owned(stop=False):
 script="$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; $marker="+repr(str(folder))+"; $child="+repr(str(child))+"; $rows=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($marker,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $_.CommandLine.IndexOf($child,[StringComparison]::OrdinalIgnoreCase) -ge 0 }); $result=@($rows | ForEach-Object { [ordered]@{pid=[int]$_.ProcessId;ppid=[int]$_.ParentProcessId;command=$_.CommandLine;executable=$_.ExecutablePath;created=[string]$_.CreationDate} }); "
 if stop:script+="foreach($p in $rows){Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop}; "
 return ps(script+"ConvertTo-Json -InputObject $result -Depth 4")
try:
 for label,exe in [('venv',sys.executable),('base',sys._base_executable)]:
  case=folder/label;case.mkdir();ready=case/'ready.json';error=case/'error.txt';err=error.open('wb');p=None;row={'label':label,'executable':exe,'deletions':[]};r['cases'].append(row)
  try:
   p=subprocess.Popen([exe,str(child),str(ready)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
   row['popen_pid']=p.pid;deadline=time.monotonic()+10
   while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
   assert ready.exists(),'pure child did not become ready';row['ready']=json.loads(ready.read_text());row['alive_tree']=owned();row['stderr_before']=error.read_text()
   started=time.monotonic();p.terminate();p.wait(timeout=2);row['popen_returncode']=p.returncode;row['terminate_wait_seconds']=time.monotonic()-started;err.close()
   for delay in (0,.025,.1,.5):
    if delay:time.sleep(delay)
    attempt={'seconds_after_wait':round(time.monotonic()-started,6)}
    try:error.unlink();attempt['deleted']=True
    except OSError as e:attempt.update(deleted=False,type=type(e).__name__,winerror=getattr(e,'winerror',None),message=str(e))
    row['deletions'].append(attempt)
    if attempt['deleted']:break
   row['after_terminate_tree']=owned()
  finally:
   err.close()
   row['cleanup_verified_processes']=owned(stop=True)
   deadline=time.monotonic()+3
   while owned() and time.monotonic()<deadline:time.sleep(.05)
   row['after_cleanup_tree']=owned()
   if p is not None and p.poll() is None:p.wait(timeout=2)
  row['error_exists_after_process_cleanup']=error.exists()
  if error.exists():
   try:error.unlink();row['delete_after_owned_cleanup']=True
   except OSError as e:row['delete_after_owned_cleanup']={'type':type(e).__name__,'winerror':getattr(e,'winerror',None),'message':str(e)}
 r['result']='PASS'
finally:
 (folder/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
