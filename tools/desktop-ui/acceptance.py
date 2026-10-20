#!/usr/bin/env python3
"""[designed: T69] Real Qt interactions over verified local game resources."""
from navigation import reveal
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
            reveal(widget);QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def country(number):
            window.country.setFocus();QTest.keyClick(window.country,Qt.Key.Key_Home)
            for _ in range(number-1):QTest.keyClick(window.country,Qt.Key.Key_Down)
        def toggle(row):
            reveal(window.table);window.table.setCurrentCell(row,0);window.table.setFocus();QTest.keyClick(window.table,Qt.Key.Key_Space);app.processEvents()
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
        def click(widget):reveal(widget);QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def finish():
            deadline=time.monotonic()+15
            while window.jobs.busy and time.monotonic()<deadline:
                QTest.qWait(20)
                if window.jobs.halftime is not None:click(window.continue_match)
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
            before=copy.deepcopy(model.state);prior=model.save_path.read_bytes()
            assert model.state.campaign.next_fixture.kind==5
            try:window.jobs.start()
            except ValueError as exc:assert 'unsupported' in str(exc)
            else:raise AssertionError('Quick accepted a competitive fixture')
            assert not window.jobs.busy and model.state==before and model.save_path.read_bytes()==prior
            assert 'Original competitive' in window.summary.text() and 'competitive' in window.play.text()
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


