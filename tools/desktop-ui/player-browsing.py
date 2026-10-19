#!/usr/bin/env python3
"""[designed: #241] Real idle active/preview table input and read-only oracles."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fresh(path):
    path=Path(path)
    if path.exists():raise FileExistsError('Evidence output must be new: '+str(path))
    path.mkdir(parents=True)
    return path


def scenario(args):
    from PySide6.QtCore import Qt,QPoint,QPointF,QRect,QCoreApplication,QEvent,qVersion
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.game.session_save import encode
    app=QApplication([]);out=fresh(args.evidence_dir)
    sources={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))}
    report={'tag':'[designed: #241]','platform':platform.platform(),'qt':qVersion(),'qpa':app.platformName(),
            'scale':os.environ.get('QT_SCALE_FACTOR','1'),'source_head':args.source_head or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'sources':sources,'scenario_sha256':digest(__file__),'resources':{k:digest(getattr(args,k)) for k in ('template','data')},'tables':[]}
    callbacks=[];previous=sys.excepthook;w=None
    def callback(kind,error,trace):callbacks.append(''.join(traceback.format_exception(kind,error,trace)))
    sys.excepthook=callback
    try:
        assert app.platformName() in ('xcb','windows'),'requires owned X11 or native Windows platform'
        with tempfile.TemporaryDirectory(prefix='fix241-') as folder:
            save=Path(folder)/'owned.g2save';m=DesktopModel.open(args.template,args.data,save,country=13)
            m.save(save);saved=save.read_bytes();w=ManagementWindow(m);w.show();w.activateWindow();QTest.qWait(120)
            report['ratio']=w.devicePixelRatioF();assert report['ratio']==float(os.environ.get('QT_SCALE_FACTOR','1')),'actual device ratio differs';report['screen']=[w.screen().availableGeometry().width(),w.screen().availableGeometry().height()]
            def snapshot():
                preview=w.preview
                return (encode(m.state,m.template_bytes),encode(preview.state,preview.template_bytes) if preview else None,
                        (m.state.rng_seed_7b62,m.state.rng_seed_8336),
                        (preview.state.rng_seed_7b62,preview.state.rng_seed_8336) if preview else None,
                        save.read_bytes(),copy.deepcopy(w.draft()),copy.deepcopy(w.active_draft),
                        tuple(c.process for c in (w.jobs,w.competitive,w.watched)),getattr(m,'match_pending',False))
            def stable(before,label):
                assert not callbacks,'Qt callback failure: '+repr(callbacks)
                assert snapshot()==before,label+' changed encoded active/preview, RNG, save, draft or job ownership'
                assert save.read_bytes()==saved,label+' changed original saved bytes'
            def focus(widget):
                # [designed] Settle native WM activation before dispatch; every attempt still requires actual focus.
                for attempt in range(3):
                    if not w.isActiveWindow():
                        w.raise_();w.activateWindow();app.processEvents();QTest.qWait(120)
                    assert QTest.qWaitForWindowActive(w,2000),'owned browsing window did not become active'
                    widget.setFocus();app.processEvents();QTest.qWait(20)
                    if w.isActiveWindow() and app.focusWidget() is widget:break
                    report.setdefault('activation_retries',[]).append({'target':widget.objectName(),'attempt':attempt+1,'active':w.isActiveWindow()})
                assert widget.isEnabled() and w.isActiveWindow() and app.focusWidget() is widget,'table browsing focus unavailable: '+repr((widget.objectName(),widget.isEnabled(),type(app.focusWidget()).__name__,app.focusWidget().objectName() if app.focusWidget() else None,w.isActiveWindow()))
            def key(widget,code,mods=Qt.KeyboardModifier.NoModifier):
                focus(widget);QTest.keyClick(widget,code,mods);app.processEvents()
            def row_band(table,row):
                # [designed: #241] visibleRegion includes ancestor/page clipping. A one-pixel
                # vertical band checks the whole row height without requiring horizontal columns.
                rect=table.visualItemRect(table.item(row,1));bounds=table.viewport().rect()
                return QRect(bounds.center().x(),rect.top(),1,rect.height())
            def visible_rows(table):
                view=table.viewport()
                return {row for row in range(table.rowCount()) if view.visibleRegion().contains(row_band(table,row))}
            def visible_selected(table):
                view=table.viewport();band=row_band(table,table.currentRow())
                assert view.rect().contains(band),'focused row outside table viewport'
                assert view.visibleRegion().contains(band),'focused row clipped by outer page'
            def wheel(table,delta):
                if table.isEnabled():focus(table)
                view=table.viewport();pos=view.visibleRegion().boundingRect().center()
                assert view.visibleRegion().contains(pos),'wheel point outside visible table'
                event=QWheelEvent(QPointF(pos),QPointF(view.mapToGlobal(pos)),QPoint(),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
                QApplication.sendEvent(view,event);app.processEvents()
            def readonly():
                assert all(not x.isEnabled() for x in (w.captain,w.confirm,w.cancel,w.save,w.exchange,*[b for _,b in w.tactics])), 'preview management controls enabled'
                assert all(not w.table.item(r,0).flags() & Qt.ItemFlag.ItemIsUserCheckable for r in range(20)), 'preview XI still checkable'
                before=snapshot();w.navigate(1);w.pages[1].ensureWidgetVisible(w.table);app.processEvents()
                key(w.table,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier);QTest.keyClick(w.table,Qt.Key.Key_Space);app.processEvents()
                item=w.table.item(0,0);rect=w.table.visualItemRect(item)
                QTest.mouseClick(w.table.viewport(),Qt.MouseButton.LeftButton,pos=QPoint(rect.left()+10,rect.center().y()));app.processEvents()
                # [designed] Disabled edit controls receive real events; direct mutation callbacks retain their own preview guard.
                for control in (w.captain,*[b for _,b in w.tactics]):
                    QTest.keyClick(control,Qt.Key.Key_Space);app.processEvents()
                for control in (w.confirm,w.exchange,w.save):QTest.mouseClick(control,Qt.MouseButton.LeftButton);app.processEvents()
                w.confirm_draft();w.exchange_selected()
                w.action(lambda:(_ for _ in ()).throw(AssertionError('preview publication executed')),'Unexpected publication')
                stable(before,'preview refused input')
            # [designed] A private active draft makes return restoration independent of preview's own draft.
            w.table.item(0,0).setCheckState(Qt.CheckState.Unchecked);w.tactics[0][1].toggle();active_draft=copy.deepcopy(w.draft())
            sizes=[(900,640)] if float(os.environ.get('QT_SCALE_FACTOR','1'))==2 else [(1440,900),(1050,780),(900,700)]
            for context in (('active','preview') if args.context=='both' else (args.context,)):
                if context=='preview':
                    w.country.setCurrentIndex(w.country.findData(14));app.processEvents();assert w.preview is not None
                context_before=snapshot()
                for width,height in sizes:
                    w.resize(width,height);QTest.qWait(80);assert (w.width(),w.height())==(width,height),'requested logical window size unavailable'
                    for index,table,detail,count in ((1,w.table,w.player_detail,20),(2,w.reserves,w.pool_detail,80)):
                        w.navigate(index);w.pages[index].ensureWidgetVisible(table);app.processEvents()
                        assert table.rowCount()==count
                        if not table.isEnabled():
                            table.verticalScrollBar().setValue(0);app.processEvents()
                            wheel(table,-120);assert table.verticalScrollBar().value()>0,'wheel blocked on roster browsing surface'
                        key(table,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier);assert table.currentRow()==0;visible_selected(table)
                        bar=table.verticalScrollBar();assert bar.maximum()>0,'test requires overflowing rows'
                        seen=visible_rows(table);previous_value=-1
                        for _ in range(160):
                            wheel(table,-120);seen.update(visible_rows(table))
                            if bar.value()==bar.maximum():break
                            assert bar.value()>previous_value,'wheel made no forward progress';previous_value=bar.value()
                        assert bar.value()==bar.maximum() and count-1 in seen,'wheel failed to reach last roster row'
                        assert seen==set(range(count)),'wheel omitted roster reading coverage'
                        for _ in range(160):
                            wheel(table,120)
                            if bar.value()==0:break
                        assert bar.value()==0 and 0 in visible_rows(table),'wheel failed to return to first roster row'
                        # [designed] Every row is selected with genuine keys; End/Home exercise full-range scroll independently of wheel.
                        key(table,Qt.Key.Key_End,Qt.KeyboardModifier.ControlModifier);assert table.currentRow()==count-1;visible_selected(table)
                        key(table,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier)
                        identities=[]
                        rows=w.display_model.view()['players'] if index==1 else w.display_model.pool_view()['reserves']
                        for row in range(count):
                            if row:key(table,Qt.Key.Key_Down)
                            assert table.currentRow()==row;visible_selected(table)
                            word=table.item(row,0).data(Qt.ItemDataRole.UserRole);assert word==rows[row]['id']
                            assert f'ID {word}' in detail.text() and rows[row]['name'] in detail.text(),'selected full-ID detail differs'
                            identities.append(word)
                        # [designed] Native scrollbar key input must also reach both endpoints.
                        key(bar,Qt.Key.Key_Home);assert bar.value()==0
                        key(bar,Qt.Key.Key_End);assert bar.value()==bar.maximum()
                        key(table,Qt.Key.Key_End,Qt.KeyboardModifier.ControlModifier);visible_selected(table)
                        w.pages[index].ensureWidgetVisible(detail);app.processEvents()
                        assert detail.visibleRegion().boundingRect().height()>=detail.height(),'selected detail is not fully readable'
                        filename=f'{context}-{width}x{height}-{index}.png';assert w.grab().save(str(out/filename))
                        stable(context_before,'scroll and selection '+context)
                        report['tables'].append({'context':context,'size':[width,height],'table':table.objectName(),'rows':count,'wheel_coverage':sorted(seen),'selected_ids':identities,'visibility_oracle':'complete row vertical band within viewport visibleRegion (ancestor clipping included)','last_detail':detail.text(),'scroll_maximum':bar.maximum(),'capture':filename,'capture_sha256':digest(out/filename)})
                if context=='preview':readonly()
            w.country.setCurrentIndex(w.country.findData(13));app.processEvents();assert w.preview is None and w.draft()==active_draft,'active draft not restored on return'
            assert encode(m.state,m.template_bytes)==context_before[0] and save.read_bytes()==saved
            # [designed] Busy inspection remains refused; this task does not relax match ownership.
            w.set_busy(True);assert not w.table.isEnabled() and not w.pool_panel.isEnabled();w.set_busy(False)
            report['result']='PASS'
            report['state_invariants']='encoded active/preview, both RNG pairs, save bytes, per-context draft and jobs unchanged; active draft restored'
    except BaseException:
        report['result']='FAIL';report['failure']=traceback.format_exc();raise
    finally:
        if w is not None:
            w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        sys.excepthook=previous;report['callbacks']=callbacks
        report['sources_unchanged']=sources=={p:digest(ROOT/p) for p in sources}
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['sources_unchanged'] and not callbacks
    print('PASS player browsing: active/preview 20/80, wheel/key/scrollbar, full-ID details, immutable state/RNG/save/drafts, preview and busy guards; '+str(out))


def controls(args):
    out=fresh(args.evidence_dir);path=ROOT/'goal2/desktop/window.py';saved=path.read_bytes();receipt={'tag':'[designed: #241]','before':digest(path),'controls':[]}
    def run(name,source,expected):
        path.write_text(source)
        command=[sys.executable,'-B',__file__,'--template',args.template,'--data',args.data,'--evidence-dir',str(out/name),'--context','preview']
        if args.source_head:command+=['--source-head',args.source_head]
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
        (out/(name+'.log')).write_text(result.stdout)
        receipt['controls'].append({'name':name,'returncode':result.returncode,'expected':expected,'log_sha256':digest(out/(name+'.log'))})
        assert result.returncode!=0 and expected in result.stdout,'negative control escaped: '+name
    try:
        source=saved.decode()
        old='for widget in (self.table,self.pool_panel):widget.setEnabled(not busy)'
        assert source.count(old)==1
        run('old-disabled-preview',source.replace(old,'for widget in (self.table,self.pool_panel):widget.setEnabled(active)'),'wheel blocked on roster browsing surface')
        path.write_bytes(saved)
        run('outer-page-clipped-row',source.replace(old,old+';self.table.setMinimumHeight(1000)'),'focused row clipped by outer page')
        path.write_bytes(saved)
        old='        self.stop.setEnabled(busy)';assert source.count(old)==1
        mutation='        for widget in (self.captain,self.confirm,self.cancel,self.save,self.exchange,*[box for _,box in self.tactics]):widget.setEnabled(not busy)\n'+old
        run('enable-everything',source.replace(old,mutation),'preview management controls enabled')
    finally:
        path.write_bytes(saved);receipt['after']=digest(path);receipt['restored']=path.read_bytes()==saved
        (out/'negative-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['restored'];print('PASS browsing negative controls: old preview disable, outer-page clipped row and broad edit enabling rejected; exact saved source restored')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--template',required=True);parser.add_argument('--data',required=True)
    parser.add_argument('--evidence-dir',required=True);parser.add_argument('--negative-controls',action='store_true')
    parser.add_argument('--context',choices=('both','active','preview'),default='both')
    parser.add_argument('--source-head',help='Full immutable source commit for a git-archive/native run')
    args=parser.parse_args()
    if args.source_head and not re.fullmatch(r'[0-9a-fA-F]{40}',args.source_head):parser.error('--source-head requires a full 40-digit commit SHA')
    (controls if args.negative_controls else scenario)(args)

if __name__=='__main__':main()
