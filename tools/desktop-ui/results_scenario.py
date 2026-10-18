"""[designed: T78] Reproducible saved-result presentation acceptance, with no match replay.
Private inputs are staged by main from generated saves and verified against inventory.
Use --prepare-results-inputs with --results-input-dir pointing at a staged inventory
folder to validate the ignored inputs before a fresh acceptance process.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs(args):
    """[designed] Hash verification and real save decoding are required, never a mock profile."""
    from goal2.desktop.model import DesktopModel
    folder=Path(args.results_input_dir);inventory=json.loads((folder/'inventory.json').read_text())
    assert {r['file'] for r in inventory}=={'competitive-regulation.g2save','original-friendly-kit1.g2save','competitive-shootout.g2save'}
    models=[]
    for row in inventory:
        path=folder/row['file'];assert digest(path)==row['sha256'],'private fixture hash differs'
        model=DesktopModel.from_save(path,args.data)
        assert model.state.last_match['teams']==row['teams'] and model.state.last_match['score']==row['score']
        models.append((Path(row['file']).stem,model,row['sha256']))
    return models


def prepare(args):
    """[designed] Reproduce ignored input staging from main's verified generated-save bundle."""
    if args.results_source_dir:
        import shutil
        source=Path(args.results_source_dir);target=Path(args.results_input_dir)
        target.mkdir(parents=True,exist_ok=True)
        for name in ('inventory.json','competitive-regulation.g2save','original-friendly-kit1.g2save','competitive-shootout.g2save'):
            destination=target/name
            if destination.exists():assert digest(destination)==digest(source/name),'refuse replacing a different private input'
            else:shutil.copyfile(source/name,destination)
    inputs(args)
    print('PASS results input staging, hashes and real save-loader validation')


