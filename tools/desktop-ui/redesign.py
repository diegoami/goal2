#!/usr/bin/env python3
"""[designed: T74] Real Qt shell interactions; no match runtime required."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def contrast(a,b):
    def luminance(color):
        values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(v*w for v,w in zip(values,(.2126,.7152,.0722)))
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)

def shell(args):
    # [designed] Import Qt only after the native caller has selected scaling.
    from PySide6.QtCore import Qt,qVersion,QPoint
    from PySide6.QtGui import QPalette
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QAbstractButton,QComboBox,QLineEdit,QLabel
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.desktop.style import COLORS
    from goal2.game.session_save import encode
    app=QApplication([])
    evidence=Path(args.evidence_dir)
    if evidence.exists() and any(evidence.iterdir()):
        index=2
        while (evidence/f'run-{index:02}').exists():index+=1
        evidence=evidence/f'run-{index:02}'
    evidence.mkdir(parents=True,exist_ok=True);args.evidence_dir=str(evidence)
    report={'tag':'[designed: T74]','platform':platform.platform(),'python':sys.version,
            'qt':qVersion(),'qpa':app.platformName(),'requested_scale':os.environ.get('QT_SCALE_FACTOR','1'),
            'sources':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))},
            'scenario_sha256':digest(__file__),'resources':{'template':digest(args.template),'data':digest(args.data)},
            'transitions':[],'captures':[],'reachable':[]}
    # [designed] Both enabled and disabled reading colors, and the focus boundary, are measured.
    pairs=(('body','text','background',4.5),('panel text','text','panel',4.5),
           ('disabled','secondary','panel',4.5),('table','ink','paper',4.5),
           ('selected','ink','accent',4.5),('focus','focus','panel',3),('control boundary','divider','panel',3),('selected focus','ink','accent',3))
    report['contrast']={}
    for name,foreground,background,minimum in pairs:
        value=contrast(COLORS[foreground],COLORS[background]);assert value>=minimum,(name,value)
        report['contrast'][name]=value
    with tempfile.TemporaryDirectory(prefix='T74-shell-') as folder:
        save=Path(folder)/'generated.g2save'
        model=DesktopModel.open(args.template,args.data,save,country=4)
        model.save(save)
        window=ManagementWindow(model);window.show();window.activateWindow();QTest.qWait(120)
        report['ratio']=window.devicePixelRatioF()
        screen=window.screen();report['available']=[screen.availableGeometry().width(),screen.availableGeometry().height()]
        assert hasattr(window,'navigation') and len(window.navigation)==5,'five-destination navigation is absent'
        assert len(window.pages)==5,'five destination pages are absent'
        names=('Overview','Squad & tactics','National pool','Fixtures & results','Save / resume')
        assert tuple(b.accessibleName() for b in window.navigation)==names,'navigation names/order changed'
        starts=[]
        patches=[patch.object(controller,'start',side_effect=lambda *a,kind=kind,**kw:starts.append(kind))
                 for kind,controller in (('quick',window.jobs),('competitive',window.competitive),('watched',window.watched))]
        for patched in patches:patched.start()
        try:
            def snapshot():
                return (encode(model.state,model.template_bytes),copy.deepcopy(window.draft()),
                        copy.deepcopy(window.active_draft),id(window.preview),
                        encode(window.preview.state,window.preview.template_bytes) if window.preview else None,
                        save.read_bytes(),model.save_path,window.path.text(),model.state.match_count,
                        tuple(starts),getattr(model,'match_pending',False),
                        tuple(c.process for c in (window.jobs,window.competitive,window.watched)))
            labels=('encoded_active','draft','active_draft','preview_identity','encoded_preview','save_bytes','save_path','path_text','match_count','starts','pending','controller_processes')
            def delta(before,after):
                def describe(value):return hashlib.sha256(value).hexdigest() if isinstance(value,bytes) else repr(value)
                return [{'field':name,'before':describe(a),'after':describe(b)} for name,a,b in zip(labels,before,after) if a!=b]
            def native_input(target):
                app.processEvents()
                if not window.isActiveWindow():window.raise_();window.activateWindow()
                assert QTest.qWaitForWindowActive(window,2000),'owned shell window is not active before synthetic input'
                target.setFocus();app.processEvents();QTest.qWait(150)
                assert window.isActiveWindow() and app.activeWindow() is window,'owned shell activation lost before synthetic input'
                if args.surface_input_control=='wrong-focus' and target is window.country:
                    window.navigation[0].setFocus();app.processEvents()
                assert app.focusWidget() is target,'synthetic input target did not acquire focus: '+target.objectName()
            def navigate(index,method):
                before=snapshot()
                # [designed] QtTest widget events do not perform the OS click-to-activate step.
                app.processEvents();QTest.qWait(10)
                active_before=window.isActiveWindow()
                if not active_before:
                    window.raise_();window.activateWindow();app.processEvents();QTest.qWait(30)
                assert QTest.qWaitForWindowActive(window,2000),'owned shell window is not active before synthetic navigation'
                assert window.isActiveWindow() and app.activeWindow() is window,'native activation precondition did not settle'
                if not active_before:report.setdefault('activation_preconditions',[]).append({'method':method,'index':index,'native_active_after':window.isActiveWindow()})
                if method=='mouse':QTest.mouseClick(window.navigation[index],Qt.MouseButton.LeftButton)
                else:QTest.keyClick(window,Qt.Key.Key_1+index,Qt.KeyboardModifier.ControlModifier)
                app.processEvents()
                assert window.page_stack.currentIndex()==index,'navigation selected wrong page'
                focus=app.focusWidget();active=app.activeWindow()
                details={'method':method,'index':index,'focus_type':type(focus).__name__ if focus else None,
                         'focus_name':focus.objectName() if focus else None,'active_type':type(active).__name__ if active else None,
                         'active_name':active.objectName() if active else None,'window_active':window.isActiveWindow()}
                if focus is not window.pages[index].heading:report['focus_failure']=details
                assert focus is window.pages[index].heading,'navigation did not focus heading: '+json.dumps(details)
                assert window.navigation[index].isChecked(),'selected destination has no checked cue'
                assert snapshot()==before,'navigation changed state/draft/preview/save/job ownership'
                report['transitions'].append({'method':method,'destination':names[index],'focus':app.focusWidget().text()})
            def tour():
                for method in ('mouse','shortcut'):
                    for index in range(5):navigate(index,method)
            # [designed] Actual native surfaces must retain contrast when inheriting this shell's style.
            before=snapshot();surfaces={};failed=[]
            def surface(name,foreground,background):
                value=contrast(foreground,background)
                surfaces[name]={'foreground':foreground,'background':background,'contrast':value}
                if value<4.5:failed.append(name)
            def surface_trace(stage):
                change=delta(before,snapshot())
                focus=app.focusWidget()
                report.setdefault('surface_trace',[]).append({'stage':stage,'native_active':window.isActiveWindow(),
                    'focus_type':type(focus).__name__ if focus else None,'focus_name':focus.objectName() if focus else None,
                    'country':window.country.currentData(),'delta':change})
                assert not change,'surface inspection changed state/draft/preview/save/job ownership at '+stage+': '+json.dumps(change)
            surface_trace('before-popup')
            native_input(window.country);surface_trace('country-focus')
            if args.surface_input_control=='country-change':
                QTest.keyClick(window.country,Qt.Key.Key_Down);app.processEvents();surface_trace('controlled-country-change')
            QTest.keyClick(window.country,Qt.Key.Key_Down,Qt.KeyboardModifier.AltModifier,100)
            app.processEvents();QTest.qWait(100);popup=window.country.view()
            surface_trace('popup-open')
            assert popup.isVisible(),'native country popup did not open'
            surface('combo popup',popup.palette().color(QPalette.ColorRole.Text).name(),popup.palette().color(QPalette.ColorRole.Base).name())
            surface('combo selection',popup.palette().color(QPalette.ColorRole.HighlightedText).name(),popup.palette().color(QPalette.ColorRole.Highlight).name())
            assert popup.window().grab().save(str(evidence/'surface-country-popup.png'))
            assert popup.hasFocus() and app.activePopupWidget() is popup.window(),'country popup does not own native input before Escape'
            QTest.keyClick(popup,Qt.Key.Key_Escape,delay=100);app.processEvents();QTest.qWait(100)
            surface_trace('popup-escape')
            assert not popup.isVisible(),'native country popup did not close'
            window.raise_();window.activateWindow();app.processEvents()
            assert QTest.qWaitForWindowActive(window,2000),'shell did not regain activation after popup close'
            report['popup_events']={'opened':True,'closed':not popup.isVisible(),'active_after_close':window.isActiveWindow()}
            navigate(4,'shortcut');native_input(window.path)
            QTest.keyClick(window.path,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);app.processEvents()
            surface_trace('path-selection')
            surface('path selection',window.path.palette().color(QPalette.ColorRole.HighlightedText).name(),window.path.palette().color(QPalette.ColorRole.Highlight).name())
            enabled=window.save.isEnabled();window.save.setEnabled(False);app.processEvents()
            surface('disabled action',window.save.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.ButtonText).name(),window.save.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Button).name())
            window.save.setEnabled(enabled)
            surface_trace('save-restored')
            surface('table',window.table.palette().color(QPalette.ColorRole.Text).name(),window.table.palette().color(QPalette.ColorRole.Base).name())
            surface('disabled table',window.table.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Text).name(),window.table.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Base).name())
            header_background=window.table.horizontalHeader().grab().toImage().pixelColor(10,5).name()
            surface('table header',COLORS['text'],header_background)
            from goal2.desktop.standings import CompetitionTable
            from goal2.game.campaign_schedule import start_opening_campaign
            other=DesktopModel(model.goaldat,model.template_bytes,model.save_path)
            other.state,_=start_opening_campaign(model.goaldat,model.template_bytes,managed_country=4,start_year=1992,seed_7b62=4660,seed_8336=33590)
            surface_trace('other-created')
            dialog=CompetitionTable(other.competition_table(),window);dialog.show();QTest.qWait(30)
            surface('competition dialog',dialog.findChildren(QLabel)[0].palette().color(QPalette.ColorRole.WindowText).name(),dialog.palette().color(QPalette.ColorRole.Window).name())
            assert dialog.grab().save(str(evidence/'surface-competition-dialog.png'))
            dialog.close();app.processEvents();QTest.qWait(120)
            window.raise_();window.activateWindow();app.processEvents()
            assert QTest.qWaitForWindowActive(window,2000),'shell did not regain native activation after closing surface probe'
            surface_trace('dialog-closed')
            report['native_surfaces']=surfaces
            report['surface_snapshot_delta']=delta(before,snapshot())
            assert snapshot()==before,'surface inspection changed state/draft/preview/save/job ownership: '+json.dumps(report['surface_snapshot_delta'])
            assert not failed,'native surface contrast failed: '+', '.join(failed)
            # [designed] Dirty active controls are deliberately different from confirmed state.
            window.navigate(1);window.pages[1].ensureWidgetVisible(window.tactics[0][1]);app.processEvents()
            QTest.mouseClick(window.tactics[0][1],Qt.MouseButton.LeftButton,pos=QPoint(10,window.tactics[0][1].height()//2));app.processEvents()
            dirty=copy.deepcopy(window.draft())
            assert dirty[2]!=model.state.country_tactics,'test did not establish dirty tactics'
            tour()
            # [designed] The selected cue remains readable under the actual hover selector.
            navigate(0,'shortcut');button=window.navigation[0]
            QTest.mouseMove(button,button.rect().center());QTest.qWait(30)
            pixel=button.grab().toImage().pixelColor(10,button.height()//2).name()
            assert pixel==COLORS['accent'],'selected hover lost its high-contrast surface'
            rendered=button.grab().toImage()
            assert any(rendered.pixelColor(x,y).name()==COLORS['ink'] for x in range(4,rendered.width()-4) for y in range(4,rendered.height()-4)),'selected hover text lost readable ink'
            report['selected_hover_background']=pixel
            # [designed] Country selector uses native keyboard events; preview navigation retains its saved draft.
            window.country.setFocus();QTest.keyClick(window.country,Qt.Key.Key_Down);app.processEvents()
            assert window.preview is not None and window.active_draft==dirty,'country preview lost active draft'
            preview_country=window.country.currentData();tour()
            before=snapshot();QTest.keyClick(window,Qt.Key.Key_S,Qt.KeyboardModifier.ControlModifier);app.processEvents()
            assert snapshot()==before,'Save shortcut mutated a country preview'
            window.country.setFocus();QTest.keyClick(window.country,Qt.Key.Key_Up);app.processEvents()
            assert window.preview is None and window.draft()==dirty,'country return did not restore dirty draft'
            report['preview_country']=preview_country
            # [designed] Pending ownership probe runs no child and keeps global cancel reachable.
            model.match_pending=True;window.set_busy(True);tour()
            assert window.stop.isVisible() and window.stop.isEnabled(),'busy Cancel is unreachable'
            assert not window.save.isEnabled() and not window.resume.isEnabled(),'busy save controls enabled'
            before=snapshot();QTest.keyClick(window,Qt.Key.Key_S,Qt.KeyboardModifier.ControlModifier);app.processEvents()
            assert snapshot()==before,'Save shortcut mutated pending ownership'
            model.match_pending=False;window.set_busy(False)
            actions=(window.new,window.friendly,window.table,window.captain,window.confirm,window.cancel,
                     *(box for _,box in window.tactics),window.search,window.position,window.reserves,window.exchange,
                     window.standings,window.play,window.watch,window.half_out,window.half_in,
                     window.substitute,window.continue_match,window.path,window.save,window.resume)
            sizes=((1440,900),(1050,780),(900,700)) if window.devicePixelRatioF()<1.5 else ((900,640),)
            for width,height in sizes:
                window.resize(width,height);QTest.qWait(80)
                assert window.width()==width and window.height()==height,'shell minimum size exceeds target'
                for index,page in enumerate(window.pages):
                    navigate(index,'shortcut');app.processEvents()
                    assert page.horizontalScrollBar().maximum()==0,'shell needs horizontal scrolling'
                    page_actions=[w for w in actions if page.isAncestorOf(w)]
                    for widget in page_actions:
                        page.ensureWidgetVisible(widget,0,0);app.processEvents()
                        origin=widget.mapTo(page.viewport(),QPoint(0,0))
                        # [designed] Qt may reveal a table's focused cell only; use real scroll keys to expose its full control.
                        for _ in range(100):
                            if origin.y()>=0 and origin.y()+widget.height()<=page.viewport().height():break
                            key=Qt.Key.Key_Up if origin.y()<0 else Qt.Key.Key_Down
                            QTest.keyClick(page.verticalScrollBar(),key);app.processEvents()
                            origin=widget.mapTo(page.viewport(),QPoint(0,0))
                        assert origin.x()>=0 and origin.x()+widget.width()<=page.viewport().width(),f'action clipped horizontally: {widget.objectName() or type(widget).__name__}'
                        assert origin.y()>=0 and origin.y()+widget.height()<=page.viewport().height(),f'action unreachable vertically: {widget.objectName() or widget.accessibleName()} y={origin.y()} height={widget.height()} viewport={page.viewport().height()}'
                        assert widget.isVisible(),'action hidden'
                        assert widget.accessibleName(),'action has no accessible name'
                        if widget.isEnabled() and isinstance(widget,(QAbstractButton,QComboBox,QLineEdit)):
                            # Native Tab traversal from heading must reach each interactive action.
                            page.heading.setFocus();seen=False
                            for _ in range(400):
                                QTest.keyClick(app.focusWidget() or window,Qt.Key.Key_Tab)
                                if app.focusWidget() is widget:seen=True;break
                            assert seen,f'action absent from Tab traversal: {widget.accessibleName()}'
                        report['reachable'].append({'size':[width,height],'page':names[index],
                                                    'action':widget.objectName() or widget.accessibleName() or type(widget).__name__,
                                                    'enabled':widget.isEnabled()})
                    navigate(index,'shortcut');page.verticalScrollBar().setValue(0);app.processEvents()
                    filename=f'shell-{width}x{height}-page{index+1}.png'
                    assert window.grab().save(str(evidence/filename)),'screenshot save failed'
                    report['captures'].append(filename)
                assert window.status.isVisible() and window.stop.isVisible(),'persistent feedback/cancel hidden'
            assert not starts,'navigation launched match work'
            report['result']='PASS'
        finally:
            for patched in reversed(patches):patched.stop()
            model.match_pending=False;window.close();app.processEvents()
            (evidence/'interaction.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"PASS shell: {len(report['transitions'])} real navigation transitions; state/draft/preview/save/job invariants; {len(report['captures'])} captures; actual ratio {report['ratio']}")
    return report['ratio']

def negative_controls(args):
    """[designed] Baseline, draft loss and saved pre-fix native surfaces fail intended assertions."""
    source=ROOT/'goal2/desktop/window.py';style=ROOT/'goal2/desktop/style.py';pages=ROOT/'goal2/desktop/pages.py'
    saved={source:source.read_bytes(),style:style.read_bytes(),pages:pages.read_bytes()}
    evidence=Path(args.evidence_dir);evidence.mkdir(parents=True,exist_ok=False)
    accepted='08e3c67d2d0dc63a73aae7ee69610639746bf4b8'
    pre_surface_fix='6eaaea2a0d1bca1a6f7dd4d89adfc65f367123fb'
    baseline=subprocess.check_output(['git','show',accepted+':goal2/desktop/window.py'],cwd=ROOT)
    old_style=subprocess.check_output(['git','show',pre_surface_fix+':goal2/desktop/style.py'],cwd=ROOT)
    old_pages=subprocess.check_output(['git','show','154bfbbc5053ba9a18d93bb734464c2a4f10f7bc:goal2/desktop/pages.py'],cwd=ROOT)
    old=b'self.page_stack.setCurrentIndex(index)'
    assert saved[source].count(old)==1,'expected one navigation mutation site'
    cases=(('baseline',source,baseline,'five-destination navigation is absent'),
           ('discard-draft',source,saved[source].replace(old,old+b';self.refresh()'),'navigation changed state/draft/preview/save/job ownership'),
           ('native-surfaces',style,old_style,'native surface contrast failed: combo popup, combo selection, path selection, competition dialog'),
           ('accessible-names',pages,old_pages,'action has no accessible name'))
    receipt={'tag':'[designed: T74]','baseline':accepted,'pre_surface_fix':pre_surface_fix,
             'source_before':{str(p.relative_to(ROOT)):hashlib.sha256(raw).hexdigest() for p,raw in saved.items()},'cases':[]}
    try:
        for name,path,mutant,expected in cases:
            try:
                path.write_bytes(mutant)
                command=[sys.executable,'-B',str(Path(__file__).resolve()),'--scenario','shell',
                         '--template',args.template,'--data',args.data,'--evidence-dir',str(evidence/name),'--single-scale']
                result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=180)
                (evidence/(name+'.log')).write_text(result.stdout+result.stderr)
                assert result.returncode!=0 and 'AssertionError: '+expected in result.stderr, f'{name} did not fail intended assertion: {result.stderr}'
                receipt['cases'].append({'name':name,'source':str(path.relative_to(ROOT)),'expected_assertion':expected,
                                         'returncode':result.returncode,'mutant_sha256':hashlib.sha256(mutant).hexdigest()})
            finally:path.write_bytes(saved[path])
    finally:
        for path,raw in saved.items():path.write_bytes(raw)
        receipt['source_after']={str(p.relative_to(ROOT)):digest(p) for p in saved}
        (evidence/'negative-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert all(path.read_bytes()==raw for path,raw in saved.items()),'source restoration differed'
    print('PASS negative controls: baseline navigation; dirty-draft loss; native surface contrast; accessible names; exact source bytes restored')

def overview(args):
    """[designed: T75] Native controls prove displayed-country ownership and overview."""
    from PySide6.QtCore import Qt,QPoint,qVersion
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QLabel
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.game.session_save import encode
    app=QApplication([])
    out=Path(args.evidence_dir)
    if out.exists() and any(out.iterdir()):
        index=2
        while (out/f'run-{index:02}').exists():index+=1
        out=out/f'run-{index:02}'
    out.mkdir(parents=True,exist_ok=True)
    sources={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))}
    r={'tag':'[designed: T75]','scenario':'overview','scenario_sha256':digest(__file__),
       'sources':sources,'resources':{'template':digest(args.template),'data':digest(args.data)},
       'platform':platform.platform(),'python':sys.version,'qt':qVersion(),'qpa':app.platformName(),
       'requested_scale':os.environ.get('QT_SCALE_FACTOR','1'),'steps':[],'captures':[]}
    try:
        with tempfile.TemporaryDirectory(prefix='goal2-t75-main-')as folder:
            save=Path(folder)/'owned.g2save';m=DesktopModel.open(args.template,args.data,save,country=4)
            # [designed] Existing pure Quick function prepares an owned real completed-result input.
            from goal2.desktop.worker import play
            m.confirm(list(m.state.starting_eleven),m.state.starting_eleven[0],m.state.country_tactics)
            m.state=play(m.state,m.template_bytes)
            assert m.state.last_match is not None
            m.save(save);saved=save.read_bytes();encoded=encode(m.state,m.template_bytes)
            w=ManagementWindow(m);w.show();w.raise_();w.activateWindow();QTest.qWait(150)
            r['ratio']=w.devicePixelRatioF()
            assert r['ratio']==float(r['requested_scale']),'actual Qt ratio differs from requested fresh-process scale'
            w.resize(900,640 if r['ratio']>1 else 700);app.processEvents();r['initial_viewport']=[w.width(),w.height()];r['available']=[w.screen().availableGeometry().width(),w.screen().availableGeometry().height()]
            def active(target=None):
                if not w.isActiveWindow():w.raise_();w.activateWindow()
                assert QTest.qWaitForWindowActive(w,2000)
                if target is not None:
                    assert target.isVisible()and target.isEnabled(),'focus target unavailable: '+target.objectName()
                    target.setFocus();app.processEvents();QTest.qWait(150)
                    actual=app.focusWidget();info={'target':target.objectName(),'actual':actual.objectName()if actual else None,'window_active':w.isActiveWindow(),'visible':target.isVisible(),'enabled':target.isEnabled(),'current_page':w.page_stack.currentIndex()}
                    r.setdefault('focus_trace',[]).append(info)
                    assert actual is target,'native input focus ownership differs: '+str(info)
            def click(button,page=0):
                w.navigate(page);w.pages[page].ensureWidgetVisible(button);app.processEvents();active(button)
                QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
            assert hasattr(w,'overview_country_identity'),'country identity and overview hierarchy are absent'
            def select(number):
                active(w.country);QTest.keyClick(w.country,Qt.Key.Key_Down,Qt.KeyboardModifier.AltModifier,80);app.processEvents();QTest.qWait(100)
                view=w.country.view();assert view.isVisible(),'country popup did not open'
                assert view.hasFocus() and app.activePopupWidget() is view.window(),'country popup does not own native input'
                QTest.keyClick(view,Qt.Key.Key_Home)
                for _ in range(number-1):QTest.keyClick(view,Qt.Key.Key_Down)
                assert view.currentIndex().row()==number-1,'popup request row differs from requested country'
                QTest.keyClick(view,Qt.Key.Key_Return);app.processEvents();QTest.qWait(60)
                assert not view.isVisible()and w.country.currentData()==number,'native country browse selected wrong country'
            # Deliberately invalid private draft; keep it across country previews.
            w.navigate(1);row=next(i for i in range(20)if w.table.item(i,0).checkState()==Qt.CheckState.Checked)
            w.table.setCurrentCell(row,0);w.pages[1].ensureWidgetVisible(w.table);app.processEvents();active(w.table)
            QTest.keyClick(w.table,Qt.Key.Key_Space);app.processEvents();dirty=copy.deepcopy(w.draft());assert len(dirty[0])==10,'invalid draft not established'
            longest=max(range(1,129),key=lambda n:len(m.goaldat.country_names[n]));countries=list(dict.fromkeys([5,13,longest]))
            for number in countries:
                select(number);expected=DesktopModel.open(args.template,args.data,save,country=number);v=expected.view()
                assert w.overview_country_identity.text()==v['country_name'],'overview identity bound to active country instead of preview'
                assert w.title.text()==v['country_name']
                assert [w.table.item(i,1).text()for i in range(20)]==[x['name']for x in v['players']],'preview roster differs from independent model'
                for i,player in enumerate(v['players']):
                    assert w.table.item(i,0).data(Qt.ItemDataRole.UserRole)==player['id']
                    assert (w.table.item(i,0).checkState()==Qt.CheckState.Checked)==(player['id']in expected.state.starting_eleven)
                    reason=', '.join(player['availability']['reasons'])or'Available'
                    if player['availability']['carried_bookings']:reason+='; carried booking'
                    values=(player['name'],player['position'],player['ability'],player['energy'],player['confidence'],reason)
                    assert [w.table.item(i,col).text()for col in range(1,7)]==[str(value)for value in values],'preview player fields differ from independent model'
                assert w.overview_fixture.text()==(v['fixture']or('Standalone friendly / no campaign fixture' if expected.state.campaign is None else 'No supported fixture'))
                assert w.overview_result.text()=='No result yet\n'+expected.result_text()
                pool=expected.pool_view()['reserves'];assert [w.reserves.item(i,1).text()for i in range(80)]==[x['name']for x in pool]
                assert encode(m.state,m.template_bytes)==encoded and save.read_bytes()==saved
                assert w.active_draft==dirty,'country browse lost invalid active draft'
                assert m.save_path==save and w.path.text()==str(save),'browse changed save path'
                assert w.context.text()=='Preview · active game: '+m.view()['country_name']
                assert expected.pool_view()['window']['reason'] in w.pool_summary.text()
                assert not any(widget.isEnabled() for widget in (w.confirm,w.cancel,w.save,w.play,w.standings,w.exchange)),'preview action enabled'
                w.navigate(0);app.processEvents()
                sizes=((1440,900),(1050,780),(900,700)) if r['ratio']<1.5 else ((900,640),)
                for width,height in sizes:
                    w.resize(width,height);QTest.qWait(80);page=w.pages[0]
                    assert (w.width(),w.height())==(width,height),'shell minimum size exceeds target'
                    assert page.horizontalScrollBar().maximum()==0,'overview needs horizontal scrolling'
                    for label in (w.title,w.context):
                        assert label.height()>=label.heightForWidth(label.width()),'country identity/context clips wrapped text'
                    for widget in (w.overview_country_identity,w.overview_fixture,w.overview_result,w.overview_return,w.new,w.friendly):
                        page.ensureWidgetVisible(widget,0,0);app.processEvents()
                        origin=widget.mapTo(page.viewport(),QPoint(0,0))
                        assert origin.x()>=0 and origin.x()+widget.width()<=page.viewport().width(),'overview clipped horizontally: '+widget.objectName()
                        assert origin.y()>=0 and origin.y()+widget.height()<=page.viewport().height(),'overview action/value unreachable: '+widget.objectName()
                        if isinstance(widget,QLabel):
                            assert widget.height()>=widget.heightForWidth(widget.width()),'overview label clips wrapped text: '+widget.objectName()
                    actions_name=f'preview-{number}-{width}x{height}-actions.png'
                    assert w.grab().save(str(out/actions_name));r['captures'].append({'path':actions_name,'sha256':digest(out/actions_name),'size':[width,height],'country':number,'context':'reachable preview replacement and Return actions'})
                    page.verticalScrollBar().setValue(0);app.processEvents()
                    name=f'preview-{number}-{width}x{height}.png'
                    assert w.grab().save(str(out/name));r['captures'].append({'path':name,'sha256':digest(out/name),'size':[width,height],'country':number})
                r['steps'].append({'country':number,'name':v['country_name'],'all20_names':True,'all20_records':True,'pool80':True,'fixture_result':'independent model match','active_and_save_unchanged':True})
            click(w.overview_return);assert w.preview is None and w.draft()==dirty,'return did not recover invalid active draft'
            assert w.context.text()=='Active game'
            assert w.overview_result.text()=='Quick simulation (rebuild setup)\n'+m.result_text()and encode(m.state,m.template_bytes)==encoded and save.read_bytes()==saved
            # Explicit replacement actions and Resume use the existing guarded callbacks.
            select(13);click(w.new);assert m.state.managed_country==13 and w.preview is None
            assert w.overview_country_identity.text().startswith(m.view()['country_name'])and w.overview_result.text()=='No result yet\n'+m.result_text()
            assert w.title.text()==m.view()['country_name'] and w.selected_ids()==m.state.starting_eleven
            select(5);click(w.friendly);assert m.state.managed_country==5 and m.state.campaign is None and w.preview is None
            assert w.title.text()==m.view()['country_name'] and w.selected_ids()==m.state.starting_eleven
            assert w.overview_fixture.text()=='Standalone friendly / no campaign fixture'
            select(13);click(w.resume,4)
            assert m.state.managed_country==4 and w.preview is None and encode(m.state,m.template_bytes)==encoded and save.read_bytes()==saved
            assert w.overview_country_identity.text().startswith(m.view()['country_name'])and w.overview_result.text()=='Quick simulation (rebuild setup)\n'+m.result_text()
            assert w.title.text()==m.view()['country_name'] and w.selected_ids()==m.state.starting_eleven
            w.navigate(0);app.processEvents();page=w.pages[0]
            result_panel=w.overview_result.parentWidget()
            page.ensureWidgetVisible(result_panel,0,0);app.processEvents()
            origin=result_panel.mapTo(page.viewport(),QPoint(0,0))
            assert origin.x()>=0 and origin.x()+result_panel.width()<=page.viewport().width(),'completed result clipped horizontally'
            assert origin.y()>=0 and origin.y()+result_panel.height()<=page.viewport().height(),'completed result card is not fully reachable'
            assert w.overview_result.height()>=w.overview_result.heightForWidth(w.overview_result.width()),'completed result clips wrapped text'
            r['completed_result_geometry']={'origin':[origin.x(),origin.y()],'size':[result_panel.width(),result_panel.height()],
                                             'viewport':[page.viewport().width(),page.viewport().height()]}
            assert w.grab().save(str(out/'completed-result.png'))
            r['captures'].append({'path':'completed-result.png','sha256':digest(out/'completed-result.png'),'context':'completed result restored'})
            r['result']='PASS';r['invalid_draft_return']=True;r['explicit_campaign_friendly_resume']=True;r['completed_result_restored']=True
            w.close();app.processEvents()
    except BaseException as exc:
        r['result']='FAIL';r['failure']=str(exc);r['exception']=type(exc).__name__;raise
    finally:
        assert sources=={name:digest(ROOT/name) for name in sources},'source changed during overview scenario'
        (out/'interaction.json').write_text(json.dumps(r,indent=2)+'\n')
    print('PASS overview: independent all20 records/pool/fixture/result; invalid-draft Return; explicit activation/Resume; source/save/state unchanged; actual ratio',r['ratio'])

def overview_negative_controls(args):
    """[designed: T75] Prove missing hierarchy and active-binding regression oracles."""
    evidence=Path(args.evidence_dir)
    evidence.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/name for name in ('goal2/desktop/pages.py','goal2/desktop/overview_page.py',
                                 'goal2/desktop/window.py','goal2/desktop/style.py')]
    saved={path:path.read_bytes() for path in paths}
    receipt={'tag':'[designed: T75]','sources_before':{str(p.relative_to(ROOT)):digest(p) for p in paths},'cases':[]}
    env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1','QT_SCALE_FACTOR':'1'}
    overview_command=[sys.executable,'-B',str(Path(__file__).resolve()),'--scenario','overview',
                      '--template',args.template,'--data',args.data,'--single-scale']
    def run(name,command,expected):
        result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
        (evidence/(name+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode!=0 and 'AssertionError: '+expected in result.stderr, f'{name} failed outside intended oracle: {result.stderr}'
        receipt['cases'].append({'name':name,'command':command,'expected_assertion':expected,'returncode':result.returncode})
    try:
        # [designed] Pinned accepted parent product must lack the new hierarchy.
        for path in paths:
            path.write_bytes(subprocess.check_output(['git','show','4f366a5084749a4ef0a045a46b460f81e3c3fcb8:'+str(path.relative_to(ROOT))],cwd=ROOT))
        run('baseline',overview_command+['--evidence-dir',str(evidence/'baseline')],
            'country identity and overview hierarchy are absent')
        for path,raw in saved.items():path.write_bytes(raw)
        path=ROOT/'goal2/desktop/window.py';old='return self.preview if self.preview is not None else self.model'
        assert path.read_text().count(old)==1,'active-binding mutation site changed'
        path.write_text(path.read_text().replace(old,'return self.model'))
        run('active-binding-country',[sys.executable,'-B',str(ROOT/'tools/desktop-ui/country-selection.py'),
             '--template',args.template,'--data',args.data],'selected country header remains on previous country')
        run('active-binding-overview',overview_command+['--evidence-dir',str(evidence/'active-binding-overview')],
            'native country browse selected wrong country')
    finally:
        for path,raw in saved.items():path.write_bytes(raw)
        receipt['sources_after']={str(p.relative_to(ROOT)):digest(p) for p in paths}
        receipt['restored']=all(path.read_bytes()==raw for path,raw in saved.items())
        (evidence/'negative-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['restored'],'source restoration differed'
    print('PASS overview negative controls: baseline hierarchy absent; active binding fails country-selection and overview; exact saved bytes restored')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',choices=['shell','overview','squad'],required=True)
    parser.add_argument('--template',required=True);parser.add_argument('--data',required=True)
    parser.add_argument('--evidence-dir',required=True);parser.add_argument('--single-scale',action='store_true');parser.add_argument('--negative-controls',action='store_true')
    parser.add_argument('--surface-input-control',choices=['wrong-focus','country-change'])
    args=parser.parse_args()
    if args.scenario=='squad' and (args.negative_controls or args.single_scale):
        from squad_scenario import scenario,negative_controls as squad_negative_controls
        return (squad_negative_controls if args.negative_controls else scenario)(args)
    if args.negative_controls:return (overview_negative_controls if args.scenario=='overview' else negative_controls)(args)
    if args.single_scale:return (overview if args.scenario=='overview' else shell)(args)
    # [designed] The orchestrator owns no Qt connection; each scale exits before the next starts.
    evidence=Path(args.evidence_dir)
    if evidence.exists() and any(evidence.iterdir()):
        index=2
        while (evidence/f'run-{index:02}').exists():index+=1
        evidence=evidence/f'run-{index:02}'
    for scale,target in (('1',evidence),('2',evidence/'scale-2')):
        env=os.environ.copy();env['QT_SCALE_FACTOR']=scale
        command=[sys.executable,str(Path(__file__).resolve()),'--scenario',args.scenario,'--template',args.template,
                 '--data',args.data,'--evidence-dir',str(target),'--single-scale']
        subprocess.run(command,env=env,check=True)
if __name__=='__main__':main()
