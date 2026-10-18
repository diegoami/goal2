"""[designed: T77] Independent native pool interaction and saved-source oracles."""
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
def fresh(path):
    path=Path(path)
    if path.exists() and any(path.iterdir()):
        number=2
        while (path/f'run-{number:02}').exists():number+=1
        path=path/f'run-{number:02}'
    path.mkdir(parents=True,exist_ok=True);return path


def scenario(args):
    from PySide6.QtCore import Qt,QRect,QCoreApplication,QEvent,qVersion
    from PySide6.QtWidgets import QApplication,QLabel,QStyle,QStyleOptionComboBox,QStyleOptionButton,QStyleOptionViewItem
    from PySide6.QtTest import QTest
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.desktop.worker import play
    from goal2.game import campaign_pool
    from goal2.game.session_save import encode
    from navigation import reveal
    app=QApplication([]);out=fresh(args.evidence_dir);w=None;callbacks=[];previous=sys.excepthook
    def exception(kind,error,trace):callbacks.append(''.join(traceback.format_exception(kind,error,trace)))
    sys.excepthook=exception
    report={'tag':'[designed: T77]','platform':platform.platform(),'python':sys.version,'qt':qVersion(),'qpa':app.platformName(),
            'requested_scale':os.environ.get('QT_SCALE_FACTOR','1'),'sources':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))},
            'scenario_sha256':digest(__file__),'dispatcher_sha256':digest(ROOT/'tools/desktop-ui/redesign.py'),'resources':{'template':digest(args.template),'data':digest(args.data)},'steps':[],'captures':[]}
    def clean():assert not callbacks,'uncaught Qt callback exception: '+''.join(callbacks)
    try:
      with tempfile.TemporaryDirectory(prefix='goal2-T77-') as folder:
        save=Path(folder)/'owned.g2save';m=DesktopModel.open(args.template,args.data,save,country=14)
        m.confirm(list(m.state.starting_eleven),261,m.state.country_tactics);m.save(save);saved=save.read_bytes()
        w=ManagementWindow(m);w.show();w.raise_();w.activateWindow();QTest.qWait(120)
        report['ratio']=w.devicePixelRatioF();assert report['ratio']==float(report['requested_scale']),'actual scale differs'
        assert all(w.findChild(QLabel,name) is not None for name in ('poolDetail','exchangeSummary','poolPolicy')),'focused incoming detail/exchange summary absent'
        def focus(widget):
            reveal(widget);w.raise_();w.activateWindow();assert QTest.qWaitForWindowActive(w,2000),'native window did not activate'
            widget.setFocus();app.processEvents();QTest.qWait(25);assert app.focusWidget() is widget,'native keyboard focus missing: '+widget.objectName();clean()
        def stable(before,label,draft=None):
            assert m.state==before,label+' changed state/RNG/membership'
            assert encode(m.state,m.template_bytes)==encode(before,m.template_bytes),label+' changed encoded state'
            assert save.read_bytes()==saved,label+' changed save'
            if draft is not None:assert w.draft()==draft,label+' changed private draft'
            clean()
        def key(widget,key):focus(widget);QTest.keyClick(widget,key);app.processEvents();clean()
        def action(widget):key(widget,Qt.Key.Key_Space)
        def search(text):
            before=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft());focus(w.search)
            QTest.keyClick(w.search,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClick(w.search,Qt.Key.Key_Backspace)
            if text:QTest.keyClicks(w.search,text)
            app.processEvents();stable(before,'search/filter',draft)
        def position(code):
            before=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft());focus(w.position);QTest.keyClick(w.position,Qt.Key.Key_Home)
            for _ in range(0 if code is None else code+1):QTest.keyClick(w.position,Qt.Key.Key_Down)
            app.processEvents();stable(before,'search/filter',draft)
        def reserve(word):
            before=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft());focus(w.reserves);QTest.keyClick(w.reserves,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier)
            ids=[w.reserves.item(i,0).data(Qt.ItemDataRole.UserRole) for i in range(w.reserves.rowCount())]
            for _ in range(ids.index(word)):QTest.keyClick(w.reserves,Qt.Key.Key_Down)
            app.processEvents();assert w.reserves.item(w.reserves.currentRow(),0).data(Qt.ItemDataRole.UserRole)==word,'keyboard selected wrong reserve'
            w.reserves.scrollToItem(w.reserves.item(w.reserves.currentRow(),1));app.processEvents()
            stable(before,'reserve selection',draft)
        def rows():
            expected=campaign_pool.view(m.state,m.goaldat,query=w.search.text(),position=w.position.currentData())['reserves']
            assert w.reserves.rowCount()==len(expected),'filtered row count differs'
            for i,row in enumerate(expected):
                values=(str(row['id']),row['name'],f"{row['position']} — {row['position_group']}",str(row['ability']),str(row['energy']),str(row['confidence']),', '.join(row['availability']['reasons']) or 'Available')
                assert tuple(w.reserves.item(i,j).text() for j in range(7))==values,'reserve raw values/order differ'
        def reading(label):
            reveal(label);app.processEvents();rect=label.contentsRect();needed=label.fontMetrics().boundingRect(QRect(0,0,rect.width(),10000),int(Qt.TextFlag.TextWordWrap),label.text())
            assert needed.height()<=rect.height(),'wrapped label content clipped: '+label.objectName()
            assert all(label.fontMetrics().horizontalAdvance(word)<=rect.width() for word in label.text().split()),'label token clipped'
            return {'name':label.objectName(),'available':[rect.width(),rect.height()],'text_bounds':[needed.width(),needed.height()],'font_height':label.fontMetrics().height(),'text':label.text()}
        def capture(name):
            bounds=[reading(x) for x in (w.pool_detail,w.exchange_summary,w.pool_policy)]
            focus(w.exchange if w.exchange.isEnabled() else w.pages[2].heading);option=QStyleOptionComboBox();w.pool_outgoing.initStyleOption(option)
            combo=w.pool_outgoing.style().subControlRect(QStyle.ComplexControl.CC_ComboBox,option,QStyle.SubControl.SC_ComboBoxEditField,w.pool_outgoing)
            if w.pool_outgoing.currentIndex()>=0:assert w.pool_outgoing.fontMetrics().horizontalAdvance(w.pool_outgoing.currentText())<=combo.width(),'outgoing identity clipped'
            assert w.pages[2].footer.geometry().top()>=w.pages[2].viewport().geometry().bottom(),'pool footer overlaps scrolling content'
            assert w.exchange.visibleRegion().boundingRect().height()>=w.exchange.height(),'focused action clipped'
            button=QStyleOptionButton();w.exchange.initStyleOption(button);content=w.exchange.style().subElementRect(QStyle.SubElement.SE_PushButtonContents,button,w.exchange)
            assert w.exchange.fontMetrics().horizontalAdvance(w.exchange.text())<=content.width() and w.exchange.fontMetrics().height()<=content.height(),'exchange caption clipped'
            w.pages[2].ensureWidgetVisible(w.exchange_summary);app.processEvents()
            for text in (w.pool_detail,w.exchange_summary,w.pool_policy):assert text.visibleRegion().boundingRect().height()>=text.height(),'selected detail/summary/reason not fully visible together'
            filename=name+'.png';w.grab().save(str(out/filename));report['captures'].append({'file':filename,'sha256':digest(out/filename),'size':[w.width(),w.height()],'ratio':w.devicePixelRatioF(),'reading':bounds,'focused_action':w.exchange.hasFocus(),'outgoing_text_width':w.pool_outgoing.fontMetrics().horizontalAdvance(w.pool_outgoing.currentText()),'outgoing_reading_width':combo.width()})
        w.navigate(2);app.processEvents();rows();before=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft())
        # [designed] Full-ID selector changes current row only, never the XI draft.
        key(w.pool_outgoing,Qt.Key.Key_Home);assert w.pool_outgoing.currentData()==261 and w.table.currentRow()==0
        key(w.pool_outgoing,Qt.Key.Key_Down);assert w.table.item(w.table.currentRow(),0).data(Qt.ItemDataRole.UserRole)==w.pool_outgoing.currentData()
        focus(w.table);QTest.keyClick(w.table,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier);app.processEvents();assert w.pool_outgoing.currentData()==261,'table-to-outgoing synchronization failed';stable(before,'outgoing selection',draft)
        reserve(2561);assert 'ID 261' in w.exchange_summary.text() and 'ID 2561' in w.exchange_summary.text()
        target=next(x for x in campaign_pool.view(m.state,m.goaldat)['reserves'] if x['id']==2561)
        outgoing=next(x for x in campaign_pool.view(m.state,m.goaldat)['squad'] if x['id']==261)
        assert all(str(outgoing[k]) in w.exchange_summary.text() for k in ('id','name','ability','energy','confidence','position_group')),'outgoing summary missing raw field'
        search(target['name'].swapcase());position(target['position']);rows();reserve(2561);capture('filtered')
        other=next(row for row in campaign_pool.view(m.state,m.goaldat)['reserves'] if row['id']!=2561 and row['name'].casefold() not in target['name'].casefold() and row['position']==target['position'])
        search(other['name']);rows();assert w.reserves.rowCount()>0 and all(int(w.reserves.item(i,0).text())!=2561 for i in range(w.reserves.rowCount())),'hidden-selection fixture did not retain other visible rows'
        assert w.reserves.currentRow()==-1 and 'No incoming' in w.pool_detail.text(),'hidden incoming selection not cleared'
        before=copy.deepcopy(m.state);w.exchange_selected();stable(before,'hidden selection with other visible rows');assert 'Select one' in w.status.text(),'hidden selection exchanged another visible identity'
        capture('hidden-selection-other-visible')
        search('no reserve matches this query');rows();assert w.reserves.currentRow()==-1 and 'No incoming' in w.pool_detail.text(),'hidden incoming selection not cleared'
        capture('empty-filter')
        before=copy.deepcopy(m.state);w.exchange_selected();stable(before,'missing selection');assert 'Select one' in w.status.text(),'existing no-selection callback error absent'
        search('');position(None);rows();reserve(2561)
        assert all(str(target[k]) in w.pool_detail.text() for k in ('id','name','ability','energy','confidence','position_group')),'selected detail missing raw field'
        # [designed: T77/M1] Reading coverage belongs to each supported size, not initial geometry.
        report['table_reading_by_size']=[]
        sizes=((1440,900),(1050,780),(900,700)) if report['ratio']==1 else ((900,640),)
        for width,height in sizes:
            w.resize(width,height);app.processEvents()
            assert (w.width(),w.height())==(width,height),'required reading size did not settle'
            before=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft());rows()
            cells=[];coverage=[];viewport=w.reserves.viewport();page=w.pages[2]
            focus(w.reserves)
            # [designed] Reveal the table through the outer scroll before its contained cell scrolling.
            page.ensureWidgetVisible(w.reserves);app.processEvents()
            for row in range(w.reserves.rowCount()):
                for col in range(w.reserves.columnCount()):
                    item=w.reserves.item(row,col);w.reserves.scrollToItem(item);app.processEvents()
                    rect=w.reserves.visualItemRect(item)
                    assert viewport.rect().intersects(rect),'reserve cell cannot be reached'
                    option=QStyleOptionViewItem();w.reserves.itemDelegate().initStyleOption(option,w.reserves.indexFromItem(item));option.rect=rect
                    text_rect=w.reserves.style().subElementRect(QStyle.SubElement.SE_ItemViewItemText,option,w.reserves)
                    metrics=option.fontMetrics;advance=metrics.horizontalAdvance(item.text());height_px=metrics.height()
                    assert advance<=text_rect.width() and height_px<=text_rect.height(),f'reserve cell text clipped row={row} col={col}'
                    glyph=QRect(text_rect.x(),text_rect.y()+(text_rect.height()-height_px)//2,advance,height_px)
                    assert rect.contains(glyph) and text_rect.contains(glyph),'reserve glyph exceeds cell/text contents'
                    # [designed] Outer scrolling exposes this reading target even when the whole table exceeds the page.
                    target_point=viewport.mapTo(page.widget(),glyph.center())
                    page.ensureVisible(target_point.x(),target_point.y(),glyph.width()//2+2,glyph.height()//2+2);app.processEvents()
                    # [designed] The complete text must be in the actual visible region, including ancestor clipping.
                    assert viewport.visibleRegion().contains(glyph),f'reserve text not fully visible row={row} col={col}'
                    outer=QRect(viewport.mapTo(page.viewport(),glyph.topLeft()),glyph.size())
                    assert page.viewport().rect().contains(outer),'reserve text outside outer scrolling viewport'
                    cells.append({'id':int(w.reserves.item(row,0).text()),'column':col,'text':item.text(),
                                  'cell':rect.getRect(),'text_contents':text_rect.getRect(),'glyph':glyph.getRect(),
                                  'outer_glyph':outer.getRect(),'table_viewport':viewport.rect().getRect(),
                                  'visible_bounds':viewport.visibleRegion().boundingRect().getRect(),'outer_viewport':page.viewport().rect().getRect(),
                                  'font_height':height_px,'font_advance':advance})
                coverage.append(int(w.reserves.item(row,0).text()))
            assert len(cells)==560 and len(coverage)==80 and len(set(coverage))==80,'per-size reading coverage incomplete'
            stable(before,'per-size table reading',draft)
            report['table_reading_by_size'].append({'size':[w.width(),w.height()],'ratio':w.devicePixelRatioF(),
                'ids':coverage,'cells':cells,'pure_state_draft_save_rng':True})
            report['table_reading_coverage']=coverage
            reserve(2561);assert 'ID 2561' in w.exchange_summary.text(),'reading did not restore intended incoming identity'
            capture(f'selected-{width}x{height}')
        # [designed] Long labels are rebuild fixture inputs, never original player-name claims.
        original=m.goaldat.player_names[2561];m.goaldat.player_names[2561]='Rebuild fixture long reserve name demonstrating complete wrapped reading'
        w.refresh_pool();reserve(2561);capture('synthetic-long-name');m.goaldat.player_names[2561]=original;w.refresh_pool();reserve(2561)
        before=copy.deepcopy(m.state);draft=copy.deepcopy(w.draft());focus(w.pool_outgoing);QTest.keyClick(w.pool_outgoing,Qt.Key.Key_Tab);app.processEvents();assert app.focusWidget() is w.search,'pool keyboard traversal differs';stable(before,'Tab traversal',draft)
        w.tactics[0][1].toggle();assert w.draft()!=(m.state.starting_eleven,m.state.captain,m.state.country_tactics)
        before=copy.deepcopy(m.state);dirty=copy.deepcopy(w.draft())
        for index in (0,1,3,2):w.navigate(index);app.processEvents();stable(before,'navigation',dirty)
        expected=copy.deepcopy(m.state);campaign_pool.exchange(expected,261,2561);records=list(m.state.players);seeds=(m.state.rng_seed_7b62,m.state.rng_seed_8336)
        action(w.exchange);assert m.state==expected,'exchange differs from independent full-state oracle'
        assert m.state.players==records and (m.state.rng_seed_7b62,m.state.rng_seed_8336)==seeds,'exchange changed player bytes/RNG'
        assert m.state.captain==2561 and 2561 in m.state.starting_eleven and w.draft()==(m.state.starting_eleven,m.state.captain,m.state.country_tactics),'XI/captain repair or draft discard failed'
        assert len(set(m.state.managed_squad+m.state.campaign.reserve_ids))==100 and len(m.state.managed_squad)==20 and len(m.state.campaign.reserve_ids)==80
        assert save.read_bytes()==saved,'exchange saved implicitly'
        action(w.save);saved=save.read_bytes();expected=copy.deepcopy(m.state)
        with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('resume regenerated records')):action(w.resume)
        assert m.state==expected,'save/resume changed membership/state';report['steps'].append('Keyboard filters/full-ID selection, all raw rows, hidden-selection clear,261→2561 full-state exchange, repair/discard and save/resume')
        def refused(name,reason):
            before=copy.deepcopy(m.state);old=save.read_bytes();w.navigate(2);app.processEvents();assert reason.casefold() in w.pool_policy.text().casefold(),'adjacent context reason absent: '+name
            w.exchange_selected();assert m.state==before and save.read_bytes()==old,name+' callback bypassed guard';clean();capture(name)
        # [designed] Existing unavailable callback stays enabled and validates atomically.
        record=m.state.players[2562];rec=bytearray(record);rec[14]=0;rec[16]=0x80;m.state.players[2562]=bytes(rec);w.refresh();key(w.pool_outgoing,Qt.Key.Key_Home);reserve(2562)
        before=copy.deepcopy(m.state);action(w.exchange);assert m.state==before and 'unavailable' in w.status.text(),'unavailable exchange not refused';assert all(reason in w.pool_detail.text() for reason in next(r for r in campaign_pool.view(m.state,m.goaldat)['reserves'] if r['id']==2562)['availability']['reasons']);refused('unavailable','provisional');m.state.players[2562]=record
        active=copy.deepcopy(m.state);m.state=play(m.state,m.template_bytes);w.refresh();key(w.pool_outgoing,Qt.Key.Key_Home);reserve(2562);assert not w.exchange.isEnabled();refused('closed-window','pending managed friendly');m.state=copy.deepcopy(active);w.refresh()
        # [designed] Pending ownership is checked independently of controller.busy.
        m.match_pending=True;w.set_busy(True);assert not w.exchange.isEnabled() and not w.jobs.busy;refused('pending-busy','Finish or cancel');m.match_pending=False;w.set_busy(False)
        before=copy.deepcopy(m.state);private=copy.deepcopy(w.draft());focus(w.country);QTest.keyClick(w.country,Qt.Key.Key_Down);app.processEvents();assert w.preview is not None and not w.exchange.isEnabled();refused('preview','Preview');stable(before,'preview',None)
        focus(w.country);QTest.keyClick(w.country,Qt.Key.Key_Up);app.processEvents();assert w.preview is None and w.draft()==private,'preview return lost private draft'
        m.new_friendly(14);w.refresh();assert not w.exchange.isEnabled();refused('standalone','standalone');assert w.reserves.rowCount()==0 and 'No incoming' in w.pool_detail.text()
        report['steps'].append('No-selection/unavailable existing callback errors; closed-window, pending ownership without controller.busy, preview and standalone refusals; visible reasons')
        report['result']='PASS'
    except BaseException as exc:report.update(result='FAIL',failure=str(exc),traceback=traceback.format_exc());raise
    finally:
        if w is not None:
            w.close();report['owned_processes_closed']=all(controller.process is None for controller in (w.jobs,w.competitive,w.watched));assert report['owned_processes_closed'],'owned controller process remains';w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        app.quit();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        sys.excepthook=previous;report['callback_exceptions']=callbacks;report['clean_widgets']=not bool(app.topLevelWidgets());report['sources_after']={x:digest(ROOT/x) for x in report['sources']};report['sources_unchanged']=report['sources']==report['sources_after']
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');assert report['clean_widgets'],'owned widgets remain';assert report['sources_unchanged'],'source changed during scenario';clean()
    print('PASS pool: independent full-ID exchange/raw records/RNG, pure filters, selection, context guards, repair/discard/save and reading bounds; '+str(out))


def negative_controls(args):
    out=fresh(args.evidence_dir);paths=[ROOT/'goal2/desktop/pool_page.py',ROOT/'goal2/desktop/window.py'];saved={p:p.read_bytes() for p in paths}
    receipt={'tag':'[designed: T77]','before':{str(p.relative_to(ROOT)):digest(p) for p in paths},'cases':[]}
    command=[sys.executable,'-B',str(ROOT/'tools/desktop-ui/redesign.py'),'--scenario','pool','--template',args.template,'--data',args.data,'--single-scale']
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','QT_SCALE_FACTOR':'1'}
    def run(name,cmd,expected):
        result=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=120);(out/(name+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode!=0 and 'AssertionError' in result.stderr and expected in result.stderr,name+' missed intended behavioral assertion: '+result.stderr
        receipt['cases'].append({'name':name,'command':cmd,'returncode':result.returncode,'expected':expected})
    try:
        # [designed] Restore the accepted pre-feature pair, preserving a real behavioral absent-hierarchy oracle.
        for p in paths:p.write_bytes(subprocess.check_output(['git','show','e337d56172373e0786b571c9b379e86ebcf63921:'+str(p.relative_to(ROOT))],cwd=ROOT))
        run('baseline',command+['--evidence-dir',str(out/'baseline')],'focused incoming detail/exchange summary absent')
        for p,raw in saved.items():p.write_bytes(raw)
        p=paths[1];source=p.read_text();old='    def refresh_pool(self):\n        if self._refreshing:return';assert source.count(old)==1
        p.write_text(source.replace(old,old+"\n        if self.search.text():self.model.state.rng_seed_7b62+=1"))
        run('filter-state',command+['--evidence-dir',str(out/'filter-state')],'search/filter changed state/RNG/membership')
        run('shared-retained-filter-state',[sys.executable,'-B','tools/desktop-ui/acceptance.py','--scenario','campaign-pool','--template',args.template,'--data',args.data],'AssertionError')
    finally:
        for p,raw in saved.items():p.write_bytes(raw)
        receipt['after']={str(p.relative_to(ROOT)):digest(p) for p in paths};receipt['restored']=all(p.read_bytes()==raw for p,raw in saved.items());(out/'negative-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['restored'];print('PASS pool negative controls: baseline hierarchy and shared filter/RNG corruption; saved bytes restored')
