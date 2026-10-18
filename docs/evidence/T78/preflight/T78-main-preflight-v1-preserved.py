"""[designed: T78] Main planning-only result mock over genuine validated saves."""
from pathlib import Path
import argparse,copy,hashlib,json,os,platform,sys,tempfile
from dataclasses import replace
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['baseline','mock','wrong-order','penalties-added','wrong-preview'],required=True);p.add_argument('--output',required=True);a=p.parse_args()
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from PySide6.QtCore import Qt,QCoreApplication,QEvent,qVersion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QLabel
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.desktop.worker import play
from goal2.game.session_save import encode
from goal2.game.watched_schema import watched,resolution,validate_result,COMPETITIVE_SCHEMA
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=Path(a.output);out.mkdir(parents=True,exist_ok=False);sources={str(x.relative_to(ROOT)):sha(x)for x in sorted((ROOT/'goal2/desktop').glob('*.py'))}
report={'tag':'[designed: T78] planning-only runtime mock','mode':a.mode,'platform':platform.platform(),'qt':qVersion(),'sources':sources,'probe_sha256':sha(__file__),'resources':{n:sha(ROOT/'.cache'/n)for n in ('e010-r0008-halftime.sav','GOAL.DAT')},'cases':[],'captures':[]}
app=QApplication([]);report['qpa']=app.platformName()
def snapshot(display):
 try:
  v=display.view();text=display.result_text();match=display.state.last_match;table=display.competition_table()
  value={'fixture':v['fixture']or'No scheduled fixture','board':'No result yet','stages':'','goals':'','standings':'Competition table unavailable'if table is None else'\n'.join(str(row['rank'])+' '+row['name']+' '+str(row['played'])+' '+str(row['points'])for row in table['rows']),'text':text,'error':False}
  if match is not None:
   teams=match['teams'];scores=list(match['score']);original=match.get('original');competitive=watched(match)and match.get('schema')==COMPETITIVE_SCHEMA
   if watched(match):validate_result(original,competitive=competitive)
   stages=resolution(original)if competitive else None
   if a.mode=='penalties-added'and stages and stages['penalties']:scores=[x+y for x,y in zip(scores,stages['penalties'])]
   names=[display.goaldat.country_names[x]for x in teams]
   if a.mode=='wrong-order':names.reverse()
   value['board']=names[0]+' '+str(scores[0])+' — '+str(scores[1])+' '+names[1]
   value['stages']=('Original engine'if watched(match)else'Quick simulation (rebuild setup)')
   if stages:
    for key,label in [('regulation','Regulation'),('extra_time','Extra time'),('penalties','Penalties')]:
     if stages[key]is not None:value['stages']+='\n'+label+': '+str(stages[key][0])+' — '+str(stages[key][1])
    value['stages']+='\n'+('Draw'if stages['winner']==2 else'Winner: '+names[stages['winner']])
   value['goals']='\n'.join(str(g['minute'])+'′ '+display.goaldat.player_names[g['player']]+' ('+display.goaldat.country_names[teams[g['team']]]+')'for g in match['goals'])or'No goals'
  return value
 except (ValueError,IndexError,KeyError,TypeError):return {'error':True,'board':'Result unavailable: invalid saved result'}
