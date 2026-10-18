#!/usr/bin/env python3
"""[designed: T82] Saved-byte synthetic controls; never runs alongside other readers.

Each mutant must fail its intended assertion (no ERROR/import/timeout counts).
Original bytes are restored in finally and verified exactly. Only text and hashes
are retained; tests inject synthetic journals, not original game resources.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    directory=ROOT/'docs/evidence/T82'/f'controls-{time.time_ns()}'
    directory.mkdir(parents=True)
    cases=[
        ('raw-axis','goal2/game/watched_pitch.py','signed(raw[0]), signed(raw[1]), raw[18]','signed(raw[1]), signed(raw[0]), raw[18]','observation'),
        ('raw-team','goal2/game/watched_pitch.py','players.append([slot, team, number, word','players.append([slot, 1-team, number, word','observation'),
        ('raw-visibility','goal2/game/watched_pitch.py',"int.from_bytes(raw[:2], 'little') == sentinel",'False','observation'),
        ('token','goal2/game/watched_jobs.py','if identity != token:', 'if False:', 'test_token_rejection'),
        ('sequence','goal2/game/watched_pitch.py',"or value['sequence'] != sequence",'or False','test_sequence_rejection'),
        ('schema','goal2/game/watched_pitch.py','integer(x,-128,127)','True','test_schema_rejection'),
        ('watermark','goal2/game/watched_pitch.py',"integer(value['watermark'], previous_watermark, 2**31-1)","integer(value['watermark'], 0, 2**31-1)",'test_watermark_regression_rejection'),
        ('total-budget','goal2/game/watched_jobs.py','if size > MAX_FRAME_BYTES:','if False:','test_total_buffer_overflow'),
        ('read-budget','goal2/game/watched_jobs.py','self._frames.read(FRAME_READ_BUDGET)','self._frames.read(FRAME_READ_BUDGET*4)','test_separate_bounded_consumer_and_ack_order'),
        ('ack-delivered','goal2/game/watched_jobs.py','sequence < self._frame_sequence','sequence <= self._frame_sequence','test_separate_bounded_consumer_and_ack_order'),
        ('deferred-publication','goal2/game/watched_jobs.py','if self._frame_ack != self._frame_sequence - 1:','if False:','test_deferred_once_only_publication'),
    ]
    receipt=dict(platform=platform.platform(),python=sys.version,kind='synthetic saved-byte controls',cases=[])
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    positive=subprocess.run([sys.executable,'-B','-m','unittest',
        'goal2.tests.test_watched_pitch_jobs.PitchTransportTests',
        'goal2.tests.test_watched_pitch_jobs.PitchObservationTests','-v'],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    (directory/'positive.log').write_text(positive.stdout+positive.stderr)
    assert positive.returncode==0,'positive synthetic suite failed'
    receipt['positive']='PASS bounded transport, cancellation/death, saved-state and raw pose edges'
    for name,relative,before,after,test in cases:
        path=ROOT/relative;original=path.read_bytes();mutated=original.replace(before.encode(),after.encode())
        assert mutated!=original,f'{name}: mutation target missing'
        record=dict(name=name,file=relative,before_sha256=sha(original),mutated_sha256=sha(mutated))
        try:
            path.write_bytes(mutated)
            result=subprocess.run([sys.executable,'-B','-m','unittest',
                ('goal2.tests.test_watched_pitch_jobs.PitchObservationTests.test_raw_signed_identity_visibility_and_generic_countries' if test=='observation' else 'goal2.tests.test_watched_pitch_jobs.PitchTransportTests.'+test),'-v'],
                cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            output=result.stdout+result.stderr
            (directory/(name+'.log')).write_text(output)
            assert result.returncode==1 and 'FAIL:' in output and 'AssertionError' in output and '\nERROR:' not in output, f'{name}: intended assertion did not fail: {output}'
            record['intended_assertion_failed']=True
        finally:
            path.write_bytes(original)
            assert path.read_bytes()==original,f'{name}: exact source restoration failed'
            record['restored_sha256']=sha(path.read_bytes())
            receipt['cases'].append(record)
            (directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(f'PASS {len(cases)} intended assertion failures; exact bytes restored; {directory.relative_to(ROOT)}')


if __name__=='__main__':main()
