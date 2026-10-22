"""[designed: T76] Native squad interaction and saved-source mutation oracles."""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def scenario(args):
    from PySide6.QtCore import Qt,QCoreApplication,QEvent,qVersion,QPoint
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QLabel,QStyle,QStyleOptionButton
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow,TACTICS
    from goal2.game.session_save import encode
    from navigation import reveal
    app=QApplication([])
    out=Path(args.evidence_dir)
    if out.exists() and any(out.iterdir()):
        i=2
        while (out/f'run-{i:02}').exists():i+=1
        out=out/f'run-{i:02}'
    out.mkdir(parents=True,exist_ok=True)
    report={'tag':'[designed: T76]','platform':platform.platform(),'python':sys.version,'qt':qVersion(),
            'qpa':app.platformName(),'requested_scale':os.environ.get('QT_SCALE_FACTOR','1'),
            'sources':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))},
            'scenario_sha256':digest(__file__),'dispatcher_sha256':digest(ROOT/'tools/desktop-ui/redesign.py'),'resources':{'template':digest(args.template),'data':digest(args.data)},
            'steps':[],'captures':[]}
    window=None;callback_exceptions=[];previous_exception_hook=sys.excepthook
    def callback_exception(kind,error,trace):
        callback_exceptions.append(''.join(traceback.format_exception(kind,error,trace)))
        previous_exception_hook(kind,error,trace)
    sys.excepthook=callback_exception
    def assert_callbacks_clean():
        assert not callback_exceptions,'uncaught Qt callback exception: '+''.join(callback_exceptions)
    try:
        with tempfile.TemporaryDirectory(prefix='T76-squad-') as folder:
            save=Path(folder)/'owned.g2save';model=DesktopModel.open(args.template,args.data,save,country=13)
            model.confirm(list(model.state.starting_eleven),model.state.starting_eleven[0],model.state.country_tactics);model.save(save)
            saved=save.read_bytes();window=ManagementWindow(model);w=window;w.show();w.activateWindow();QTest.qWait(120)
            report['ratio']=w.devicePixelRatioF()
            # [designed: T99] The grouped XI/bench is the roster strip; the player's detail is his card.
            assert getattr(getattr(w,'team_roster',None),'grouped',False) and hasattr(w,'team_card') and w.findChild(QLabel,'draftState') is not None,'grouped XI/bench and draft hierarchy absent'
            assert hasattr(w.pages[1],'footer'),'persistent draft footer absent'
            w.navigate(1);app.processEvents()
            def state():return encode(model.state,model.template_bytes)
            def unchanged(before,label):
                assert state()==before,label+' prematurely published active state'
                assert save.read_bytes()==saved,label+' changed confirmed save bytes'
            def focus(widget):
                if not w.isActiveWindow():w.raise_();w.activateWindow()
                assert QTest.qWaitForWindowActive(w,2000),'owned squad window did not become active'
                widget.setFocus();app.processEvents()
                assert app.focusWidget() is widget,'native focus not acquired: '+widget.objectName()
            def pick(row):
                # [designed: T99] A real click on the strip's row selects that player.
                reveal(w.team_roster);strip=w.team_roster;rect=strip.row_rect(row)
                w.pages[1].ensureVisible(0,strip.mapTo(w.pages[1].widget(),rect.center()).y(),0,rect.height());app.processEvents()
                QTest.mouseClick(strip,Qt.MouseButton.LeftButton,pos=rect.center());app.processEvents()
                assert strip.current==row and w.table.currentRow()==row,'strip click did not select the row'
            def toggle(row):
                before=state();pick(row);focus(w.team_roster)
                QTest.keyClick(w.team_roster,Qt.Key.Key_Space);app.processEvents();unchanged(before,'XI checkbox')
            def key(widget,key):
                before=state();reveal(widget);focus(widget);QTest.keyClick(widget,key);app.processEvents();unchanged(before,'draft control')
            def action(widget):
                before=state();reveal(widget);focus(widget);QTest.keyClick(widget,Qt.Key.Key_Return);app.processEvents()
                assert save.read_bytes()==saved,'draft action changed confirmed save bytes'
                if widget is w.cancel:unchanged(before,'Discard')
            def footer_caption(button,focused):
                other=w.cancel if button is w.confirm else w.confirm
                focus(button if focused else other)
                assert button.hasFocus()==focused,'footer caption focus precondition failed'
                option=QStyleOptionButton();button.initStyleOption(option)
                contents=button.style().subElementRect(QStyle.SubElement.SE_PushButtonContents,option,button)
                metrics=button.fontMetrics();advance=metrics.horizontalAdvance(button.text());text_height=metrics.height()
                record={'size':[w.width(),w.height()],'button':button.objectName(),'text':button.text(),
                        'focused':focused,'widget':[button.width(),button.height()],
                        'contents':[contents.x(),contents.y(),contents.width(),contents.height()],
                        'font_advance':advance,'font_height':text_height,'font':button.font().toString(),
                        'ratio':w.devicePixelRatioF()}
                report.setdefault('footer_captions',[]).append(record)
                assert contents.width()>=advance and contents.height()>=text_height,'footer caption clipped: '+json.dumps(record)
            def capture(name):
                app.processEvents();path=out/(name+'.png');assert w.grab().save(str(path))
                report['captures'].append({'path':path.name,'sha256':digest(path),'size':[w.width(),w.height()],
                                           'scroll':w.pages[1].verticalScrollBar().value(),'focus':app.focusWidget().objectName() if app.focusWidget() else None})
            def detail(row):
                # [designed: T99] The selected player's detail is his card: the same fields, painted.
                pick(row);p=model.view()['players'][row];c=w.team_card.card;w.team_card.grab();drawn=' | '.join(w.team_card.drawn)
                raw={name:value for name,_,_,value in c['characteristics']}
                assert c['id']==p['id'] and c['full_name'].endswith(p['name']) and c['full_name'].upper() in drawn,'selected player raw detail missing '+p['name']
                assert c['role']==p['role'] and c['role'] in drawn,'selected player raw detail missing role'
                assert raw['energy']==p['energy'] and raw['morale']==p['confidence'],'selected player raw detail missing energy/confidence'
                assert str(p['id']) in w.team_card.accessibleName() or c['id']==p['id']
                assert (c['readiness']=='ready to play')==p['availability']['available'] and c['readiness'].upper() in drawn,'selected detail omitted availability'
                for reason in p['availability']['reasons']:
                    shown={'Injured':raw['energy']==0,'Unavailable energy':raw['energy']>=128,'Suspended':c['readiness']=='suspended' or 'suspended' in drawn.lower(),
                           'Sent off':'sent off' in drawn.lower(),'Substituted off':c['readiness']=='substituted'}[reason]
                    assert shown,'selected detail omitted availability'
                if p['availability']['carried_bookings']:assert 'carried booking' in drawn
            capture('initial')
            wanted=list(range(250,261))
            for row in range(20):
                if (w.table.item(row,0).checkState()==Qt.CheckState.Checked)!=(241+row in wanted):toggle(row)
            assert w.selected_ids()==wanted,'full integer player IDs were truncated'
            key(w.captain,Qt.Key.Key_End);assert w.captain.currentData()==260,'captain full ID was truncated'
            assert tuple(e for e,_ in w.tactics)==(5,6,7,1,2,3,4,8)
            for element,box in w.tactics:
                # [designed: T99] A tactic row carries the TACTICS label as its alternatives and
                # names its category and current word; the word follows the bit.
                assert box.property('alternatives')==dict(TACTICS)[element]
                assert box.accessibleName().endswith(': '+(lambda x:x[:1].upper()+x[1:])(dict(TACTICS)[element].split(' / ')[int(box.isChecked())]))
                key(box,Qt.Key.Key_Space)
                if not box.isChecked():key(box,Qt.Key.Key_Space)
            assert w.draft()==(wanted,260,255)
            assert 'Unconfirmed draft' in w.draft_state.text()
            # [designed: T99] The strip: the eleven in the draft's order, a rule, the bench; C marks the captain.
            strip=w.team_roster;shown=[strip.rows[i] for i in strip.order]
            assert strip.eleven()==11 and len(shown)==20 and 'XI 11, bench 9' in strip.accessibleName()
            assert [r[0] for r in shown[:11]]==w.drafted_eleven()
            assert [r[0] for r in shown if r[5]]==[260] and ' C' in strip.accessibleName()
            for p in model.view()['players']:
                row=next(r for r in shown if r[0]==p['id'])
                assert row[1].endswith(p['name']) and p['name'] in strip.accessibleName()
                assert (shown.index(row)<11)==(p['id'] in wanted)
                if p['id'] in wanted:assert row[2]==p['role'] and row[3]==p['line']
            for row in range(20):detail(row)
            capture('dirty-full-id-detail')
            before=state();draft=copy.deepcopy(w.draft())
            for index in (0,2,3,4,1):
                QTest.keyClick(w,Qt.Key.Key_1+index,Qt.KeyboardModifier.ControlModifier);app.processEvents()
                assert w.draft()==draft;unchanged(before,'navigation')
            key(w.country,Qt.Key.Key_Home);assert w.preview is not None
            key(w.country,Qt.Key.Key_Home)
            for _ in range(12):key(w.country,Qt.Key.Key_Down)
            assert w.preview is None and w.draft()==draft,'country return lost active draft'
            action(w.confirm)
            assert model.state.starting_eleven==wanted and model.state.captain==260 and model.state.country_tactics==255,'Confirm did not publish full IDs/all bits'
            confirmed=state();assert 'Confirmed' in w.draft_state.text();capture('confirmed-grouped')
            for row in (19,0):
                toggle(row);action(w.confirm)
                assert state()==confirmed and 'eleven' in w.status.text(),'invalid XI count accepted'
                capture('invalid-count-'+str(len(w.selected_ids())))
                action(w.cancel);assert w.draft()==(wanted,260,255),'Discard did not restore confirmed management'
            # [designed] Force a corrupt captain input through the real Confirm action, independently of combo filtering.
            w.captain.addItem('Invalid captain outside XI',241);key(w.captain,Qt.Key.Key_End);action(w.confirm)
            assert state()==confirmed and 'Captain' in w.status.text(),'invalid captain accepted'
            action(w.cancel)
            for box in (w.tactics[0][1],w.tactics[-1][1]):key(box,Qt.Key.Key_Space)
            action(w.cancel);assert w.draft()==(wanted,260,255),'Discard lost confirmed tactics'
            for word in (260,241):
                rec=bytearray(model.state.players[word]);rec[14]=0;rec[16]=0x88;model.state.players[word]=bytes(rec)
            w.refresh();before=state();action(w.confirm)
            assert state()==before and 'unavailable' in w.status.text(),'unavailable starter was accepted'
            detail(19);capture('unavailable-player-detail');toggle(0)
            assert 241 not in w.selected_ids(),'unavailable reserve added to XI'
            toggle(19);assert 260 not in w.selected_ids(),'unavailable starter could not be removed'
            toggle(1);assert len(w.selected_ids())==11 and 242 in w.selected_ids()
            action(w.confirm);assert 260 not in model.state.starting_eleven and 242 in model.state.starting_eleven
            report['steps'].append('Full IDs250–260, captain260, all8bits; private events/save; Confirm/Discard; invalid10/12/captain; unavailable starter/removal/reserve; navigation/preview return')
            sizes=[(900,640)] if report['ratio']>1 else [(1440,900),(1050,780),(900,700)]
            original_names=model.goaldat.player_names
            # [designed] Generated long names exercise wrapping; original names are restored before workers run.
            names=list(original_names)
            for word in model.state.managed_squad:names[word]='Long national player name '+str(word)+' with extended family name'
            from dataclasses import replace
            model.goaldat=replace(model.goaldat,player_names=names)
            w.refresh()
            for width,height in sizes:
                w.resize(width,height);w.navigate(1);app.processEvents();page=w.pages[1]
                # [designed: T99] The roster and the detail are view 0 (strip and card), the tactics view 1.
                def top(widget):return widget.mapTo(page.widget(),QPoint(0,0)).y()
                for fraction,label,view in ((0,'roster',0),(2,'detail',0),(1,'tactics',1)):
                    w.team_view(view);app.processEvents()
                    scroll=page.verticalScrollBar().maximum()//fraction if fraction else 0
                    page.verticalScrollBar().setValue(scroll);app.processEvents()
                    footer=page.footer
                    assert footer.isVisible() and footer.geometry().bottom()<page.height(),'draft bar is outside page'
                    assert not page.viewport().geometry().intersects(footer.geometry()),'draft bar covers scroll content'
                    assert w.confirm.geometry().right()<footer.width(),'draft action clipped by footer'
                    assert footer.geometry().right()<page.verticalScrollBar().mapTo(page,QPoint(0,0)).x() or not page.verticalScrollBar().isVisible(),'scrollbar overlaps draft action bar'
                    for control in (w.cancel,w.confirm):
                        footer_caption(control,False);footer_caption(control,True)
                        assert control.visibleRegion().boundingRect().height()>0 and control.accessibleName()
                        QTest.keyClick(control,Qt.Key.Key_Tab);app.processEvents();QTest.keyClick(app.focusWidget(),Qt.Key.Key_Backtab);app.processEvents()
                        assert app.focusWidget() is control,'Tab/Shift-Tab did not return to draft action'
                    capture(f'long-{width}x{height}-{label}-focused-confirm')
                name_rows=set();value_rows=set()
                # [designed: T99] Every strip row is brought into the page viewport and selected; its
                # complete name is painted on the card, never elided, with its raw fields.
                w.team_view(0);app.processEvents();strip=w.team_roster
                for row in range(20):
                    rect=strip.row_rect(row);y=strip.mapTo(page.widget(),rect.topLeft()).y()
                    page.ensureVisible(0,y+rect.height()//2,0,rect.height());app.processEvents()
                    origin=strip.mapTo(page.viewport(),rect.topLeft())
                    if origin.y()>=0 and origin.y()+rect.height()<=page.viewport().height():
                        detail(row);app.processEvents()
                        name=w.team_card.card['full_name'].upper()
                        if name in w.team_card.drawn:name_rows.add(row)
                        value_rows.add(row)
                    capture(f'long-{width}x{height}-roster-row-{row+1}')
                assert name_rows==set(range(20)),'long-name captures missed complete roster names'
                assert value_rows==set(range(20)),'roster captures missed complete raw fields/availability'
                report.setdefault('roster_coverage',[]).append({'size':[width,height],'name_rows':sorted(name_rows),'value_rows':sorted(value_rows)})
                # [designed] Read every table column through its native contained horizontal scroll.
                for row in range(20):
                    for col in range(7):w.table.scrollToItem(w.table.item(row,col));app.processEvents();assert w.table.item(row,col).text() or col==0
                for widget,name,view in ((w.team_card_area,'selected-detail',0),(w.team_roster,'grouped-xi-bench',0)):
                    w.team_view(view);app.processEvents()
                    # [designed] Overlap viewport segments so long wrapped values are readable in full across captures.
                    intervals=[];step=max(40,page.viewport().height()-100)
                    for offset in range(0,widget.height(),step):
                        page.verticalScrollBar().setValue(top(widget)-16+offset);app.processEvents()
                        first=page.verticalScrollBar().value()-top(widget);bottom=first+page.viewport().height()
                        intervals.append([max(0,first),min(widget.height(),bottom)])
                        capture(f'long-{width}x{height}-{name}-segment-{offset}')
                        if bottom>=widget.height():break
                    assert intervals[0][0]==0 and max(end for start,end in intervals)>=widget.height(),'scroll captures missed a reading area'
                    assert all(first[1]>=second[0]+40 for first,second in zip(intervals,intervals[1:])),'reading captures lack wrapped-line overlap'
                    report.setdefault('reading_coverage',[]).append({'size':[width,height],'widget':name,'height':widget.height(),'intervals':intervals,'text_sha256':hashlib.sha256((w.team_card if widget is w.team_card_area else widget).accessibleName().encode()).hexdigest()})
            model.goaldat=replace(model.goaldat,player_names=original_names)
            model.new_campaign(4);model.exchange(80,2561);model.confirm(list(model.state.starting_eleven),61,165);w.refresh()
            # [derived: T47] Real private first-half worker, substitution and cancellation preserve confirmed management.
            import time
            before=state();reveal(w.play);focus(w.play);QTest.mouseClick(w.play,Qt.MouseButton.LeftButton);app.processEvents()
            deadline=time.monotonic()+20
            while w.jobs.halftime is None and time.monotonic()<deadline:QTest.qWait(20)
            assert w.jobs.halftime is not None,'real halftime worker did not pause: '+w.status.text()
            assert state()==before and not w.confirm.isEnabled() and not w.table.isEnabled()
            reveal(w.half_out);focus(w.half_out);QTest.keyClick(w.half_out,Qt.Key.Key_Home)
            reveal(w.half_in);focus(w.half_in);QTest.keyClick(w.half_in,Qt.Key.Key_End)
            assert w.half_out.currentData()==61 and w.half_in.currentData()==2561
            reveal(w.substitute);QTest.mouseClick(w.substitute,Qt.MouseButton.LeftButton);app.processEvents()
            assert w.jobs.halftime['captain']==2561 and 2561 in w.jobs.halftime['eleven'] and w.half_in.findData(61)==-1
            assert state()==before and save.read_bytes()==saved
            owned_directory=Path(w.jobs.directory);started=time.monotonic()
            reveal(w.stop);QTest.mouseClick(w.stop,Qt.MouseButton.LeftButton);app.processEvents();assert_callbacks_clean()
            assert time.monotonic()-started<2,'Cancel exceeded existing bounded wait'
            assert not w.jobs.busy and state()==before and save.read_bytes()==saved
            assert w.jobs.folder is None and not owned_directory.exists(),'owned worker folder remains after Cancel'
            # [designed: T76/#233] Real Qt Cancel also visits one transient own-folder sharing error deterministically.
            reveal(w.play);focus(w.play);QTest.mouseClick(w.play,Qt.MouseButton.LeftButton);app.processEvents()
            deadline=time.monotonic()+20
            while w.jobs.halftime is None and time.monotonic()<deadline:QTest.qWait(20)
            assert w.jobs.halftime is not None,'second real halftime worker did not pause'
            owned_folder=w.jobs.folder;owned_directory=Path(owned_folder.name);cleanup=owned_folder.cleanup;cleanup_calls=[]
            def transient_cleanup():
                cleanup_calls.append(True)
                if len(cleanup_calls)==1:
                    error=PermissionError('owned stderr handle still closing');error.winerror=32;raise error
                cleanup()
            with patch.object(owned_folder,'cleanup',side_effect=transient_cleanup):
                started=time.monotonic();reveal(w.stop);QTest.mouseClick(w.stop,Qt.MouseButton.LeftButton);app.processEvents();assert_callbacks_clean()
                assert time.monotonic()-started<2,'sharing retry exceeded existing cancellation bound'
            assert len(cleanup_calls)>=2,'transient owned sharing violation did not retry'
            assert w.jobs.folder is None and not owned_directory.exists(),'owned sharing-error folder remains after Cancel'
            assert not w.jobs.busy and state()==before and save.read_bytes()==saved
            report['cleanup_retry_calls']=len(cleanup_calls)
            report['steps'].append('Real pending halftime, captain2561 private substitution/no re-entry, disabled management and cancellation without publication')
            report['result']='PASS'
    except BaseException as exc:
        report['failure']=str(exc);report['exception']=type(exc).__name__;raise
    finally:
        if window is not None:
            window.close();window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        app.quit();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        report['callback_exceptions']=callback_exceptions
        sys.excepthook=previous_exception_hook
        if callback_exceptions:report.update(result='FAIL',failure='uncaught Qt callback exception',exception='AssertionError')
        report['clean_widgets']=not bool(app.topLevelWidgets())
        report['sources_after']={name:digest(ROOT/name) for name in report['sources']}
        report['source_unchanged']=report['sources']==report['sources_after']
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        assert report['source_unchanged'],'source changed during squad scenario'
        assert report['clean_widgets'],'owned Qt widgets remained after cleanup'
        assert_callbacks_clean()
    print('PASS squad: real private drafts/full IDs/eligibility, grouped raw detail, persistent actions, navigation, real pending halftime; '+str(out))


def negative_controls(args):
    out=Path(args.evidence_dir)
    if out.exists() and any(out.iterdir()):out=out/('negative-'+str(len(list(out.iterdir()))+1))
    out.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/'goal2/desktop/squad_page.py',ROOT/'goal2/desktop/window.py',ROOT/'goal2/desktop/model.py',ROOT/'goal2/desktop/style.py']
    saved={p:p.read_bytes() for p in paths};receipt={'tag':'[designed: T76]','cases':[],'before':{str(p.relative_to(ROOT)):digest(p) for p in paths}}
    command=[sys.executable,'-B',str(ROOT/'tools/desktop-ui/redesign.py'),'--scenario','squad','--template',args.template,'--data',args.data,'--single-scale']
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','QT_SCALE_FACTOR':'1'}
    def run(name,cmd,expected,scale='1'):
        r=subprocess.run(cmd,cwd=ROOT,env={**env,'QT_SCALE_FACTOR':scale},capture_output=True,text=True,timeout=120)
        (out/(name+'.log')).write_text(r.stdout+r.stderr)
        assert r.returncode!=0 and 'AssertionError' in r.stderr and expected in r.stderr,name+' missed intended assertion: '+r.stderr
        receipt['cases'].append({'name':name,'command':cmd,'returncode':r.returncode,'expected':expected,'scale':scale,'mutated_sources':{str(p.relative_to(ROOT)):digest(p) for p in paths}})
    def legacy(name,scenario_name):
        cmd=[sys.executable,'-B','tools/desktop-ui/acceptance.py','--scenario',scenario_name,'--template',args.template,'--data',args.data]
        result=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
        (out/(name+'.log')).write_text(result.stdout+result.stderr)
        receipt.setdefault('legacy_coverage',[]).append({'name':name,'command':cmd,'returncode':result.returncode,'assertion_failed':'AssertionError' in result.stderr})
    try:
        p=paths[0];p.write_bytes(subprocess.check_output(['git','show','f1697ef628508ac19130299194d751990ca7fa9e:goal2/desktop/squad_page.py'],cwd=ROOT))
        # [designed] Restore matching baseline window as it has no additive presentation bindings.
        paths[1].write_bytes(subprocess.check_output(['git','show','f1697ef628508ac19130299194d751990ca7fa9e:goal2/desktop/window.py'],cwd=ROOT))
        run('baseline',command+['--evidence-dir',str(out/'baseline')],'grouped XI/bench and draft hierarchy absent')
        for p,raw in saved.items():p.write_bytes(raw)
        p=paths[2];source=p.read_text();old='candidate.captain=captain;';assert source.count(old)==1
        p.write_text(source.replace(old,'candidate.captain=captain & 255;'))
        run('truncated-captain',command+['--evidence-dir',str(out/'truncated-captain')],'Confirm did not publish full IDs/all bits')
        run('truncated-management',[sys.executable,'-B','tools/desktop-ui/acceptance.py','--scenario','management','--template',args.template,'--data',args.data],'AssertionError')
        legacy('truncated-captain-halftime','campaign-halftime')
        p.write_bytes(saved[p]);p=paths[1];source=p.read_text();old='        self.country.currentIndexChanged.connect(self.country_changed)';assert source.count(old)==1
        p.write_text(source.replace(old,old+'\n        for _,box in self.tactics:box.toggled.connect(lambda *_:self.model.confirm(self.selected_ids(),self.captain.currentData(),self.draft()[2]))'))
        run('eager-tactic',command+['--evidence-dir',str(out/'eager-tactic')],'prematurely published active state')
        # [designed] Record actual legacy coverage without claiming isolation assertions they do not have.
        legacy('eager-legacy-management','management');legacy('eager-legacy-halftime','campaign-halftime')
        p.write_bytes(saved[p]);source=p.read_text();old='.data(Qt.ItemDataRole.UserRole) for row in range(20)'
        assert source.count(old)==1
        p.write_text(source.replace(old,'.data(Qt.ItemDataRole.UserRole) & 255 for row in range(20)'))
        run('truncated-player-id',command+['--evidence-dir',str(out/'truncated-player-id')],'full integer player IDs were truncated')
        for p,raw in saved.items():p.write_bytes(raw)
        p=paths[3];source=p.read_text();lines=source.splitlines(keepends=True)
        old_border=[line for line in lines if line.startswith('    QWidget#draftBar QPushButton')]
        assert len(old_border)==2,'scoped stable footer border pair absent'
        p.write_text(''.join(line for line in lines if line not in old_border))
        run('focused-caption-old-border',command+['--evidence-dir',str(out/'focused-caption-old-border')],'footer caption clipped',scale='2')
    finally:
        for p,raw in saved.items():p.write_bytes(raw)
        receipt['after']={str(p.relative_to(ROOT)):digest(p) for p in paths};receipt['restored']=all(p.read_bytes()==raw for p,raw in saved.items())
        (out/'negative-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['restored'];print('PASS squad negative controls: baseline/truncated captain/eager tactics/full IDs/focused captions; exact saved bytes restored')
