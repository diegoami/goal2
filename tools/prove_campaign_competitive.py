#!/usr/bin/env python3
"""[designed: T51] Reproduce missing behavior and strong saved-byte assertion controls.
Run mutations sequentially after readers; every edited consumer file is restored in finally.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from watched_evidence import archaeology

ROOT=Path(__file__).resolve().parents[1]
BASE='f880138bbeaf612157d389cc235f9d7675aba696'
MODULES=('test_campaign_competitive_match','test_campaign_competitive_publication','test_campaign_competitive_save')
MUTATIONS=(
 ('competitive-to-friendly setup bypass','goal2/game/quick_match.py',
  "    campaign=getattr(game_state,'campaign',None)",
  "    return template\n    campaign=getattr(game_state,'campaign',None)",
  'goal2.tests.test_campaign_competitive_save.CompetitiveSaveTests.test_quick_setup_is_private_and_preserves_strict_template_refusals'),
 ('winner resolution bypass','goal2/game/watched_schema.py','if winner!=expected:','if False:',
  'goal2.tests.test_campaign_competitive_save.CompetitiveSaveTests.test_no_world_compact_resolution_survives_later_friendly_and_rejects_damage'),
 ('penalty kicks published as normal goals','goal2/game/watched_publication.py',
  "'teams':[fixture.first,fixture.second],'score':list(result['score']),'goals':",
  "'teams':[fixture.first,fixture.second],'score':list(result['board']['final_score']),'goals':",
  'goal2.tests.test_campaign_competitive_publication.CompetitivePublicationTests.test_original_winner_and_full_tail_publish_once_without_quick_effects'),
 ('premature completion without original end','goal2/game/watched_publication.py',
  "not kinds or kinds[-1]!='end' or kinds.count('end')!=1 or kinds.count('full_time')!=1",
  "False",
  'goal2.tests.test_campaign_competitive_publication.CompetitivePublicationTests.test_stale_options_kind_budget_incomplete_and_view_failures_are_atomic'),
 ('memory captured before original tail','goal2/game/watched_match.py','memory = match.memory_component()',
  'memory = image.memory_component()',
  'goal2.tests.test_campaign_competitive_match.CompetitiveAdapterTests.test_owner_budget_cases_match_independent_execution_and_guest_stamps'),
 ('optional runtime imported by ordinary quick campaign','goal2/game/campaign_rounds.py',
  "        allowed=(1,)\n        if competitive:\n            from goal2.engine.original_match.match import KINDS\n            allowed=tuple(k for k in KINDS if k!=1)",
  "        from goal2.engine.original_match.match import KINDS\n        allowed=tuple(k for k in KINDS if k!=1) if competitive else (1,)",
  'goal2.tests.test_campaign_competitive_save.CompetitiveSaveTests.test_quick_setup_is_private_and_preserves_strict_template_refusals'),

 ('World winner inferred from tied normal goals','goal2/game/watched_publication.py',
  "'winner':result['winner'] if competitive else", "'winner':2 if competitive else",
  'goal2.tests.test_campaign_competitive_publication.CompetitivePublicationTests.test_world_knockout_keeps_original_winner_separate_from_tied_normal_goals'),

)


def run(command,folder,log,timeout=240):
    start=time.monotonic()
    with log.open('x') as stream:
        child=subprocess.run(command,cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,
            env={**os.environ,'GOAL2_ARCHAEOLOGY':os.environ.get('GOAL2_ARCHAEOLOGY') or str(archaeology())})
    return {'command':command,'exit_code':child.returncode,'wall_s':round(time.monotonic()-start,3),
            'log':str(log.relative_to(ROOT)),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--case',type=int,choices=range(len(MUTATIONS)),help='run one existing control')
    args=parser.parse_args();folder=ROOT/'.cache'/('T51-proofs-'+str(time.time_ns()));folder.mkdir();rows=[]
    if args.baseline:
        archive=subprocess.check_output(['git','archive',BASE],cwd=ROOT);export=folder/'application';export.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(export,filter='data')
        (export/'.cache').symlink_to(ROOT/'.cache',target_is_directory=True)
        tests=[]
        for name in MODULES:
            source=ROOT/'goal2/tests'/(name+'.py');shutil.copyfile(source,export/'goal2/tests'/source.name)
            tests.extend(n.name for n in ast.walk(ast.parse(source.read_text())) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
        row=run([sys.executable,'-B','-m','unittest',*['goal2.tests.'+m for m in MODULES],'-v'],export,folder/'baseline.log')
        text=(folder/'baseline.log').read_text()
        if row['exit_code']==0 or 'ERROR:' in text or any('FAIL: '+test not in text for test in tests):
            raise AssertionError('every new behavior must fail by assertion against the accepted baseline: '+str(folder))
        row.update(source=BASE,archive_sha256=hashlib.sha256(archive).hexdigest(),assertion_tests=tests)
        rows.append(row);print(f'PASS all{len(tests)} new tests fail by assertion on accepted baseline',flush=True)
    else:
        for number,(name,file,old,new,test) in enumerate(MUTATIONS):
            if args.case is not None and number!=args.case:continue
            path=ROOT/file;saved=path.read_bytes()
            try:
                text=saved.decode()
                if text.count(old)!=1:raise AssertionError('mutation site changed: '+name)
                path.write_text(text.replace(old,new))
                row=run([sys.executable,'-B','-m','unittest',test,'-v'],ROOT,folder/(str(number)+'.log'))
                output=(folder/(str(number)+'.log')).read_text()
                if row['exit_code']==0 or 'FAIL:' not in output or 'ERROR:' in output:
                    raise AssertionError('expected specific assertion failure, not error or timeout: '+name+'; '+str(folder))
                row.update(name=name,assertion_killed=True,source_before_sha256=hashlib.sha256(saved).hexdigest())
                rows.append(row);print('PASS assertion kills '+name,flush=True)
            finally:
                path.write_bytes(saved)
                if path.read_bytes()!=saved:raise AssertionError('saved source restoration failed')
    (folder/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS '+str(folder),flush=True)


if __name__=='__main__':main()
