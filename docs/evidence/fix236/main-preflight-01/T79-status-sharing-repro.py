"""[designed: T79/#236] Windows stdlib reproduction; no game inputs or source edits."""
from pathlib import Path
import json,os,sys,time,threading
assert sys.platform=='win32'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);target=out/'status';temporary=out/'status.new';target.write_text('{"kind":"ready"}');temporary.write_text('{"kind":"ready","sequence":1}')
rows=[]
held=target.open('rb')
try:
 try:os.replace(temporary,target)
 except PermissionError as exc:rows.append({'case':'old-replace-held-reader','winerror':exc.winerror,'errno':exc.errno})
 else:raise AssertionError('expected original replacement to fail while reader holds target')
finally:held.close()
os.replace(temporary,target);rows.append({'case':'old-replace-after-reader-close','success':True})
def bounded_replace():
 deadline=time.monotonic()+.25;tries=[]
 while True:
  try:os.replace(temporary,target);return tries
  except PermissionError as exc:
   tries.append(exc.winerror);remaining=deadline-time.monotonic()
   if exc.winerror not in(5,32)or remaining<=0:raise
   time.sleep(min(.01,remaining))
   if time.monotonic()>=deadline:raise
temporary.write_text('{"kind":"ready","sequence":2}');held=target.open('rb');released=threading.Event()
def release():time.sleep(.03);held.close();released.set()
thread=threading.Thread(target=release);thread.start();start=time.monotonic()
tries=bounded_replace();thread.join(timeout=1);assert released.is_set()and tries
rows.append({'case':'bounded-mock-transient','errors':tries,'seconds':time.monotonic()-start,'success':True})
temporary.write_text('{"kind":"ready","sequence":3}');held=target.open('rb');start=time.monotonic()
try:
 try:bounded_replace()
 except PermissionError as exc:
  elapsed=time.monotonic()-start;assert exc.winerror in(5,32)and .20<=elapsed<.40
  rows.append({'case':'bounded-mock-permanent','winerror':exc.winerror,'seconds':elapsed,'propagated':True})
 else:raise AssertionError('permanent reader unexpectedly permitted replacement')
finally:held.close()
r={'result':'PASS','claim':'Only new owned status files; native held-read sharing and runtime-only bounded replacement mock; no product change','rows':rows};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
