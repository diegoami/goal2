#!/usr/bin/env python3
"""[designed: #254] Real Windows file-sharing regression through controller.poll.
The controlled read stall and inert engine/viewer isolate status I/O; this is
not original-match or UI acceptance. The writer uses real production status().
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from goal2.desktop import watched
from goal2.tests.test_desktop_watched_sharing import SharingTests


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence-dir',required=True,type=Path)
    args=parser.parse_args()
    assert sys.platform=='win32','real native Windows is required; no simulated-platform acceptance'
    out=args.evidence_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    report={'tag':'[designed: #254] Real native status read/replace interleave',
            'platform':platform.platform(),'python':sys.version,
            'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'controller_sha256':hashlib.sha256((ROOT/'goal2/desktop/watched.py').read_bytes()).hexdigest(),
            'scope':'Actual controller status read and native writer; inert engine/viewer; not match/UI acceptance',
            'cases':[],'result':'RUNNING'}
    try:
        # [designed: #254] Repeat the same deterministic interleave on three fresh owned files.
        for index in range(3):
            helper=SharingTests();row={'index':index,'reader_interleave_visited':False}
            with tempfile.TemporaryDirectory(prefix='fix254-sharing-')as folder:
                controller=helper.controller(folder);path=Path(folder)/'status';value=helper.value(controller)
                path.write_text(json.dumps(value,indent=2));old=path.read_bytes()
                original_open=Path.open
                factory=getattr(watched,'_open_status',lambda target:original_open(target,'rb'))
                opened=[];children=[]
                class InterleavedRead:
                    def __init__(self,stream):self.stream=stream;opened.append(stream)
                    def __enter__(self):return self
                    def __exit__(self,*exc):return self.stream.__exit__(*exc)
                    def read(self,size):
                        row['reader_interleave_visited']=True
                        code='import json,sys;from pathlib import Path;from goal2.desktop.pygame_viewer import status;status(Path(sys.argv[1]),json.loads(sys.argv[2]))'
                        start=time.monotonic()
                        child=subprocess.Popen([sys.executable,'-B','-c',code,str(path),json.dumps(value)],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        children.append(child)
                        try:stdout,stderr=child.communicate(timeout=5)
                        finally:
                            if child.poll()is None:child.kill();child.wait(timeout=2)
                        row.update(writer_exit=child.returncode,writer_seconds=time.monotonic()-start,writer_stderr=stderr.decode('utf-8',errors='replace'))
                        return self.stream.read(size)
                def shared(target):return InterleavedRead(factory(target))
                def legacy_open(target,*a,**kw):
                    stream=original_open(target,*a,**kw)
                    return InterleavedRead(stream)if target==path and a==('rb',)else stream
                row['production_factory']='_open_status'if hasattr(watched,'_open_status')else'Path.open'
                context=patch.object(watched,'_open_status',shared)if hasattr(watched,'_open_status')else patch.object(Path,'open',legacy_open)
                try:
                    with context:published=controller.poll()
                    row.update(published=published,old_snapshot_validated=controller.last_status==value,
                               old_snapshot_byte_count=len(old),replacement_complete=path.read_bytes()==json.dumps(value).encode(),
                               replacement_bytes_differ=path.read_bytes()!=old,pending_retained=controller.model.match_pending)
                finally:
                    row['all_read_handles_closed']=all(stream.closed for stream in opened)
                    row['owned_writers_reaped']=all(child.poll()is not None for child in children)
                    controller.process=None
                report['cases'].append(row)
            assert row['reader_interleave_visited'],'production read factory was not visited'
            assert row['writer_exit']==0,'native production writer could not replace status while its actual reader remained open'
            assert row['old_snapshot_validated']and not row['published']and row['pending_retained']
            assert row['replacement_complete']and row['replacement_bytes_differ']
            assert row['all_read_handles_closed']and row['owned_writers_reaped']
        report['result']='PASS'
    except BaseException as error:
        report.update(result='FAIL',failure=repr(error));raise
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS native status sharing: three real controller-read/atomic-writer interleaves, complete snapshots, handles closed and writers reaped')


if __name__=='__main__':main()