try:
 with tempfile.TemporaryDirectory(prefix='T78-main-mock-')as folder:
  save=Path(folder)/'owned.g2save';m=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',save,country=61);m.confirm(list(m.state.starting_eleven),m.state.starting_eleven[0],m.state.country_tactics)
  cases=[('empty',copy.deepcopy(m.state),m.template_bytes)];quick=play(m.state,m.template_bytes);cases.append(('quick-long-country',quick,m.template_bytes))
  from goal2.game.campaign_schedule import start_opening_campaign
  standings_state,_=start_opening_campaign(m.goaldat,m.template_bytes,managed_country=4,start_year=1992,seed_7b62=4660,seed_8336=33590);cases.append(('standings-1992',standings_state,m.template_bytes))
  inputs=ROOT/'.cache/T78-presentation-inputs-03';inventory=json.loads((inputs/'inventory.json').read_text());report['input_saves']=[{k:r[k]for k in ('file','sha256')}for r in inventory]
  for row in inventory:
   path=inputs/row['file'];assert sha(path)==row['sha256'];loaded=DesktopModel.from_save(path,ROOT/'.cache/GOAL.DAT');cases.append((row['file'],loaded.state,loaded.template_bytes))
  for name,state,template in cases:
   m=DesktopModel(m.goaldat,template,save);m.state=copy.deepcopy(state);m.save(save);saved=save.read_bytes();before=encode(m.state,template);w=ManagementWindow(m)
   if a.mode!='baseline':
    labels={}
    for key,obj in [('fixture','fixtureCard'),('board','scoreboard'),('stages','resultStages'),('goals','resultGoals'),('standings','standingsSnapshot')]:
     label=QLabel();label.setObjectName(obj);label.setWordWrap(True);labels[key]=label;w.pages[3].content.insertWidget(1,label)
    original=w.refresh
    def refresh(*args,**kwargs):
     original(*args,**kwargs);display=m if a.mode=='wrong-preview'else w.display_model;value=snapshot(display)
     for key,label in labels.items():label.setText(value[key])
    w.refresh=refresh;w.refresh()
   w.show();w.raise_();w.activateWindow();QTest.qWait(100);report['ratio']=w.devicePixelRatioF()
   assert w.findChild(QLabel,'scoreboard')is not None,'named scoreboard/stage hierarchy absent on baseline'
   w.navigate(3);app.processEvents();match=m.state.last_match
   if match is None:assert labels['board'].text()=='No result yet'
   else:
    names=[m.goaldat.country_names[t]for t in match['teams']];score=match['score'];expected=names[0]+' '+str(score[0])+' — '+str(score[1])+' '+names[1]
    assert labels['board'].text()==expected,'scoreboard changed A/B order or summed penalty kicks into goals'
    assert ('Original engine'if watched(match)else'Quick simulation')in labels['stages'].text()
    for g in match['goals']:assert m.goaldat.player_names[g['player']]in labels['goals'].text()
    if watched(match)and match.get('schema')==COMPETITIVE_SCHEMA:
     stages=resolution(match['original'])
     for key,label in [('regulation','Regulation'),('extra_time','Extra time'),('penalties','Penalties')]:
      if stages[key]is not None:assert label+': '+str(stages[key][0])+' — '+str(stages[key][1])in labels['stages'].text()
   assert labels['fixture'].text()==(m.view()['fixture']or'No scheduled fixture')
   table=m.competition_table()
   if table:
    for row in table['rows']:assert row['name']in labels['standings'].text()and str(row['points'])in labels['standings'].text()
   for widget in (w.play,w.standings):
    w.pages[3].ensureWidgetVisible(widget);widget.setFocus();app.processEvents();assert app.focusWidget()is widget,'action not keyboard reachable'
   assert encode(m.state,template)==before and save.read_bytes()==saved,'painting/navigation changed state/RNG/save'
   sizes=[(900,640)]if report['ratio']>1 else[(1440,900),(1050,780),(900,700)]
   for size in sizes:
    w.resize(*size);app.processEvents();w.pages[3].ensureWidgetVisible(labels['board']);app.processEvents();fname=name.replace('.g2save','')+'-'+str(size[0])+'x'+str(size[1])+'.png';assert w.grab().save(str(out/fname));report['captures'].append({'path':fname,'sha256':sha(out/fname)})
   m.match_pending=True;w.set_busy(True);assert not w.play.isEnabled()and not w.standings.isEnabled();w.start_match();w.show_standings();assert encode(m.state,template)==before;m.match_pending=False;w.set_busy(False)
   # A fresh independent other-country preview must never inherit the active result.
   preview_number=5 if m.state.managed_country!=5 else 13
   w.country.setCurrentIndex(w.country.findData(preview_number));app.processEvents();assert w.preview is not None
   assert labels['board'].text()=='No result yet','preview leaked active result'
   assert labels['fixture'].text()==w.preview.view()['fixture']
   assert encode(m.state,template)==before and save.read_bytes()==saved
   if match:
    broken=DesktopModel(m.goaldat,template,save);broken.state=copy.deepcopy(state);broken.state.last_match['score']=['bad',0];previous=copy.deepcopy(broken.state);bad=snapshot(broken);assert bad['error']and'invalid saved result'in bad['board'];assert broken.state==previous
   report['cases'].append({'name':name,'source_order_and_score':True,'all_stages':True,'pure_display_and_rng':True,'preview_isolated':True,'busy_refused':True,'standings':table is not None,'malformed_adapter_refused':bool(match)})
   w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
  report['result']='PASS';app.shutdown()
except BaseException as e:report['failure']=str(e);report['exception']=type(e).__name__;raise
finally:
 assert sources=={name:sha(ROOT/name)for name in sources},'product source changed during mock';report['source_unchanged']=True;(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS T78 planning-only mock:',a.mode,'ratio',report['ratio'],'cases',len(report['cases']))
