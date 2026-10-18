"""[designed: T79] Earlier implementation checkpoint proves both presentation regressions."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path.cwd();out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);receipt=[]
cases=[('wrapped-board',['goal2/desktop/pygame_viewer.py'],'test_wrapped_commentary_lands_at_board_and_scroll_retains_tail','not greater than 1'),('future-score',['goal2/desktop/match_page.py','goal2/desktop/window.py'],'test_qt_score_uses_consumed_pose_not_future_ingress','9 — 8')]
for name,files,test,expected in cases:
 saved={f:(root/f).read_bytes()for f in files}
 try:
  for f in files:(root/f).write_bytes(subprocess.check_output(['git','show','0fa2c295:'+f]))
  run=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_pygame_match_view.PresentationTests.'+test,'-v'],env={**os.environ,'QT_QPA_PLATFORM':'offscreen','SDL_VIDEODRIVER':'dummy','SDL_AUDIODRIVER':'dummy','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True)
  log=run.stdout+run.stderr;(out/(name+'.log')).write_text(log)
  assert run.returncode!=0 and 'FAIL:'in log and '\nERROR:'not in log and expected in log,(name,log)
  receipt.append({'case':name,'before_checkpoint':'0fa2c295','test':test,'returncode':run.returncode,'expected_assertion':expected,'sources_restored':{f:hashlib.sha256(b).hexdigest()for f,b in saved.items()}})
 finally:
  for f,data in saved.items():(root/f).write_bytes(data);assert(root/f).read_bytes()==data
(out/'restoration.json').write_text(json.dumps({'result':'PASS','cases':receipt,'exact_saved_bytes_restored':True},indent=2)+'\n')
print('PASS2 intended earlier-checkpoint behavior failures; exact saved bytes restored')
