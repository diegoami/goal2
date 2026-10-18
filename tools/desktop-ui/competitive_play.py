#!/usr/bin/env python3
"""[designed: T80] Real Qt competitive Play; actual engines vs synthetic IPC waits.
Original resources stay in ignored caches. Default offscreen; set QT_QPA_PLATFORM
and use xvfb-run for the separate xcb platform run. No screenshot is committed.
"""
import builtins
import copy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QCoreApplication,QEvent,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.data.goaldat import load
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.tests.test_campaign_competitive_publication import campaign
from goal2.tests.test_desktop_competitive_jobs import direct

BLOCK=[sys.executable,'-c','import time;time.sleep(60)']


def main():
    app=QApplication.instance() or QApplication([])
    data=load((ROOT/'.cache/GOAL.DAT').read_bytes())
    receipts=[]
    def click(widget):
        QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
    def finish_window(window):
        window.close();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
    with tempfile.TemporaryDirectory(prefix='goal2-T80-Qt-') as folder:
        for kind,index in ((2,21),(200,42)):
            state,raw,fixture=campaign(index,kind)
            model=DesktopModel(data,raw,Path(folder)/f'kind{kind}.g2save');model.state=state
            window=ManagementWindow(model);window.show();app.processEvents()
            try:
                assert model.state.captain==0
                assert window.captain.currentData()==0,'loaded automatic captain was replaced by a named draft'
                assert window.captain.currentText()=='Original captain selection'
                assert window.draft()==(state.starting_eleven,0,state.country_tactics)
                before=copy.deepcopy(model.state)
                model.save(model.save_path);prior_bytes=model.save_path.read_bytes()
                click(window.resume)
                assert model.state==before and window.captain.currentData()==0
                assert 'competitive' in window.play.text().lower()
                click(window.watch)
                assert 'friendlies only' in window.status.text(),window.status.text()
                assert model.state==before and not getattr(model,'match_pending',False)
                click(window.play)
                assert model.match_pending and window.competitive.busy,'Play did not start the original competitive child'
                assert not window.jobs.busy and not window.watched.busy
                assert not window.save.isEnabled() and not window.confirm.isEnabled()
                token=window.competitive.token
                window.start_match();assert window.competitive.token==token
                for operation in (window.jobs.start,window.watched.start):
                    try:operation()
                    except ValueError as exc:assert 'already running' in str(exc)
                    else:raise AssertionError('another match overlapped competitive Play')
                try:model.save(model.save_path)
                except ValueError as exc:assert 'Saving during a match' in str(exc)
                else:raise AssertionError('midmatch save was accepted')
                assert model.save_path.read_bytes()==prior_bytes and model.state==before
                statuses=set();started=time.monotonic()
                while window.competitive.busy and time.monotonic()-started<180:
                    app.processEvents();statuses.add(window.status.text());QTest.qWait(5)
                assert not window.competitive.busy,'competitive job exceeded test guard'
                expected=direct(kind)
                assert window.competitive.outcome==expected,'UI child differs from direct accepted T51 input'
                assert model.state.mem==expected.memory and model.state.last_match['seeds']==list(expected.seeds)
                assert window.competitive.outcome.events[-1].kind=='end'
                assert any('Original competitive engine:' in value for value in statuses),'no live competitive progress reached Qt'
                text=window.result.text()
                assert 'Original engine' in text and 'Regulation' in text
                assert data.country_names[fixture.first] in text and data.country_names[fixture.second] in text
                if kind==200:
                    assert expected.result['score']==[0,0] and expected.result['shootout'] is not None
                    assert 'Extra time' in text and 'Penalties:' in text and 'Winner:' in text
                assert window.confirm.isEnabled() and window.save.isEnabled() and not getattr(model,'match_pending',False)
                after=copy.deepcopy(model.state);click(window.save);click(window.resume)
                assert model.state==after and window.captain.currentData()==0
                assert window.result.text()==text
                receipts.append(dict(mode='real original engine and Qt controls',kind=kind,index=index,
                    source='424d5998076da1e4efc399c2715689ddb44d3e1a',captain_override=None,
                    budget=[5,5],reference_seed=None,delay_byte=None,policy='default play_on',
                    memory_sha256=hashlib.sha256(expected.memory).hexdigest(),
                    events_sha256=hashlib.sha256(json.dumps([asdict(e) for e in expected.events],sort_keys=True).encode()).hexdigest(),
                    seeds=list(expected.seeds),result_label=text,progress_updates=len(statuses),
                    full_outcome_equals_direct=True,save_resume_exact=True))
                print(f'PASS real Qt competitive kind{kind} index{index}: original result/events/Memory/both seeds, progress, captain0, save/resume',flush=True)
            finally:finish_window(window)

        # [designed] Bounded synthetic children visit UI ownership/refusal boundaries.
        state,raw,_=campaign(21,2);model=DesktopModel(data,raw,Path(folder)/'failures.g2save');model.state=state
        window=ManagementWindow(model);window.show();app.processEvents()
        try:
            before=copy.deepcopy(model.state);model.save(model.save_path);prior=model.save_path.read_bytes()
            original_import=builtins.__import__
            def without_unicorn(name,*args,**kwargs):
                if name=='unicorn':raise ImportError('synthetic optional-runtime absence')
                return original_import(name,*args,**kwargs)
            with patch('builtins.__import__',side_effect=without_unicorn):click(window.play)
            assert 'pip install' in window.status.text() and 'desktop,watched' in window.status.text()
            assert model.state==before and window.confirm.isEnabled() and not getattr(model,'match_pending',False)
            raw=model.template_bytes;model.template_bytes=b'broken'
            click(window.play)
            assert 'local game resources' in window.status.text()
            model.template_bytes=raw
            assert model.state==before and model.save_path.read_bytes()==prior
            window.competitive.command=BLOCK
            click(window.play);assert window.competitive.busy and model.match_pending
            process=window.competitive.process
            click(window.stop)
            assert process.poll() is not None and not getattr(model,'match_pending',False) and model.state==before
            assert model.save_path.read_bytes()==prior
            # [designed] Explicit new campaign action returns to existing friendly paths.
            window.country.setCurrentIndex(window.country.findData(4));click(window.new)
            assert model.state.campaign.next_fixture.kind==1
            assert window.play.text()=='Play quick friendly'
            window.jobs.command=BLOCK
            friendly=copy.deepcopy(model.state);click(window.play)
            assert window.jobs.busy and model.match_pending
            try:window.competitive.start()
            except ValueError as exc:assert 'Another match' in str(exc)
            else:raise AssertionError('competitive Play overlapped Quick')
            try:window.watched.start()
            except ValueError as exc:assert 'already running' in str(exc)
            else:raise AssertionError('Watch overlapped Quick')
            quick=window.jobs.process;click(window.stop)
            assert quick.poll() is not None and model.state==friendly and not getattr(model,'match_pending',False)
            window.watched.engine.command=BLOCK;window.watched.viewer_command=BLOCK
            click(window.watch);assert window.watched.busy and model.match_pending
            try:window.competitive.start()
            except ValueError as exc:assert 'Another match' in str(exc)
            else:raise AssertionError('competitive Play overlapped friendly Watch')
            window.competitive.close()
            assert model.match_pending,'inactive competitive close unlocked friendly Watch'
            window.set_busy(False);assert not window.save.isEnabled() and not window.play.isEnabled()
            click(window.stop)
            assert not getattr(model,'match_pending',False) and model.state==friendly and window.confirm.isEnabled()
            receipts.append(dict(mode='synthetic blocked child and optional-runtime/resource failures',
                state_and_prior_save_preserved=True,mutual_exclusion=['competitive','Quick','friendly Watch'],
                inactive_controller_preserves_other_lock=True))
            print('PASS synthetic Qt lifecycle: runtime/resource guidance, cancel, prior save, Quick/Watch/competitive exclusion and inactive ownership',flush=True)
        finally:finish_window(window)
    report=ROOT/'docs/evidence/T80'/f'competitive-play-{time.time_ns()}.json'
    report.write_text(json.dumps(dict(platform=platform.platform(),python=sys.version,qt_platform=app.platformName(),
                                    receipts=receipts),indent=2)+'\n')
    print(report.relative_to(ROOT));app.shutdown()


if __name__=='__main__':main()