def pool(template,data,screenshot=None):
    # [designed: T71] Real Qt search/position/exchange, full-ID save/play/resume.
    from goal2.desktop.worker import play as direct_play
    import time
    app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        model=DesktopModel.open(template,data,Path(folder)/'pool.g2save',country=4)
        window=ManagementWindow(model);window.resize(1500,900);window.show();QTest.qWait(80)
        def click(widget):reveal(widget);QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def select(table,row,col=1):
            item=table.item(row,col);table.scrollToItem(item);app.processEvents()
            reveal(table);QTest.mouseClick(table.viewport(),Qt.MouseButton.LeftButton,pos=table.visualItemRect(item).center());app.processEvents()
        def search(text):
            reveal(window.search);window.search.setFocus();QTest.keyClick(window.search,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
            QTest.keyClick(window.search,Qt.Key.Key_Backspace)
            if text:QTest.keyClicks(window.search,text)
            app.processEvents()
        def position(code):
            reveal(window.position);window.position.setFocus();QTest.keyClick(window.position,Qt.Key.Key_Home)
            for _ in range(0 if code is None else code+1):QTest.keyClick(window.position,Qt.Key.Key_Down)
            app.processEvents()
        def finish():
            deadline=time.monotonic()+15
            while window.jobs.busy and time.monotonic()<deadline:
                QTest.qWait(20)
                if window.jobs.halftime is not None:click(window.continue_match)
            assert not window.jobs.busy,'worker deadline exceeded'
        before=copy.deepcopy(model.state)
        assert window.reserves.rowCount()==80 and window.table.rowCount()==20
        target=next(r for r in model.pool_view()['reserves'] if r['id']==2561)
        search(target['name'].swapcase());position(target['position'])
        assert model.state==before and window.reserves.rowCount()>0
        ids=[window.reserves.item(i,0).data(Qt.ItemDataRole.UserRole) for i in range(window.reserves.rowCount())]
        assert 2561 in ids
        assert all(target['name'].casefold() in window.reserves.item(i,1).text().casefold() for i in range(window.reserves.rowCount()))
        outgoing=model.state.starting_eleven[0]
        window.captain.setCurrentIndex(window.captain.findData(outgoing));click(window.confirm)
        records=list(model.state.players);seeds=(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        select(window.table,model.state.managed_squad.index(outgoing));select(window.reserves,ids.index(2561))
        click(window.exchange)
        assert 2561 in model.state.managed_squad and 2561 in model.state.starting_eleven
        assert model.state.captain==2561 and outgoing in model.state.campaign.reserve_ids
        assert model.state.players==records and seeds==(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        search('');position(None)
        assert window.reserves.rowCount()==80 and '20 / Reserves 80' in window.pool_summary.text()
        assert len(set(model.state.managed_squad+model.state.campaign.reserve_ids))==100
        assert all(model.state.players[w][0]==4 for w in model.state.managed_squad+model.state.campaign.reserve_ids)
        click(window.confirm);assert model.state.captain==2561
        # Invalid selected IDs and unavailable incoming player refuse via real action.
        snapshot=copy.deepcopy(model.state);window.reserves.clearSelection();window.reserves.setCurrentCell(-1,-1);click(window.exchange)
        assert model.state==snapshot and 'Select one' in window.status.text()
        rec=bytearray(model.state.players[2562]);rec[14]=0;rec[16]=0x80;model.state.players[2562]=bytes(rec)
        window.refresh();ids=[window.reserves.item(i,0).data(Qt.ItemDataRole.UserRole) for i in range(80)]
        select(window.table,0);select(window.reserves,ids.index(2562));snapshot=copy.deepcopy(model.state);click(window.exchange)
        assert model.state==snapshot and 'unavailable' in window.status.text()
        # Existing XI gate rejects a now-unavailable selected reserve, then repairs it.
        rec=bytearray(model.state.players[2561]);old_record=bytes(rec);rec[14]=0;model.state.players[2561]=bytes(rec)
        window.refresh();snapshot=copy.deepcopy(model.state);click(window.confirm)
        assert model.state==snapshot and 'unavailable' in window.status.text()
        model.state.players[2561]=old_record;window.refresh();click(window.confirm)
        click(window.save);snapshot=copy.deepcopy(model.state)
        click(window.new)
        with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('load regenerated')):click(window.resume)
        assert model.state==snapshot and model.state.captain==2561
        window.refresh();search('nobody matches this');search('');assert model.state==snapshot
        expected=direct_play(snapshot,model.template_bytes)
        click(window.play);assert window.jobs.busy and not window.pool_panel.isEnabled()
        finish();assert model.state==expected,window.status.text()
        effect=model.state.match_state['campaign_energy']['pool']
        assert effect['confidence_draws']==160 and model.state.match_count==1
        click(window.save);snapshot=copy.deepcopy(model.state);click(window.resume);assert model.state==snapshot
        assert model.state.campaign.reserve_ids==expected.campaign.reserve_ids
        expected=direct_play(model.state,model.template_bytes);click(window.play);finish();assert model.state==expected
        assert 'pending managed friendly' in window.pool_summary.text() and not window.exchange.isEnabled()
        snapshot=copy.deepcopy(model.state);click(window.exchange);assert model.state==snapshot
        assert len(set(model.state.managed_squad+model.state.campaign.reserve_ids))==100
        if screenshot:window.grab().save(str(screenshot))
        window.close();window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();app.shutdown()
    print('PASS campaign-pool: search/filter, 20/80 identities, exchange/captain2561, unavailable/closed refusal, save/resume, ordered condition and real play')


def halftime(template,data,screenshot=None):
    # [designed: T47] Real first/second-half worker with explicit Qt decisions.
    from goal2.game.quick_match import begin_full_match
    from goal2.game.state import to_savestate
    from goal2.engine.savestate import Savestate
    from goal2.desktop.worker import complete
    from goal2.game.campaign_rounds import prepare as prepare_round
    import time
    app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        model=DesktopModel.open(template,data,Path(folder)/'halftime.g2save',country=4)
        model.exchange(80,2561);model.confirm(list(model.state.starting_eleven),61,165)
        model.save(model.save_path);saved=model.save_path.read_bytes();before=copy.deepcopy(model.state)
        window=ManagementWindow(model);window.show();QTest.qWait(60)
        def click(widget):reveal(widget);QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def wait_for(predicate):
            deadline=time.monotonic()+15
            while not predicate() and time.monotonic()<deadline:QTest.qWait(20)
            assert predicate(),window.status.text()
        click(window.play);pid=window.jobs.process.pid
        wait_for(lambda:window.jobs.halftime is not None)
        assert model.state==before and model.state.match_count==0
        assert 'Halftime:' in window.result.text() and 'Saving is unavailable' in window.status.text()
        assert not window.save.isEnabled() and not window.exchange.isEnabled()
        try:model.save(model.save_path)
        except ValueError as exc:assert 'Saving during' in str(exc)
        else:raise AssertionError('half-time save unexpectedly accepted')
        assert model.save_path.read_bytes()==saved
        # Select full-ID reserve and the confirmed captain using real combo events.
        window.half_out.setFocus();QTest.keyClick(window.half_out,Qt.Key.Key_Home)
        assert window.half_out.currentData()==61
        window.half_in.setFocus();QTest.keyClick(window.half_in,Qt.Key.Key_End)
        assert window.half_in.currentData()==2561
        click(window.substitute)
        assert window.jobs.halftime['captain']==2561
        assert 2561 in window.jobs.halftime['eleven'] and 61 in window.jobs.halftime['removed']
        assert window.half_in.findData(61)==-1
        assert model.state==before
        # Independent direct continuation with identical change; no engine restart.
        candidate=prepare_round(before,model.template_bytes)
        match=begin_full_match(Savestate(to_savestate(candidate,original=model.template_bytes)),candidate)
        match.substitute(61,2561);expected=complete(candidate,match.finish(retain_state=True),template=model.template_bytes)
        if screenshot:window.grab().save(str(screenshot))
        click(window.continue_match);assert window.jobs.process.pid==pid
        assert not window.continue_match.isEnabled()
        try:window.jobs.continue_match()
        except ValueError:pass
        else:raise AssertionError('duplicate continuation accepted')
        wait_for(lambda:not window.jobs.busy)
        assert model.state==expected and model.state.captain==2561
        assert model.state.match_count==1 and len(model.state.campaign.results)==1
        assert model.state.managed_squad[:11]==model.state.starting_eleven
        click(window.save);snapshot=copy.deepcopy(model.state);click(window.new);click(window.resume)
        assert model.state==snapshot and model.state.captain==2561
        # Next scheduled fixture uses the saved XI, then cancel without publication.
        click(window.play);wait_for(lambda:window.jobs.halftime is not None)
        assert 2561 in window.jobs.halftime['eleven'] and 61 not in window.jobs.halftime['eleven']
        model.confirm(list(model.state.starting_eleven),model.state.captain,90)
        snapshot=copy.deepcopy(model.state);process=window.jobs.process;click(window.continue_match)
        assert model.state==snapshot and process.poll() is not None
        assert not window.jobs.busy and window.play.isEnabled() and 'stale' in window.status.text()
        click(window.play);wait_for(lambda:window.jobs.halftime is not None)
        snapshot=copy.deepcopy(model.state);process=window.jobs.process;start=time.monotonic()
        click(window.stop)
        assert time.monotonic()-start<2 and process.poll() is not None and model.state==snapshot
        assert window.save.isEnabled() and not window.continue_match.isEnabled()
        window.close();window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents();app.shutdown()
    print('PASS campaign-halftime: real pause/substitute/captain2561/no re-entry/continue once, full state/save/resume/next XI, cancel and safe save refusal')


def continental(template,data,screenshot=None):
    # [designed: T50] Real Qt start-year choice and Play through a whole stage 2, once to
    # qualification and once to elimination, with save/resume mid-group. Bounded inputs: the
    # fixed seeds of New campaign and the two managed countries below; unavailable starters
    # are replaced by repair(), as a manager would.
    from goal2.desktop.worker import play as direct_play
    from goal2.game import continental_qualifying
    import time
    app=QApplication.instance() or QApplication([])
    receipts=[]
    for country,expected in QUALIFYING_PATHS:
        with tempfile.TemporaryDirectory() as folder:
            model=DesktopModel.open(template,data,Path(folder)/'qualifying.g2save',country=country)
            window=ManagementWindow(model);window.show();QTest.qWait(60)
            def click(widget):reveal(widget);QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
            def wait(busy):
                deadline=time.monotonic()+180
                while busy() and time.monotonic()<deadline:
                    QTest.qWait(30)
                    if window.jobs.halftime is not None:click(window.continue_match)
                assert not busy(),'match did not finish: '+window.status.text()
            assert window.start_year.currentData()==1990 and model.state.campaign.stage==5
            before=copy.deepcopy(model.state)
            window.start_year.setFocus();QTest.keyClick(window.start_year,Qt.Key.Key_Down);app.processEvents()
            assert window.start_year.currentData()==1992 and model.state==before,'start year is a draft'
            click(window.new)
            campaign=model.state.campaign
            assert (campaign.start_year,campaign.stage,model.state.managed_country)==(1992,2,country)
            assert 'In progress' in window.qualifying.text()
            competitive=0
            while (pending:=model.state.campaign.next_fixture) is not None:
                if repair(model):window.refresh()
                done=len(model.state.campaign.completed_fixture_ids)
                if pending.kind==1:
                    expected_state=direct_play(model.state,model.template_bytes)
                    click(window.play);assert window.jobs.busy,window.status.text()
                    wait(lambda:window.jobs.busy);assert model.state==expected_state,window.status.text()
                else:
                    assert 'competitive' in window.play.text().lower()
                    click(window.play);assert window.competitive.busy,window.status.text()
                    wait(lambda:window.competitive.busy);competitive+=1
                assert model.state.campaign.completed_fixture_ids[done:]==[pending.fixture_id],window.status.text()
                if competitive==3 and pending.kind!=1:
                    # Save/resume mid-group: the persisted draw and schedule come back unchanged.
                    click(window.save);snapshot=copy.deepcopy(model.state)
                    view=model.qualifying();assert not view['complete'] and view['qualifiers'] is None
                    click(window.new);assert model.state!=snapshot
                    with patch('goal2.game.campaign_schedule.build_opening_campaign',side_effect=AssertionError('resume drew again')):
                        click(window.resume)
                    assert model.state==snapshot and model.qualifying()==view,'mid-group resume changed the campaign'
            world=model.state.campaign.world
            assert competitive==6 and len(world.results)==len(world.fixtures)==768,'stage 2 did not resolve every fixture'
            outcome=continental_qualifying.outcome(model.state.campaign,model.template_bytes,country)
            assert outcome['managed']['status']==expected,outcome['managed']
            text=window.qualifying.text()
            assert ('Qualified' if expected=='qualified' else 'Eliminated') in text,text
            for continent,winners in outcome['qualifiers'].items():
                assert len(winners)==8 and all(model.goaldat.country_names[c] in text for c in winners)
            assert not window.play.isEnabled() and 'this stage is complete' in window.fixture_routes.text()
            assert 'Stage complete' in window.overview_fixture.text()
            click(window.save);snapshot=copy.deepcopy(model.state);click(window.new);click(window.resume)
            assert model.state==snapshot and window.qualifying.text()==text
            receipts.append(f"{model.goaldat.country_names[country]} {expected} (group {outcome['managed']['group']}, rank {outcome['managed']['rank']})")
            if screenshot:window.grab().save(str(screenshot))
            window.close();window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
    app.shutdown()
    print('PASS continental-qualifying: real start-year choice, 12 managed fixtures (6 original competitive), mid-group save/resume without a redraw, 768 world results, 32 group winners, '+'; '.join(receipts))


def repair(model):
    """[designed: T50] As a manager would: replace each unavailable starter with the first
    available reserve of the same position group, else any available outfield reserve."""
    rows={r['id']:r for r in model.view()['players']};state=model.state
    free=[w for w in state.managed_squad if rows[w]['availability']['available']]
    eleven=list(state.starting_eleven)
    if set(eleven)<=set(free):return False
    for i,word in enumerate(eleven):
        if word in free:continue
        bench=[w for w in free if w not in eleven];group=rows[word]['position']
        eleven[i]=next((w for w in bench if rows[w]['position']==group),None) or next(
            w for w in bench if (rows[w]['position']=='Goalkeeper')==(group=='Goalkeeper'))
    model.confirm(eleven,state.captain if state.captain in eleven else eleven[0],state.country_tactics)
    return True


# [designed: T50] Managed countries whose fixed-seed stage 2 ends in each path.
QUALIFYING_PATHS=((7,'qualified'),(4,'eliminated'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['management','launch','campaign-friendlies','worker','campaign-pool','campaign-halftime','continental-qualifying'],required=True)
    p.add_argument('--template',required=True,type=Path);p.add_argument('--data',required=True,type=Path);p.add_argument('--screenshot',type=Path)
    args=p.parse_args()
    if args.scenario=='management':management(args.template,args.data,args.screenshot)
    elif args.scenario=='launch':launch(args.template,args.data)
    elif args.scenario=='campaign-pool':pool(args.template,args.data,args.screenshot)
    elif args.scenario=='campaign-halftime':halftime(args.template,args.data,args.screenshot)
    elif args.scenario=='continental-qualifying':continental(args.template,args.data,args.screenshot)
    else:friendlies(args.template,args.data,args.screenshot,blocked=args.scenario=='worker')
if __name__=='__main__':main()
