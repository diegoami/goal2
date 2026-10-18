import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path.cwd();files=['goal2/desktop/pygame_viewer.py','goal2/desktop/fixtures_page.py','goal2/desktop/window.py'];saved={name:(root/name).read_bytes() for name in files}
out=root/'docs/evidence/T79/linux-unit-01';receipt=[]
tests=['test_real_framebuffer_matches_original_text_projection','test_wrapped_reading_preserves_long_text_and_compact_pitch_is_read_only','test_named_match_surface_tracks_current_authority_instead_of_old_viewer']
try:
 for name in files:(root/name).write_bytes(subprocess.check_output(['git','show','5c26616917d19a77a0e548a0baa2a3997112c477:'+name]))
 for test in tests:
  p=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_pygame_match_view.PresentationTests.'+test,'-v'],env={**os.environ,'QT_QPA_PLATFORM':'offscreen','SDL_VIDEODRIVER':'dummy','SDL_AUDIODRIVER':'dummy'},capture_output=True,text=True)
  log=p.stdout+p.stderr;(out/('before-'+test+'.log')).write_text(log)
  assert p.returncode!=0 and 'FAIL:' in log and '\nERROR:' not in log,(test,log)
  receipt.append({'test':test,'returncode':p.returncode,'intended_assertion_failure':True})
finally:
 for name,data in saved.items():(root/name).write_bytes(data);assert (root/name).read_bytes()==data
 (out/'before-restoration.json').write_text(json.dumps({'controls':receipt,'restored':{name:hashlib.sha256(data).hexdigest() for name,data in saved.items()}},indent=2)+'\n')
print('PASS3 intended baseline assertion failures; all saved source bytes restored')
