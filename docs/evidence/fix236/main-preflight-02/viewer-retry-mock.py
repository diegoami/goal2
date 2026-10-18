import json,os,sys,time
from pathlib import Path
from goal2.desktop import pygame_viewer as v
log=Path(__file__).with_name('viewer-retry-mock-events.jsonl')
def record(row):
 with log.open('a')as f:f.write(json.dumps(row)+'\n')
def status(path,value):
 temporary=path.with_suffix('.new');temporary.write_text(json.dumps(value));deadline=time.monotonic()+.25;attempts=0
 while True:
  try:
   os.replace(temporary,path)
   if attempts:record({'case':'retry-success','attempts':attempts,'kind':value['kind']})
   return
  except PermissionError as exc:
   remaining=deadline-time.monotonic()
   if sys.platform!='win32'or getattr(exc,'winerror',None)!=5 or remaining<=0:raise
   attempts+=1;record({'case':'transient-replace-denied','winerror':exc.winerror,'attempt':attempts})
   time.sleep(min(.01,remaining))
   if time.monotonic()>=deadline:raise
v.status=status
sys.exit(v.main())
