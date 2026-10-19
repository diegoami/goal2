"""[designed: #254] Compare native single-rename operations and concurrent complete snapshots; diagnostic only."""
import ctypes,hashlib,json,os,platform,sys,tempfile,threading
from ctypes import wintypes
from pathlib import Path
assert sys.platform=='win32'
sys.path.insert(0,sys.argv[1])
from goal2.desktop.watched import _open_status
out=Path(sys.argv[2]);out.mkdir(exist_ok=False)
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE);k.CreateFileW.restype=wintypes.HANDLE
k.CloseHandle.argtypes=(wintypes.HANDLE,);k.CloseHandle.restype=wintypes.BOOL
k.SetFileInformationByHandle.argtypes=(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD);k.SetFileInformationByHandle.restype=wintypes.BOOL
k.ReplaceFileW.argtypes=(wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p);k.ReplaceFileW.restype=wintypes.BOOL
class Info(ctypes.Structure):
 _fields_=[('Flags',wintypes.DWORD),('RootDirectory',wintypes.HANDLE),('FileNameLength',wintypes.DWORD),('FileName',wintypes.WCHAR*1)]
def replace(source,target,operation):
 if operation=='ReplaceFileW':
  if not k.ReplaceFileW(str(target),str(source),None,0,None,None):raise ctypes.WinError(ctypes.get_last_error())
  return
 handle=k.CreateFileW(str(source),0x10000,7,None,3,0x80,None)
 if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
 try:
  name=str(target.resolve()).encode('utf-16-le');data=ctypes.create_string_buffer(Info.FileName.offset+len(name)+2)
  info=Info.from_buffer(data);info.Flags=3 if operation=='FileRenameInfoEx' else 1;info.RootDirectory=None;info.FileNameLength=len(name)
  ctypes.memmove(ctypes.addressof(data)+Info.FileName.offset,name,len(name))
  if not k.SetFileInformationByHandle(handle,22 if operation=='FileRenameInfoEx'else 3,data,len(data)):raise ctypes.WinError(ctypes.get_last_error())
 finally:assert k.CloseHandle(handle)
rows=[]
for operation in('ReplaceFileW','FileRenameInfo','FileRenameInfoEx'):
 for mode in('ordinary-reader','shared-reader','absent-target'):
  with tempfile.TemporaryDirectory(dir=out)as folder:
   target=Path(folder)/'status';source=Path(folder)/'status.new';source.write_bytes(b'new');stream=None
   if mode!='absent-target':target.write_bytes(b'old');stream=target.open('rb')if mode=='ordinary-reader'else _open_status(target)
   row={'operation':operation,'mode':mode}
   try:
    try:replace(source,target,operation);row['result']='PASS'
    except OSError as e:row.update(result='FAIL',winerror=e.winerror,error=repr(e))
    if stream:row['snapshot']=stream.read().decode()
   finally:
    if stream:stream.close();row['closed']=stream.closed
   row['target']=target.read_bytes().decode()if target.exists()else None;rows.append(row)
for operation in('ReplaceFileW','FileRenameInfo','FileRenameInfoEx'):
 with tempfile.TemporaryDirectory(dir=out)as folder:
  target=Path(folder)/'status';source=Path(folder)/'status.new';target.write_bytes(b'old');stopped=threading.Event();stats={'reads':0,'missing':0,'errors':{},'bad_payloads':[]};writer_errors=[]
  def read():
   while not stopped.is_set():
    try:
     with _open_status(target)as stream:value=stream.read()
     stats['reads']+=1
     if value not in(b'old',b'new'):stats['bad_payloads'].append(value.hex())
    except FileNotFoundError:stats['missing']+=1
    except OSError as e:stats['errors'][str(e.winerror)]=stats['errors'].get(str(e.winerror),0)+1
  thread=threading.Thread(target=read);thread.start()
  try:
   for n in range(2000):
    source.write_bytes(b'new'if n%2==0 else b'old')
    try:replace(source,target,operation)
    except OSError as e:writer_errors.append({'winerror':e.winerror,'error':repr(e)})
  finally:stopped.set();thread.join()
  rows.append({'operation':operation,'mode':'concurrent-2000','reader':stats,'writer_errors':writer_errors,'thread_closed':not thread.is_alive()})
report={'claim':'[designed: #254] New private text, real native APIs; diagnostic only','platform':platform.platform(),'python':sys.version,'info_offsets':{n:getattr(Info,n).offset for n,_ in Info._fields_},'rows':rows}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