def results(args):
    from PySide6.QtCore import Qt,QPoint,qVersion,QCoreApplication,QEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.desktop.fixtures_page import snapshot
    from goal2.desktop.worker import play
    from goal2.game.session_save import encode
    from goal2.game.watched_schema import resolution,watched
    from goal2.game.campaign_schedule import start_opening_campaign
    app=QApplication.instance() or QApplication([])
    out=Path(args.evidence_dir)
    if out.exists() and any(out.iterdir()):
        number=2
        while (out/f'run-{number:02}').exists():number+=1
        out=out/f'run-{number:02}'
    out.mkdir(parents=True,exist_ok=True)
    report={'tag':'[designed: T78]','platform':platform.platform(),'python':sys.version,'qt':qVersion(),'qpa':app.platformName(),
        'scale':os.environ.get('QT_SCALE_FACTOR','1'),'sources':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'goal2/desktop').glob('*.py'))},
        'scenario_sha256':digest(__file__),'resources':{'template':digest(args.template),'data':digest(args.data)},'cases':[],'captures':[]}
    try:
        with tempfile.TemporaryDirectory(prefix='goal2-t78-') as temporary:
            root=Path(temporary)
            loaded=inputs(args)
            empty=DesktopModel.open(args.template,args.data,root/'empty.g2save',country=4)
            quick=DesktopModel.open(args.template,args.data,root/'quick.g2save',country=61)
            quick.confirm(list(quick.state.starting_eleven),quick.state.starting_eleven[0],quick.state.country_tactics)
            quick.state=play(quick.state,quick.template_bytes);quick.save(quick.save_path);quick.resume(quick.save_path)
            table=DesktopModel.open(args.template,args.data,root/'table.g2save',country=4)
            table.state,_=start_opening_campaign(table.goaldat,table.template_bytes,managed_country=4,start_year=1992,seed_7b62=4660,seed_8336=33590)
            standalone=DesktopModel.open(args.template,args.data,root/'standalone.g2save',country=4);standalone.new_friendly(4)
            cases=[('empty',empty,None),('quick-long-country',quick,digest(quick.save_path)),('opening-table-1992',table,None),('standalone',standalone,None)]+loaded
            for name,model,source_hash in cases:
                # [designed] Never write the staged save; any action/save path belongs to this scenario.
                model.save_path=root/(name+'.g2save');model.save(model.save_path)
                before=encode(model.state,model.template_bytes);saved=model.save_path.read_bytes();rng=(model.state.rng_seed_7b62,model.state.rng_seed_8336)
                w=ManagementWindow(model);w.resize(900,640);w.show();w.raise_();w.activateWindow();QTest.qWait(100)
                def active(target=None):
                    w.raise_();w.activateWindow();assert QTest.qWaitForWindowActive(w,2000),'window activation failed'
                    if target is not None:
                        target.setFocus();app.processEvents();QTest.qWait(50)
                        assert app.focusWidget() is target,'native input focus differs'
                active();assert w.devicePixelRatioF()==float(report['scale']),'actual scale differs'
                assert hasattr(w,'scoreboard'),'named scoreboard hierarchy absent'
                active(w.navigation[3]);QTest.keyClick(w.navigation[3],Qt.Key.Key_Space);app.processEvents()
                assert w.page_stack.currentIndex()==3,'keyboard fixtures navigation failed'
                match=model.state.last_match
                if match:
                    a,b=match['teams'];x,y=match['score']
                    expected=f'{model.goaldat.country_names[a]} {x} — {y} {model.goaldat.country_names[b]}'
                    assert w.scoreboard.text()==expected,'scoreboard A/B or ordinary goals differ'
                    assert ('Original engine' if watched(match) else 'Quick simulation (rebuild setup)') in w.result.text(),'provenance differs'
                    for goal in match['goals']:
                        assert f"{goal['minute']}′ {model.goaldat.player_names[goal['player']]} ({model.goaldat.country_names[match['teams'][goal['team']]]})" in w.result.text(),'goal name/minute/team differs'
                    if watched(match) and match['schema']==2:
                        stage=resolution(match['original'])
                        for key,label in (('regulation','Regulation'),('extra_time','Extra time'),('penalties','Penalties')):
                            score=stage[key]
                            if score is not None:assert f'{label}: {score[0]} — {score[1]}' in w.result_stages.text(),'stage differs'
                        winner=stage['winner'];assert ('Draw' if winner==2 else 'Winner: '+model.goaldat.country_names[match['teams'][winner]]) in w.result_stages.text(),'winner differs'
                else:assert w.scoreboard.text()=='No match played','empty result differs'
                backend=model.competition_table()
                if backend:
                    for row in backend['rows']:
                        assert f"{row['rank']}. {row['name']}   P {row['played']}   GF {row['goals_for']}   GA {row['goals_against']}   GD {row['goal_difference']}   Pts {row['points']}" in w.fixture_table.text(),'standings snapshot differs'
                # [designed] Reach enabled Play and standings by Tab, and reverse with Shift-Tab.
                w.pages[3].ensureWidgetVisible(w.standings);app.processEvents();active(w.standings)
                QTest.keyClick(w.standings,Qt.Key.Key_Tab);app.processEvents()
                expected=w.play if w.play.isEnabled() else w.substitute if w.substitute.isEnabled() else None
                if w.play.isEnabled():
                    assert app.focusWidget() is w.play,'Tab did not reach Play'
                    QTest.keyClick(w.play,Qt.Key.Key_Backtab);assert app.focusWidget() is w.standings,'Shift-Tab did not return to standings'
                active(w.standings);QTest.keyClick(w.standings,Qt.Key.Key_Space);app.processEvents()
                if backend:
                    dialog=w.standings_dialog;assert dialog is not None
                    for i,row in enumerate(backend['rows']):
                        assert dialog.table.item(i,1).text()==row['name']
                        assert dialog.table.item(i,9).text()==str(row['points'])
                    dialog.close();w.standings_dialog=None;active()
                # [designed] Busy direct callbacks use retained guards without starting workers.
                model.match_pending=True;w.set_busy(True);w.start_match();assert 'Finish or cancel' in w.status.text()
                w.start_watched();assert 'Finish or cancel' in w.status.text();model.match_pending=False;w.set_busy(False)
                assert not w.jobs.busy and not w.competitive.busy
                w.navigate(0);active(w.country);other=1 if model.state.managed_country!=1 else 2
                w.country.setCurrentIndex(w.country.findData(other));app.processEvents();w.navigate(3);app.processEvents()
                assert w.preview is not None and w.scoreboard.text()=='No match played','active result leaked into preview'
                assert w.fixture_next.text()==w.display_model.view()['fixture'].rsplit(' (',1)[0],'preview fixture differs'
                w.country.setCurrentIndex(w.country.findData(model.state.managed_country));app.processEvents();w.navigate(3)
                # [designed] Capture full wrapped panels after scrolling, at each required viewport.
                sizes=[(1440,900),(1050,780),(900,700)] if report['scale']=='1' else [(900,640)]
                for width,height in sizes:
                    w.resize(width,height);app.processEvents()
                    for label in (w.fixture_next,w.scoreboard,w.result_stages,w.result,w.fixture_table):
                        panel=label.parentWidget();page=w.pages[3];page.ensureWidgetVisible(panel,0,0);app.processEvents()
                        origin=panel.mapTo(page.viewport(),QPoint(0,0))
                        assert origin.x()>=0 and origin.x()+panel.width()<=page.viewport().width(),'panel clipped horizontally'
                        assert origin.y()>=0 and origin.y()+panel.height()<=page.viewport().height(),'panel not completely reachable'
                        assert label.height()>=label.heightForWidth(label.width()),'wrapped result line clipped'
                        filename=f'{name}-{width}x{height}-{label.objectName()}.png';assert w.grab().save(str(out/filename))
                        report['captures'].append({'file':filename,'sha256':digest(out/filename),'panel':label.objectName(),'geometry':[origin.x(),origin.y(),panel.width(),panel.height()]})
                assert encode(model.state,model.template_bytes)==before and model.save_path.read_bytes()==saved and rng==(model.state.rng_seed_7b62,model.state.rng_seed_8336),'painting/navigation changed encoded state/RNG/save'
                # [designed] Copied malformed data visits the pure boundary; active state stays valid.
                bad=copy.copy(model);bad.state=copy.deepcopy(model.state);bad.state.last_match={'teams':[1,1],'score':[0,0],'goals':[]}
                assert snapshot(bad)['error'] and snapshot(bad)['score']=='Result unavailable','malformed result was not refused'
                if name=='empty':
                    damaged=snapshot(bad);w.scoreboard.setText(damaged['score']);w.result_stages.setText(damaged['stages']);w.result.setText(damaged['detail'])
                    page=w.pages[3];page.ensureWidgetVisible(w.scoreboard.parentWidget(),0,0);app.processEvents()
                    filename='malformed-copied-result.png';assert w.grab().save(str(out/filename))
                    report['captures'].append({'file':filename,'sha256':digest(out/filename),'context':'malformed pure copied input; save loading remains strict'})
                    w.refresh();w.navigate(3)
                report['cases'].append({'name':name,'source_save_sha256':source_hash,'state_sha256':hashlib.sha256(before).hexdigest(),'score':w.scoreboard.text(),'stages':w.result_stages.text(),'standings':backend,'pure':True,'busy_refused':True,'preview_isolated':True})
                w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
            # [designed] Unsupported callbacks must refuse using real job capability guards.
            from dataclasses import replace
            unsupported=empty;unsupported.confirm(list(unsupported.state.starting_eleven),unsupported.state.starting_eleven[0],unsupported.state.country_tactics);f=unsupported.state.campaign.next_fixture
            unsupported.state.campaign.fixtures=tuple(replace(x,kind=255) if x.fixture_id==f.fixture_id else x for x in unsupported.state.campaign.fixtures)
            w=ManagementWindow(unsupported);w.show();app.processEvents();before=copy.deepcopy(unsupported.state)
            w.start_match();assert 'No supported pending competitive fixture' in w.status.text(),'unsupported Play guard differs'
            w.start_watched();assert 'Watch supports scheduled friendlies only' in w.status.text(),'unsupported Watch guard differs'
            assert not w.play.isEnabled() and not w.watch.isEnabled() and unsupported.state==before
            report['unsupported_callbacks_refused']=True;w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
            report['result']='PASS'
    except Exception as exc:
        report['result']='FAIL';report['exception']=type(exc).__name__;report['failure']=str(exc);raise
    finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS results: validated saved quick/original/competitive stages, A/B/goals, standings, pure navigation/preview, keyboard, busy/unsupported refusal, full-panel captures')


