#!/usr/bin/env python3
"""[designed: T66] Intended assertion failures only; full saved bytes restored in finally."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]


def main():
    target=Path(sys.argv[1]);target.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',QT_QPA_PLATFORM='offscreen',TMPDIR=str(ROOT/'.cache/tmp'))
    cases=[
        ('ordering','goal2/desktop/match_view.py','packet[1] != self.sequence','False',
         'goal2.tests.test_pygame_match_view.PresentationTests.test_order_display_copy_and_once_completion'),
        ('framebuffer','goal2/desktop/pygame_viewer.py','font.render(line, True','font.render(line.replace("2 — 1", "0 — 0"), True',
         'goal2.tests.test_pygame_match_view.PresentationTests.test_real_framebuffer_matches_original_text_projection'),
        ('live-follow','goal2/desktop/pygame_viewer.py','return 10**9, follow, finished','return scroll, False, finished',
         'goal2.tests.test_pygame_match_view.PresentationTests.test_real_framebuffer_matches_original_text_projection'),
        ('raw-rating','goal2/desktop/match_view.py','record[18:20]','record[16:18]',
         'goal2.tests.test_pygame_match_view.PresentationTests.test_raw_rating_original_word_boundaries'),
        ('shared-start','goal2/desktop/jobs.py',"self.busy or getattr(self.model,'match_pending',False)",'self.busy',
         'goal2.tests.test_pygame_match_view.PresentationTests.test_real_viewer_cancel_duplicate_and_failed_start_preserve_save'),
        ('qualifier-priority','goal2/desktop/window.py','self.watched.fixture()','pass',
         'goal2.tests.test_pygame_match_view.PresentationTests.test_qt_heartbeat_blocked_tail_and_actual_viewer_quit'),
        ('lock-ownership','goal2/desktop/watched.py','if self._pending_owned:','if True:',
         'goal2.tests.test_pygame_match_view.OriginalQtAcceptance.test_original_qt_save_resume_repeat'),
        ('once-publication','goal2/game/watched_publication.py',"        self._pending=None\n        if self.owner.state is not original or self.owner.state!=snapshot or self.owner.template_bytes!=template:\n            raise ValueError('watched completion is stale; active state changed')",'        # [designed: negative control] Retain the consumed token and allow its second publication.',
         'goal2.tests.test_pygame_match_view.OriginalQtAcceptance.test_original_qt_save_resume_repeat'),
        ('save-continuation','goal2/desktop/model.py','self.state=candidate;self.template_bytes=raw;self.save_path=Path(path)',
         'self.state=candidate;self.template_bytes=raw;self.save_path=Path(path);self.state.rng_seed_8336 ^= 1',
         'goal2.tests.test_pygame_match_view.OriginalQtAcceptance.test_original_qt_save_resume_repeat'),
    ]
    receipts=[]
    for name,file,before,after,test in cases:
        path=ROOT/file;saved=path.read_bytes();source=saved.decode()
        if source.count(before)!=1:raise ValueError(f'{name}: mutation anchor differs')
        try:
            path.write_text(source.replace(before,after))
            result=subprocess.run([sys.executable,'-B','-m','unittest',test,'-v'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
            output=result.stdout.decode(errors='replace')
            (target/f'{name}.log').write_text(output)
            intended=result.returncode!=0 and 'FAIL:' in output and '\nERROR:' not in output and 'ModuleNotFoundError' not in output
            receipts.append({'name':name,'test':test,'returncode':result.returncode,'intended_assertion_failure':intended,'file':file,'restored_sha256':hashlib.sha256(saved).hexdigest()})
            if not intended:raise AssertionError(f'{name} did not produce intended assertion failure; inspect retained log')
        finally:
            path.write_bytes(saved)
            assert path.read_bytes()==saved
    (target/'controls.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print(json.dumps(receipts,indent=2));print(f'PASS all{len(cases)} intended assertion controls; saved source bytes restored')


if __name__=='__main__':main()
