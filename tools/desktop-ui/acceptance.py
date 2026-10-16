#!/usr/bin/env python3
"""[designed: T69] Real Qt interactions over verified local game resources."""
import argparse
import copy
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import Qt,QCoreApplication,QEvent,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow


def management(template,data,screenshot=None):
    app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        save=Path(folder)/'desktop.g2save'
        model=DesktopModel.open(template,data,save,country=4)
        window=ManagementWindow(model);window.show();QTest.qWait(80)
        def click(widget):
            QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def country(number):
            window.country.setFocus();QTest.keyClick(window.country,Qt.Key.Key_Home)
            for _ in range(number-1):QTest.keyClick(window.country,Qt.Key.Key_Down)
        def toggle(row):
            window.table.setCurrentCell(row,0);window.table.setFocus();QTest.keyClick(window.table,Qt.Key.Key_Space);app.processEvents()
        original=copy.deepcopy(model.state)
        country(13)
        assert model.state==original,'country draft mutated active game'
        assert window.country.currentData()==13
        click(window.new)
        assert model.state.managed_country==13
        assert window.title.text()==model.goaldat.country_names[13]
        assert [window.table.item(i,1).text() for i in range(20)]==[model.goaldat.player_names[w] for w in model.state.managed_squad]
        for row in list(range(9))+list(range(11,20)):toggle(row)
        window.captain.setFocus();QTest.keyClick(window.captain,Qt.Key.Key_End)
        for _,box in window.tactics:
            if not box.isChecked():click(box)
        click(window.confirm)
        assert model.state.starting_eleven==list(range(250,261))
        assert model.state.captain==260 and model.state.country_tactics==255
        assert window.status.text()=='Management confirmed'
        confirmed=copy.deepcopy(model.state)
        toggle(19);click(window.confirm)
        assert model.state==confirmed and 'eleven' in window.status.text()
        click(window.cancel)
        assert window.selected_ids()==confirmed.starting_eleven
        injured=260;rec=bytearray(model.state.players[injured]);rec[14]=0;rec[16]=0x88;model.state.players[injured]=bytes(rec)
        window.refresh();before=copy.deepcopy(model.state);click(window.confirm)
        assert model.state==before and 'unavailable' in window.status.text()
        assert 'Injured' in window.table.item(19,6).text() and 'Suspended' in window.table.item(19,6).text() and 'carried booking' in window.table.item(19,6).text()
        toggle(19);toggle(0);click(window.confirm)
        assert injured not in model.state.starting_eleven and 241 in model.state.starting_eleven
        assert model.state.captain in model.state.starting_eleven
        click(window.save);assert save.is_file()
        saved=save.read_bytes();snapshot=copy.deepcopy(model.state)
        country(4);assert model.state==snapshot
        click(window.new);assert model.state.managed_country==4
        with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('resume regenerated players')):
            click(window.resume)
        assert model.state==snapshot,'complete saved state was not resumed'
        seeds=(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        window.refresh();window.refresh();assert model.state==snapshot
        assert seeds==(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        bad=Path(folder)/'bad.g2save';bad.write_bytes(b'broken')
        window.path.setText(str(bad));click(window.resume)
        assert model.state==snapshot and 'Cannot resume' in window.status.text()
        blocked=Path(folder)/'not-a-directory';blocked.write_text('blocked')
        window.path.setText(str(blocked/'save.g2save'));click(window.save)
        assert model.state==snapshot and 'Cannot save' in window.status.text() and save.read_bytes()==saved
        window.path.setText(str(save));click(window.resume)
        assert model.state==snapshot
        assert str(model.view()['morale']) in window.summary.text()
        if screenshot:window.grab().save(str(screenshot))
        window.close();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.processEvents()
        app.shutdown()
    print('PASS management: real Qt country/draft/XI/captain260/all tactics, injury/ban repair, complete save/resume, failure rollback and pure redraw')


def launch(template,data):
    # [designed: T69] Exercise the real CLI entry and normal window close.
    from goal2.desktop.__main__ import main as desktop_main
    app=QApplication.instance() or QApplication([])
    errors=[]
    def close():
        windows=[w for w in app.topLevelWidgets() if isinstance(w,ManagementWindow)]
        if len(windows)!=1:errors.append('real entry did not create its management window')
        elif windows[0].model.state.managed_country!=13:errors.append('real entry ignored selected country')
        app.closeAllWindows();app.quit()
    QTimer.singleShot(150,close)
    with tempfile.TemporaryDirectory() as folder:
        result=desktop_main(['--template',str(template),'--data',str(data),'--country','13','--save',str(Path(folder)/'game.g2save')])
    assert result==0 and not errors,errors
    print('PASS launch: real desktop entry, country13, window close and clean Qt shutdown')


def friendlies(template,data,screenshot=None,blocked=False):
    # [designed: T70] Exercise actual buttons and real subprocesses; no HTTP.
    from goal2.desktop.worker import play as direct_play
    from goal2.desktop.jobs import QuickJobs
    import time
    app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        model=DesktopModel.open(template,data,Path(folder)/'game.g2save',country=4)
        window=ManagementWindow(model);window.show();QTest.qWait(80)
        def click(widget):QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def finish():
            deadline=time.monotonic()+15
            while window.jobs.busy and time.monotonic()<deadline:QTest.qWait(20)
            assert not window.jobs.busy,'worker did not complete'
        if blocked:
            click(window.confirm)
            before=copy.deepcopy(model.state)
            window.jobs=QuickJobs(model,command=[sys.executable,'-c','import time;time.sleep(60)'])
            beats=[];heartbeat=QTimer();heartbeat.setInterval(10);heartbeat.timeout.connect(lambda:beats.append(1));heartbeat.start()
            click(window.play);assert window.jobs.busy
            process=window.jobs.process
            assert not window.confirm.isEnabled() and not window.new.isEnabled() and window.stop.isEnabled()
            QTest.qWait(150);assert len(beats)>=5,'blocked worker stopped Qt heartbeat'
            click(window.stop);assert process.poll() is not None and model.state==before
            assert window.play.isEnabled() and 'cancelled' in window.status.text()
            click(window.play);process=window.jobs.process
            start=time.monotonic();window.close()
            assert time.monotonic()-start<2 and process.poll() is not None and model.state==before
            heartbeat.stop()
        else:
            # Country selection and confirmation through real controls.
            window.country.setCurrentIndex(window.country.findData(4));click(window.new)
            window.tactics[0][1].toggle();click(window.confirm)
            direct=copy.deepcopy(model.state)
            first=direct.campaign.next_fixture
            for n in range(2):
                expected=direct_play(direct,model.template_bytes)
                click(window.play);assert window.jobs.busy
                finish();assert model.state==expected,window.status.text()
                assert model.state.match_count==n+1 and len(model.state.campaign.results)==n+1
                match=model.state.last_match
                assert model.goaldat.country_names[match['teams'][0]] in window.result.text()
                assert f"{match['score'][0]} — {match['score'][1]}" in window.result.text()
                for goal in match['goals']:assert model.goaldat.player_names[goal['player']] in window.result.text()
                assert 'Quick simulation' in window.result.text()
                direct=expected
                click(window.save);snapshot=copy.deepcopy(model.state)
                click(window.new);click(window.resume);assert model.state==snapshot
            assert model.state.campaign.results[0]['teams']==[first.side_a,first.side_b]
            before=copy.deepcopy(model.state);click(window.play)
            assert not window.jobs.busy and model.state==before and 'unsupported' in window.status.text()
            assert 'Unsupported fixture' in window.summary.text()
            # Explicit standalone mode and repeat; full continuation remains saveable.
            click(window.friendly);click(window.confirm);assert model.state.campaign is None
            direct=copy.deepcopy(model.state)
            for _ in range(2):
                direct=direct_play(direct,model.template_bytes)
                click(window.play);finish();assert model.state==direct,window.status.text()
            click(window.save);click(window.new);click(window.resume);assert model.state==direct
            if screenshot:window.grab().save(str(screenshot))
            window.close()
        window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();app.shutdown()
    print('PASS worker' if blocked else 'PASS campaign-friendlies: two scheduled fixtures, complete state/RNG/history, save/resume, boundary and standalone repeat')


def main():
    p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['management','launch','campaign-friendlies','worker'],required=True)
    p.add_argument('--template',required=True,type=Path);p.add_argument('--data',required=True,type=Path);p.add_argument('--screenshot',type=Path)
    args=p.parse_args()
    if args.scenario=='management':management(args.template,args.data,args.screenshot)
    elif args.scenario=='launch':launch(args.template,args.data)
    else:friendlies(args.template,args.data,args.screenshot,blocked=args.scenario=='worker')
if __name__=='__main__':main()
