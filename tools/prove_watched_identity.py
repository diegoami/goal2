#!/usr/bin/env python3
"""[designed: T51a] Prove strict dual-profile guards; restore each saved source in finally.
Run sequentially after other suites: these controls temporarily change consumer code.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='goal2/game/watched_schema.py'
MUTATIONS=[
 ('unknown raw result fields accepted',SCHEMA,'if keys is None or set(result)!=keys:', 'if keys is None:',
  'test_exact_profiles_keep_actual_engine_identity'),
 ('current friendly resolution unchecked',SCHEMA,"_players(result) if competitive else _friendly_kit2(result)","_players(result) if competitive else None",
  'test_kit2_remains_friendly_with_exact_default_resolution_and_players'),
 ('historical result silently relabeled',SCHEMA,"if last['engine']!=engine:raise ValueError('watched engine differs from original result profile')",
  "if False:raise ValueError('watched engine differs from original result profile')",
  'test_publication_uses_actual_result_profile_and_save_rejects_relabeling'),
 ('world and history engine mismatch accepted','goal2/game/campaign_rounds.py',
  "or (watched(row) and row['engine']!=match['engine'])",'or False',
  'test_mixed_history_world_preserves_identity_and_strict_quick_rng'),
]


def main():
    folder=ROOT/'.cache'/('watched-identity-proofs-'+str(time.time_ns()));folder.mkdir()
    rows=[]
    for number,(name,file,old,new,test) in enumerate(MUTATIONS):
        path=ROOT/file;saved=path.read_bytes()
        try:
            text=saved.decode()
            if text.count(old)!=1:raise AssertionError('mutation site changed: '+name)
            path.write_text(text.replace(old,new))
            run=subprocess.run([sys.executable,'-B','-m','unittest',
                'goal2.tests.test_watched_kit_identity.KitIdentityTests.'+test,'-v'],
                cwd=ROOT,capture_output=True,text=True,timeout=30)
            output=run.stdout+run.stderr;log=folder/(str(number)+'.log');log.write_text(output)
            if run.returncode==0 or 'FAIL:' not in output or 'ERROR:' in output:
                raise AssertionError('expected targeted assertion failure: '+name+'\n'+output)
            rows.append({'name':name,'test':test,'assertion_killed':True,'log':str(log.relative_to(ROOT)),
                         'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
            print('PASS assertion kills '+name,flush=True)
        finally:path.write_bytes(saved)
    (folder/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('PASS4 dual-profile controls; saved bytes restored; '+str(folder),flush=True)


if __name__=='__main__':main()
