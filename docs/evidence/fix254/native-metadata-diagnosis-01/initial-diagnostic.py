"""[designed: #254] Native metadata/read comparison while the real writer retains its rename handle."""
import json,platform,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
assert sys.platform=='win32';sys.path.insert(0,sys.argv[1])
from goal2.desktop import pygame_viewer as viewer,watched
from goal2.tests.test_desktop_watched_sharing import SharingTests
out=Path(sys.argv[2]);out.mkdir(exist_ok=False)
query=r'''
import json,sys
from pathlib import Path
from goal2.desktop import watched
from goal2.tests.test_desktop_watched_sharing import SharingTests
p=Path(sys.argv[1]);row={'exists':p.exists()}
try:row['stat_size']=p.stat().st_size
except OSError as e:row['stat_error']={'error':repr(e),'winerror':getattr(e,'winerror',None)}
try:
 with watched._open_status(p)as stream:row['native_read']=json.loads(stream.read())
 row['read_closed']=stream.closed
except OSError as e:row['read_error']={'error':repr(e),'winerror':getattr(e,'winerror',None)}
c=SharingTests().controller(p.parent)
try:row.update(published=c.poll(),last_status=c.last_status,pending=c.model.match_pending)
except Exception as e:row['poll_error']=repr(e)
finally:c.process=None
print(json.dumps(row))
'''
rows=[]
for existing in(False,True):
 with tempfile.TemporaryDirectory(dir=out)as folder:
  path=Path(folder)/'status';helper=SharingTests();controller=helper.controller(folder);value=helper.value(controller)
  if existing:viewer.status(path,value)
  api=viewer._status_replace_api();row={'existing':existing}
  def inspect(label):
   run=subprocess.run([sys.executable,'-B','-c',query,str(path)],capture_output=True,text=True,timeout=5)
   assert run.returncode==0,run.stdout+run.stderr
   row[label]=json.loads(run.stdout)
  def close(handle):
   try:inspect('writer_handle_open')
   finally:row['writer_handle_closed']=bool(api[2](handle))
  with patch.object(viewer,'_status_replace_api',return_value=(*api[:2],close,api[3])):viewer.status(path,value)
  inspect('writer_handle_closed_result');controller.process=None;rows.append(row)
report={'claim':'[designed: #254] Actual metadata/read/controller paths, controlled real writer close only; diagnostic not UI acceptance','platform':platform.platform(),'python':sys.version,'rows':rows}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
