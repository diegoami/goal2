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
            def navigate(index,method):
                before=snapshot()
                if method=='mouse':QTest.mouseClick(window.navigation[index],Qt.MouseButton.LeftButton)
                else:QTest.keyClick(window,Qt.Key.Key_1+index,Qt.KeyboardModifier.ControlModifier)
                app.processEvents()
                assert window.page_stack.currentIndex()==index,'navigation selected wrong page'
                assert app.focusWidget() is window.pages[index].heading,'navigation did not focus heading'
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
            window.country.setFocus();QTest.keyClick(window.country,Qt.Key.Key_Down,Qt.KeyboardModifier.AltModifier)
            app.processEvents();QTest.qWait(30);popup=window.country.view()
            assert popup.isVisible(),'native country popup did not open'
            surface('combo popup',popup.palette().color(QPalette.ColorRole.Text).name(),popup.palette().color(QPalette.ColorRole.Base).name())
            surface('combo selection',popup.palette().color(QPalette.ColorRole.HighlightedText).name(),popup.palette().color(QPalette.ColorRole.Highlight).name())
            assert popup.window().grab().save(str(evidence/'surface-country-popup.png'))
            QTest.keyClick(window.country,Qt.Key.Key_Escape);window.country.hidePopup();app.processEvents()
            navigate(4,'shortcut');window.path.setFocus()
            QTest.keyClick(window.path,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);app.processEvents()
            surface('path selection',window.path.palette().color(QPalette.ColorRole.HighlightedText).name(),window.path.palette().color(QPalette.ColorRole.Highlight).name())
            enabled=window.save.isEnabled();window.save.setEnabled(False);app.processEvents()
            surface('disabled action',window.save.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.ButtonText).name(),window.save.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Button).name())
            window.save.setEnabled(enabled)
            surface('table',window.table.palette().color(QPalette.ColorRole.Text).name(),window.table.palette().color(QPalette.ColorRole.Base).name())
            surface('disabled table',window.table.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Text).name(),window.table.palette().color(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Base).name())
            header_background=window.table.horizontalHeader().grab().toImage().pixelColor(10,5).name()
            surface('table header',COLORS['text'],header_background)
            from goal2.desktop.standings import CompetitionTable
            from goal2.game.campaign_schedule import start_opening_campaign
            other=DesktopModel(model.goaldat,model.template_bytes,model.save_path)
            other.state,_=start_opening_campaign(model.goaldat,model.template_bytes,managed_country=4,start_year=1992,seed_7b62=4660,seed_8336=33590)
            dialog=CompetitionTable(other.competition_table(),window);dialog.show();QTest.qWait(30)
            surface('competition dialog',dialog.findChildren(QLabel)[0].palette().color(QPalette.ColorRole.WindowText).name(),dialog.palette().color(QPalette.ColorRole.Window).name())
            assert dialog.grab().save(str(evidence/'surface-competition-dialog.png'))
            dialog.close();app.processEvents();QTest.qWait(120)
            window.raise_();window.activateWindow();app.processEvents()
            assert QTest.qWaitForWindowActive(window,2000),'shell did not regain native activation after closing surface probe'
            report['native_surfaces']=surfaces
            assert snapshot()==before,'surface inspection changed state/draft/preview/save/job ownership'
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
    source=ROOT/'goal2/desktop/window.py';style=ROOT/'goal2/desktop/style.py'
    saved={source:source.read_bytes(),style:style.read_bytes()}
    evidence=Path(args.evidence_dir);evidence.mkdir(parents=True,exist_ok=False)
    accepted='08e3c67d2d0dc63a73aae7ee69610639746bf4b8'
    pre_surface_fix='6eaaea2a0d1bca1a6f7dd4d89adfc65f367123fb'
    baseline=subprocess.check_output(['git','show',accepted+':goal2/desktop/window.py'],cwd=ROOT)
    old_style=subprocess.check_output(['git','show',pre_surface_fix+':goal2/desktop/style.py'],cwd=ROOT)
    old=b'self.page_stack.setCurrentIndex(index)'
    assert saved[source].count(old)==1,'expected one navigation mutation site'
    cases=(('baseline',source,baseline,'five-destination navigation is absent'),
           ('discard-draft',source,saved[source].replace(old,old+b';self.refresh()'),'navigation changed state/draft/preview/save/job ownership'),
           ('native-surfaces',style,old_style,'native surface contrast failed: combo popup, combo selection, path selection, competition dialog'))
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
    print('PASS negative controls: baseline navigation; dirty-draft loss; saved pre-fix native surface contrast; exact source bytes restored')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',choices=['shell'],required=True)
    parser.add_argument('--template',required=True);parser.add_argument('--data',required=True)
    parser.add_argument('--evidence-dir',required=True);parser.add_argument('--single-scale',action='store_true');parser.add_argument('--negative-controls',action='store_true')
    args=parser.parse_args()
    if args.negative_controls:return negative_controls(args)
    if args.single_scale:return shell(args)
    # [designed] The orchestrator owns no Qt connection; each scale exits before the next starts.
    evidence=Path(args.evidence_dir)
    if evidence.exists() and any(evidence.iterdir()):
        index=2
        while (evidence/f'run-{index:02}').exists():index+=1
        evidence=evidence/f'run-{index:02}'
    for scale,target in (('1',evidence),('2',evidence/'scale-2')):
        env=os.environ.copy();env['QT_SCALE_FACTOR']=scale
        command=[sys.executable,str(Path(__file__).resolve()),'--scenario','shell','--template',args.template,
                 '--data',args.data,'--evidence-dir',str(target),'--single-scale']
        subprocess.run(command,env=env,check=True)
if __name__=='__main__':main()
