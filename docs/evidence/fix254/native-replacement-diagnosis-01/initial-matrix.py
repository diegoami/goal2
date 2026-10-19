"""[designed: #254] Native replacement semantics diagnosis; no game/UI acceptance."""
from pathlib import Path
import ctypes,json,os,platform,sys,tempfile,time
from ctypes import wintypes
assert sys.platform=='win32'
sys.path.insert(0,sys.argv[1])
from goal2.desktop.watched import _open_status
out=Path(sys.argv[2]);out.mkdir(exist_ok=False)
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE);k.CreateFileW.restype=wintypes.HANDLE
k.CloseHandle.argtypes=(wintypes.HANDLE,);k.CloseHandle.restype=wintypes.BOOL
k.ReplaceFileW.argtypes=(wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p);k.ReplaceFileW.restype=wintypes.BOOL
k.MoveFileExW.argtypes=(wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD);k.MoveFileExW.restype=wintypes.BOOL
rows=[]
for mode in('none','path-reader','native-shared-handle','native-shared-delete-access','production-shared-reader'):
 for operation in('os.replace','MoveFileExW','ReplaceFileW'):
  with tempfile.TemporaryDirectory(prefix='replace-matrix-',dir=out)as folder:
   target=Path(folder)/'status';source=Path(folder)/'status.new';target.write_bytes(b'old');source.write_bytes(b'new')
   stream=None;handle=None;row={'mode':mode,'operation':operation}
   try:
    if mode=='path-reader':stream=target.open('rb')
    elif mode=='production-shared-reader':stream=_open_status(target)
    elif mode.startswith('native-shared'):
     access=0x80000000|(0x10000 if mode=='native-shared-delete-access'else 0)
     handle=k.CreateFileW(str(target),access,7,None,3,0x80,None)
     if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
     if operation=='os.replace':os.replace(source,target)
     elif operation=='MoveFileExW':
      if not k.MoveFileExW(str(source),str(target),1):raise ctypes.WinError(ctypes.get_last_error())
     else:
      if not k.ReplaceFileW(str(target),str(source),None,0,None,None):raise ctypes.WinError(ctypes.get_last_error())
     row['result']='PASS'
    except OSError as error:row.update(result='FAIL',error=repr(error),winerror=getattr(error,'winerror',None))
    row['target_bytes']=target.read_bytes().decode();row['source_exists']=source.exists()
    if stream is not None:row['open_snapshot']=stream.read().decode()
   finally:
    if stream is not None:stream.close();row['reader_closed']=stream.closed
    if handle is not None:row['handle_closed']=bool(k.CloseHandle(handle))
   rows.append(row)
report={'claim':'[designed: #254] Native API diagnosis on new private text only; not acceptance','platform':platform.platform(),'python':sys.version,'rows':rows}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