def negative_controls(args):
    """[designed: T78] Exact byte restoration surrounds deliberate presentation defects."""
    out=Path(args.evidence_dir);out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'goal2/desktop/fixtures_page.py';saved=source.read_bytes();window=ROOT/'goal2/desktop/window.py';window_saved=window.read_bytes();receipt={'cases':[]}
    command_base=[sys.executable,'-B',str(ROOT/'tools/desktop-ui/redesign.py'),'--scenario','results','--template',args.template,'--data',args.data,'--results-input-dir',args.results_input_dir,'--single-scale']
    try:
        for path in (source,window):path.write_bytes(subprocess.check_output(['git','show','f1697ef628508ac19130299194d751990ca7fa9e:'+str(path.relative_to(ROOT))],cwd=ROOT))
        command=command_base+['--evidence-dir',str(out/'baseline')]
        result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=240)
        (out/'baseline.log').write_text(result.stdout+result.stderr)
        assert result.returncode!=0 and 'AssertionError: named scoreboard hierarchy absent' in result.stderr,'baseline failed outside intended oracle: '+result.stderr
        receipt['cases'].append({'name':'baseline','expected':'named scoreboard hierarchy absent','returncode':result.returncode,'command':command})
    finally:source.write_bytes(saved);window.write_bytes(window_saved)
    replacements=[('swap-ab',"a,b=match['teams'];x,y=match['score']","b,a=match['teams'];x,y=match['score']",'scoreboard A/B or ordinary goals differ'),
        ('sum-kicks',"a,b=match['teams'];x,y=match['score']","a,b=match['teams'];x,y=match['score'];x,y=([x+match['original']['shootout']['score'][0],y+match['original']['shootout']['score'][1]] if match.get('original',{}).get('shootout') else [x,y])",'scoreboard A/B or ordinary goals differ'),
        ('preview-leak','data=snapshot(display,view)','data=snapshot(self.model,view)','active result leaked into preview')]
    try:
        for name,old,new,expected in replacements:
            assert saved.decode().count(old)==1,'mutation site differs'
            source.write_bytes(saved.decode().replace(old,new).encode())
            command=[sys.executable,'-B',str(ROOT/'tools/desktop-ui/redesign.py'),'--scenario','results','--template',args.template,'--data',args.data,'--results-input-dir',args.results_input_dir,'--single-scale','--evidence-dir',str(out/name)]
            result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=240)
            (out/(name+'.log')).write_text(result.stdout+result.stderr)
            assert result.returncode!=0 and 'AssertionError: '+expected in result.stderr,'mutation failed outside intended oracle: '+result.stderr
            receipt['cases'].append({'name':name,'expected':expected,'returncode':result.returncode,'command':command})
            source.write_bytes(saved)
    finally:
        source.write_bytes(saved);window.write_bytes(window_saved);receipt['restored']=source.read_bytes()==saved;(out/'negative-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS results negative controls: swapped A/B, summed penalty kicks, preview leakage; exact source restored')
