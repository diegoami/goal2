#!/usr/bin/env python3
"""[designed: T66] Real Qt controls, SDL child and independent original continuation."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop.window import ManagementWindow
from goal2.desktop.match_view import completion
from goal2.tests.test_pygame_match_view import model,pump
from goal2.tests.test_watched_adapter import direct
from goal2.game.watched_publication import WatchedPublication
from goal2.game.watched_match import WatchedOutcome,engine_year
from goal2.engine.original_match import Fixture,Image
from goal2.engine.original_match.match import Event


def expected(owner):
    f=owner.state.campaign.next_fixture
    fixture=Fixture(f.side_a,f.side_b,int(f.fixture_id.split(':')[1]))
    publication=WatchedPublication(owner);job=publication.begin(fixture)
    result,memory,events=direct(job.state,fixture,seed=None,delay=0)
    image=Image.from_memory_component(memory)
    outcome=WatchedOutcome(result,memory,tuple(Event(**e) for e in events),
                           (image.rd(0x7b62),image.rd(0x8336)),engine_year(job.state.campaign))
    publication.complete(job.token,outcome)
    return outcome,events


def main():
    app=QApplication.instance() or QApplication([])
    receipts=[]
    with tempfile.TemporaryDirectory() as folder:
        save=Path(folder)/'watched.g2save';m=model(save);w=ManagementWindow(m);w.show();app.processEvents()
        beats=[];heartbeat=QTimer();heartbeat.setInterval(5);heartbeat.timeout.connect(lambda:beats.append(time.monotonic()));heartbeat.start()
        try:
            w.country.setCurrentIndex(w.country.findData(4));QTest.mouseClick(w.new,Qt.MouseButton.LeftButton);app.processEvents()
            w.captain.setCurrentIndex(3)
            w.tactics[0][1].setChecked(not w.tactics[0][1].isChecked())
            QTest.mouseClick(w.confirm,Qt.MouseButton.LeftButton);app.processEvents()
            assert m.state.managed_country==4 and m.state.captain==w.captain.currentData()
            assert w.draft()==(m.state.starting_eleven,m.state.captain,m.state.country_tactics)
            control=type(m)(m.goaldat,m.template_bytes,Path(folder)/'control');control.state=copy.deepcopy(m.state)
            for round_number in range(2):
                outcome,events=expected(control)
                before=copy.deepcopy(m.state);beats.clear()
                QTest.mouseClick(w.watch,Qt.MouseButton.LeftButton);app.processEvents()
                assert w.watched.busy,w.status.text()
                engine=w.watched.engine.process;viewer=w.watched.process
                w.start_watched();w.start_match();w.refresh();assert w.watched.engine.process is engine
                def finished():return not w.watched.busy
                pump(finished,app=app,timeout=300)
                assert m.state==control.state,'complete state/Memory/both RNG/history differs from direct original'
                assert m.state.match_count==before.match_count+1
                assert len(beats)>5,'Qt heartbeat did not run during original execution'
                display=w.watched.display
                assert display.events==json.loads(json.dumps(events)),'displayed ordered events differ from independent original'
                expected_view=completion(outcome,m.goaldat.player_names)
                assert display.result==expected_view,'board/raw ratings/MOTM differ'
                # [derived: F014 at424d5998076da1e4efc399c2715689ddb44d3e1a] Independent raw Memory read.
                original_players=Image.from_memory_component(outcome.memory).players()
                for side in display.result['ratings']:
                    for row in side:assert row['word']==int.from_bytes(original_players[row['player']][18:20],'little')
                assert 'Original engine' in w.result.text()
                assert any('Raw rating' in line for line in display.lines())
                pump(lambda:w.watched.last_status and w.watched.last_status['sequence']==display.sequence,app=app)
                assert w.watched.last_status['digest']==display.digest(),'real SDL child display differs'
                state=copy.deepcopy(m.state)
                for _ in range(4):w.poll_watched();w.refresh();app.processEvents()
                assert m.state==state,'redraw published again'
                QTest.mouseClick(w.save,Qt.MouseButton.LeftButton);app.processEvents();assert save.is_file()
                saved=save.read_bytes()
                QTest.mouseClick(w.resume,Qt.MouseButton.LeftButton);app.processEvents()
                assert m.state==control.state,'Qt resume lost completed original continuation'
                assert save.read_bytes()==saved
                if round_number==0:
                    # [designed] An old completed viewer cannot release a newer quick job's lock.
                    from goal2.desktop.jobs import QuickJobs
                    quick=QuickJobs(m,command=[sys.executable,'-c','import time;time.sleep(60)'])
                    quick.start();w.set_busy(True);other=quick.process
                    try:
                        w.watched.cancel();w.poll_watched()
                        assert m.match_pending and not w.save.isEnabled() and not w.confirm.isEnabled()
                        assert other.poll() is None and quick.busy
                        try:m.save(save)
                        except ValueError:pass
                        else:raise AssertionError('old viewer close permitted mid-match save')
                        assert m.state==control.state and save.read_bytes()==saved
                    finally:quick.cancel();w.set_busy(False)
                else:w.watched.close_viewer();w.poll_watched()
                assert viewer.poll() is not None
                receipts.append({'round':round_number+1,'fixture':outcome.result['index'],'events':len(events),
                    'score':outcome.result['score'],'heartbeats':len(beats),'digest':display.digest(),
                    'seeds':list(outcome.seeds),'state_memory_rng_history_equal':True})
            # [designed] Closing the Qt owner reaps only its two children and keeps the saved result.
            if m.state.campaign.next_fixture.kind==1:
                snapshot=copy.deepcopy(m.state);saved=save.read_bytes();w.start_watched();engine=w.watched.engine.process;viewer=w.watched.process
                w.close();app.processEvents()
                assert engine.poll() is not None and viewer.poll() is not None
                assert m.state==snapshot and save.read_bytes()==saved
            print(json.dumps(receipts,indent=2));print('PASS T66 Qt controls + original events/board/raw ratings/MOTM + SDL acknowledgement + save/resume/repeat')
        finally:heartbeat.stop();w.close();w.deleteLater();app.processEvents()
    return receipts


if __name__=='__main__':main()
