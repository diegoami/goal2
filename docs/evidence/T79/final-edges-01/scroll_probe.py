"""[designed: T79] Synthetic SDL observer smoke; no original-output acceptance claim."""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tools/desktop-ui')]
from goal2.tests.test_pygame_pitch_view import sample
from match_handoff_scenario import VIEWER
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
f=sample();f['watermark']=1
rows=[{'name':'SYNTHETIC Player '+str(n),'raw':55}for n in range(20)]
values=[('start',['SYNTHETIC A','SYNTHETIC B']),('pitch',{'rate':60}),('event',{'kind':'commentary','minute':7,'score':[1,0],'data':{'text':'SYNTHETIC long text '*65}}),('frame',f),('event',{'kind':'end','minute':90,'score':[1,0],'data':{}}),('complete',{'board':{'statistics':{'corners':[1,2]},'bars':[[1,2],[3,4]]},'ratings':[rows,rows],'man_of_the_match':'SYNTHETIC Player 0'})]
with tempfile.TemporaryDirectory(prefix='T79-synthetic-scroll-')as folder:
 p=Path(folder);(p/'display').write_text(''.join(json.dumps(['owned',i,k,v])+'\n'for i,(k,v)in enumerate(values)))
 with (out/'child.log').open('x')as log:
  child=subprocess.Popen([sys.executable,'-c',VIEWER,str(out/'sdl'),'actual',str(p),'owned'],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
  try:time.sleep(1)
  finally:
   child.terminate();child.wait(timeout=3)
 r=json.loads((out/'sdl/metrics.json').read_text())
 assert r['rating_tail']['observed_after_flip'] and r['scrolled_up']['observed_after_flip'] and r['rating_tail']['last_painted']=='SYNTHETIC Player 19: 55'
 assert r['scrolled_up']['scroll']<r['rating_tail']['scroll'] and r['read_only']
 print('PASS synthetic actual SDL End/Up/post-flip final-rating capture; diagnostics read after writer reaped; no original-output claim')
